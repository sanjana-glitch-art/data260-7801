from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from code.memory_schemas import (
    AggregateResponse,
    ChatRequest,
    ChatResponse,
    MemoryResponse,
)
from code.memory_service import (
    EPISODIC_TOP_K,
    SHORT_TERM_N,
    SUMMARIZE_EVERY_USER_MSGS,
    assemble_chat_prompt,
    count_user_messages,
    create_session_id,
    latest_summary,
    lifetime_summary_prompt,
    load_short_term_messages,
    retrieve_relevant_episodes,
    save_message,
    save_summary,
    serialize_episode,
    serialize_message,
    serialize_summary,
    session_summary_prompt,
    should_create_session_summary,
    store_episode_facts,
)
from code.mongo_database import (
    episodes_collection,
    messages_collection,
    summaries_collection,
)
from src.model_client import ModelClient


ROOT = Path(
    __file__
).resolve().parents[1]

RAW_DIRECTORY = (
    ROOT
    / "reports"
    / "hw06"
    / "raw"
)

JSONL_METRICS_PATH = (
    RAW_DIRECTORY
    / "chat_turn_metrics.jsonl"
)

CSV_METRICS_PATH = (
    RAW_DIRECTORY
    / "chat_turn_metrics.csv"
)


MODEL_NAME = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b",
)

MODEL_BASE_URL = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)


router = APIRouter(
    tags=[
        "MongoDB Memory",
    ]
)


model_client = ModelClient(
    model=MODEL_NAME,
    base_url=MODEL_BASE_URL,
    temperature=0.0,
    num_ctx=2048,
    num_predict=256,
)


_metrics_lock = threading.Lock()


def utc_iso_timestamp() -> str:
    """Return the current UTC timestamp as text."""

    return datetime.utcnow().isoformat(
        timespec="microseconds"
    ) + "Z"


