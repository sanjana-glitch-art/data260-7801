from __future__ import annotations

import json
import re
import subprocess
import sys
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    DEAD_LETTER_TOPIC,
    DRAFTS_TOPIC,
    FINAL_TOPIC,
    INBOX_TOPIC,
    PREFIX,
    REQUEST_TOPIC,
    RESPONSE_TOPIC,
    SEED,
    SID4,
    TASKS_TOPIC,
    VERIFY_SEED,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from confluent_kafka.admin import AdminClient

OUTPUT_PATH = Path(
    "reports/hw08/verification.json"
)
RAW_PATH = Path(
    "reports/hw08/raw"
)


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def record_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Append one objective verification check."""

    checks.append({
        "name": name,
        "passed": passed,
        "details": details,
    })


def read_json(
    path: Path,
) -> dict[str, Any]:
    """Read one JSON object."""

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise TypeError(
            f"{path} must contain an object."
        )

    return data


def git_commit_hash() -> str:
    """Return the checked-out commit hash."""

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        return "unavailable"

    return result.stdout.strip()


def verify_configuration(
    checks: list[dict[str, Any]],
) -> None:
    """Verify personalized configuration."""

    passed = all([
        SID4 == 7801,
        PREFIX == "s7801",
        SEED == 7801,
        VERIFY_SEED == 267801,
    ])

    record_check(
        checks,
        name="personal_configuration",
        passed=passed,
        details=(
            f"SID4={SID4}, PREFIX={PREFIX}, "
            f"SEED={SEED}, "
            f"VERIFY_SEED={VERIFY_SEED}"
        ),
    )


def verify_topics(
    checks: list[dict[str, Any]],
) -> None:
    """Verify required Kafka topics."""

    required_topics = {
        REQUEST_TOPIC,
        RESPONSE_TOPIC,
        INBOX_TOPIC,
        TASKS_TOPIC,
        DRAFTS_TOPIC,
        FINAL_TOPIC,
        DEAD_LETTER_TOPIC,
    }

    try:
        admin = AdminClient({
            "bootstrap.servers": (
                BOOTSTRAP_SERVERS
            ),
        })

        metadata = admin.list_topics(
            timeout=10.0
        )

        available_topics = set(
            metadata.topics
        )

        missing_topics = sorted(
            required_topics
            - available_topics
        )

        record_check(
            checks,
            name="required_kafka_topics",
            passed=not missing_topics,
            details=(
                "All required topics exist."
                if not missing_topics
                else (
                    "Missing topics: "
                    + ", ".join(missing_topics)
                )
            ),
        )

        task_metadata = metadata.topics.get(
            TASKS_TOPIC
        )

        partition_count = (
            len(task_metadata.partitions)
            if task_metadata is not None
            else 0
        )

        record_check(
            checks,
            name="tasks_topic_two_partitions",
            passed=partition_count == 2,
            details=(
                f"{TASKS_TOPIC} has "
                f"{partition_count} partitions."
            ),
        )

    except (
        RuntimeError,
        TimeoutError,
    ) as error:
        record_check(
            checks,
            name="required_kafka_topics",
            passed=False,
            details=(
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )

        record_check(
            checks,
            name="tasks_topic_two_partitions",
            passed=False,
            details=(
                "Kafka metadata unavailable."
            ),
        )


def verify_demo(
    checks: list[dict[str, Any]],
) -> None:
    """Run the Part 1 CREATE-to-GET smoke test."""

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code.homework_demo",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )

        output = (
            result.stdout
            + "\n"
            + result.stderr
        )

        round_trip_passed = (
            result.returncode == 0
            and (
                "CREATE -> GET round trip: PASS"
                in output
            )
        )

        correlation_passed = (
            result.returncode == 0
            and (
                "Correlation ID preserved: PASS"
                in output
            )
        )

        record_check(
            checks,
            name="create_get_round_trip",
            passed=round_trip_passed,
            details=(
                "CREATE followed by GET passed."
                if round_trip_passed
                else "CREATE/GET smoke test failed."
            ),
        )

        record_check(
            checks,
            name="correlation_id_preserved",
            passed=correlation_passed,
            details=(
                "Correlation ID was preserved."
                if correlation_passed
                else (
                    "Correlation ID check failed."
                )
            ),
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as error:
        record_check(
            checks,
            name="create_get_round_trip",
            passed=False,
            details=(
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )

        record_check(
            checks,
            name="correlation_id_preserved",
            passed=False,
            details=(
                "Demo could not complete."
            ),
        )


def verify_json_evidence(
    checks: list[dict[str, Any]],
) -> None:
    """Verify machine-readable experiment output."""

    evidence = [
        (
            "duplicate_before_demonstrated",
            RAW_PATH
            / "duplicate_before.json",
            "duplicate_side_effect",
            True,
        ),
        (
            "duplicate_after_idempotent",
            RAW_PATH
            / "duplicate_after.json",
            "idempotency_passed",
            True,
        ),
        (
            "poison_message_recovery",
            RAW_PATH
            / "poison_message_results.json",
            "overall_passed",
            True,
        ),
        (
            "ordering_experiment",
            RAW_PATH
            / "ordering_results.json",
            "overall_passed",
            True,
        ),
    ]

    for (
        name,
        path,
        field,
        expected,
    ) in evidence:
        try:
            data = read_json(path)
            actual = data.get(field)

            record_check(
                checks,
                name=name,
                passed=actual is expected,
                details=(
                    f"{path.name}: "
                    f"{field}={actual}"
                ),
            )

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
        ) as error:
            record_check(
                checks,
                name=name,
                passed=False,
                details=(
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

    try:
        pipeline = read_json(
            RAW_PATH
            / "pipeline_result.json"
        )

        pipeline_result = pipeline.get(
            "result"
        )

        if not isinstance(
            pipeline_result,
            dict,
        ):
            pipeline_result = {}

        pipeline_passed = (
            pipeline_result.get("status")
            == "approved"
            and bool(
                pipeline_result.get(
                    "correlation_id"
                )
            )
        )

        record_check(
            checks,
            name="three_agent_pipeline",
            passed=pipeline_passed,
            details=(
                "Final status="
                f"{pipeline_result.get('status')}"
            ),
        )

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ) as error:
        record_check(
            checks,
            name="three_agent_pipeline",
            passed=False,
            details=(
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def verify_consumer_redelivery(
    checks: list[dict[str, Any]],
) -> None:
    """Verify the consumer-death log."""

    path = (
        RAW_PATH
        / "consumer_death_writer_test.log"
    )

    try:
        raw_content = path.read_bytes()

        if raw_content.startswith((
            b"\xff\xfe",
            b"\xfe\xff",
        )):
            content = raw_content.decode(
                "utf-16"
            )
        else:
            content = raw_content.decode(
                "utf-8-sig",
                errors="replace",
            )

        received_ids = re.findall(
            (
                r'WRITER_RECEIVE\s+\|\s+'
                r'\{"correlation_id":\s*"'
                r'([^"]+)"'
            ),
            content,
        )

        sent_ids = set(
            re.findall(
                (
                    r'WRITER_SEND\s+\|\s+'
                    r'\{"correlation_id":\s*"'
                    r'([^"]+)"'
                ),
                content,
            )
        )

        redelivered_ids = {
            correlation_id
            for correlation_id
            in received_ids
            if (
                received_ids.count(
                    correlation_id
                )
                >= 2
            )
        }

        completed_ids = (
            redelivered_ids
            & sent_ids
        )

        delay_observed = (
            "WRITER_PROCESSING_DELAY"
            in content
        )

        passed = bool(
            completed_ids
        ) and delay_observed

        record_check(
            checks,
            name="consumer_death_redelivery",
            passed=passed,
            details=(
                "Redelivered and completed IDs: "
                + (
                    ", ".join(
                        sorted(completed_ids)
                    )
                    if completed_ids
                    else "none"
                )
            ),
        )

    except OSError as error:
        record_check(
            checks,
            name="consumer_death_redelivery",
            passed=False,
            details=(
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def main() -> None:
    """Run the Homework 8 self-check."""

    checks: list[dict[str, Any]] = []

    verify_configuration(checks)
    verify_topics(checks)
    verify_demo(checks)
    verify_json_evidence(checks)
    verify_consumer_redelivery(checks)

    passed_count = sum(
        1
        for check in checks
        if check["passed"]
    )

    overall_passed = (
        passed_count
        == len(checks)
    )

    document = {
        "homework": 8,
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": SID4,
        "commit_hash": (
            git_commit_hash()
        ),
        "configuration": {
            "prefix": PREFIX,
            "port_base": 8601,
            "seed": SEED,
            "verify_seed": VERIFY_SEED,
            "domain_id": 1,
            "domain": "Clinical Trials",
            "kafka_bootstrap_servers": (
                BOOTSTRAP_SERVERS
            ),
            "model": (
                "Deterministic Kafka agents; "
                "no LLM required"
            ),
        },
        "checks": checks,
        "passed_count": passed_count,
        "check_count": len(checks),
        "overall_passed": (
            overall_passed
        ),
        "generated_at": utc_timestamp(),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            document,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "DATA-260 Homework 8 Verification"
    )

    for check in checks:
        status = (
            "PASS"
            if check["passed"]
            else "FAIL"
        )

        print(
            f"{status} | "
            f"{check['name']} | "
            f"{check['details']}"
        )

    print()
    print(
        f"Passed: {passed_count}/"
        f"{len(checks)}"
    )
    print(
        "Overall:",
        (
            "PASS"
            if overall_passed
            else "FAIL"
        ),
    )
    print(
        "Saved:",
        OUTPUT_PATH.resolve(),
    )

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()