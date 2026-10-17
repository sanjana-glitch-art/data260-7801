from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from bson import ObjectId
from sentence_transformers import (
    SentenceTransformer,
)

from code.mongo_database import (
    episodes_collection,
    messages_collection,
    summaries_collection,
)


SHORT_TERM_N = int(
    os.getenv(
        "SHORT_TERM_N",
        "12",
    )
)

SUMMARIZE_EVERY_USER_MSGS = int(
    os.getenv(
        "SUMMARIZE_EVERY_USER_MSGS",
        "5",
    )
)

EPISODIC_TOP_K = int(
    os.getenv(
        "EPISODIC_TOP_K",
        "3",
    )
)

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    (
        "sentence-transformers/"
        "all-MiniLM-L6-v2"
    ),
)


SYSTEM_PRIMER = """
/no_think

You are a helpful clinical-trial listing assistant.

Answer directly without describing your reasoning process.
Use the supplied memory only when it is relevant to the
current request. Do not invent clinical facts. Clearly say
when requested information is not available. Do not reveal
private submitter contact information. Follow the user's
requested response format. Give concise answers.
""".strip()


_embedding_model: (
    SentenceTransformer | None
) = None


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def create_session_id() -> str:
    """Create a unique conversation-session ID."""

    return (
        "session-"
        + uuid4().hex
    )


def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model only when first needed."""

    global _embedding_model

    if _embedding_model is None:
        print(
            "Loading embedding model:",
            EMBEDDING_MODEL_NAME,
        )

        _embedding_model = (
            SentenceTransformer(
                EMBEDDING_MODEL_NAME
            )
        )

    return _embedding_model


def embed_text(
    text: str,
) -> list[float]:
    """Create a normalized embedding for text."""

    cleaned = text.strip()

    if not cleaned:
        raise ValueError(
            "Text must not be empty."
        )

    model = get_embedding_model()

    embedding = model.encode(
        cleaned,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return [
        float(value)
        for value in embedding.tolist()
    ]


def cosine_similarity(
    first: list[float],
    second: list[float],
) -> float:
    """Calculate cosine similarity for two vectors."""

    if (
        not first
        or not second
        or len(first) != len(second)
    ):
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(
            first,
            second,
        )
    )

    first_norm = math.sqrt(
        sum(
            value * value
            for value in first
        )
    )

    second_norm = math.sqrt(
        sum(
            value * value
            for value in second
        )
    )

    if (
        first_norm == 0
        or second_norm == 0
    ):
        return 0.0

    return (
        dot_product
        / (
            first_norm
            * second_norm
        )
    )


def approximate_tokens(
    text: str | None,
) -> int:
    """
    Estimate component tokens consistently.

    Actual complete-request token counts are obtained from
    the Ollama model adapter. This approximation is used to
    attribute tokens to individual prompt components.
    """

    if not text:
        return 0

    return max(
        1,
        math.ceil(
            len(text) / 4
        ),
    )


def save_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
) -> ObjectId:
    """Store one user or assistant message."""

    if role not in {
        "user",
        "assistant",
    }:
        raise ValueError(
            "Message role must be user or assistant."
        )

    result = messages_collection().insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content.strip(),
        "created_at": utc_now(),
    })

    return result.inserted_id


def load_short_term_messages(
    user_id: str,
    session_id: str,
    limit: int | None = None,
    exclude_message_id: ObjectId | None = None,
) -> list[dict[str, Any]]:
    """Load the most recent session messages in order."""

    selected_limit = (
        limit
        if limit is not None
        else SHORT_TERM_N
    )

    mongo_filter: dict[str, Any] = {
        "user_id": user_id,
        "session_id": session_id,
    }

    if exclude_message_id is not None:
        mongo_filter["_id"] = {
            "$ne": exclude_message_id
        }

    newest_first = list(
        messages_collection()
        .find(
            mongo_filter
        )
        .sort(
            "created_at",
            -1,
        )
        .limit(
            selected_limit
        )
    )

    newest_first.reverse()

    return newest_first


def count_user_messages(
    user_id: str,
    session_id: str,
) -> int:
    """Count user-authored messages in one session."""

    return messages_collection().count_documents({
        "user_id": user_id,
        "session_id": session_id,
        "role": "user",
    })


def latest_summary(
    user_id: str,
    scope: str,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Load the newest session or lifetime summary."""

    mongo_filter: dict[str, Any] = {
        "user_id": user_id,
        "scope": scope,
    }

    if scope == "session":
        mongo_filter[
            "session_id"
        ] = session_id
    else:
        mongo_filter[
            "session_id"
        ] = None

    return summaries_collection().find_one(
        mongo_filter,
        sort=[
            (
                "created_at",
                -1,
            )
        ],
    )


