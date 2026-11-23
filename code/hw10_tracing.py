from __future__ import annotations

import json
import threading
from code.hw10_config import (
    CACHE_ERROR,
    CACHE_HIT,
    CACHE_MISS,
    TRACE_PATH,
    TRACE_STATUS_FAILED,
    TRACE_STATUS_SUCCESS,
    ensure_hw10_directories,
)
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import TracebackType
from typing import Any, Self
from uuid import uuid4

_TRACE_WRITE_LOCK = threading.Lock()


def utc_timestamp() -> str:
    """Return the current UTC time in ISO 8601 format."""

    return datetime.now(UTC).isoformat()


def generate_trace_id() -> str:
    """Create a new trace ID suitable for Kafka correlation."""

    return str(uuid4())


def _json_safe(value: Any) -> Any:
    """Convert common values into JSON-safe values."""

    if value is None:
        return None

    if isinstance(
        value,
        str | int | float | bool,
    ):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list | tuple | set):
        return [
            _json_safe(item)
            for item in value
        ]

    return str(value)


@dataclass
class TraceSpan:
    """One timed operation in a distributed request trace."""

    trace_id: str
    stage: str
    start_time: str
    end_time: str
    duration_ms: float
    status: str
    error: str | None = None
    error_type: str | None = None
    cache_result: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the span to a JSON-safe dictionary."""

        return _json_safe(asdict(self))


def append_span(
    span: TraceSpan,
    *,
    path: Path = TRACE_PATH,
) -> None:
    """Append one trace span to a JSON Lines file."""

    ensure_hw10_directories()
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = json.dumps(
        span.to_dict(),
        ensure_ascii=False,
        default=str,
    )

    with _TRACE_WRITE_LOCK, path.open(
        "a",
        encoding="utf-8",
    ) as trace_file:
        trace_file.write(serialized + "\n")


class SpanRecorder(
    AbstractContextManager["SpanRecorder"]
):
    """Context manager that records a timed trace span."""

    def __init__(
        self,
        trace_id: str,
        stage: str,
        *,
        cache_result: str | None = None,
        metadata: dict[str, Any] | None = None,
        path: Path = TRACE_PATH,
    ) -> None:
        if not trace_id.strip():
            raise ValueError(
                "trace_id must be a non-empty string."
            )

        if not stage.strip():
            raise ValueError(
                "stage must be a non-empty string."
            )

        if cache_result not in {
            None,
            CACHE_HIT,
            CACHE_MISS,
            CACHE_ERROR,
        }:
            raise ValueError(
                "cache_result must be hit, miss, "
                "error, or None."
            )

        self.trace_id = trace_id
        self.stage = stage
        self.cache_result = cache_result
        self.metadata = metadata or {}
        self.path = path

        self.start_time = ""
        self.end_time = ""
        self.duration_ms = 0.0
        self.status = TRACE_STATUS_SUCCESS
        self.error: str | None = None
        self.error_type: str | None = None

        self._start_counter = 0.0

    def __enter__(self) -> Self:
        self.start_time = utc_timestamp()
        self._start_counter = perf_counter()
        return self

    def add_metadata(
        self,
        **values: Any,
    ) -> None:
        """Add information to the active span."""

        self.metadata.update(values)

    def set_cache_result(
        self,
        cache_result: str,
    ) -> None:
        """Set whether the cache lookup hit or missed."""

        if cache_result not in {
            CACHE_HIT,
            CACHE_MISS,
            CACHE_ERROR,
        }:
            raise ValueError(
                "cache_result must be hit, miss, "
                "or error."
            )

        self.cache_result = cache_result

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.end_time = utc_timestamp()
        self.duration_ms = round(
            (
                perf_counter()
                - self._start_counter
            )
            * 1000,
            3,
        )

        if exception is not None:
            self.status = TRACE_STATUS_FAILED
            self.error = str(exception)
            self.error_type = type(exception).__name__

            if self.stage == "cache_lookup":
                self.cache_result = CACHE_ERROR

        span = TraceSpan(
            trace_id=self.trace_id,
            stage=self.stage,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=self.duration_ms,
            status=self.status,
            error=self.error,
            error_type=self.error_type,
            cache_result=self.cache_result,
            metadata=self.metadata,
        )

        append_span(
            span,
            path=self.path,
        )

        # Returning False preserves normal exception behavior.
        return False


def trace_span(
    trace_id: str,
    stage: str,
    *,
    cache_result: str | None = None,
    metadata: dict[str, Any] | None = None,
    path: Path = TRACE_PATH,
) -> SpanRecorder:
    """Create a span-recording context manager."""

    return SpanRecorder(
        trace_id=trace_id,
        stage=stage,
        cache_result=cache_result,
        metadata=metadata,
        path=path,
    )


def load_spans(
    *,
    path: Path = TRACE_PATH,
) -> list[dict[str, Any]]:
    """Load all valid spans from a JSON Lines file."""

    if not path.exists():
        return []

    spans: list[dict[str, Any]] = []

    with path.open(
        encoding="utf-8-sig",
    ) as trace_file:
        for line_number, line in enumerate(
            trace_file,
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Invalid JSON in trace file "
                    f"at line {line_number}."
                ) from error

            if not isinstance(value, dict):
                raise TypeError(
                    "Each trace line must contain "
                    "a JSON object."
                )

            spans.append(value)

    return spans


def spans_for_trace(
    trace_id: str,
    *,
    path: Path = TRACE_PATH,
) -> list[dict[str, Any]]:
    """Return all spans belonging to one trace ID."""

    matching_spans = [
        span
        for span in load_spans(path=path)
        if span.get("trace_id") == trace_id
    ]

    return sorted(
        matching_spans,
        key=lambda span: str(
            span.get("start_time", "")
        ),
    )


def trace_ids(
    *,
    path: Path = TRACE_PATH,
) -> list[str]:
    """Return unique trace IDs in first-seen order."""

    identifiers: list[str] = []
    seen: set[str] = set()

    for span in load_spans(path=path):
        trace_id = span.get("trace_id")

        if (
            isinstance(trace_id, str)
            and trace_id
            and trace_id not in seen
        ):
            identifiers.append(trace_id)
            seen.add(trace_id)

    return identifiers


def clear_trace_file(
    *,
    path: Path = TRACE_PATH,
) -> None:
    """Remove existing trace evidence."""

    if path.exists():
        path.unlink()