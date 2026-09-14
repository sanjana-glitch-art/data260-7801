from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from code.agent_graph import (  # noqa: E402
    initialize_state,
    run_workflow
)
from src.model_client import ModelClient  # noqa: E402


REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw02"
)

CASE_DIRECTORY = (
    REPORT_DIRECTORY
    / "cases"
)

RAW_DIRECTORY = (
    REPORT_DIRECTORY
    / "raw"
)

SCHEMA_INPUT_PATH = (
    CASE_DIRECTORY
    / "schema_input.json"
)

ADVERSARIAL_INPUT_PATH = (
    CASE_DIRECTORY
    / "adversarial_input.json"
)

SCHEMA_RESULTS_PATH = (
    RAW_DIRECTORY
    / "schema_validation_results.json"
)

SCHEMA_CSV_PATH = (
    RAW_DIRECTORY
    / "schema_validation_results.csv"
)

SCHEMA_METRICS_PATH = (
    RAW_DIRECTORY
    / "schema_validation_metrics.json"
)

CEILING_RESULTS_PATH = (
    RAW_DIRECTORY
    / "ceiling_comparison_results.json"
)

CEILING_CSV_PATH = (
    RAW_DIRECTORY
    / "ceiling_comparison_results.csv"
)

CEILING_METRICS_PATH = (
    RAW_DIRECTORY
    / "ceiling_comparison_metrics.json"
)

ADVERSARIAL_RESULTS_PATH = (
    RAW_DIRECTORY
    / "adversarial_results.json"
)

ADVERSARIAL_CSV_PATH = (
    RAW_DIRECTORY
    / "adversarial_results.csv"
)

ADVERSARIAL_METRICS_PATH = (
    RAW_DIRECTORY
    / "adversarial_metrics.json"
)


DEFAULT_MODEL = "qwen3:4b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_NUM_CTX = 4096
DEFAULT_NUM_PREDICT = 256

SCHEMA_RUN_COUNT = 30
SCHEMA_TURN_CEILING = 10

CEILING_RUN_COUNT = 20
CEILINGS = (2, 10)

