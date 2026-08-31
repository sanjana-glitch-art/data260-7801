import csv
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.model_client import ModelClient

from agents_demo import (
    call_planner,
    call_reviewer,
    finalize_output
)


INPUT_PATH = Path(
    "reports/hw01/cases/nondeterminism_input.json"
)

RAW_DIRECTORY = Path("reports/hw01/raw")

RESULTS_JSON_PATH = (
    RAW_DIRECTORY / "nondeterminism_results.json"
)

RESULTS_CSV_PATH = (
    RAW_DIRECTORY / "nondeterminism_results.csv"
)

METRICS_JSON_PATH = (
    RAW_DIRECTORY / "nondeterminism_metrics.json"
)

FAILURES_JSON_PATH = (
    RAW_DIRECTORY / "nondeterminism_failures.json"
)

MODEL_NAME = "qwen3:4b"
TEMPERATURES = [0.7, 0.0]
RUNS_PER_TEMPERATURE = 20


def save_json(path: Path, data: Any) -> None:
    """Save JSON data using readable indentation."""
    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )


def load_existing_results() -> list[dict[str, Any]]:
    """Resume safely if a previous experiment was interrupted."""
    if not RESULTS_JSON_PATH.exists():
        return []

    return json.loads(
        RESULTS_JSON_PATH.read_text(encoding="utf-8")
    )


def percentile(
    values: list[float],
    percentage: float
) -> float:
    """Calculate a percentile using linear interpolation."""
    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return round(ordered[0], 2)

    position = (len(ordered) - 1) * percentage
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return round(ordered[lower_index], 2)

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    fraction = position - lower_index

    result = lower_value + (
        upper_value - lower_value
    ) * fraction

    return round(result, 2)


def normalized_tag_set(
    tags: list[str]
) -> tuple[str, ...]:
    """Make tag-set comparison independent of tag order."""
    return tuple(
        sorted(
            tag.strip().lower()
            for tag in tags
        )
    )


def run_pipeline(
    model: ModelClient,
    title: str,
    content: str
) -> dict[str, Any]:
    """Run Planner, Reviewer, and finalization once."""
    planner_start = time.perf_counter()

    planner_output = call_planner(
        model,
        title,
        content
    )

    planner_latency = (
        time.perf_counter() - planner_start
    ) * 1000

    reviewer_start = time.perf_counter()

    reviewer_output = call_reviewer(
        model,
        title,
        content,
        planner_output
    )

    reviewer_latency = (
        time.perf_counter() - reviewer_start
    ) * 1000

    final_output = finalize_output(
        reviewer_output,
        title,
        content
    )

    return {
        "planner": planner_output,
        "reviewer": reviewer_output,
        "final": final_output,
        "plannerLatencyMs": round(
            planner_latency,
            2
        ),
        "reviewerLatencyMs": round(
            reviewer_latency,
            2
        ),
        "latencyMs": round(
            planner_latency + reviewer_latency,
            2
        )
    }


