from __future__ import annotations

import argparse
import csv
import json
from code.hw7_agent import (
    MODEL_NAME,
    run_agent,
)
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from src.model_client import ModelClient

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

CASES_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw07"
    / "cases"
)

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw07"
    / "raw"
)

TASKS_PATH = (
    CASES_DIRECTORY
    / "agent_verification_tasks.json"
)

SHOWCASE_PATH = (
    RAW_DIRECTORY
    / "agent_verification_tasks.json"
)

ERROR_PATH = (
    RAW_DIRECTORY
    / "agent_error_recovery.json"
)

RESULTS_PATH = (
    RAW_DIRECTORY
    / "agent_reliability_results.json"
)

RESULTS_CSV_PATH = (
    RAW_DIRECTORY
    / "agent_reliability_results.csv"
)

METRICS_PATH = (
    RAW_DIRECTORY
    / "agent_reliability_metrics.json"
)

TOOL_LOG_PATH = (
    RAW_DIRECTORY
    / "agent_tool_calls.jsonl"
)


TASKS: tuple[
    dict[str, Any],
    ...,
] = (
    {
        "task_id": "task_a",
        "name": "search_then_detail",
        "prompt": (
            "Search for clinical trials related to "
            "sleep, then retrieve full details for "
            "the first result."
        ),
        "expected_tools": [
            "search_trials",
            "trial_details",
        ],
        "minimum_tool_calls": 2,
    },
    {
        "task_id": "task_b",
        "name": "aggregate_then_example",
        "prompt": (
            "Show the number of clinical trials in "
            "each trial phase, then search for one "
            "sleep trial as a supporting example."
        ),
        "expected_tools": [
            "trial_phase_summary",
            "search_trials",
        ],
        "minimum_tool_calls": 2,
    },
    {
        "task_id": "task_c",
        "name": "compare_two_trials",
        "prompt": (
            "First call search_trials using exactly "
            "{\"query\": \"Study\", \"limit\": 4}. "
            "From that result, select two different "
            "trial IDs. Call trial_details once for "
            "the first ID and once for the second ID. "
            "Then compare the two trials by title, "
            "phase, sponsor, and enrollment target."
        ),
        "expected_tools": [
            "search_trials",
            "trial_details",
            "trial_details",
        ],
        "minimum_tool_calls": 3,
    },
)


ERROR_CASE = {
    "case_id": "nonexistent_id",
    "name": "impossible_trial_id",
    "prompt": (
        "Retrieve details for clinical trial ID "
        "999999999. If it does not exist, explain "
        "the tool error without crashing."
    ),
    "expected_tool": "trial_details",
    "trial_id": 999999999,
}


def utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(
        UTC
    ).isoformat()


def is_subsequence(
    expected: list[str],
    observed: list[str],
) -> bool:
    """Return whether expected tools occur in order."""

    expected_index = 0

    for tool_name in observed:
        if (
            expected_index
            < len(expected)
            and tool_name
            == expected[
                expected_index
            ]
        ):
            expected_index += 1

    return (
        expected_index
        == len(expected)
    )


def successful_tool_results(
    result: dict[str, Any],
) -> bool:
    """Return whether every tool invocation succeeded."""

    calls = result.get(
        "tool_calls",
        [],
    )

    return bool(
        calls
    ) and all(
        bool(
            call.get(
                "result",
                {},
            ).get("ok")
        )
        for call in calls
    )


