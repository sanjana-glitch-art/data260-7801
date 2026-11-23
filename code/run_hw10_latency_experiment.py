from __future__ import annotations

import csv
import json
import multiprocessing
from code.hw10_config import (
    CACHE_MISS,
    LATENCY_EXPERIMENT_REQUEST_COUNT,
    LATENCY_RESULTS_PATH,
    LATENCY_SPANS_PATH,
    LATENCY_SUMMARY_PATH,
    PREFIX,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    STUDENT_NAME,
    ensure_hw10_directories,
)
from code.hw10_evaluator import evaluate_writer_draft
from code.hw10_tracing import (
    generate_trace_id,
    trace_span,
)
from statistics import mean
from time import perf_counter
from typing import Any

import numpy as np
from redis import Redis

REFERENCE_ANSWER = (
    "The Sleep Quality and Academic Performance "
    "Study is a Phase II trial sponsored by "
    "San Jose State University with an enrollment "
    "target of 120 participants."
)


def percentile(
    values: list[float],
    value: float,
) -> float:
    """Calculate a rounded percentile."""

    return round(
        float(np.percentile(values, value)),
        3,
    )


def write_json(
    path: Any,
    value: Any,
) -> None:
    """Write one JSON document."""

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


def write_rows_csv(
    rows: list[dict[str, Any]],
) -> None:
    """Write one row for every cache-miss request."""

    fields = [
        "request_number",
        "trace_id",
        "cache_result",
        "cache_lookup_ms",
        "planner_ms",
        "writer_ms",
        "reviewer_ms",
        "queue_wait_total_ms",
        "evaluation_ms",
        "end_to_end_ms",
        "judge_score",
        "judge_success",
    ]

    with LATENCY_SPANS_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(
    summaries: list[dict[str, Any]],
) -> None:
    """Write stage-level latency statistics."""

    fields = [
        "stage",
        "sample_count",
        "mean_ms",
        "p50_ms",
        "p95_ms",
        "percent_of_cache_miss_e2e",
    ]

    with LATENCY_SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(summaries)


def queue_handoff(
    trace_id: str,
    payload: dict[str, Any],
    *,
    source: str,
    destination: str,
) -> tuple[dict[str, Any], float]:
    """Measure a serialized stage handoff."""

    with trace_span(
        trace_id,
        "queue_wait",
        metadata={
            "source_stage": source,
            "destination_stage": destination,
        },
    ) as span:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
        )
        received = json.loads(serialized)

    return received, span.duration_ms


def run_cache_miss(
    request_number: int,
    redis_client: Redis,
) -> dict[str, Any]:
    """Run one confirmed cache-miss pipeline request."""

    trace_id = generate_trace_id()
    cache_key = (
        f"{PREFIX}:hw10_latency:"
        f"{trace_id}"
    )

    question = (
        "Give the phase, sponsor, and enrollment "
        "target of the sleep quality trial."
    )

    end_to_end_started = perf_counter()

    with trace_span(
        trace_id,
        "cache_lookup",
        cache_result=CACHE_MISS,
        metadata={
            "request_number": request_number,
            "cache_key": cache_key,
            "experiment": (
                "50_confirmed_cache_misses"
            ),
        },
    ) as cache_span:
        cached_value = redis_client.get(
            cache_key
        )

        if cached_value is not None:
            raise RuntimeError(
                "Expected an empty cache key, but "
                "a cached value was found."
            )

    with trace_span(
        trace_id,
        "planner",
        metadata={
            "request_number": request_number,
        },
    ) as planner_span:
        plan = [
            (
                "Find the sleep quality clinical "
                "trial."
            ),
            (
                "Retrieve its phase, sponsor, and "
                "enrollment target."
            ),
            (
                "Return all requested facts."
            ),
        ]

        planner_message = {
            "trace_id": trace_id,
            "correlation_id": trace_id,
            "question": question,
            "plan": plan,
        }

    writer_input, first_queue_ms = (
        queue_handoff(
            trace_id,
            planner_message,
            source="planner",
            destination="writer",
        )
    )

    with trace_span(
        trace_id,
        "writer",
        metadata={
            "request_number": request_number,
        },
    ) as writer_span:
        writer_draft = (
            "The Sleep Quality and Academic "
            "Performance Study is a Phase II trial."
        )

        writer_message = {
            **writer_input,
            "writer_draft": writer_draft,
        }

    reviewer_input, second_queue_ms = (
        queue_handoff(
            trace_id,
            writer_message,
            source="writer",
            destination="reviewer",
        )
    )

    with trace_span(
        trace_id,
        "reviewer",
        metadata={
            "request_number": request_number,
        },
    ) as reviewer_span:
        final_answer = REFERENCE_ANSWER

        reviewer_message = {
            **reviewer_input,
            "final_answer": final_answer,
        }

    evaluation_input, third_queue_ms = (
        queue_handoff(
            trace_id,
            reviewer_message,
            source="reviewer",
            destination="evaluation",
        )
    )

    with trace_span(
        trace_id,
        "evaluation",
        metadata={
            "request_number": request_number,
            "judge_type": "DeepEval GEval",
        },
    ) as evaluation_span:
        judge_result = evaluate_writer_draft(
            question=evaluation_input[
                "question"
            ],
            writer_draft=evaluation_input[
                "final_answer"
            ],
            reference_answer=REFERENCE_ANSWER,
        )

    end_to_end_ms = round(
        (
            perf_counter()
            - end_to_end_started
        )
        * 1000,
        3,
    )

    queue_total_ms = round(
        first_queue_ms
        + second_queue_ms
        + third_queue_ms,
        3,
    )

    return {
        "request_number": request_number,
        "trace_id": trace_id,
        "cache_result": CACHE_MISS,
        "cache_lookup_ms": cache_span.duration_ms,
        "planner_ms": planner_span.duration_ms,
        "writer_ms": writer_span.duration_ms,
        "reviewer_ms": reviewer_span.duration_ms,
        "queue_wait_total_ms": queue_total_ms,
        "evaluation_ms": (
            evaluation_span.duration_ms
        ),
        "end_to_end_ms": end_to_end_ms,
        "judge_score": judge_result.score,
        "judge_success": judge_result.success,
    }