def calculate_metrics(
    results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Calculate all metrics required by the assignment."""
    metrics: dict[str, Any] = {}

    for temperature in TEMPERATURES:
        temperature_results = [
            result
            for result in results
            if result["temperature"] == temperature
        ]

        tag_sets = [
            normalized_tag_set(result["tags"])
            for result in temperature_results
        ]

        distinct_tag_sets = set(tag_sets)

        tag_counter: Counter[str] = Counter()

        for tag_set in tag_sets:
            # Each tag counts at most once in each run.
            tag_counter.update(set(tag_set))

        tags_in_all_runs = sorted(
            tag
            for tag, count in tag_counter.items()
            if count == len(temperature_results)
        )

        tags_in_exactly_one_run = sorted(
            tag
            for tag, count in tag_counter.items()
            if count == 1
        )

        latencies = [
            result["latencyMs"]
            for result in temperature_results
        ]

        key = f"{temperature:.1f}"

        metrics[key] = {
            "temperature": temperature,
            "runCount": len(temperature_results),
            "distinctTagSets": len(
                distinct_tag_sets
            ),
            "tagsInAllRuns": tags_in_all_runs,
            "tagsInExactlyOneRun": (
                tags_in_exactly_one_run
            ),
            "latencyP50Ms": percentile(
                latencies,
                0.50
            ),
            "latencyP95Ms": percentile(
                latencies,
                0.95
            ),
            "latencyP99Ms": percentile(
                latencies,
                0.99
            )
        }

    return metrics


def save_csv(
    results: list[dict[str, Any]]
) -> None:
    """Save machine-readable CSV results."""
    fieldnames = [
        "temperature",
        "runNumber",
        "timestamp",
        "model",
        "tags",
        "summary",
        "plannerLatencyMs",
        "reviewerLatencyMs",
        "latencyMs",
        "reviewerChanged"
    ]

    with RESULTS_CSV_PATH.open(
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
            writer.writerow({
                "temperature": result["temperature"],
                "runNumber": result["runNumber"],
                "timestamp": result["timestamp"],
                "model": result["model"],
                "tags": json.dumps(
                    result["tags"]
                ),
                "summary": result["summary"],
                "plannerLatencyMs": (
                    result["plannerLatencyMs"]
                ),
                "reviewerLatencyMs": (
                    result["reviewerLatencyMs"]
                ),
                "latencyMs": result["latencyMs"],
                "reviewerChanged": (
                    result["reviewerChanged"]
                )
            })


def main() -> None:
    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    fixed_input = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    title = fixed_input["title"]
    content = fixed_input["content"]

    results = load_existing_results()
    failures: list[dict[str, Any]] = []

    if FAILURES_JSON_PATH.exists():
        failures = json.loads(
            FAILURES_JSON_PATH.read_text(
                encoding="utf-8"
            )
        )

    print("Fixed input loaded:")
    print(json.dumps(fixed_input, indent=2))
    print(f"\nModel: {MODEL_NAME}")
    print(
        f"Target: {RUNS_PER_TEMPERATURE} runs "
        "per temperature"
    )

    for temperature in TEMPERATURES:
        completed = sum(
            1
            for result in results
            if result["temperature"] == temperature
        )

        print(
            f"\nTemperature {temperature}: "
            f"{completed} runs already completed."
        )

        model = ModelClient(
            model=MODEL_NAME,
            base_url="http://localhost:11434",
            temperature=temperature,
            num_ctx=2048,
            num_predict=256
        )

        for run_number in range(
            completed + 1,
            RUNS_PER_TEMPERATURE + 1
        ):
            print(
                f"\nTemperature {temperature}, "
                f"run {run_number}/"
                f"{RUNS_PER_TEMPERATURE}"
            )

            success = False

            for attempt in range(1, 4):
                try:
                    pipeline_result = run_pipeline(
                        model,
                        title,
                        content
                    )

                    final_output = (
                        pipeline_result["final"]
                    )

                    result = {
                        "temperature": temperature,
                        "runNumber": run_number,
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "model": MODEL_NAME,
                        "title": title,
                        "content": content,
                        "tags": final_output["tags"],
                        "summary": (
                            final_output["summary"]
                        ),
                        "planner": (
                            pipeline_result["planner"]
                        ),
                        "reviewer": (
                            pipeline_result["reviewer"]
                        ),
                        "reviewerChanged": (
                            pipeline_result[
                                "reviewer"
                            ].get("changed", False)
                        ),
                        "plannerLatencyMs": (
                            pipeline_result[
                                "plannerLatencyMs"
                            ]
                        ),
                        "reviewerLatencyMs": (
                            pipeline_result[
                                "reviewerLatencyMs"
                            ]
                        ),
                        "latencyMs": (
                            pipeline_result["latencyMs"]
                        )
                    }

                    results.append(result)
                    save_json(
                        RESULTS_JSON_PATH,
                        results
                    )

                    print(
                        "Tags:",
                        json.dumps(
                            result["tags"]
                        )
                    )
                    print(
                        "Latency:",
                        f'{result["latencyMs"]} ms'
                    )

                    success = True
                    break

                except Exception as error:
                    failure = {
                        "temperature": temperature,
                        "runNumber": run_number,
                        "attempt": attempt,
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "error": repr(error)
                    }

                    failures.append(failure)

                    save_json(
                        FAILURES_JSON_PATH,
                        failures
                    )

                    print(
                        f"Attempt {attempt} failed:",
                        repr(error)
                    )

            if not success:
                raise RuntimeError(
                    f"Run {run_number} at temperature "
                    f"{temperature} failed three times."
                )

    save_csv(results)

    metrics = calculate_metrics(results)

    save_json(
        METRICS_JSON_PATH,
        metrics
    )

    print("\n=== Experiment Metrics ===")
    print(json.dumps(metrics, indent=2))

    print("\nFiles created:")
    print(RESULTS_JSON_PATH)
    print(RESULTS_CSV_PATH)
    print(METRICS_JSON_PATH)


if __name__ == "__main__":
    main()