def model_text(
    prompt: str,
    purpose: str,
    num_predict: int = 180,
) -> tuple[
    str,
    dict[str, Any],
]:
    """Call the HW1 model adapter for a utility task."""

    utility_client = ModelClient(
        model=MODEL_NAME,
        base_url=MODEL_BASE_URL,
        temperature=0.0,
        num_ctx=2048,
        num_predict=num_predict,
    )

    started = perf_counter()

    result = utility_client.complete([
        {
            "role": "system",
            "content": (
                "/no_think\n\n"
                "You are a careful memory "
                "summarization assistant. "
                "Return only the requested "
                "summary. Do not describe your "
                "reasoning process. Use only the "
                "supplied text. Do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ])

    latency_ms = (
        perf_counter()
        - started
    ) * 1000

    return (
        result.content.strip(),
        {
            "purpose": purpose,
            "input_tokens": (
                result.input_tokens
            ),
            "output_tokens": (
                result.output_tokens
            ),
            "total_tokens": (
                result.total_tokens
            ),
            "latency_ms": round(
                latency_ms,
                3,
            ),
        },
    )


def update_summaries_if_needed(
    user_id: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Create periodic session and lifetime summaries."""

    summary_calls: list[
        dict[str, Any]
    ] = []

    if not should_create_session_summary(
        user_id,
        session_id,
    ):
        return summary_calls

    prompt = session_summary_prompt(
        user_id,
        session_id,
    )

    text, metrics = model_text(
        prompt,
        purpose="session_summary",
        num_predict=180,
    )

    if text:
        save_summary(
            user_id=user_id,
            session_id=session_id,
            scope="session",
            text=text,
        )

    summary_calls.append(
        metrics
    )

    user_message_count = count_user_messages(
        user_id,
        session_id,
    )

    lifetime_interval = (
        SUMMARIZE_EVERY_USER_MSGS
        * 2
    )

    if (
        user_message_count
        % lifetime_interval
        != 0
    ):
        return summary_calls

    lifetime_prompt = (
        lifetime_summary_prompt(
            user_id
        )
    )

    if lifetime_prompt is None:
        return summary_calls

    lifetime_text, lifetime_metrics = (
        model_text(
            lifetime_prompt,
            purpose="lifetime_summary",
            num_predict=220,
        )
    )

    if lifetime_text:
        save_summary(
            user_id=user_id,
            session_id=None,
            scope="user",
            text=lifetime_text,
        )

    summary_calls.append(
        lifetime_metrics
    )

    return summary_calls


def append_turn_metrics(
    record: dict[str, Any],
) -> None:
    """Append one request record to JSONL and CSV."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_fields = [
        "timestamp",
        "user_id",
        "session_id",
        "short_term_n",
        "short_term_count",
        "episodic_top_k",
        "episodic_fact_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "system_primer_tokens",
        "long_term_summary_tokens",
        "short_term_tokens",
        "episodic_fact_tokens",
        "latency_ms",
        "session_summary_created",
        "lifetime_summary_created",
    ]

    with _metrics_lock:
        with JSONL_METRICS_PATH.open(
            "a",
            encoding="utf-8",
        ) as jsonl_file:
            jsonl_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

        write_header = (
            not CSV_METRICS_PATH.exists()
            or CSV_METRICS_PATH.stat().st_size
            == 0
        )

        with CSV_METRICS_PATH.open(
            "a",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=csv_fields,
            )

            if write_header:
                writer.writeheader()

            writer.writerow({
                field: record.get(
                    field
                )
                for field in csv_fields
            })


@router.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
    """Generate one memory-assisted model response."""

    request_started = perf_counter()

    session_id = (
        request.session_id
        or create_session_id()
    )

    try:
        current_message_id = save_message(
            user_id=request.user_id,
            session_id=session_id,
            role="user",
            content=request.message,
        )

        short_term = (
            load_short_term_messages(
                user_id=request.user_id,
                session_id=session_id,
                limit=SHORT_TERM_N,
                exclude_message_id=(
                    current_message_id
                ),
            )
        )

        session_summary = latest_summary(
            user_id=request.user_id,
            session_id=session_id,
            scope="session",
        )

        lifetime_summary = latest_summary(
            user_id=request.user_id,
            scope="user",
        )

        relevant_episodes = (
            retrieve_relevant_episodes(
                user_id=request.user_id,
                query=request.message,
                top_k=EPISODIC_TOP_K,
            )
        )

        model_messages, component_tokens = (
            assemble_chat_prompt(
                current_message=(
                    request.message
                ),
                short_term_messages=(
                    short_term
                ),
                session_summary=(
                    session_summary
                ),
                lifetime_summary=(
                    lifetime_summary
                ),
                episodes=(
                    relevant_episodes
                ),
            )
        )

        model_started = perf_counter()

        result = model_client.complete(
            model_messages
        )

        model_latency_ms = (
            perf_counter()
            - model_started
        ) * 1000

        reply = result.content.strip()

        if not reply:
            reply = (
                "I could not generate a "
                "response for this turn."
            )

        save_message(
            user_id=request.user_id,
            session_id=session_id,
            role="assistant",
            content=reply,
        )

        store_episode_facts(
            user_id=request.user_id,
            session_id=session_id,
            message=request.message,
        )

        summary_calls = (
            update_summaries_if_needed(
                user_id=request.user_id,
                session_id=session_id,
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The memory-assisted chat "
                "request failed: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
        ) from error

    total_latency_ms = (
        perf_counter()
        - request_started
    ) * 1000

    summary_purposes = {
        item["purpose"]
        for item in summary_calls
    }

    metrics_record = {
        "timestamp": utc_iso_timestamp(),
        "user_id": request.user_id,
        "session_id": session_id,
        "short_term_n": SHORT_TERM_N,
        "short_term_count": len(
            short_term
        ),
        "episodic_top_k": EPISODIC_TOP_K,
        "episodic_fact_count": len(
            relevant_episodes
        ),
        "prompt_tokens": (
            result.input_tokens
        ),
        "completion_tokens": (
            result.output_tokens
        ),
        "total_tokens": (
            result.total_tokens
        ),
        **component_tokens,
        "model_latency_ms": round(
            model_latency_ms,
            3,
        ),
        "latency_ms": round(
            total_latency_ms,
            3,
        ),
        "session_summary_created": (
            "session_summary"
            in summary_purposes
        ),
        "lifetime_summary_created": (
            "lifetime_summary"
            in summary_purposes
        ),
        "summary_calls": summary_calls,
    }

    append_turn_metrics(
        metrics_record
    )

    memory_messages = [
        {
            "role": document["role"],
            "content": document[
                "content"
            ],
            "created_at": document[
                "created_at"
            ],
        }
        for document in short_term
    ]

    memory_episodes = [
        {
            "fact": document[
                "fact"
            ],
            "importance": float(
                document[
                    "importance"
                ]
            ),
            "similarity": float(
                document.get(
                    "similarity",
                    0,
                )
            ),
            "created_at": document.get(
                "created_at"
            ),
        }
        for document in relevant_episodes
    ]

    return ChatResponse(
        user_id=request.user_id,
        session_id=session_id,
        reply=reply,
        memory_used={
            "short_term_count": len(
                short_term
            ),
            "short_term_messages": (
                memory_messages
            ),
            "session_summary": (
                session_summary[
                    "text"
                ]
                if session_summary
                else None
            ),
            "lifetime_summary": (
                lifetime_summary[
                    "text"
                ]
                if lifetime_summary
                else None
            ),
            "episodic_facts": (
                memory_episodes
            ),
        },
        usage={
            "prompt_tokens": (
                result.input_tokens
            ),
            "completion_tokens": (
                result.output_tokens
            ),
            "total_tokens": (
                result.total_tokens
            ),
            **component_tokens,
            "latency_ms": round(
                total_latency_ms,
                3,
            ),
        },
    )


@router.get(
    "/api/memory/{user_id}",
    response_model=MemoryResponse,
)
def inspect_memory(
    user_id: str,
    session_id: str | None = Query(
        default=None,
        max_length=100,
    ),
) -> MemoryResponse:
    """Return recent memory for one user."""

    cleaned_user_id = user_id.strip()

    if not cleaned_user_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "user_id must not be empty."
            ),
        )

    message_filter: dict[
        str,
        Any,
    ] = {
        "user_id": cleaned_user_id
    }

    if session_id:
        message_filter[
            "session_id"
        ] = session_id

    messages = list(
        messages_collection()
        .find(
            message_filter
        )
        .sort(
            "created_at",
            -1,
        )
        .limit(
            16
        )
    )

    messages.reverse()

    if session_id:
        session_summary = latest_summary(
            user_id=cleaned_user_id,
            session_id=session_id,
            scope="session",
        )
    else:
        session_summary = (
            summaries_collection().find_one(
                {
                    "user_id": (
                        cleaned_user_id
                    ),
                    "scope": "session",
                },
                sort=[
                    (
                        "created_at",
                        -1,
                    )
                ],
            )
        )

    lifetime_summary = latest_summary(
        user_id=cleaned_user_id,
        scope="user",
    )

    episodes = list(
        episodes_collection()
        .find({
            "user_id": cleaned_user_id
        })
        .sort(
            "created_at",
            -1,
        )
        .limit(
            20
        )
    )

    return MemoryResponse(
        user_id=cleaned_user_id,
        messages=[
            serialize_message(
                document
            )
            for document in messages
        ],
        session_summary=(
            serialize_summary(
                session_summary
            )
            if session_summary
            else None
        ),
        lifetime_summary=(
            serialize_summary(
                lifetime_summary
            )
            if lifetime_summary
            else None
        ),
        episodes=[
            serialize_episode(
                document
            )
            for document in episodes
        ],
    )


@router.get(
    "/api/aggregate/{user_id}",
    response_model=AggregateResponse,
)
def aggregate_memory(
    user_id: str,
) -> AggregateResponse:
    """Return daily counts and recent summaries."""

    cleaned_user_id = user_id.strip()

    if not cleaned_user_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "user_id must not be empty."
            ),
        )

    pipeline = [
        {
            "$match": {
                "user_id": cleaned_user_id
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": (
                            "%Y-%m-%d"
                        ),
                        "date": (
                            "$created_at"
                        ),
                        "timezone": "UTC",
                    }
                },
                "count": {
                    "$sum": 1
                },
            }
        },
        {
            "$sort": {
                "_id": 1
            }
        },
    ]

    daily_rows = list(
        messages_collection().aggregate(
            pipeline
        )
    )

    recent_summaries = list(
        summaries_collection()
        .find({
            "user_id": cleaned_user_id
        })
        .sort(
            "created_at",
            -1,
        )
        .limit(
            5
        )
    )

    return AggregateResponse(
        user_id=cleaned_user_id,
        daily_message_counts=[
            {
                "date": row["_id"],
                "count": row["count"],
            }
            for row in daily_rows
        ],
        recent_summaries=[
            serialize_summary(
                document
            )
            for document
            in recent_summaries
        ],
    )