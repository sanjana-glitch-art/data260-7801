from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    CREATE_OPERATION,
    REQUEST_TOPIC,
    RESPONSE_TOPIC,
)
from code.hw8_kafka_client import (
    KafkaRpcClient,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw08"
    / "raw"
)


def parse_arguments() -> argparse.Namespace:
    """Read the experiment label."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--label",
        choices=(
            "before",
            "after",
        ),
        required=True,
    )

    return parser.parse_args()


def run_duplicate_test(
    label: str,
) -> dict[str, Any]:
    """Replay one CREATE request."""

    correlation_id = str(uuid4())

    trial_data = {
        "trial_title": (
            "Duplicate Delivery "
            "Clinical Trial"
        ),
        "trial_description": (
            "This trial is used to test "
            "duplicate Kafka delivery."
        ),
        "trial_phase": "Phase I",
        "sponsor_name": (
            "San Jose State University"
        ),
        "enrollment_target": 75,
    }

    client = KafkaRpcClient(
        bootstrap_servers=(
            BOOTSTRAP_SERVERS
        ),
        request_topic=REQUEST_TOPIC,
        response_topic=RESPONSE_TOPIC,
        timeout_seconds=20.0,
    )

    print(
        "HW8 DUPLICATE DELIVERY TEST"
    )
    print("Label:", label)
    print(
        "Correlation ID:",
        correlation_id,
    )

    first_response = client.request(
        CREATE_OPERATION,
        trial_data,
        correlation_id=correlation_id,
    )

    print(
        "FIRST_RESPONSE |",
        json.dumps(
            first_response,
            ensure_ascii=False,
        ),
    )

    second_response = client.request(
        CREATE_OPERATION,
        trial_data,
        correlation_id=correlation_id,
    )

    print(
        "SECOND_RESPONSE |",
        json.dumps(
            second_response,
            ensure_ascii=False,
        ),
    )

    first_entity_id = (
        first_response.get(
            "entity_id"
        )
    )

    second_entity_id = (
        second_response.get(
            "entity_id"
        )
    )

    duplicate_side_effect = (
        first_entity_id
        != second_entity_id
    )

    document = {
        "experiment": (
            "hw8_duplicate_delivery"
        ),
        "label": label,
        "correlation_id": (
            correlation_id
        ),
        "first_response": (
            first_response
        ),
        "second_response": (
            second_response
        ),
        "duplicate_side_effect": (
            duplicate_side_effect
        ),
        "idempotency_passed": (
            not duplicate_side_effect
        ),
    }

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        RAW_DIRECTORY
        / f"duplicate_{label}.json"
    )

    output_path.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "First entity ID:",
        first_entity_id,
    )
    print(
        "Second entity ID:",
        second_entity_id,
    )
    print(
        "Duplicate side effect:",
        duplicate_side_effect,
    )
    print(
        "Idempotency passed:",
        not duplicate_side_effect,
    )
    print(
        "Saved:",
        output_path,
    )

    return document


def main() -> None:
    """Run the selected duplicate test."""

    arguments = parse_arguments()

    run_duplicate_test(
        arguments.label
    )


if __name__ == "__main__":
    main()