ADVERSARIAL_RUN_COUNT = 5
ADVERSARIAL_TURN_CEILING = 2


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(
    path: Path
) -> Any:
    """Load JSON from a file."""

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(
    path: Path,
    payload: Any
) -> None:
    """Write JSON safely using a temporary file."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    temporary_path.replace(path)


def load_existing_results(
    path: Path
) -> list[dict[str, Any]]:
    """Load resumable results from an existing output file."""

    if not path.exists():
        return []

    payload = load_json(path)

    if isinstance(payload, list):
        return payload

    return payload.get(
        "results",
        []
    )


def save_results(
    path: Path,
    *,
    experiment: str,
    model: str,
    temperature: float,
    results: list[dict[str, Any]]
) -> None:
    """Write experiment results and configuration."""

    payload = {
        "experiment": experiment,
        "student": "Sanjana Thummalapalli",
        "sid4": 7801,
        "seed": 7801,
        "verifySeed": 267801,
        "model": model,
        "temperature": temperature,
        "numCtx": DEFAULT_NUM_CTX,
        "numPredict": DEFAULT_NUM_PREDICT,
        "updatedAt": utc_timestamp(),
        "results": results
    }

    write_json(
        path,
        payload
    )


def save_csv(
    path: Path,
    results: list[dict[str, Any]]
) -> None:
    """Write the flattened experiment records to CSV."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "experiment",
        "run",
        "turn_ceiling",
        "temperature",
        "status",
        "completed",
        "abandoned",
        "turn_count",
        "retry_count",
        "classification",
        "latency_ms",
        "tag_1",
        "tag_2",
        "tag_3",
        "summary",
        "reviewer_approved",
        "reviewer_issues",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "started_at",
        "finished_at"
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for result in results:
            tags = result.get(
                "planner_proposal",
                {}
            ).get(
                "tags",
                []
            )

            reviewer = result.get(
                "reviewer_feedback",
                {}
            )

            model_stats = result.get(
                "model_stats",
                {}
            )

            writer.writerow({
                "experiment": result.get(
                    "experiment",
                    ""
                ),
                "run": result.get(
                    "run",
                    ""
                ),
                "turn_ceiling": result.get(
                    "turn_ceiling",
                    ""
                ),
                "temperature": result.get(
                    "temperature",
                    ""
                ),
                "status": result.get(
                    "status",
                    ""
                ),
                "completed": result.get(
                    "completed",
                    False
                ),
                "abandoned": result.get(
                    "abandoned",
                    False
                ),
                "turn_count": result.get(
                    "turn_count",
                    0
                ),
                "retry_count": result.get(
                    "retry_count",
                    0
                ),
                "classification": result.get(
                    "classification",
                    ""
                ),
                "latency_ms": result.get(
                    "latency_ms",
                    0
                ),
                "tag_1": (
                    tags[0]
                    if len(tags) > 0
                    else ""
                ),
                "tag_2": (
                    tags[1]
                    if len(tags) > 1
                    else ""
                ),
                "tag_3": (
                    tags[2]
                    if len(tags) > 2
                    else ""
                ),
                "summary": result.get(
                    "planner_proposal",
                    {}
                ).get(
                    "summary",
                    ""
                ),
                "reviewer_approved": reviewer.get(
                    "approved",
                    False
                ),
                "reviewer_issues": json.dumps(
                    reviewer.get(
                        "issues",
                        []
                    ),
                    ensure_ascii=False
                ),
                "input_tokens": model_stats.get(
                    "cumulative_input_tokens",
                    0
                ),
                "output_tokens": model_stats.get(
                    "cumulative_output_tokens",
                    0
                ),
                "total_tokens": model_stats.get(
                    "cumulative_total_tokens",
                    0
                ),
                "started_at": result.get(
                    "started_at",
                    ""
                ),
                "finished_at": result.get(
                    "finished_at",
                    ""
                )
            })


def classify_run(
    final_state: dict[str, Any]
) -> str:
    """Classify one run by completion and retry count."""

    if not final_state.get(
        "completed",
        False
    ):
        return "hit_turn_ceiling"

    turn_count = int(
        final_state.get(
            "turn_count",
            0
        )
    )

    if turn_count <= 1:
        return "valid_first_attempt"

    if turn_count == 2:
        return "valid_after_one_retry"

    return "valid_after_two_or_more_retries"


def run_one_graph(
    *,
    experiment: str,
    run_number: int,
    input_data: dict[str, Any],
    model: str,
    temperature: float,
    turn_ceiling: int
) -> dict[str, Any]:
    """Execute one isolated graph run."""

    client = ModelClient(
        model=model,
        temperature=temperature,
        num_ctx=DEFAULT_NUM_CTX,
        num_predict=DEFAULT_NUM_PREDICT
    )

    initial_state = initialize_state(
        title=input_data["title"],
        content=input_data["content"],
        email=input_data["email"],
        task=input_data["task"],
        llm=client,
        strict=input_data.get(
            "strict",
            True
        ),
        turn_ceiling=turn_ceiling,
        force_reviewer_issue=False
    )

    started_at = utc_timestamp()
    started = perf_counter()

    # Suppress detailed node output during repeated experiments.
    captured_output = io.StringIO()

    with redirect_stdout(captured_output):
        final_state = run_workflow(
            initial_state,
            show_stream=False
        )

    latency_ms = (
        perf_counter() - started
    ) * 1000

    finished_at = utc_timestamp()

    turn_count = int(
        final_state.get(
            "turn_count",
            0
        )
    )

    return {
        "experiment": experiment,
        "run": run_number,
        "title": input_data["title"],
        "content": input_data["content"],
        "email": input_data["email"],
        "temperature": temperature,
        "turn_ceiling": turn_ceiling,
        "status": final_state.get(
            "status",
            "unknown"
        ),
        "completed": bool(
            final_state.get(
                "completed",
                False
            )
        ),
        "abandoned": bool(
            final_state.get(
                "abandoned",
                False
            )
        ),
        "turn_count": turn_count,
        "retry_count": max(
            turn_count - 1,
            0
        ),
        "classification": classify_run(
            final_state
        ),
        "planner_proposal": final_state.get(
            "planner_proposal",
            {}
        ),
        "reviewer_feedback": final_state.get(
            "reviewer_feedback",
            {}
        ),
        "validation_error": final_state.get(
            "validation_error",
            ""
        ),
        "trace": final_state.get(
            "trace",
            []
        ),
        "model_stats": client.get_stats(),
        "latency_ms": round(
            latency_ms,
            2
        ),
        "started_at": started_at,
        "finished_at": finished_at
    }


