from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw04"
    / "raw"
)

RESULTS_JSON_PATH = (
    RAW_DIRECTORY
    / "n_plus_one_results.json"
)

RESULTS_CSV_PATH = (
    RAW_DIRECTORY
    / "n_plus_one_results.csv"
)

METRICS_PATH = (
    RAW_DIRECTORY
    / "n_plus_one_metrics.json"
)


BASE_URL = "http://127.0.0.1:8601"

PAGE_SIZES = [
    10,
    50,
    100,
]

VERSIONS = [
    "naive",
    "optimized",
]

RUNS_PER_CONFIGURATION = 30

TOTAL_TRIALS = 5000

REQUEST_TIMEOUT_SECONDS = 60


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def percentile(
    values: list[float],
    percentile_value: float,
) -> float:
    """Calculate a percentile using linear interpolation."""

    if not values:
        raise ValueError(
            "Cannot calculate a percentile "
            "from an empty list."
        )

    ordered_values = sorted(
        values
    )

    if len(ordered_values) == 1:
        return ordered_values[0]

    position = (
        len(ordered_values) - 1
    ) * percentile_value

    lower_index = int(
        position
    )

    upper_index = min(
        lower_index + 1,
        len(ordered_values) - 1,
    )

    fraction = (
        position - lower_index
    )

    lower_value = ordered_values[
        lower_index
    ]

    upper_value = ordered_values[
        upper_index
    ]

    return (
        lower_value
        + (
            upper_value
            - lower_value
        )
        * fraction
    )


def experiment_page(
    run_number: int,
    page_size: int,
) -> int:
    """Choose a deterministic page for an experiment run."""

    maximum_page = max(
        TOTAL_TRIALS // page_size,
        1,
    )

    return (
        (
            (run_number - 1)
            * 17
        )
        % maximum_page
    ) + 1


def check_server() -> None:
    """Verify that FastAPI is running."""

    try:
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(
            "FastAPI is not available at "
            f"{BASE_URL}. Start it before running "
            "the experiment."
        ) from error


def run_request(
    version: str,
    page_size: int,
    run_number: int,
) -> dict[str, Any]:
    """Run one measured request."""

    page = experiment_page(
        run_number,
        page_size,
    )

    endpoint = (
        f"{BASE_URL}"
        f"/api/performance/trials/{version}"
    )

    started_at = perf_counter()

    response = requests.get(
        endpoint,
        params={
            "page": page,
            "page_size": page_size,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    client_latency_ms = (
        perf_counter()
        - started_at
    ) * 1000

    response.raise_for_status()

    payload = response.json()

    return {
        "timestamp": utc_timestamp(),
        "version": version,
        "page_size": page_size,
        "run_number": run_number,
        "page": page,
        "status_code": response.status_code,
        "record_count": payload[
            "record_count"
        ],
        "query_count": payload[
            "query_count"
        ],
        "server_latency_ms": payload[
            "latency_ms"
        ],
        "client_latency_ms": round(
            client_latency_ms,
            3,
        ),
    }


def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize latency and query-count results."""

    configurations: dict[str, Any] = {}

    for version in VERSIONS:
        for page_size in PAGE_SIZES:
            matching_results = [
                result
                for result in results
                if (
                    result["version"]
                    == version
                    and result["page_size"]
                    == page_size
                )
            ]

            client_latencies = [
                float(
                    result[
                        "client_latency_ms"
                    ]
                )
                for result
                in matching_results
            ]

            server_latencies = [
                float(
                    result[
                        "server_latency_ms"
                    ]
                )
                for result
                in matching_results
            ]

            query_counts = [
                int(
                    result["query_count"]
                )
                for result
                in matching_results
            ]

            key = (
                f"{version}_"
                f"page_size_{page_size}"
            )

            configurations[key] = {
                "version": version,
                "pageSize": page_size,
                "runCount": len(
                    matching_results
                ),
                "queryCount": {
                    "minimum": min(
                        query_counts
                    ),
                    "maximum": max(
                        query_counts
                    ),
                    "mean": round(
                        fmean(
                            query_counts
                        ),
                        3,
                    ),
                },
                "clientLatencyMs": {
                    "mean": round(
                        fmean(
                            client_latencies
                        ),
                        3,
                    ),
                    "p50": round(
                        percentile(
                            client_latencies,
                            0.50,
                        ),
                        3,
                    ),
                    "p95": round(
                        percentile(
                            client_latencies,
                            0.95,
                        ),
                        3,
                    ),
                    "p99": round(
                        percentile(
                            client_latencies,
                            0.99,
                        ),
                        3,
                    ),
                },
                "serverLatencyMs": {
                    "mean": round(
                        fmean(
                            server_latencies
                        ),
                        3,
                    ),
                    "p50": round(
                        percentile(
                            server_latencies,
                            0.50,
                        ),
                        3,
                    ),
                    "p95": round(
                        percentile(
                            server_latencies,
                            0.95,
                        ),
                        3,
                    ),
                    "p99": round(
                        percentile(
                            server_latencies,
                            0.99,
                        ),
                        3,
                    ),
                },
            }

    return {
        "experiment": "n_plus_one_comparison",
        "totalRequests": len(
            results
        ),
        "runsPerConfiguration": (
            RUNS_PER_CONFIGURATION
        ),
        "pageSizes": PAGE_SIZES,
        "versions": VERSIONS,
        "percentileMethod": (
            "linear interpolation"
        ),
        "configurations": configurations,
        "generatedAt": utc_timestamp(),
    }


def save_results(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> None:
    """Write raw and summarized experiment files."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_JSON_PATH.write_text(
        json.dumps(
            results,
            indent=2,
        ),
        encoding="utf-8",
    )

    fieldnames = [
        "timestamp",
        "version",
        "page_size",
        "run_number",
        "page",
        "status_code",
        "record_count",
        "query_count",
        "server_latency_ms",
        "client_latency_ms",
    ]

    with RESULTS_CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )


