from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

from sqlalchemy import text

from code.database import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw04"
    / "raw"
)

OUTPUT_PATH = (
    RAW_DIRECTORY
    / "index_experiment.json"
)

INDEX_NAME = (
    "idx_clinical_trials_submitter_email"
)

REPETITIONS = 30


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def percentile(
    values: list[float],
    fraction: float,
) -> float:
    """Calculate a percentile using linear interpolation."""

    ordered = sorted(
        values
    )

    position = (
        len(ordered) - 1
    ) * fraction

    lower = int(
        position
    )

    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    weight = position - lower

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * weight
    )


def index_exists() -> bool:
    """Return whether the experiment index exists."""

    with engine.connect() as connection:
        count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'clinical_trials'
                  AND INDEX_NAME = :index_name
                """
            ),
            {
                "index_name": INDEX_NAME,
            },
        )

    return bool(
        count
    )


def drop_experiment_index() -> None:
    """Remove the experiment index when it already exists."""

    if not index_exists():
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                DROP INDEX {INDEX_NAME}
                ON clinical_trials
                """
            )
        )


def create_experiment_index() -> None:
    """Create the email lookup index."""

    if index_exists():
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE INDEX {INDEX_NAME}
                ON clinical_trials (submitter_email)
                """
            )
        )


def analyze_table() -> None:
    """Refresh MySQL table statistics."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ANALYZE TABLE clinical_trials
                """
            )
        )


def choose_test_email() -> str:
    """Select an existing email from near the table midpoint."""

    with engine.connect() as connection:
        email = connection.scalar(
            text(
                """
                SELECT submitter_email
                FROM clinical_trials
                WHERE submitter_email <> ''
                ORDER BY id
                LIMIT 1 OFFSET 2500
                """
            )
        )

    if not email:
        raise RuntimeError(
            "Could not find an email for the index experiment."
        )

    return str(
        email
    )


def explain_query(
    email: str,
) -> list[dict[str, Any]]:
    """Return MySQL EXPLAIN output for an email lookup."""

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                EXPLAIN
                SELECT *
                FROM clinical_trials
                WHERE submitter_email = :email
                """
            ),
            {
                "email": email,
            },
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


def benchmark_query(
    email: str,
) -> dict[str, Any]:
    """Measure repeated exact-email lookups."""

    latencies: list[float] = []

    with engine.connect() as connection:
        for _ in range(
            REPETITIONS
        ):
            started_at = perf_counter()

            connection.execute(
                text(
                    """
                    SELECT *
                    FROM clinical_trials
                    WHERE submitter_email = :email
                    """
                ),
                {
                    "email": email,
                },
            ).mappings().all()

            latency_ms = (
                perf_counter()
                - started_at
            ) * 1000

            latencies.append(
                latency_ms
            )

    return {
        "runCount": REPETITIONS,
        "meanLatencyMs": round(
            fmean(latencies),
            4,
        ),
        "p50LatencyMs": round(
            percentile(
                latencies,
                0.50,
            ),
            4,
        ),
        "p95LatencyMs": round(
            percentile(
                latencies,
                0.95,
            ),
            4,
        ),
        "minimumLatencyMs": round(
            min(latencies),
            4,
        ),
        "maximumLatencyMs": round(
            max(latencies),
            4,
        ),
        "rawLatenciesMs": [
            round(
                value,
                4,
            )
            for value in latencies
        ],
    }


def main() -> None:
    """Run the before-and-after MySQL index experiment."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_email = choose_test_email()

    print(
        "Test email:",
        test_email,
    )

    print(
        "\nRemoving experiment index for the before test."
    )

    drop_experiment_index()
    analyze_table()

    before_explain = explain_query(
        test_email
    )

    before_benchmark = benchmark_query(
        test_email
    )

    print(
        "Before EXPLAIN:"
    )
    print(
        json.dumps(
            before_explain,
            indent=2,
            default=str,
        )
    )

    print(
        "\nCreating index:",
        INDEX_NAME,
    )

    create_experiment_index()
    analyze_table()

    after_explain = explain_query(
        test_email
    )

    after_benchmark = benchmark_query(
        test_email
    )

    before_mean = before_benchmark[
        "meanLatencyMs"
    ]

    after_mean = after_benchmark[
        "meanLatencyMs"
    ]

    improvement_percent = (
        (
            before_mean - after_mean
        )
        / before_mean
        * 100
        if before_mean > 0
        else 0
    )

    result = {
        "experiment": "mysql_index_comparison",
        "table": "clinical_trials",
        "column": "submitter_email",
        "indexName": INDEX_NAME,
        "testEmail": test_email,
        "query": (
            "SELECT * FROM clinical_trials "
            "WHERE submitter_email = :email"
        ),
        "beforeIndex": {
            "indexPresent": False,
            "explain": before_explain,
            "benchmark": before_benchmark,
        },
        "afterIndex": {
            "indexPresent": True,
            "explain": after_explain,
            "benchmark": after_benchmark,
        },
        "meanLatencyImprovementPercent": round(
            improvement_percent,
            2,
        ),
        "generatedAt": utc_timestamp(),
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(
        "\nAfter EXPLAIN:"
    )

    print(
        json.dumps(
            after_explain,
            indent=2,
            default=str,
        )
    )

    print(
        "\nBefore mean latency:",
        before_mean,
        "ms",
    )

    print(
        "After mean latency:",
        after_mean,
        "ms",
    )

    print(
        "Mean latency improvement:",
        round(
            improvement_percent,
            2,
        ),
        "%",
    )

    print(
        "\nFile created:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()