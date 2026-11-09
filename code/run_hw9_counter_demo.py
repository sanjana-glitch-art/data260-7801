from __future__ import annotations

from code.database import engine
from code.hw9_view_counter import (
    ClinicalTrialViewCounter,
)

from sqlalchemy import text


def first_trial_id() -> int:
    """Return the first available trial ID."""

    with engine.connect() as connection:
        trial_id = connection.execute(
            text(
                """
                SELECT id
                FROM clinical_trials
                ORDER BY id
                LIMIT 1
                """
            )
        ).scalar_one_or_none()

    if trial_id is None:
        raise RuntimeError(
            "No clinical trials exist. "
            "Seed the database first."
        )

    return int(trial_id)


def main() -> None:
    """Run the required 25-access demo."""

    counter = ClinicalTrialViewCounter()
    trial_id = first_trial_id()

    try:
        counter.reset_counter(trial_id)

        print(
            "DATA-260 Homework 9 Part 1"
        )
        print(
            "Student: Sanjana Thummalapalli"
        )
        print("SID4: 7801")
        print(
            f"Clinical trial ID: {trial_id}"
        )
        print(
            "\n=== Testing Counter ===\n"
        )

        for access_number in range(1, 26):
            total = (
                counter.increment_trial_views(
                    trial_id
                )
            )

            print(
                f"Access #{access_number}: "
                f"Total = {total}"
            )

        redis_count = int(
            counter.redis_client.get(
                counter.view_key(trial_id)
            )
            or 0
        )

        database_count = (
            counter.database_view_count(
                trial_id
            )
        )

        print(
            "\n=== Final Counter State ==="
        )
        print(
            f"Redis count: {redis_count}"
        )
        print(
            f"Database count: "
            f"{database_count}"
        )
        print(
            "Expected database count: 20"
        )
        print(
            "Counter demonstration: "
            + (
                "PASS"
                if (
                    redis_count == 25
                    and database_count == 20
                )
                else "FAIL"
            )
        )
    finally:
        counter.close()


if __name__ == "__main__":
    main()