def save_summary(
    user_id: str,
    session_id: str | None,
    scope: str,
    text: str,
) -> ObjectId:
    """Store a new session or lifetime summary."""

    if scope not in {
        "session",
        "user",
    }:
        raise ValueError(
            "Summary scope must be session or user."
        )

    result = summaries_collection().insert_one({
        "user_id": user_id,
        "session_id": (
            session_id
            if scope == "session"
            else None
        ),
        "scope": scope,
        "text": text.strip(),
        "created_at": utc_now(),
    })

    return result.inserted_id


def should_create_session_summary(
    user_id: str,
    session_id: str,
) -> bool:
    """Return True at each configured summary interval."""

    count = count_user_messages(
        user_id,
        session_id,
    )

    return (
        count > 0
        and count
        % SUMMARIZE_EVERY_USER_MSGS
        == 0
    )


def recent_session_transcript(
    user_id: str,
    session_id: str,
    limit: int = 20,
) -> str:
    """Return a labeled transcript for summarization."""

    documents = load_short_term_messages(
        user_id,
        session_id,
        limit=limit,
    )

    lines = [
        (
            f"{document['role'].upper()}: "
            f"{document['content']}"
        )
        for document in documents
    ]

    return "\n".join(
        lines
    )


def session_summary_prompt(
    user_id: str,
    session_id: str,
) -> str:
    """Build the prompt used for a session summary."""

    transcript = recent_session_transcript(
        user_id,
        session_id,
        limit=20,
    )

    return f"""
Summarize this clinical-trial assistant conversation.

Write no more than five concise bullet points.
Preserve user preferences, important facts, unresolved
questions, and decisions. Do not invent information.

Conversation:
{transcript}
""".strip()


def lifetime_summary_prompt(
    user_id: str,
    limit: int = 8,
) -> str | None:
    """Build a prompt from recent session summaries."""

    session_summaries = list(
        summaries_collection()
        .find({
            "user_id": user_id,
            "scope": "session",
        })
        .sort(
            "created_at",
            -1,
        )
        .limit(
            limit
        )
    )

    if len(session_summaries) < 2:
        return None

    session_summaries.reverse()

    combined = "\n\n".join(
        summary["text"]
        for summary in session_summaries
    )

    return f"""
Condense the following session summaries into a durable
lifetime summary.

Use no more than eight concise bullet points. Preserve stable
preferences, recurring goals, important facts, and unresolved
issues. Merge duplicates. Do not invent information.

Session summaries:
{combined}
""".strip()


def importance_for_fact(
    fact: str,
) -> float:
    """Assign a deterministic importance score."""

    lowered = fact.casefold()

    high_importance_markers = {
        "allergy",
        "allergic",
        "never",
        "must",
        "privacy",
        "do not",
        "don't",
        "cannot",
        "can't",
        "medical",
        "safety",
    }

    medium_importance_markers = {
        "prefer",
        "favorite",
        "remember",
        "goal",
        "study",
        "trial",
        "phase",
        "sponsor",
        "university",
    }

    if any(
        marker in lowered
        for marker
        in high_importance_markers
    ):
        return 0.95

    if any(
        marker in lowered
        for marker
        in medium_importance_markers
    ):
        return 0.75

    return 0.55


def extract_episode_facts(
    message: str,
    maximum: int = 3,
) -> list[dict[str, Any]]:
    """
    Extract up to three short facts deterministically.

    This avoids an extra model call on every chat request.
    """

    cleaned = " ".join(
        message.strip().split()
    )

    if not cleaned:
        return []

    candidates = re.split(
        r"(?<=[.!?])\s+",
        cleaned,
    )

    facts: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    for candidate in candidates:
        fact = candidate.strip(
            " -\t\r\n"
        )

        if len(fact) < 8:
            continue

        if len(fact) > 300:
            fact = fact[:297].rstrip() + "..."

        normalized = fact.casefold()

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        facts.append({
            "fact": fact,
            "importance": (
                importance_for_fact(
                    fact
                )
            ),
        })

        if len(facts) >= maximum:
            break

    return facts


def store_episode_facts(
    user_id: str,
    session_id: str,
    message: str,
) -> list[dict[str, Any]]:
    """Extract, embed, and store facts from one message."""

    extracted = extract_episode_facts(
        message,
        maximum=3,
    )

    stored: list[
        dict[str, Any]
    ] = []

    for item in extracted:
        embedding = embed_text(
            item["fact"]
        )

        document = {
            "user_id": user_id,
            "session_id": session_id,
            "fact": item["fact"],
            "importance": float(
                item["importance"]
            ),
            "embedding": embedding,
            "created_at": utc_now(),
        }

        result = episodes_collection().insert_one(
            document
        )

        document["_id"] = (
            result.inserted_id
        )

        stored.append(
            document
        )

    return stored


