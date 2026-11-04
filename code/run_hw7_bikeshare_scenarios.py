from __future__ import annotations

import argparse
import csv
import json
import os
import threading
from code.hw7_bikeshare_agent import (
    run_bikeshare_agent,
)
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any

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

RUN_LOG_PATH = (
    PROJECT_ROOT
    / "reports"
    / "hw07"
    / "RUN_LOG.txt"
)

RESULTS_PATH = (
    RAW_DIRECTORY
    / "bikeshare_scenario_results.json"
)

RESULTS_CSV_PATH = (
    RAW_DIRECTORY
    / "bikeshare_scenario_metrics.csv"
)

LOCAL_POLICY_PATH = (
    CASES_DIRECTORY
    / "bikeshare_clean_pricing.html"
)

MEMBERSHIP_CASE_PATH = (
    CASES_DIRECTORY
    / "bikeshare_membership_wins.csv"
)

PAY_CASE_PATH = (
    CASES_DIRECTORY
    / "bikeshare_pay_per_use_wins.csv"
)

OFFICIAL_PRICING_URL = (
    "https://citibikenyc.com/pricing"
)

DATASET_ROW_COUNT = 600


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(
        UTC
    ).isoformat()

def json_default(
    value: Any,
) -> Any:
    """Convert nonstandard result values for JSON output."""

    if isinstance(
        value,
        Decimal,
    ):
        return float(
            value
        )

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    raise TypeError(
        "Object of type "
        f"{type(value).__name__} "
        "is not JSON serializable."
    )

def create_clean_policy_page() -> None:
    """Create deterministic local pricing evidence."""

    LOCAL_POLICY_PATH.write_text(
        """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Citi Bike Pricing Scenario Fixture</title>
</head>

<body>
    <main>
        <h1>Citi Bike Pricing</h1>

        <section>
            <h2>Single Ride</h2>
            <p>
                A single ride costs $4.99 and includes
                the first 30 minutes.
            </p>
        </section>

        <section>
            <h2>Monthly Membership</h2>
            <p>
                Monthly membership costs $19.00 and
                includes rides up to 45 minutes.
            </p>
        </section>

        <section>
            <h2>Overage</h2>
            <p>
                Ride time beyond the included duration
                costs $0.25 per minute.
            </p>
        </section>

        <section>
            <h2>Machine-readable verification values</h2>
            <p>
                PAY_PER_RIDE_PRICE_USD=4.99
                MONTHLY_MEMBERSHIP_PRICE_USD=19.00
                PAY_INCLUDED_MINUTES=30
                MEMBERSHIP_INCLUDED_MINUTES=45
                OVERAGE_PER_MINUTE_USD=0.25
            </p>
        </section>
    </main>
</body>
</html>
        """.strip()
        + "\n",
        encoding="utf-8",
    )


