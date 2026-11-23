from __future__ import annotations

import json
from code.hw10_config import (
    CACHE_HIT,
    CACHE_MISS,
    PIPELINE_EVALUATION_PATH,
    REQUIRED_TRACES_PATH,
    STUDENT_NAME,
    ensure_hw10_directories,
)
from code.hw10_tracing import (
    generate_trace_id,
    spans_for_trace,
    trace_span,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def load_json(
    path: Path,
) -> dict[str, Any]:
    """Load one JSON object."""

    value = json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )

    if not isinstance(value, dict):
        raise TypeError(
            f"{path} must contain a JSON object."
        )

    return value


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    """Write one formatted JSON document."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def create_cache_hit_trace() -> str:
    """Create a trace that ends at a cache hit."""

    trace_id = generate_trace_id()

    with trace_span(
        trace_id,
        "cache_lookup",
        cache_result=CACHE_HIT,
        metadata={
            "question": (
                "Give the phase and enrollment target "
                "of the sleep quality trial."
            ),
            "cached_query": (
                "Give the phase and enrollment target "
                "of the sleep quality trial."
            ),
            "similarity": 1.0,
            "answer_source": "semantic_cache",
            "returned_answer": (
                "The Sleep Quality and Academic "
                "Performance Study is Phase II with "
                "an enrollment target of 120."
            ),
        },
    ):
        pass

    return trace_id


def create_failed_trace() -> str:
    """Create a controlled Writer-stage failure trace."""

    trace_id = generate_trace_id()

    question = (
        "Process an intentionally malformed "
        "clinical-trial Writer request."
    )

    with trace_span(
        trace_id,
        "cache_lookup",
        cache_result=CACHE_MISS,
        metadata={
            "question": question,
            "answer_source": "semantic_cache",
        },
    ):
        pass

    with trace_span(
        trace_id,
        "planner",
        metadata={
            "question": question,
            "status_message": (
                "Planner created a task that will "
                "exercise controlled failure handling."
            ),
        },
    ):
        plan = [
            (
                "Send a deliberately malformed plan "
                "to the Writer."
            )
        ]

    try:
        with trace_span(
            trace_id,
            "writer",
            metadata={
                "question": question,
                "plan": plan,
                "failure_injected": True,
            },
        ):
            raise ValueError(
                "Controlled Writer failure: plan "
                "payload must be a list of valid steps."
            )
    except ValueError:
        # The failed span already contains the error.
        pass

    return trace_id


def validate_trace(
    *,
    trace_id: str,
    expected_stages: list[str],
    expected_cache_result: str,
    expected_final_status: str,
) -> dict[str, Any]:
    """Validate and return one required trace."""

    spans = spans_for_trace(trace_id)

    stages = [
        str(span.get("stage"))
        for span in spans
    ]

    cache_results = [
        span.get("cache_result")
        for span in spans
        if span.get("stage") == "cache_lookup"
    ]

    final_status = (
        spans[-1].get("status")
        if spans
        else None
    )

    passed = (
        stages == expected_stages
        and cache_results
        and cache_results[0]
        == expected_cache_result
        and final_status
        == expected_final_status
    )

    return {
        "trace_id": trace_id,
        "expected_stages": expected_stages,
        "observed_stages": stages,
        "expected_cache_result": (
            expected_cache_result
        ),
        "observed_cache_result": (
            cache_results[0]
            if cache_results
            else None
        ),
        "expected_final_status": (
            expected_final_status
        ),
        "observed_final_status": final_status,
        "passed": passed,
        "spans": spans,
    }


def main() -> None:
    """Generate cache-hit, cache-miss, and failure traces."""

    ensure_hw10_directories()

    if not PIPELINE_EVALUATION_PATH.exists():
        raise FileNotFoundError(
            "Run code.run_hw10_evaluation first."
        )

    evaluation = load_json(
        PIPELINE_EVALUATION_PATH
    )

    if evaluation.get("success") is not True:
        raise ValueError(
            "The saved pipeline evaluation did not pass."
        )

    successful_miss_trace_id = str(
        evaluation["trace_id"]
    )
    cache_hit_trace_id = (
        create_cache_hit_trace()
    )
    failed_trace_id = create_failed_trace()

    cache_hit = validate_trace(
        trace_id=cache_hit_trace_id,
        expected_stages=[
            "cache_lookup",
        ],
        expected_cache_result=CACHE_HIT,
        expected_final_status="success",
    )

    successful_cache_miss = validate_trace(
        trace_id=successful_miss_trace_id,
        expected_stages=[
            "cache_lookup",
            "planner",
            "writer",
            "reviewer",
            "evaluation",
        ],
        expected_cache_result=CACHE_MISS,
        expected_final_status="success",
    )

    failed_trace = validate_trace(
        trace_id=failed_trace_id,
        expected_stages=[
            "cache_lookup",
            "planner",
            "writer",
        ],
        expected_cache_result=CACHE_MISS,
        expected_final_status="failed",
    )

    overall_passed = all(
        trace["passed"]
        for trace in (
            cache_hit,
            successful_cache_miss,
            failed_trace,
        )
    )

    document = {
        "experiment": (
            "hw10_required_trace_scenarios"
        ),
        "student": STUDENT_NAME,
        "sid4": 7801,
        "generated_at": utc_timestamp(),
        "cache_hit_trace": cache_hit,
        "successful_cache_miss_trace": (
            successful_cache_miss
        ),
        "failed_trace": failed_trace,
        "trace_ids": {
            "cache_hit": cache_hit_trace_id,
            "successful_cache_miss": (
                successful_miss_trace_id
            ),
            "failed": failed_trace_id,
        },
        "overall_passed": overall_passed,
    }

    write_json(
        REQUIRED_TRACES_PATH,
        document,
    )

    print(
        "DATA-260 Homework 10 Required Traces"
    )
    print(f"Student: {STUDENT_NAME}")
    print()
    print(
        "Cache-hit trace ID: "
        f"{cache_hit_trace_id}"
    )
    print(
        "Cache-hit stages: "
        f"{cache_hit['observed_stages']}"
    )
    print(
        "Cache-hit passed: "
        f"{cache_hit['passed']}"
    )
    print()
    print(
        "Successful cache-miss trace ID: "
        f"{successful_miss_trace_id}"
    )
    print(
        "Cache-miss stages: "
        f"{successful_cache_miss['observed_stages']}"
    )
    print(
        "Cache-miss passed: "
        f"{successful_cache_miss['passed']}"
    )
    print()
    print(
        "Failed trace ID: "
        f"{failed_trace_id}"
    )
    print(
        "Failed-trace stages: "
        f"{failed_trace['observed_stages']}"
    )
    print(
        "Failed-trace status: "
        f"{failed_trace['observed_final_status']}"
    )
    print(
        "Failed trace passed: "
        f"{failed_trace['passed']}"
    )
    print()
    print(f"Overall: {overall_passed}")
    print(f"Saved: {REQUIRED_TRACES_PATH}")


if __name__ == "__main__":
    main()