def mean_or_none(
    values: list[float]
) -> float | None:
    """Return a rounded mean, or None for no observations."""

    if not values:
        return None

    return round(
        fmean(values),
        2
    )


def create_schema_metrics(
    results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Aggregate the 30-run schema experiment."""

    classifications = [
        "valid_first_attempt",
        "valid_after_one_retry",
        "valid_after_two_or_more_retries",
        "hit_turn_ceiling"
    ]

    outcomes: dict[str, Any] = {}

    for classification in classifications:
        matching = [
            result
            for result in results
            if result["classification"] == classification
        ]

        outcomes[classification] = {
            "count": len(matching),
            "meanLatencyMs": mean_or_none([
                float(result["latency_ms"])
                for result in matching
            ])
        }

    return {
        "experiment": "schema_validation",
        "runCount": len(results),
        "turnCeiling": SCHEMA_TURN_CEILING,
        "outcomes": outcomes,
        "overallMeanLatencyMs": mean_or_none([
            float(result["latency_ms"])
            for result in results
        ]),
        "generatedAt": utc_timestamp()
    }


def create_ceiling_metrics(
    results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Aggregate the 2-versus-10 ceiling experiment."""

    ceiling_metrics: dict[str, Any] = {}

    for ceiling in CEILINGS:
        matching = [
            result
            for result in results
            if result["turn_ceiling"] == ceiling
        ]

        completed = [
            result
            for result in matching
            if result["completed"]
        ]

        abandoned = [
            result
            for result in matching
            if result["abandoned"]
        ]

        completion_rate = (
            (
                len(completed)
                / len(matching)
            ) * 100
            if matching
            else 0.0
        )

        ceiling_metrics[str(ceiling)] = {
            "turnCeiling": ceiling,
            "runCount": len(matching),
            "completedCount": len(completed),
            "abandonedCount": len(abandoned),
            "completionRatePercent": round(
                completion_rate,
                2
            ),
            "meanLatencyMs": mean_or_none([
                float(result["latency_ms"])
                for result in matching
            ]),
            "meanCompletedLatencyMs": mean_or_none([
                float(result["latency_ms"])
                for result in completed
            ]),
            "meanPlannerAttempts": mean_or_none([
                float(result["turn_count"])
                for result in matching
            ])
        }

    ceiling_two = ceiling_metrics["2"]
    ceiling_ten = ceiling_metrics["10"]

    recommended_ceiling: int | None = None
    recommendation_reason = (
        "Insufficient completed runs to select a ceiling."
    )

    if (
        ceiling_two["runCount"] == CEILING_RUN_COUNT
        and ceiling_ten["runCount"] == CEILING_RUN_COUNT
    ):
        if (
            ceiling_two["completionRatePercent"]
            >= ceiling_ten["completionRatePercent"]
        ):
            recommended_ceiling = 2
            recommendation_reason = (
                "Ceiling 2 achieved an equal or higher completion "
                "rate while limiting correction-loop work."
            )
        else:
            recommended_ceiling = 10
            recommendation_reason = (
                "Ceiling 10 achieved a higher measured completion "
                "rate than ceiling 2."
            )

    return {
        "experiment": "ceiling_comparison",
        "ceilings": ceiling_metrics,
        "recommendedCeiling": recommended_ceiling,
        "recommendationReason": recommendation_reason,
        "generatedAt": utc_timestamp()
    }


def create_adversarial_metrics(
    results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Aggregate the five adversarial runs."""

    hit_ceiling = [
        result
        for result in results
        if result["classification"] == "hit_turn_ceiling"
    ]

    rate = (
        (
            len(hit_ceiling)
            / len(results)
        ) * 100
        if results
        else 0.0
    )

    return {
        "experiment": "adversarial",
        "runCount": len(results),
        "turnCeiling": ADVERSARIAL_TURN_CEILING,
        "hitTurnCeilingCount": len(hit_ceiling),
        "hitTurnCeilingRatePercent": round(
            rate,
            2
        ),
        "preferredThresholdReached": (
            len(hit_ceiling) >= 4
        ),
        "completedCount": sum(
            1
            for result in results
            if result["completed"]
        ),
        "meanLatencyMs": mean_or_none([
            float(result["latency_ms"])
            for result in results
        ]),
        "generatedAt": utc_timestamp()
    }


def run_schema_experiment(
    model: str,
    temperature: float
) -> None:
    """Run or resume the 30-run schema experiment."""

    input_data = load_json(
        SCHEMA_INPUT_PATH
    )

    results = load_existing_results(
        SCHEMA_RESULTS_PATH
    )

    completed_runs = {
        int(result["run"])
        for result in results
    }

    print(
        "\n=== Schema Validation Experiment ==="
    )

    print(
        f"Completed: {len(completed_runs)}/"
        f"{SCHEMA_RUN_COUNT}"
    )

    for run_number in range(
        1,
        SCHEMA_RUN_COUNT + 1
    ):
        if run_number in completed_runs:
            continue

        print(
            f"Schema run {run_number}/"
            f"{SCHEMA_RUN_COUNT}"
        )

        result = run_one_graph(
            experiment="schema_validation",
            run_number=run_number,
            input_data=input_data,
            model=model,
            temperature=temperature,
            turn_ceiling=SCHEMA_TURN_CEILING
        )

        results.append(result)
        results.sort(
            key=lambda item: item["run"]
        )

        save_results(
            SCHEMA_RESULTS_PATH,
            experiment="schema_validation",
            model=model,
            temperature=temperature,
            results=results
        )

        save_csv(
            SCHEMA_CSV_PATH,
            results
        )

        print(
            f"  {result['classification']} | "
            f"attempts={result['turn_count']} | "
            f"latency={result['latency_ms']} ms"
        )

    metrics = create_schema_metrics(
        results
    )

    write_json(
        SCHEMA_METRICS_PATH,
        metrics
    )

    print(
        json.dumps(
            metrics,
            indent=2
        )
    )


def run_ceiling_experiment(
    model: str,
    temperature: float
) -> None:
    """Run or resume both 20-run ceiling groups."""

    input_data = load_json(
        SCHEMA_INPUT_PATH
    )

    results = load_existing_results(
        CEILING_RESULTS_PATH
    )

    completed_keys = {
        (
            int(result["turn_ceiling"]),
            int(result["run"])
        )
        for result in results
    }

    print(
        "\n=== Turn-Ceiling Comparison ==="
    )

    for ceiling in CEILINGS:
        completed_for_ceiling = sum(
            1
            for saved_ceiling, _ in completed_keys
            if saved_ceiling == ceiling
        )

        print(
            f"\nCeiling {ceiling}: "
            f"{completed_for_ceiling}/"
            f"{CEILING_RUN_COUNT} completed"
        )

        for run_number in range(
            1,
            CEILING_RUN_COUNT + 1
        ):
            key = (
                ceiling,
                run_number
            )

            if key in completed_keys:
                continue

            print(
                f"Ceiling {ceiling}, "
                f"run {run_number}/"
                f"{CEILING_RUN_COUNT}"
            )

            result = run_one_graph(
                experiment="ceiling_comparison",
                run_number=run_number,
                input_data=input_data,
                model=model,
                temperature=temperature,
                turn_ceiling=ceiling
            )

            results.append(result)
            results.sort(
                key=lambda item: (
                    item["turn_ceiling"],
                    item["run"]
                )
            )

            save_results(
                CEILING_RESULTS_PATH,
                experiment="ceiling_comparison",
                model=model,
                temperature=temperature,
                results=results
            )

            save_csv(
                CEILING_CSV_PATH,
                results
            )

            print(
                f"  {result['classification']} | "
                f"attempts={result['turn_count']} | "
                f"latency={result['latency_ms']} ms"
            )

    metrics = create_ceiling_metrics(
        results
    )

    write_json(
        CEILING_METRICS_PATH,
        metrics
    )

    print(
        json.dumps(
            metrics,
            indent=2
        )
    )


def run_adversarial_experiment(
    model: str,
    temperature: float
) -> None:
    """Run or resume five adversarial executions."""

    input_data = load_json(
        ADVERSARIAL_INPUT_PATH
    )

    results = load_existing_results(
        ADVERSARIAL_RESULTS_PATH
    )

    completed_runs = {
        int(result["run"])
        for result in results
    }

    print(
        "\n=== Adversarial Experiment ==="
    )

    print(
        f"Completed: {len(completed_runs)}/"
        f"{ADVERSARIAL_RUN_COUNT}"
    )

    for run_number in range(
        1,
        ADVERSARIAL_RUN_COUNT + 1
    ):
        if run_number in completed_runs:
            continue

        print(
            f"Adversarial run {run_number}/"
            f"{ADVERSARIAL_RUN_COUNT}"
        )

        result = run_one_graph(
            experiment="adversarial",
            run_number=run_number,
            input_data=input_data,
            model=model,
            temperature=temperature,
            turn_ceiling=ADVERSARIAL_TURN_CEILING
        )

        results.append(result)
        results.sort(
            key=lambda item: item["run"]
        )

        save_results(
            ADVERSARIAL_RESULTS_PATH,
            experiment="adversarial",
            model=model,
            temperature=temperature,
            results=results
        )

        save_csv(
            ADVERSARIAL_CSV_PATH,
            results
        )

        print(
            f"  {result['classification']} | "
            f"attempts={result['turn_count']} | "
            f"latency={result['latency_ms']} ms"
        )

    metrics = create_adversarial_metrics(
        results
    )

    write_json(
        ADVERSARIAL_METRICS_PATH,
        metrics
    )

    print(
        json.dumps(
            metrics,
            indent=2
        )
    )


def parse_arguments() -> argparse.Namespace:
    """Read experiment command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Run DATA-260 Homework 2 experiments."
        )
    )

    parser.add_argument(
        "--experiment",
        choices=[
            "all",
            "schema",
            "ceilings",
            "adversarial"
        ],
        default="all"
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE
    )

    return parser.parse_args()


def verify_input_files() -> None:
    """Require both frozen case files."""

    missing = [
        str(path)
        for path in [
            SCHEMA_INPUT_PATH,
            ADVERSARIAL_INPUT_PATH
        ]
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required input files: "
            + ", ".join(missing)
        )


def main() -> None:
    """Run the requested experiment groups."""

    arguments = parse_arguments()

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    verify_input_files()

    print(
        "DATA-260 Homework 2 Experiments"
    )

    print(
        f"Model: {arguments.model}"
    )

    print(
        f"Temperature: {arguments.temperature}"
    )

    print(
        f"Started: {utc_timestamp()}"
    )

    if arguments.experiment in {
        "all",
        "schema"
    }:
        run_schema_experiment(
            arguments.model,
            arguments.temperature
        )

    if arguments.experiment in {
        "all",
        "ceilings"
    }:
        run_ceiling_experiment(
            arguments.model,
            arguments.temperature
        )

    if arguments.experiment in {
        "all",
        "adversarial"
    }:
        run_adversarial_experiment(
            arguments.model,
            arguments.temperature
        )

    print(
        "\nAll requested experiments finished."
    )

    print(
        f"Finished: {utc_timestamp()}"
    )


if __name__ == "__main__":
    main()