def distinct_detail_ids(
    result: dict[str, Any],
) -> set[int]:
    """Return distinct IDs passed to trial_details."""

    identifiers: set[int] = set()

    for call in result.get(
        "tool_calls",
        [],
    ):
        if call.get(
            "tool_name"
        ) != "trial_details":
            continue

        raw_identifier = call.get(
            "inputs",
            {},
        ).get("trial_id")

        try:
            identifiers.add(
                int(raw_identifier)
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

    return identifiers


def verify_task(
    task: dict[str, Any],
    result: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Deterministically verify one task result."""

    failures: list[str] = []

    observed_tools = [
        str(call.get("tool_name"))
        for call in result.get(
            "tool_calls",
            [],
        )
    ]

    if (
        result.get("stop_reason")
        != "normal_completion"
    ):
        failures.append(
            "agent_did_not_complete"
        )

    if (
        int(
            result.get(
                "tool_call_count",
                0,
            )
        )
        < int(
            task[
                "minimum_tool_calls"
            ]
        )
    ):
        failures.append(
            "lost_multi_step_chain"
        )

    if not is_subsequence(
        task["expected_tools"],
        observed_tools,
    ):
        failures.append(
            "lost_multi_step_chain"
        )

    if not successful_tool_results(
        result
    ):
        failures.append(
            "tool_execution_failure"
        )

    if (
        task["task_id"]
        == "task_c"
        and len(
            distinct_detail_ids(
                result
            )
        )
        < 2
    ):
        failures.append(
            "lost_multi_step_chain"
        )

    return (
        not failures,
        sorted(
            set(failures)
        ),
    )


def verify_error_case(
    result: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Verify graceful nonexistent-ID handling."""

    failures: list[str] = []

    calls = result.get(
        "tool_calls",
        [],
    )

    observed_tools = [
        call.get("tool_name")
        for call in calls
    ]

    if "trial_details" not in (
        observed_tools
    ):
        failures.append(
            "missing_error_tool_call"
        )

    failed_detail_results = [
        call
        for call in calls
        if (
            call.get("tool_name")
            == "trial_details"
            and not call.get(
                "result",
                {},
            ).get("ok")
        )
    ]

    if not failed_detail_results:
        failures.append(
            "missing_useful_tool_error"
        )

    if (
        result.get("stop_reason")
        != "normal_completion"
    ):
        failures.append(
            "agent_did_not_stop_cleanly"
        )

    answer = str(
        result.get(
            "answer",
            "",
        )
    ).casefold()

    if not any(
        phrase in answer
        for phrase in (
            "not found",
            "does not exist",
            "could not find",
            "no clinical trial",
        )
    ):
        failures.append(
            "error_not_explained"
        )

    return (
        not failures,
        sorted(
            set(failures)
        ),
    )


def result_record(
    task: dict[str, Any],
    attempt_number: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Create one raw reliability record."""

    success, verifier_failures = (
        verify_task(
            task,
            result,
        )
    )

    model_failures = list(
        result.get(
            "failure_classification",
            [],
        )
    )

    failures = sorted(
        set(
            model_failures
            + verifier_failures
        )
    )

    observed_tools = [
        call.get("tool_name")
        for call in result.get(
            "tool_calls",
            [],
        )
    ]

    return {
        "task_id": task["task_id"],
        "task_name": task["name"],
        "attempt_number": (
            attempt_number
        ),
        "prompt": task["prompt"],
        "success": success,
        "observed_tools": (
            observed_tools
        ),
        "expected_tools": (
            task["expected_tools"]
        ),
        "tool_call_count": (
            result.get(
                "tool_call_count",
                0,
            )
        ),
        "repair_count": (
            result.get(
                "repair_count",
                0,
            )
        ),
        "well_formed_before_repair": (
            result.get(
                "well_formed_before_repair",
                False,
            )
        ),
        "well_formed_after_repair": (
            result.get(
                "well_formed_after_repair",
                False,
            )
        ),
        "failure_classification": (
            failures
        ),
        "stop_reason": (
            result.get(
                "stop_reason"
            )
        ),
        "answer": result.get(
            "answer"
        ),
        "input_tokens": (
            result.get(
                "input_tokens",
                0,
            )
        ),
        "output_tokens": (
            result.get(
                "output_tokens",
                0,
            )
        ),
        "total_tokens": (
            result.get(
                "total_tokens",
                0,
            )
        ),
        "latency_ms": (
            result.get(
                "latency_ms",
                0,
            )
        ),
        "run_id": result.get(
            "run_id"
        ),
    }


def run_showcase(
    model: ModelClient,
) -> dict[str, Any]:
    """Run the three fixed tasks once."""

    showcase_tasks: list[
        dict[str, Any]
    ] = []

    print(
        "\n=== PART 2 VERIFICATION TASKS ==="
    )

    for task in TASKS:
        print(
            "\n---",
            task["task_id"],
            ":",
            task["name"],
            "---",
        )

        result = run_agent(
            task["prompt"],
            model=model,
            log_path=TOOL_LOG_PATH,
            run_label=task[
                "task_id"
            ],
        )

        success, failures = (
            verify_task(
                task,
                result,
            )
        )

        observed_tools = [
            call.get("tool_name")
            for call in result.get(
                "tool_calls",
                [],
            )
        ]

        showcase_record = {
            **task,
            "success": success,
            "observed_tools": (
                observed_tools
            ),
            "verifier_failures": (
                failures
            ),
            "result": result,
        }

        showcase_tasks.append(
            showcase_record
        )

        print(
            "Success:",
            success,
        )

        print(
            "Tool calls:",
            result[
                "tool_call_count"
            ],
        )

        print(
            "Observed tools:",
            observed_tools,
        )

        print(
            "Repairs:",
            result[
                "repair_count"
            ],
        )

        print(
            "Stop reason:",
            result[
                "stop_reason"
            ],
        )

        print(
            "Answer:",
            result["answer"],
        )

    document = {
        "experiment": (
            "hw7_part2_showcase"
        ),
        "model": MODEL_NAME,
        "task_count": len(
            showcase_tasks
        ),
        "all_passed": all(
            task["success"]
            for task in showcase_tasks
        ),
        "tasks": showcase_tasks,
        "generated_at": (
            utc_timestamp()
        ),
    }

    SHOWCASE_PATH.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    return document


def run_error_recovery(
    model: ModelClient,
) -> dict[str, Any]:
    """Run the required nonexistent-ID case."""

    print(
        "\n=== ERROR RECOVERY CASE ==="
    )

    result = run_agent(
        ERROR_CASE["prompt"],
        model=model,
        log_path=TOOL_LOG_PATH,
        run_label="nonexistent-id",
    )

    success, failures = (
        verify_error_case(
            result
        )
    )

    document = {
        "experiment": (
            "hw7_part2_error_recovery"
        ),
        "case": {
            **ERROR_CASE,
            "handled_without_crash": (
                success
            ),
            "verifier_failures": (
                failures
            ),
            "result": result,
        },
        "generated_at": (
            utc_timestamp()
        ),
    }

    ERROR_PATH.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "Handled without crash:",
        success,
    )

    print(
        "Tool calls:",
        result[
            "tool_call_count"
        ],
    )

    print(
        "Stop reason:",
        result[
            "stop_reason"
        ],
    )

    print(
        "Answer:",
        result["answer"],
    )

    return document


def attempt_schedule(
    attempt_count: int,
) -> list[dict[str, Any]]:
    """Distribute attempts across the fixed tasks."""

    return [
        TASKS[
            index % len(TASKS)
        ]
        for index in range(
            attempt_count
        )
    ]


def write_results_csv(
    records: list[
        dict[str, Any]
    ],
) -> None:
    """Save flattened reliability records."""

    fields = [
        "task_id",
        "task_name",
        "attempt_number",
        "success",
        "observed_tools",
        "expected_tools",
        "tool_call_count",
        "repair_count",
        "well_formed_before_repair",
        "well_formed_after_repair",
        "failure_classification",
        "stop_reason",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "latency_ms",
        "run_id",
    ]

    with RESULTS_CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for record in records:
            writer.writerow({
                field: (
                    json.dumps(
                        record[field]
                    )
                    if isinstance(
                        record[field],
                        list,
                    )
                    else record[field]
                )
                for field in fields
            })


def calculate_metrics(
    records: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """Calculate Part 2 reliability metrics."""

    attempt_count = len(
        records
    )

    successful_count = sum(
        bool(record["success"])
        for record in records
    )

    before_count = sum(
        bool(
            record[
                "well_formed_before_repair"
            ]
        )
        for record in records
    )

    after_count = sum(
        bool(
            record[
                "well_formed_after_repair"
            ]
        )
        for record in records
    )

    repaired_count = sum(
        int(
            record["repair_count"]
        )
        > 0
        for record in records
    )

    failure_counts: Counter[
        str
    ] = Counter()

    for record in records:
        for failure in record[
            "failure_classification"
        ]:
            failure_counts[
                failure
            ] += 1

    required_failure_names = (
        "malformed_arguments",
        "unknown_tool",
        "text_when_tool_required",
        "lost_multi_step_chain",
    )

    classified_failures = {
        name: failure_counts.get(
            name,
            0,
        )
        for name in (
            required_failure_names
        )
    }

    for name, count in sorted(
        failure_counts.items()
    ):
        if name not in (
            classified_failures
        ):
            classified_failures[
                name
            ] = count

    return {
        "experiment": (
            "hw7_agent_reliability"
        ),
        "model": MODEL_NAME,
        "model_settings": {
            "temperature": 0.0,
            "num_ctx": 2048,
            "num_predict": 256,
        },
        "attempt_count": (
            attempt_count
        ),
        "successful_attempt_count": (
            successful_count
        ),
        "task_success_rate_percent": round(
            successful_count
            / attempt_count
            * 100,
            2,
        ),
        "well_formed_before_repair_count": (
            before_count
        ),
        "well_formed_before_repair_percent": round(
            before_count
            / attempt_count
            * 100,
            2,
        ),
        "well_formed_after_repair_count": (
            after_count
        ),
        "well_formed_after_repair_percent": round(
            after_count
            / attempt_count
            * 100,
            2,
        ),
        "attempts_using_repair": (
            repaired_count
        ),
        "repair_rate_percent": round(
            repaired_count
            / attempt_count
            * 100,
            2,
        ),
        "failure_classification": (
            classified_failures
        ),
        "total_tool_calls": sum(
            int(
                record[
                    "tool_call_count"
                ]
            )
            for record in records
        ),
        "mean_tool_calls": round(
            fmean(
                float(
                    record[
                        "tool_call_count"
                    ]
                )
                for record in records
            ),
            3,
        ),
        "mean_total_tokens": round(
            fmean(
                float(
                    record[
                        "total_tokens"
                    ]
                )
                for record in records
            ),
            3,
        ),
        "mean_latency_ms": round(
            fmean(
                float(
                    record[
                        "latency_ms"
                    ]
                )
                for record in records
            ),
            3,
        ),
        "generated_at": (
            utc_timestamp()
        ),
    }


def run_reliability(
    model: ModelClient,
    attempt_count: int,
) -> dict[str, Any]:
    """Run the fixed reliability sweep."""

    records: list[
        dict[str, Any]
    ] = []

    print(
        "\n=== RELIABILITY SWEEP ==="
    )

    for attempt_number, task in enumerate(
        attempt_schedule(
            attempt_count
        ),
        start=1,
    ):
        print(
            f"Attempt {attempt_number}/"
            f"{attempt_count} | "
            f"{task['task_id']}"
        )

        result = run_agent(
            task["prompt"],
            model=model,
            log_path=TOOL_LOG_PATH,
            run_label=(
                f"reliability-"
                f"{attempt_number:02d}-"
                f"{task['task_id']}"
            ),
        )

        record = result_record(
            task,
            attempt_number,
            result,
        )

        records.append(
            record
        )

        print(
            "  success =",
            record["success"],
            "| tools =",
            record[
                "observed_tools"
            ],
            "| repairs =",
            record[
                "repair_count"
            ],
            "| stop =",
            record[
                "stop_reason"
            ],
        )

    results_document = {
        "experiment": (
            "hw7_agent_reliability_results"
        ),
        "model": MODEL_NAME,
        "attempt_count": (
            attempt_count
        ),
        "records": records,
        "generated_at": (
            utc_timestamp()
        ),
    }

    RESULTS_PATH.write_text(
        json.dumps(
            results_document,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    write_results_csv(
        records
    )

    metrics = calculate_metrics(
        records
    )

    METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\n=== RELIABILITY METRICS ==="
    )

    print(
        json.dumps(
            metrics,
            indent=2,
        )
    )

    return metrics


def save_cases() -> None:
    """Save the fixed verification cases."""

    CASES_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    TASKS_PATH.write_text(
        json.dumps(
            {
                "tasks": TASKS,
                "error_case": (
                    ERROR_CASE
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse experiment options."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--attempts",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--showcase-only",
        action="store_true",
    )

    return parser.parse_args()


def main() -> None:
    """Run Homework 7 Part 2 experiments."""

    arguments = parse_arguments()

    if arguments.attempts < 20:
        raise ValueError(
            "Part 2 requires at least 20 attempts."
        )

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_cases()

    model = ModelClient(
        model=MODEL_NAME,
        temperature=0.0,
        num_ctx=2048,
        num_predict=256,
    )

    print(
        "DATA-260 Homework 7 Part 2"
    )

    print(
        "Model:",
        MODEL_NAME,
    )

    print(
        "Fixed verification tasks:",
        len(TASKS),
    )

    showcase = run_showcase(
        model
    )

    error_document = (
        run_error_recovery(
            model
        )
    )

    if not arguments.showcase_only:
        run_reliability(
            model,
            arguments.attempts,
        )

    print(
        "\nShowcase passed:",
        showcase["all_passed"],
    )

    print(
        "Error recovery passed:",
        error_document[
            "case"
        ][
            "handled_without_crash"
        ],
    )

    print(
        "\nPart 2 output files:"
    )

    for path in (
        SHOWCASE_PATH,
        ERROR_PATH,
        RESULTS_PATH,
        RESULTS_CSV_PATH,
        METRICS_PATH,
        TOOL_LOG_PATH,
    ):
        print(path)


if __name__ == "__main__":
    main()