def print_summary(
    metrics: dict[str, Any],
) -> None:
    """Print a compact experiment summary."""

    print("\n=== N+1 Experiment Metrics ===")

    for configuration in (
        metrics["configurations"].values()
    ):
        print(
            configuration["version"],
            "| page size:",
            configuration["pageSize"],
            "| runs:",
            configuration["runCount"],
            "| mean queries:",
            configuration[
                "queryCount"
            ]["mean"],
            "| client p50:",
            configuration[
                "clientLatencyMs"
            ]["p50"],
            "ms",
            "| client p95:",
            configuration[
                "clientLatencyMs"
            ]["p95"],
            "ms",
        )

    print(
        "\nTotal requests:",
        metrics["totalRequests"],
    )

    print("\nFiles created:")
    print(RESULTS_JSON_PATH)
    print(RESULTS_CSV_PATH)
    print(METRICS_PATH)


def main() -> None:
    """Run the complete N+1 performance experiment."""

    check_server()

    results: list[dict[str, Any]] = []

    total_requests = (
        len(PAGE_SIZES)
        * len(VERSIONS)
        * RUNS_PER_CONFIGURATION
    )

    completed_requests = 0

    print(
        "Starting N+1 experiment."
    )

    print(
        "Total requests:",
        total_requests,
    )

    for page_size in PAGE_SIZES:
        for version in VERSIONS:
            print(
                f"\nConfiguration: "
                f"{version}, "
                f"page size {page_size}"
            )

            for run_number in range(
                1,
                RUNS_PER_CONFIGURATION + 1,
            ):
                result = run_request(
                    version,
                    page_size,
                    run_number,
                )

                results.append(
                    result
                )

                completed_requests += 1

                print(
                    f"{completed_requests}/"
                    f"{total_requests}"
                    f" | queries="
                    f"{result['query_count']}"
                    f" | latency="
                    f"{result['client_latency_ms']}"
                    f" ms"
                )

    metrics = calculate_metrics(
        results
    )

    save_results(
        results,
        metrics,
    )

    print_summary(
        metrics
    )


if __name__ == "__main__":
    main()