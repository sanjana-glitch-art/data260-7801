from __future__ import annotations

import json
from code.database import engine
from code.hw9_semantic_cache import (
    SemanticResponseCache,
)
from pathlib import Path
from typing import Any

from sqlalchemy import text

OUTPUT_PATH = Path(
    "reports/hw09/raw/"
    "stale_cache_results.json"
)


def get_sleep_trial() -> dict[str, Any]:
    """Return the sleep trial database row."""

    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    id,
                    trial_code,
                    trial_title,
                    enrollment_target,
                    updated_at
                FROM clinical_trials
                WHERE trial_code =
                    'S7801-CT-000001'
                LIMIT 1
                """
            )
        ).mappings().one_or_none()

    if row is None:
        raise RuntimeError(
            "Sleep clinical trial not found."
        )

    return dict(row)


def update_enrollment(
    trial_id: int,
    enrollment_target: int,
) -> None:
    """Update the record and its data version."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE clinical_trials
                SET
                    enrollment_target =
                        :enrollment_target,
                    updated_at = UTC_TIMESTAMP()
                WHERE id = :trial_id
                """
            ),
            {
                "trial_id": trial_id,
                "enrollment_target": (
                    enrollment_target
                ),
            },
        )


def restore_trial(
    trial_id: int,
    enrollment_target: int,
    updated_at: Any,
) -> None:
    """Restore original database values."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE clinical_trials
                SET
                    enrollment_target =
                        :enrollment_target,
                    updated_at = :updated_at
                WHERE id = :trial_id
                """
            ),
            {
                "trial_id": trial_id,
                "enrollment_target": (
                    enrollment_target
                ),
                "updated_at": updated_at,
            },
        )


def main() -> None:
    """Demonstrate stale hit and invalidation."""

    cache = SemanticResponseCache(
        threshold=0.90
    )

    query = (
        "What is the enrollment target "
        "of the sleep quality trial?"
    )

    original = get_sleep_trial()
    trial_id = int(original["id"])

    original_target = int(
        original["enrollment_target"]
    )

    updated_target = (
        original_target + 25
    )

    original_updated_at = (
        original["updated_at"]
    )

    cache.clear_semantic_cache()

    try:
        version_before = (
            cache.current_data_version()
        )

        old_answer = (
            "The sleep quality trial has "
            f"an enrollment target of "
            f"{original_target}."
        )

        cache.store(
            query,
            old_answer,
            version_before,
        )

        print(
            "DATA-260 Homework 9 Part 3.5"
        )
        print(
            "Student: Sanjana Thummalapalli"
        )
        print("SID4: 7801")
        print(f"Query: {query}")
        print(
            "Original database value: "
            f"{original_target}"
        )
        print(
            "Cached answer: "
            f"{old_answer}"
        )
        print(
            "Stored data version: "
            f"{version_before}"
        )

        update_enrollment(
            trial_id,
            updated_target,
        )

        version_after_update = (
            cache.current_data_version()
        )

        stale_match = cache.search(query)

        if stale_match is None:
            raise RuntimeError(
                "Expected a stale cache hit."
            )

        stale_answer = str(
            stale_match["answer"]
        )

        print(
            "\n=== STALE HIT BEFORE "
            "INVALIDATION ==="
        )
        print(
            "Updated database value: "
            f"{updated_target}"
        )
        print(
            "Current data version: "
            f"{version_after_update}"
        )
        print(
            "Cached entry version: "
            f"{stale_match['data_version']}"
        )
        print(
            "Returned stale answer: "
            f"{stale_answer}"
        )
        print(
            "Stale hit demonstrated: "
            f"{str(original_target) in stale_answer}"
        )

        deleted = (
            cache.invalidate_stale_entries(
                version_after_update
            )
        )

        match_after_invalidation = (
            cache.search(query)
        )

        invalidation_miss = (
            match_after_invalidation is None
        )

        refreshed_answer = (
            "The sleep quality trial has "
            f"an enrollment target of "
            f"{updated_target}."
        )

        if invalidation_miss:
            cache.store(
                query,
                refreshed_answer,
                version_after_update,
            )

        refreshed_match = (
            cache.search(query)
        )

        refreshed_correctly = (
            refreshed_match is not None
            and str(updated_target)
            in str(
                refreshed_match["answer"]
            )
        )

        print(
            "\n=== AFTER INVALIDATION ==="
        )
        print(
            f"Stale entries deleted: {deleted}"
        )
        print(
            "Cache miss after invalidation: "
            f"{invalidation_miss}"
        )
        print(
            "Refreshed answer: "
            f"{refreshed_answer}"
        )
        print(
            "Refreshed cache correct: "
            f"{refreshed_correctly}"
        )

        overall_passed = (
            str(original_target)
            in stale_answer
            and deleted >= 1
            and invalidation_miss
            and refreshed_correctly
        )

        result = {
            "experiment": (
                "hw9_stale_cache_invalidation"
            ),
            "query": query,
            "trial_id": trial_id,
            "trial_code": (
                original["trial_code"]
            ),
            "original_enrollment_target": (
                original_target
            ),
            "updated_enrollment_target": (
                updated_target
            ),
            "version_before_update": (
                version_before
            ),
            "version_after_update": (
                version_after_update
            ),
            "stale_cached_answer": (
                stale_answer
            ),
            "correct_updated_answer": (
                refreshed_answer
            ),
            "stale_hit_demonstrated": (
                str(original_target)
                in stale_answer
            ),
            "stale_entries_deleted": deleted,
            "cache_miss_after_invalidation": (
                invalidation_miss
            ),
            "refreshed_cache_correct": (
                refreshed_correctly
            ),
            "invalidation_strategy": (
                "Delete semantic-cache entries "
                "whose stored data-version marker "
                "does not match the current "
                "clinical_trials data version."
            ),
            "trade_off": (
                "Version checking prevents stale "
                "answers but adds a database version "
                "read and may invalidate more cached "
                "entries than a record-specific "
                "strategy."
            ),
            "overall_passed": overall_passed,
        }

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT_PATH.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "\nOverall: "
            + (
                "PASS"
                if overall_passed
                else "FAIL"
            )
        )
        print(f"Saved: {OUTPUT_PATH}")
    finally:
        restore_trial(
            trial_id,
            original_target,
            original_updated_at,
        )

        cache.clear_semantic_cache()
        cache.close()


if __name__ == "__main__":
    main()
