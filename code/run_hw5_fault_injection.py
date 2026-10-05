from __future__ import annotations

import csv
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

from code.hw5_domain_tools import (
    search_trials_operation,
)


VERIFY_SEED = 267801
CALLS_PER_RATE = 50
FAILURE_RATES = (
    0.0,
    0.2,
    0.5,
)

ROOT = Path(
    __file__
).resolve().parents[1]

RAW_DIRECTORY = (
    ROOT
    / "reports"
    / "hw05"
    / "raw"
)

RESULTS_JSON = (
    RAW_DIRECTORY
    / "fault_injection_results.json"
)

RESULTS_CSV = (
    RAW_DIRECTORY
    / "fault_injection_results.csv"
)

METRICS_JSON = (
    RAW_DIRECTORY
    / "fault_injection_metrics.json"
)

DEMONSTRATION_JSON = (
    RAW_DIRECTORY
    / "retry_demonstration.json"
)


def utc_timestamp() -> str:
    """Return an ISO UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def percentile(
    values: list[float],
    probability: float,
) -> float:
    """Calculate a linearly interpolated percentile."""

    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        (len(ordered) - 1)
        * probability
    )

    lower = int(position)
    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    fraction = position - lower

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * fraction
    )


def sequence_injector(
    outcomes: list[bool],
) -> Callable[[], bool]:
    """Return failures from a fixed sequence."""

    position = 0

    def should_fail() -> bool:
        nonlocal position

        if position >= len(outcomes):
            return False

        result = outcomes[position]
        position += 1

        return result

    return should_fail


def demonstrate_retry_states() -> list[dict[str, Any]]:
    """Demonstrate all three required retry outcomes."""

    scenarios = [
        (
            "success_first_attempt",
            [
                False,
            ],
        ),
        (
            "failure_then_retry_success",
            [
                True,
                False,
            ],
        ),
        (
            "failure_after_all_retries",
            [
                True,
                True,
                True,
            ],
        ),
    ]

    demonstrations: list[
        dict[str, Any]
    ] = []

    for name, outcomes in scenarios:
        started = time.perf_counter()

        result, metadata = (
            search_trials_operation(
                "Sleep",
                1,
                should_inject_failure=(
                    sequence_injector(
                        outcomes
                    )
                ),
            )
        )

        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000

        demonstrations.append({
            "scenario": name,
            "planned_failures": outcomes,
            "result": result,
            "attempts": metadata[
                "attempts"
            ],
            "retried": metadata[
                "retried"
            ],
            "attempt_errors": metadata[
                "errors"
            ],
            "latency_ms": round(
                latency_ms,
                3,
            ),
        })

    return demonstrations


def run_fault_experiment() -> list[dict[str, Any]]:
    """Run 50 calls at each required failure rate."""

    records: list[dict[str, Any]] = []

    for failure_rate in FAILURE_RATES:
        rate_seed = (
            VERIFY_SEED
            + int(
                failure_rate * 1000
            )
        )

        generator = random.Random(
            rate_seed
        )

        def should_fail() -> bool:
            return (
                generator.random()
                < failure_rate
            )

        print(
            (
                "\nFailure rate: "
                f"{failure_rate:.0%}"
            )
        )

        for call_number in range(
            1,
            CALLS_PER_RATE + 1,
        ):
            started = time.perf_counter()

            result, metadata = (
                search_trials_operation(
                    "Sleep",
                    1,
                    should_inject_failure=(
                        should_fail
                    ),
                )
            )

            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000

            record = {
                "failure_rate": (
                    failure_rate
                ),
                "rate_seed": rate_seed,
                "call_number": call_number,
                "ok": result["ok"],
                "error": result["error"],
                "attempts": metadata[
                    "attempts"
                ],
                "retried": metadata[
                    "retried"
                ],
                "attempt_error_count": len(
                    metadata["errors"]
                ),
                "attempt_errors": (
                    metadata["errors"]
                ),
                "latency_ms": round(
                    latency_ms,
                    3,
                ),
                "timestamp": (
                    utc_timestamp()
                ),
            }

            records.append(record)

            print(
                (
                    f"Call {call_number:02d}/"
                    f"{CALLS_PER_RATE} | "
                    f"ok={record['ok']} | "
                    f"attempts="
                    f"{record['attempts']} | "
                    f"{record['latency_ms']}"
                    " ms"
                )
            )

    return records


def calculate_metrics(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize each failure rate."""

    metrics: dict[str, Any] = {}

    for failure_rate in FAILURE_RATES:
        matching = [
            record
            for record in records
            if (
                record["failure_rate"]
                == failure_rate
            )
        ]

        successes = sum(
            bool(record["ok"])
            for record in matching
        )

        latencies = [
            float(
                record["latency_ms"]
            )
            for record in matching
        ]

        retried_calls = sum(
            bool(record["retried"])
            for record in matching
        )

        key = (
            f"{failure_rate:.1f}"
        )

        metrics[key] = {
            "injectedFailureRate": (
                failure_rate
            ),
            "callCount": len(matching),
            "successCount": successes,
            "successRatePercent": round(
                successes
                / len(matching)
                * 100,
                2,
            ),
            "retriedCallCount": (
                retried_calls
            ),
            "meanLatencyMs": round(
                fmean(latencies),
                3,
            ),
            "p99LatencyMs": round(
                percentile(
                    latencies,
                    0.99,
                ),
                3,
            ),
        }

    return {
        "experiment": (
            "hw5_fault_injection"
        ),
        "verifySeed": VERIFY_SEED,
        "callsPerRate": (
            CALLS_PER_RATE
        ),
        "totalCalls": len(records),
        "maxAttempts": 3,
        "timeoutSeconds": 3.0,
        "backoffSeconds": [
            0.025,
            0.050,
        ],
        "rates": metrics,
        "generatedAt": utc_timestamp(),
    }


def save_results(
    records: list[dict[str, Any]],
    metrics: dict[str, Any],
    demonstrations: list[
        dict[str, Any]
    ],
) -> None:
    """Write JSON and CSV evidence."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_JSON.write_text(
        json.dumps(
            records,
            indent=2,
        ),
        encoding="utf-8",
    )

    csv_records = [
        {
            **record,
            "attempt_errors": json.dumps(
                record["attempt_errors"]
            ),
        }
        for record in records
    ]

    with RESULTS_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=list(
                csv_records[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(csv_records)

    METRICS_JSON.write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )

    DEMONSTRATION_JSON.write_text(
        json.dumps(
            demonstrations,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Run demonstrations and experiment."""

    print(
        "HW5 Retry Demonstrations"
    )

    demonstrations = (
        demonstrate_retry_states()
    )

    print(
        json.dumps(
            demonstrations,
            indent=2,
        )
    )

    records = run_fault_experiment()

    metrics = calculate_metrics(
        records
    )

    save_results(
        records,
        metrics,
        demonstrations,
    )

    print(
        "\n=== Fault Injection Metrics ==="
    )

    print(
        json.dumps(
            metrics,
            indent=2,
        )
    )

    print(
        "\nFiles created:"
    )

    print(RESULTS_JSON)
    print(RESULTS_CSV)
    print(METRICS_JSON)
    print(DEMONSTRATION_JSON)


if __name__ == "__main__":
    main()