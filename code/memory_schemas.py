from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ChatRequest(BaseModel):
    """Request accepted by POST /api/chat."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator(
        "user_id",
        "message",
    )
    @classmethod
    def required_text_not_blank(
        cls,
        value: str,
    ) -> str:
        """Reject required values containing only spaces."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Value must not be blank."
            )

        return cleaned

    @field_validator(
        "session_id",
    )
    @classmethod
    def optional_session_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional session ID."""

        if value is None:
            return None

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Session ID must not be blank."
            )

        return cleaned


class MessageMemory(BaseModel):
    """One stored conversation message."""

    role: Literal[
        "user",
        "assistant",
    ]

    content: str

    created_at: datetime


class EpisodicFactMemory(BaseModel):
    """One retrieved episodic-memory fact."""

    fact: str

    importance: float = Field(
        ge=0,
        le=1,
    )

    similarity: float | None = None

    created_at: datetime | None = None


class MemoryUsed(BaseModel):
    """Memory components used for one chat turn."""

    short_term_count: int = Field(
        ge=0
    )

    short_term_messages: list[
        MessageMemory
    ]

    session_summary: str | None = None

    lifetime_summary: str | None = None

    episodic_facts: list[
        EpisodicFactMemory
    ]


class TokenUsage(BaseModel):
    """Token and latency values for one chat request."""

    prompt_tokens: int = Field(
        ge=0
    )

    completion_tokens: int = Field(
        ge=0
    )

    total_tokens: int = Field(
        ge=0
    )

    system_primer_tokens: int = Field(
        ge=0
    )

    long_term_summary_tokens: int = Field(
        ge=0
    )

    short_term_tokens: int = Field(
        ge=0
    )

    episodic_fact_tokens: int = Field(
        ge=0
    )

    latency_ms: float = Field(
        ge=0
    )


class ChatResponse(BaseModel):
    """Response returned by POST /api/chat."""

    user_id: str

    session_id: str

    reply: str

    memory_used: MemoryUsed

    usage: TokenUsage


class StoredMessageResponse(BaseModel):
    """Message returned by the memory-inspection endpoint."""

    id: str

    user_id: str

    session_id: str

    role: Literal[
        "user",
        "assistant",
    ]

    content: str

    created_at: datetime


class StoredSummaryResponse(BaseModel):
    """Summary returned by the memory endpoint."""

    id: str

    user_id: str

    session_id: str | None

    scope: Literal[
        "session",
        "user",
    ]

    text: str

    created_at: datetime


class StoredEpisodeResponse(BaseModel):
    """Episode returned by the memory endpoint."""

    id: str

    user_id: str

    session_id: str

    fact: str

    importance: float

    created_at: datetime


class MemoryResponse(BaseModel):
    """Response returned by GET /api/memory/{user_id}."""

    user_id: str

    messages: list[
        StoredMessageResponse
    ]

    session_summary: (
        StoredSummaryResponse | None
    )

    lifetime_summary: (
        StoredSummaryResponse | None
    )

    episodes: list[
        StoredEpisodeResponse
    ]


class DailyMessageCount(BaseModel):
    """Messages stored on one UTC calendar date."""

    date: str

    count: int = Field(
        ge=0
    )


class AggregateResponse(BaseModel):
    """Response returned by GET /api/aggregate/{user_id}."""

    user_id: str

    daily_message_counts: list[
        DailyMessageCount
    ]

    recent_summaries: list[
        StoredSummaryResponse
    ]


class ProbeCriterion(BaseModel):
    """One expected criterion for a memory probe."""

    description: str

    keywords: list[str] = []


class MemoryProbe(BaseModel):
    """One fixed probe used by the experiment."""

    id: str

    question: str

    expected_criteria: list[
        ProbeCriterion
    ]

    scoring_rubric: dict[
        str,
        str,
    ]


class ExperimentTurnRecord(BaseModel):
    """Machine-readable metrics for one experiment turn."""

    model_config = ConfigDict(
        extra="allow",
    )

    setting: str

    session_id: str

    turn: int = Field(
        ge=1
    )

    prompt_tokens: int = Field(
        ge=0
    )

    completion_tokens: int = Field(
        ge=0
    )

    total_tokens: int = Field(
        ge=0
    )

    latency_ms: float = Field(
        ge=0
    )

    metadata: dict[
        str,
        Any,
    ] = {}