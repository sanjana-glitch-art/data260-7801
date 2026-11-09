from __future__ import annotations

import json
import subprocess
from code.database import engine
from code.hw9_config import (
    EMBEDDING_DIMENSIONS,
    PREFIX,
    REDIS_URL,
    SEMANTIC_CACHE_INDEX,
    SID4,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from redis import Redis
from sqlalchemy import inspect

OUTPUT_PATH = Path(
    "reports/hw09/verification.json"
)


def load_json(
    path: str,
) -> Any:
    """Load one JSON document."""

    return json.loads(
        Path(path).read_text(
            encoding="utf-8-sig"
        )
    )


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Append and print one verification."""

    checks.append({
        "name": name,
        "passed": passed,
        "details": details,
    })

    print(
        ("PASS" if passed else "FAIL")
        + " | "
        + name
        + " | "
        + details
    )


def current_commit() -> str:
    """Return the current Git commit."""

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def verify_configuration(
    checks: list[dict[str, Any]],
) -> None:
    """Verify personal configuration."""

    passed = (
        SID4 == 7801
        and PREFIX == "s7801"
        and EMBEDDING_DIMENSIONS == 384
    )

    add_check(
        checks,
        "personal_configuration",
        passed,
        (
            f"SID4={SID4}, PREFIX={PREFIX}, "
            f"embedding_dimensions="
            f"{EMBEDDING_DIMENSIONS}"
        ),
    )


def verify_redis(
    checks: list[dict[str, Any]],
) -> None:
    """Verify Redis and vector index."""

    client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    try:
        ping_passed = bool(client.ping())

        add_check(
            checks,
            "redis_connection",
            ping_passed,
            "Redis PING succeeded.",
        )

        indexes = [
            str(index)
            for index in client.execute_command(
                "FT._LIST"
            )
        ]

        index_passed = (
            SEMANTIC_CACHE_INDEX
            in indexes
        )

        add_check(
            checks,
            "redis_vector_index",
            index_passed,
            (
                f"Indexes={indexes}; expected="
                f"{SEMANTIC_CACHE_INDEX}"
            ),
        )

        keys = [
            (
                key.decode("utf-8")
                if isinstance(key, bytes)
                else str(key)
            )
            for key in client.scan_iter(
                match="*"
            )
        ]

        prefix_passed = all(
            key.startswith(PREFIX)
            for key in keys
        )

        add_check(
            checks,
            "redis_key_prefix",
            prefix_passed,
            (
                f"Checked {len(keys)} Redis "
                f"keys; all begin with "
                f"{PREFIX}."
            ),
        )
    finally:
        client.close()


def verify_view_counter(
    checks: list[dict[str, Any]],
) -> None:
    """Verify Part 1 evidence."""

    columns = {
        column["name"]
        for column in inspect(
            engine
        ).get_columns(
            "clinical_trials"
        )
    }

    column_passed = (
        "view_count" in columns
    )

    add_check(
        checks,
        "database_view_column",
        column_passed,
        (
            "clinical_trials.view_count "
            + (
                "exists."
                if column_passed
                else "is missing."
            )
        ),
    )

    log_path = Path(
        "reports/hw09/raw/"
        "view_counter_demo.log"
    )

    content = ""

    if log_path.exists():
        try:
            content = log_path.read_text(
                encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            content = log_path.read_text(
                encoding="utf-16"
            )

    demo_passed = all(
        marker in content
        for marker in (
            "Access #25: Total = 25",
            (
                "Synced views to database "
                "at count 10"
            ),
            (
                "Synced views to database "
                "at count 20"
            ),
            (
                "Counter demonstration: "
                "PASS"
            ),
        )
    )

    add_check(
        checks,
        "redis_view_counter",
        demo_passed,
        (
            "25 accesses, database syncs "
            "at 10 and 20, and PASS found."
        ),
    )


def verify_semantic_cache(
    checks: list[dict[str, Any]],
) -> None:
    """Verify Part 2 results."""

    result = load_json(
        "reports/hw09/raw/"
        "semantic_cache_results.json"
    )

    passed = (
        result["query_count"] >= 10
        and result["cache_hits"] > 0
        and result["cache_misses"] > 0
        and (
            result[
                "average_cached_latency_ms"
            ]
            <
            result[
                "average_non_cached_latency_ms"
            ]
        )
    )

    add_check(
        checks,
        "semantic_cache_performance",
        passed,
        (
            f"queries={result['query_count']}, "
            f"hits={result['cache_hits']}, "
            f"hit_rate="
            f"{result['cache_hit_rate_percent']}%, "
            f"cached_latency="
            f"{result['average_cached_latency_ms']} "
            f"ms, miss_latency="
            f"{result['average_non_cached_latency_ms']} "
            "ms"
        ),
    )


def verify_cache_cases(
    checks: list[dict[str, Any]],
) -> None:
    """Verify the committed labeled dataset."""

    document = yaml.safe_load(
        Path("cache_cases.yaml").read_text(
            encoding="utf-8-sig"
        )
    )

    cases = document["cases"]

    categories = {
        category: sum(
            case["category"] == category
            for case in cases
        )
        for category in (
            "exact_duplicate",
            "paraphrase",
            "similar_different_answer",
            "unrelated",
        )
    }

    passed = (
        len(cases) == 40
        and all(
            count == 10
            for count in categories.values()
        )
        and sum(
            bool(case["should_hit"])
            for case in cases
        )
        == 20
    )

    add_check(
        checks,
        "labeled_cache_cases",
        passed,
        (
            f"cases={len(cases)}, "
            f"categories={categories}"
        ),
    )


def verify_threshold_sweep(
    checks: list[dict[str, Any]],
) -> None:
    """Verify threshold and false-hit results."""

    result = load_json(
        "reports/hw09/raw/"
        "threshold_sweep_results.json"
    )

    thresholds = [
        item["threshold"]
        for item in result["results"]
    ]

    passed = thresholds == [
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
    ]

    add_check(
        checks,
        "threshold_sweep",
        passed,
        (
            f"thresholds={thresholds}, "
            f"recommended="
            f"{result['recommended_threshold']}"
        ),
    )

    false_hit = load_json(
        "reports/hw09/raw/"
        "false_hit_example.json"
    )

    false_hit_passed = (
        false_hit is not None
        and false_hit["false_hit"]
        and bool(false_hit["cached_query"])
        and bool(false_hit["incoming_query"])
        and bool(false_hit["cached_answer"])
        and bool(false_hit["correct_answer"])
    )

    add_check(
        checks,
        "complete_false_hit",
        false_hit_passed,
        (
            "False-hit evidence includes "
            "both queries, similarity, cached "
            "answer and correct answer."
        ),
    )


def verify_stale_cache(
    checks: list[dict[str, Any]],
) -> None:
    """Verify stale hit and invalidation."""

    result = load_json(
        "reports/hw09/raw/"
        "stale_cache_results.json"
    )

    passed = all([
        result[
            "stale_hit_demonstrated"
        ],
        result[
            "cache_miss_after_invalidation"
        ],
        result[
            "refreshed_cache_correct"
        ],
        result["overall_passed"],
    ])

    add_check(
        checks,
        "stale_cache_invalidation",
        passed,
        (
            "Stale hit demonstrated, stale "
            "entry deleted, and refreshed "
            "answer verified."
        ),
    )


def verify_agent_datasets(
    checks: list[dict[str, Any]],
) -> None:
    """Verify required Part 4 datasets."""

    reference = load_json(
        "reference_data.json"
    )

    training = load_json(
        "training_data.json"
    )

    validation = load_json(
        "validation_data.json"
    )

    test = load_json(
        "test_data.json"
    )

    input_only = all(
        "answer" not in item
        and "expected_answer" not in item
        and "correct_answer" not in item
        for dataset in (
            training,
            validation,
            test,
        )
        for item in dataset
    )

    passed = (
        len(reference["facts"]) == 4
        and len(training) >= 1
        and len(validation) >= 1
        and len(test) >= 1
        and input_only
    )

    add_check(
        checks,
        "agent_datasets",
        passed,
        (
            f"reference_facts="
            f"{len(reference['facts'])}, "
            f"training={len(training)}, "
            f"validation={len(validation)}, "
            f"test={len(test)}, "
            f"input_only={input_only}"
        ),
    )


def verify_self_improvement(
    checks: list[dict[str, Any]],
) -> None:
    """Verify repair, lessons and variants."""

    revision = load_json(
        "reports/hw09/raw/"
        "revision_sequence.json"
    )

    revision_passed = (
        revision["attempt_count"] == 2
        and revision["attempts"][0][
            "evaluation_result"
        ]
        == "REVISE"
        and revision["attempts"][1][
            "evaluation_result"
        ]
        == "PASS"
    )

    add_check(
        checks,
        "evaluator_revision",
        revision_passed,
        (
            "Initial attempt REVISE; "
            "second attempt PASS."
        ),
    )

    lessons = load_json(
        "lessons.json"
    )

    lesson_reuse = load_json(
        "reports/hw09/raw/"
        "lesson_reuse_example.json"
    )

    lesson_passed = (
        len(lessons) >= 1
        and all(
            field in lessons[0]
            for field in (
                "lesson_id",
                "failure_pattern",
                "correction",
                "created_at",
                "use_count",
            )
        )
        and lessons[0]["use_count"] > 0
        and (
            "lesson_001"
            in lesson_reuse[
                "attempts"
            ][0]["loaded_lesson_ids"]
        )
    )

    add_check(
        checks,
        "lesson_memory_reuse",
        lesson_passed,
        (
            f"lessons={len(lessons)}, "
            f"use_count="
            f"{lessons[0]['use_count']}"
        ),
    )

    result = load_json(
        "reports/hw09/raw/"
        "self_improvement_results.json"
    )

    variants = result["variants"]
    validation = result["validation"]

    variants_passed = (
        len(variants) == 4
        and validation["lesson_kept"]
        and not validation["regressions"]
        and (
            validation["correct_after"]
            >= validation["correct_before"]
        )
        and all(
            variant["correct_answers"]
            + variant["incorrect_answers"]
            == 8
            for variant in variants
        )
    )

    add_check(
        checks,
        "validated_four_variants",
        variants_passed,
        (
            f"variants={len(variants)}, "
            f"before="
            f"{validation['correct_before']}, "
            f"after="
            f"{validation['correct_after']}, "
            f"regressions="
            f"{validation['regressions']}"
        ),
    )


def main() -> None:
    """Run all Homework 9 checks."""

    checks: list[dict[str, Any]] = []

    print(
        "DATA-260 Homework 9 Verification"
    )

    verify_configuration(checks)
    verify_redis(checks)
    verify_view_counter(checks)
    verify_semantic_cache(checks)
    verify_cache_cases(checks)
    verify_threshold_sweep(checks)
    verify_stale_cache(checks)
    verify_agent_datasets(checks)
    verify_self_improvement(checks)

    passed_count = sum(
        check["passed"]
        for check in checks
    )

    overall_passed = (
        passed_count == len(checks)
    )

    output = {
        "homework": 9,
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "prefix": PREFIX,
        "domain": "Clinical Trials",
        "commit_hash": current_commit(),
        "checks": checks,
        "passed_count": passed_count,
        "check_count": len(checks),
        "overall_passed": overall_passed,
        "generated_at": (
            datetime.now(UTC).isoformat()
        ),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"\nPassed: {passed_count}/"
        f"{len(checks)}"
    )

    print(
        "Overall: "
        + (
            "PASS"
            if overall_passed
            else "FAIL"
        )
    )

    print(f"Saved: {OUTPUT_PATH}")

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

