from __future__ import annotations

import time
from code.database import engine
from code.hw9_config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    REDIS_URL,
    SEMANTIC_CACHE_INDEX,
    SEMANTIC_CACHE_PREFIX,
)
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import numpy as np
from redis import Redis
from redis.commands.search.query import Query
from redis.exceptions import ResponseError
from sentence_transformers import (
    SentenceTransformer,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine


class SemanticResponseCache:
    """Redis vector cache for agent responses."""

    def __init__(
        self,
        database_engine: Engine = engine,
        redis_url: str = REDIS_URL,
        threshold: float = (
            DEFAULT_SIMILARITY_THRESHOLD
        ),
    ) -> None:
        self.engine = database_engine
        self.threshold = threshold

        self.redis_client = Redis.from_url(
            redis_url,
            decode_responses=False,
        )

        self.redis_client.ping()

        self.embedding_model = (
            SentenceTransformer(
                EMBEDDING_MODEL
            )
        )

        self.ensure_vector_index()

    def ensure_vector_index(self) -> None:
        """Create the Redis HNSW index."""

        try:
            self.redis_client.execute_command(
                "FT.INFO",
                SEMANTIC_CACHE_INDEX,
            )
            return
        except ResponseError:
            pass

        self.redis_client.execute_command(
            "FT.CREATE",
            SEMANTIC_CACHE_INDEX,
            "ON",
            "HASH",
            "PREFIX",
            "1",
            SEMANTIC_CACHE_PREFIX,
            "SCHEMA",
            "query",
            "TEXT",
            "answer",
            "TEXT",
            "data_version",
            "TAG",
            "created_at",
            "TEXT",
            "embedding",
            "VECTOR",
            "HNSW",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            str(EMBEDDING_DIMENSIONS),
            "DISTANCE_METRIC",
            "COSINE",
        )

    def embed(
        self,
        query: str,
    ) -> np.ndarray:
        """Return one normalized float32 vector."""

        vector = self.embedding_model.encode(
            query,
            normalize_embeddings=True,
        )

        return np.asarray(
            vector,
            dtype=np.float32,
        )

    def current_data_version(self) -> str:
        """Return a marker for relational data."""

        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS row_count,
                        COALESCE(
                            MAX(updated_at),
                            'none'
                        ) AS latest_update
                    FROM clinical_trials
                    """
                )
            ).mappings().one()

        return (
            f"{row['row_count']}:"
            f"{row['latest_update']}"
        )

    @staticmethod
    def decode_value(
        value: Any,
    ) -> str:
        """Convert Redis values into strings."""

        if isinstance(value, bytes):
            return value.decode("utf-8")

        return str(value)

    def search(
        self,
        query: str,
    ) -> dict[str, Any] | None:
        """Return the nearest cached response."""

        vector = self.embed(query)

        search_query = (
            Query(
                "*=>[KNN 1 "
                "@embedding $query_vector "
                "AS vector_distance]"
            )
            .sort_by("vector_distance")
            .return_fields(
                "query",
                "answer",
                "data_version",
                "created_at",
                "vector_distance",
            )
            .dialect(2)
        )

        try:
            result = (
                self.redis_client.ft(
                    SEMANTIC_CACHE_INDEX
                ).search(
                    search_query,
                    query_params={
                        "query_vector": (
                            vector.tobytes()
                        ),
                    },
                )
            )
        except ResponseError as error:
            if "No results found" in str(error):
                return None
            raise

        if not result.docs:
            return None

        document = result.docs[0]

        distance = float(
            self.decode_value(
                document.vector_distance
            )
        )

        similarity = 1.0 - distance

        return {
            "cache_key": document.id,
            "cached_query": self.decode_value(
                document.query
            ),
            "answer": self.decode_value(
                document.answer
            ),
            "data_version": self.decode_value(
                document.data_version
            ),
            "created_at": self.decode_value(
                document.created_at
            ),
            "similarity": similarity,
        }

    def store(
        self,
        query: str,
        answer: str,
        data_version: str,
    ) -> str:
        """Store a query, vector and answer."""

        cache_key = (
            SEMANTIC_CACHE_PREFIX
            + str(uuid4())
        )

        vector = self.embed(query)

        self.redis_client.hset(
            cache_key,
            mapping={
                "query": query,
                "answer": answer,
                "data_version": data_version,
                "created_at": (
                    datetime.now(UTC).isoformat()
                ),
                "embedding": vector.tobytes(),
            },
        )

        return cache_key

    def answer(
        self,
        query: str,
        answer_provider: Any,
    ) -> dict[str, Any]:
        """Return cached or newly generated answer."""

        started_at = time.perf_counter()
        match = self.search(query)

        if (
            match is not None
            and match["similarity"]
            >= self.threshold
        ):
            latency_ms = (
                time.perf_counter()
                - started_at
            ) * 1000

            print(
                "CACHE_HIT | "
                f"similarity="
                f"{match['similarity']:.4f}"
            )

            return {
                "query": query,
                "answer": match["answer"],
                "is_cached": True,
                "similarity": round(
                    match["similarity"],
                    6,
                ),
                "latency_ms": round(
                    latency_ms,
                    3,
                ),
                "cached_query": (
                    match["cached_query"]
                ),
                "data_version": (
                    match["data_version"]
                ),
            }

        print("CACHE_MISS | running agent")

        answer = str(
            answer_provider(query)
        )

        data_version = (
            self.current_data_version()
        )

        self.store(
            query,
            answer,
            data_version,
        )

        latency_ms = (
            time.perf_counter()
            - started_at
        ) * 1000

        return {
            "query": query,
            "answer": answer,
            "is_cached": False,
            "similarity": (
                round(
                    match["similarity"],
                    6,
                )
                if match is not None
                else None
            ),
            "latency_ms": round(
                latency_ms,
                3,
            ),
            "cached_query": (
                match["cached_query"]
                if match is not None
                else None
            ),
            "data_version": data_version,
        }

    def clear_semantic_cache(self) -> int:
        """Delete semantic-cache hashes only."""

        deleted = 0

        for key in self.redis_client.scan_iter(
            match=SEMANTIC_CACHE_PREFIX + "*"
        ):
            if self.redis_client.delete(key):
                deleted += 1

        return deleted

    def invalidate_stale_entries(
        self,
        current_version: str | None = None,
    ) -> int:
        """Delete entries with stale data versions."""

        active_version = (
            current_version
            or self.current_data_version()
        )

        deleted = 0

        for key in self.redis_client.scan_iter(
            match=SEMANTIC_CACHE_PREFIX + "*"
        ):
            stored_version = (
                self.redis_client.hget(
                    key,
                    "data_version",
                )
            )

            if stored_version is None:
                continue

            decoded_version = (
                self.decode_value(
                    stored_version
                )
            )

            if (
                decoded_version != active_version
                and self.redis_client.delete(key)
            ):
                deleted += 1

        return deleted

    def close(self) -> None:
        """Close the Redis connection."""

        self.redis_client.close()