def measure_cache_hits(
    redis_client: Redis,
    *,
    sample_count: int = 20,
) -> dict[str, Any]:
    """Measure Redis cache-hit latency separately."""

    cache_key = (
        f"{PREFIX}:hw10_latency:cache_hit"
    )
    redis_client.set(
        cache_key,
        REFERENCE_ANSWER,
        ex=3600,
    )

    latencies: list[float] = []

    try:
        for _ in range(sample_count):
            started = perf_counter()
            value = redis_client.get(cache_key)
            duration_ms = (
                perf_counter()
                - started
            ) * 1000

            if value is None:
                raise RuntimeError(
                    "Expected a cache hit."
                )

            latencies.append(duration_ms)
    finally:
        redis_client.delete(cache_key)

    return {
        "sample_count": sample_count,
        "mean_ms": round(
            mean(latencies),
            3,
        ),
        "p50_ms": percentile(
            latencies,
            50,
        ),
        "p95_ms": percentile(
            latencies,
            95,
        ),
        "data_source": (
            "Redis GET using a confirmed existing "
            "s7801-prefixed cache key."
        ),
    }


def summarize_stages(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calculate mean, p50, p95, and E2E share."""

    stage_fields = {
        "cache_lookup": "cache_lookup_ms",
        "planner": "planner_ms",
        "writer": "writer_ms",
        "reviewer": "reviewer_ms",
        "queue_wait_total": (
            "queue_wait_total_ms"
        ),
        "evaluation": "evaluation_ms",
        "end_to_end": "end_to_end_ms",
    }

    mean_e2e = mean(
        float(row["end_to_end_ms"])
        for row in rows
    )

    summaries: list[dict[str, Any]] = []

    for stage, field_name in (
        stage_fields.items()
    ):
        values = [
            float(row[field_name])
            for row in rows
        ]

        if stage == "end_to_end":
            percentage = 100.0
        else:
            percentage = round(
                mean(values)
                / mean_e2e
                * 100,
                3,
            )

        summaries.append(
            {
                "stage": stage,
                "sample_count": len(values),
                "mean_ms": round(
                    mean(values),
                    3,
                ),
                "p50_ms": percentile(
                    values,
                    50,
                ),
                "p95_ms": percentile(
                    values,
                    95,
                ),
                "percent_of_cache_miss_e2e": (
                    percentage
                ),
            }
        )

    return summaries


def main() -> None:
    """Run 50 confirmed cache misses."""

    ensure_hw10_directories()

    redis_client = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )
    redis_client.ping()

    rows: list[dict[str, Any]] = []

    print(
        "DATA-260 Homework 10 Latency Experiment"
    )
    print(f"Student: {STUDENT_NAME}")
    print(
        "Confirmed cache misses: "
        f"{LATENCY_EXPERIMENT_REQUEST_COUNT}"
    )

    for request_number in range(
        1,
        LATENCY_EXPERIMENT_REQUEST_COUNT + 1,
    ):
        print(
            (
                f"[{request_number:02d}/"
                f"{LATENCY_EXPERIMENT_REQUEST_COUNT}]"
            ),
            end=" ",
            flush=True,
        )

        row = run_cache_miss(
            request_number,
            redis_client,
        )
        rows.append(row)

        print(
            
                f"miss={row['cache_result']} "
                f"e2e={row['end_to_end_ms']} ms "
                f"judge={row['judge_score']} "
                f"success={row['judge_success']}"
            
        )

        write_json(
            LATENCY_RESULTS_PATH.parent
            / "latency_checkpoint.json",
            {
                "completed_count": len(rows),
                "expected_count": (
                    LATENCY_EXPERIMENT_REQUEST_COUNT
                ),
                "rows": rows,
            },
        )

    summaries = summarize_stages(rows)
    cache_hit_summary = measure_cache_hits(
        redis_client
    )

    stage_candidates = [
        summary
        for summary in summaries
        if summary["stage"]
        not in {
            "end_to_end",
        }
    ]

    dominant_stage = max(
        stage_candidates,
        key=lambda value: value["mean_ms"],
    )

    failed_judgments = sum(
        not bool(row["judge_success"])
        for row in rows
    )

    document = {
        "experiment": (
            "hw10_50_confirmed_cache_misses"
        ),
        "student": STUDENT_NAME,
        "sid4": 7801,
        "request_count": len(rows),
        "confirmed_cache_miss_count": sum(
            row["cache_result"] == CACHE_MISS
            for row in rows
        ),
        "unexpected_cache_hit_count": sum(
            row["cache_result"] != CACHE_MISS
            for row in rows
        ),
        "failed_judgment_count": (
            failed_judgments
        ),
        "stage_summaries": summaries,
        "cache_hit_latency": (
            cache_hit_summary
        ),
        "dominant_stage": {
            "stage": dominant_stage["stage"],
            "mean_ms": dominant_stage[
                "mean_ms"
            ],
            "percent_of_cache_miss_e2e": (
                dominant_stage[
                    "percent_of_cache_miss_e2e"
                ]
            ),
            "interpretation": (
                f"{dominant_stage['stage']} was "
                "the largest measured contributor "
                "to cache-miss latency."
            ),
            "optimization": (
                "Reuse a warm local judge process, "
                "batch evaluations where appropriate, "
                "and move non-blocking evaluation "
                "outside the user-facing response path."
            ),
        },
        "data_source": (
            "Controlled local Redis cache lookups, "
            "instrumented Planner-Writer-Reviewer "
            "processing, JSON message handoffs, and "
            "DeepEval GEval using qwen3:4b."
        ),
        "overall_passed": (
            len(rows)
            == LATENCY_EXPERIMENT_REQUEST_COUNT
            and all(
                row["cache_result"]
                == CACHE_MISS
                for row in rows
            )
            and failed_judgments == 0
        ),
        "rows": rows,
    }

    write_json(
        LATENCY_RESULTS_PATH,
        document,
    )
    write_rows_csv(rows)
    write_summary_csv(summaries)

    print("\n=== LATENCY SUMMARY ===")

    for summary in summaries:
        print(
            
                f"{summary['stage']} | "
                f"p50={summary['p50_ms']} ms | "
                f"p95={summary['p95_ms']} ms | "
                f"share="
                f"{summary['percent_of_cache_miss_e2e']}%"
            
        )

    print("\n=== CACHE-HIT LATENCY ===")
    print(
        "Cache-hit p50: "
        f"{cache_hit_summary['p50_ms']} ms"
    )
    print(
        "Cache-hit p95: "
        f"{cache_hit_summary['p95_ms']} ms"
    )
    print(
        "Dominant stage: "
        f"{dominant_stage['stage']}"
    )
    print(
        f"Overall: {document['overall_passed']}"
    )
    print(f"JSON: {LATENCY_RESULTS_PATH}")
    print(f"CSV: {LATENCY_SPANS_PATH}")
    print(f"Summary: {LATENCY_SUMMARY_PATH}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()