def retrieve_relevant_episodes(
    user_id: str,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve episodic facts using cosine similarity."""

    selected_top_k = (
        top_k
        if top_k is not None
        else EPISODIC_TOP_K
    )

    query_embedding = embed_text(
        query
    )

    documents = list(
        episodes_collection()
        .find({
            "user_id": user_id
        })
        .sort(
            "created_at",
            -1,
        )
        .limit(
            500
        )
    )

    scored: list[
        dict[str, Any]
    ] = []

    for document in documents:
        similarity = cosine_similarity(
            query_embedding,
            document.get(
                "embedding",
                [],
            ),
        )

        combined_score = (
            similarity * 0.85
            + float(
                document.get(
                    "importance",
                    0.5,
                )
            )
            * 0.15
        )

        scored.append({
            **document,
            "similarity": round(
                similarity,
                6,
            ),
            "combined_score": round(
                combined_score,
                6,
            ),
        })

    scored.sort(
        key=lambda item: (
            item["combined_score"]
        ),
        reverse=True,
    )

    return scored[
        :selected_top_k
    ]


def format_short_term(
    messages: list[dict[str, Any]],
) -> str:
    """Format short-term messages for a model prompt."""

    if not messages:
        return "(none)"

    return "\n".join(
        (
            f"{message['role'].upper()}: "
            f"{message['content']}"
        )
        for message in messages
    )


def format_episodes(
    episodes: list[dict[str, Any]],
) -> str:
    """Format episodic facts for a model prompt."""

    if not episodes:
        return "(none)"

    return "\n".join(
        (
            f"- {episode['fact']} "
            f"(importance="
            f"{episode['importance']:.2f}, "
            f"similarity="
            f"{episode['similarity']:.3f})"
        )
        for episode in episodes
    )


def assemble_chat_prompt(
    current_message: str,
    short_term_messages: list[
        dict[str, Any]
    ],
    session_summary: (
        dict[str, Any] | None
    ),
    lifetime_summary: (
        dict[str, Any] | None
    ),
    episodes: list[
        dict[str, Any]
    ],
) -> tuple[
    list[dict[str, str]],
    dict[str, int],
]:
    """Create model messages and component token counts."""

    short_term_text = format_short_term(
        short_term_messages
    )

    session_summary_text = (
        session_summary["text"]
        if session_summary
        else "(none)"
    )

    lifetime_summary_text = (
        lifetime_summary["text"]
        if lifetime_summary
        else "(none)"
    )

    long_term_text = (
        "Session summary:\n"
        f"{session_summary_text}\n\n"
        "Lifetime summary:\n"
        f"{lifetime_summary_text}"
    )

    episodic_text = format_episodes(
        episodes
    )

    memory_prompt = f"""
LONG-TERM MEMORY
{long_term_text}

SHORT-TERM CONVERSATION
{short_term_text}

RELEVANT EPISODIC FACTS
{episodic_text}
""".strip()

    user_prompt = f"""
Use the supplied memory only when relevant.

Current user message:
{current_message}
""".strip()

    model_messages = [
        {
            "role": "system",
            "content": SYSTEM_PRIMER,
        },
        {
            "role": "system",
            "content": memory_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    component_tokens = {
        "system_primer_tokens": (
            approximate_tokens(
                SYSTEM_PRIMER
            )
        ),
        "long_term_summary_tokens": (
            approximate_tokens(
                long_term_text
            )
        ),
        "short_term_tokens": (
            approximate_tokens(
                short_term_text
            )
        ),
        "episodic_fact_tokens": (
            approximate_tokens(
                episodic_text
            )
        ),
    }

    return (
        model_messages,
        component_tokens,
    )


def serialize_message(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Serialize a message document."""

    return {
        "id": str(
            document["_id"]
        ),
        "user_id": document[
            "user_id"
        ],
        "session_id": document[
            "session_id"
        ],
        "role": document[
            "role"
        ],
        "content": document[
            "content"
        ],
        "created_at": document[
            "created_at"
        ],
    }


def serialize_summary(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Serialize a summary document."""

    return {
        "id": str(
            document["_id"]
        ),
        "user_id": document[
            "user_id"
        ],
        "session_id": document.get(
            "session_id"
        ),
        "scope": document[
            "scope"
        ],
        "text": document[
            "text"
        ],
        "created_at": document[
            "created_at"
        ],
    }


def serialize_episode(
    document: dict[str, Any],
    include_similarity: bool = False,
) -> dict[str, Any]:
    """Serialize an episodic-memory document."""

    serialized = {
        "id": str(
            document["_id"]
        ),
        "user_id": document[
            "user_id"
        ],
        "session_id": document[
            "session_id"
        ],
        "fact": document[
            "fact"
        ],
        "importance": float(
            document["importance"]
        ),
        "created_at": document[
            "created_at"
        ],
    }

    if include_similarity:
        serialized[
            "similarity"
        ] = float(
            document.get(
                "similarity",
                0,
            )
        )

    return serialized