def write_scenario_csv(
    path: Path,
    *,
    target_ride_count: int,
    target_duration_base: int,
) -> None:
    """Create one deterministic 600-row scenario CSV."""

    fieldnames = [
        "ride_id",
        "started_at",
        "ended_at",
        "duration_minutes",
        "week_number",
        "analysis_target",
        "member_type",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for index in range(
            1,
            DATASET_ROW_COUNT + 1,
        ):
            is_target = (
                index <= target_ride_count
            )

            if is_target:
                duration = (
                    target_duration_base
                    + (index % 8)
                )
            else:
                duration = (
                    8
                    + (index % 18)
                )

            day = (
                ((index - 1) % 28)
                + 1
            )

            week_number = (
                ((day - 1) // 7)
                + 1
            )

            writer.writerow({
                "ride_id": (
                    f"ride-{index:04d}"
                ),
                "started_at": (
                    f"2026-10-{day:02d}"
                    "T08:00:00"
                ),
                "ended_at": (
                    f"2026-10-{day:02d}"
                    "T08:30:00"
                ),
                "duration_minutes": (
                    duration
                ),
                "week_number": (
                    week_number
                ),
                "analysis_target": (
                    "true"
                    if is_target
                    else "false"
                ),
                "member_type": (
                    "casual"
                ),
            })


class QuietRequestHandler(
    SimpleHTTPRequestHandler
):
    """Local test handler without console noise."""

    def log_message(
        self,
        format_string: str,
        *args: object,
    ) -> None:
        """Suppress local HTTP request logs."""


@contextmanager
def local_policy_server() -> Iterator[str]:
    """Serve the local pricing fixture."""

    handler = partial(
        QuietRequestHandler,
        directory=str(
            CASES_DIRECTORY
        ),
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        handler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    host, port = (
        server.server_address
    )

    try:
        yield (
            f"http://{host}:{port}/"
            f"{LOCAL_POLICY_PATH.name}"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(
            timeout=5
        )


def add_weekly_spend(
    result: dict[str, Any],
) -> None:
    """
    Add weekly cost estimates to the result table.

    Weekly membership values represent allocated base
    membership cost plus residual overage.
    """

    pricing = result["pricing"]

    weekly_rows = result[
        "weekly_rows"
    ]

    base_weekly_membership = (
        pricing[
            "monthly_membership_price"
        ]
        / 4
    )

    for row in weekly_rows:
        ride_count = int(
            row["ride_count"]
        )

        average_duration = float(
            row[
                "average_duration_minutes"
            ]
        )

        pay_overage = max(
            average_duration
            - pricing[
                "pay_included_minutes"
            ],
            0,
        )

        membership_overage = max(
            average_duration
            - pricing[
                "membership_included_minutes"
            ],
            0,
        )

        row["estimated_pay_spend"] = round(
            ride_count
            * (
                pricing[
                    "pay_per_ride_price"
                ]
                + (
                    pay_overage
                    * pricing[
                        "overage_per_minute"
                    ]
                )
            ),
            2,
        )

        row[
            "estimated_membership_spend"
        ] = round(
            base_weekly_membership
            + (
                ride_count
                * membership_overage
                * pricing[
                    "overage_per_minute"
                ]
            ),
            2,
        )


def scenario_summary(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Return compact metrics for one scenario."""

    return {
        "scenario_label": (
            result["scenario_label"]
        ),
        "dataset_row_count": (
            result[
                "dataset_row_count"
            ]
        ),
        "target_ride_count": (
            result["ride_count"]
        ),
        "average_duration_minutes": (
            result[
                "average_duration_minutes"
            ]
        ),
        "pay_per_use_cost": (
            result[
                "pay_per_use_cost"
            ]
        ),
        "membership_cost": (
            result[
                "membership_cost"
            ]
        ),
        "break_even_rides": (
            result[
                "break_even_rides"
            ]
        ),
        "decision": (
            result["decision"]
        ),
        "step_count": (
            result["step_count"]
        ),
        "total_time_ms": (
            result["total_time_ms"]
        ),
        "stop_reason": (
            result["stop_reason"]
        ),
        "snapshot_sha256": (
            result["snapshot"].get(
                "sha256"
            )
        ),
        "source_url": (
            result["snapshot"].get(
                "source_url"
            )
        ),
        "accessed_at": (
            result["snapshot"].get(
                "accessed_at"
            )
        ),
    }


def save_csv_metrics(
    summaries: list[
        dict[str, Any]
    ],
) -> None:
    """Save scenario metrics as CSV."""

    if not summaries:
        return

    with RESULTS_CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                summaries[0]
            ),
        )

        writer.writeheader()
        writer.writerows(
            summaries
        )


def append_run_log(
    document: dict[str, Any],
) -> None:
    """Append the complete scenario output."""

    with RUN_LOG_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n=== HW7 Part 4 Bike Share Scenarios ===\n"
        )

        file.write(
            json.dumps(
                document,
                indent=2,
                ensure_ascii=False,
                default=json_default,
            )
        )

        file.write("\n")


def run_scenarios(
    pricing_url: str,
) -> dict[str, Any]:
    """Run both opposite-winner scenarios."""

    scenario_definitions = (
        {
            "label": (
                "membership_wins"
            ),
            "csv_path": (
                MEMBERSHIP_CASE_PATH
            ),
            "target_ride_count": 80,
            "target_duration_base": 32,
            "expected_decision": (
                "Buy Monthly Membership"
            ),
        },
        {
            "label": (
                "pay_per_use_wins"
            ),
            "csv_path": (
                PAY_CASE_PATH
            ),
            "target_ride_count": 3,
            "target_duration_base": 12,
            "expected_decision": (
                "Pay Per Ride/Minute"
            ),
        },
    )

    results: list[
        dict[str, Any]
    ] = []

    for scenario in (
        scenario_definitions
    ):
        write_scenario_csv(
            scenario["csv_path"],
            target_ride_count=scenario[
                "target_ride_count"
            ],
            target_duration_base=scenario[
                "target_duration_base"
            ],
        )

        print(
            "\n=== SCENARIO:",
            scenario["label"],
            "===",
        )

        result = run_bikeshare_agent(
            scenario["csv_path"],
            pricing_url,
            scenario_label=scenario[
                "label"
            ],
        )

        if result["stop_reason"] != (
            "success"
        ):
            raise RuntimeError(
                f"{scenario['label']} failed: "
                f"{result.get('error')}"
            )

        add_weekly_spend(
            result
        )

        decision_matches = (
            result["decision"]
            == scenario[
                "expected_decision"
            ]
        )

        result["expected_decision"] = (
            scenario[
                "expected_decision"
            ]
        )

        result[
            "decision_matches_expected"
        ] = decision_matches

        if not decision_matches:
            raise AssertionError(
                f"{scenario['label']} expected "
                f"{scenario['expected_decision']}, "
                f"received {result['decision']}."
            )

        if (
            result[
                "dataset_row_count"
            ]
            < 500
        ):
            raise AssertionError(
                "Scenario must contain at least "
                "500 trip rows."
            )

        print(
            "Dataset rows:",
            result[
                "dataset_row_count"
            ],
        )

        print(
            "Target rides:",
            result["ride_count"],
        )

        print(
            "Pay-per-use cost:",
            f"${result['pay_per_use_cost']:.2f}",
        )

        print(
            "Membership cost:",
            f"${result['membership_cost']:.2f}",
        )

        print(
            "Decision:",
            result["decision"],
        )

        print(
            "Steps:",
            result["step_count"],
        )

        print(
            "Total time:",
            result["total_time_ms"],
            "ms",
        )

        print(
            "Stop reason:",
            result["stop_reason"],
        )

        print(
            "Snapshot SHA-256:",
            result["snapshot"].get(
                "sha256"
            ),
        )

        results.append(
            result
        )

    summaries = [
        scenario_summary(result)
        for result in results
    ]

    return {
        "experiment": (
            "hw7_bikeshare_scenarios"
        ),
        "pricing_url": pricing_url,
        "scenario_count": len(
            results
        ),
        "all_passed": all(
            result[
                "decision_matches_expected"
            ]
            for result in results
        ),
        "summaries": summaries,
        "scenarios": results,
        "generated_at": utc_timestamp(),
    }


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Run Homework 7 Bike Share "
            "acceptance scenarios."
        )
    )

    parser.add_argument(
        "--pricing-url",
        default=None,
        help=(
            "Pricing-policy URL. When omitted, "
            "the deterministic local test page is used."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Create cases and run the acceptance scenarios."""

    arguments = parse_arguments()

    CASES_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_clean_policy_page()

    print(
        "DATA-260 Homework 7 Part 4"
    )

    print(
        "Bike Share ReAct/MRKL Scenarios"
    )

    if arguments.pricing_url:
        document = run_scenarios(
            arguments.pricing_url
        )
    else:
        previous_setting = (
            os.environ.get(
                "HW7_ALLOW_LOCAL_POLICY_TEST"
            )
        )

        os.environ[
            "HW7_ALLOW_LOCAL_POLICY_TEST"
        ] = "1"

        try:
            with local_policy_server() as (
                pricing_url
            ):
                document = (
                    run_scenarios(
                        pricing_url
                    )
                )
        finally:
            if previous_setting is None:
                os.environ.pop(
                    "HW7_ALLOW_LOCAL_POLICY_TEST",
                    None,
                )
            else:
                os.environ[
                    "HW7_ALLOW_LOCAL_POLICY_TEST"
                ] = previous_setting

    RESULTS_PATH.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
            default=json_default,
        )
        + "\n",
        encoding="utf-8",
    )

    save_csv_metrics(
        document["summaries"]
    )

    append_run_log(
        document
    )

    print(
        "\n=== FINAL SUMMARY ==="
    )

    for summary in (
        document["summaries"]
    ):
        print(
            summary[
                "scenario_label"
            ],
            "| rows =",
            summary[
                "dataset_row_count"
            ],
            "| rides =",
            summary[
                "target_ride_count"
            ],
            "| decision =",
            summary["decision"],
            "| stop =",
            summary[
                "stop_reason"
            ],
        )

    print(
        "\nAll scenarios passed:",
        document["all_passed"],
    )

    print(
        "JSON:",
        RESULTS_PATH,
    )

    print(
        "CSV:",
        RESULTS_CSV_PATH,
    )


if __name__ == "__main__":
    main()