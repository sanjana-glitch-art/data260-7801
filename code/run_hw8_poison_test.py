from __future__ import annotations

import json
import time
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    DEAD_LETTER_TOPIC,
    DRAFTS_TOPIC,
    TASKS_TOPIC,
)
from code.hw8_kafka_client import (
    json_bytes,
    parse_json_bytes,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    Producer,
    TopicPartition,
)

RESULT_PATH = Path(
    "reports/hw08/raw/poison_message_results.json"
)

WAIT_SECONDS = 30.0


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def create_tail_consumer(
    topic: str,
) -> Consumer:
    """Consume only messages produced after startup."""

    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": (
            "s7801-poison-verifier-"
            + str(uuid4())
        ),
        "enable.auto.commit": False,
        "auto.offset.reset": "latest",
    })

    partition = TopicPartition(
        topic,
        0,
    )

    _, high_watermark = (
        consumer.get_watermark_offsets(
            partition,
            timeout=10.0,
            cached=False,
        )
    )

    consumer.assign([
        TopicPartition(
            topic,
            0,
            high_watermark,
        )
    ])

    return consumer


def produce_json(
    producer: Producer,
    topic: str,
    message: dict[str, Any],
    key: str,
) -> None:
    """Produce one JSON message."""

    producer.produce(
        topic,
        key=key,
        value=json_bytes(message),
    )

    undelivered = producer.flush(
        timeout=10.0
    )

    if undelivered:
        raise RuntimeError(
            f"Delivery to {topic} failed."
        )


def wait_for_correlation(
    consumer: Consumer,
    correlation_id: str,
) -> dict[str, Any]:
    """Wait for one matching correlation ID."""

    deadline = (
        time.monotonic()
        + WAIT_SECONDS
    )

    while time.monotonic() < deadline:
        kafka_message = consumer.poll(1.0)

        if kafka_message is None:
            continue

        if kafka_message.error():
            raise RuntimeError(
                str(kafka_message.error())
            )

        message = parse_json_bytes(
            kafka_message.value()
        )

        if (
            message.get("correlation_id")
            == correlation_id
        ):
            return message

    raise TimeoutError(
        "Timed out waiting for "
        f"correlation ID {correlation_id}."
    )


def main() -> None:
    """Test poison handling and worker recovery."""

    producer = Producer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
    })

    dead_letter_consumer = (
        create_tail_consumer(
            DEAD_LETTER_TOPIC
        )
    )

    draft_consumer = create_tail_consumer(
        DRAFTS_TOPIC
    )

    poison_correlation_id = str(
        uuid4()
    )
    valid_correlation_id = str(
        uuid4()
    )

    poison_message = {
        "correlation_id": (
            poison_correlation_id
        ),
        "question": (
            "This message intentionally "
            "contains an invalid plan."
        ),
        "plan": "not-a-list",
        "entity_key": "clinical-trials",
        "stage": "planned",
        "created_at": utc_timestamp(),
    }

    valid_message = {
        "correlation_id": (
            valid_correlation_id
        ),
        "question": (
            "How does Kafka support "
            "clinical-trial coordination?"
        ),
        "plan": [
            (
                "Explain Kafka message "
                "coordination."
            ),
            (
                "Relate the explanation "
                "to clinical trials."
            ),
        ],
        "entity_key": "clinical-trials",
        "stage": "planned",
        "created_at": utc_timestamp(),
    }

    print(
        "DATA-260 Homework 8 Part 3"
    )
    print(
        "Poison Message and Dead Letter Test"
    )
    print(
        "Poison correlation ID:",
        poison_correlation_id,
    )

    try:
        produce_json(
            producer,
            TASKS_TOPIC,
            poison_message,
            poison_correlation_id,
        )

        print(
            "POISON_SEND |",
            json.dumps(poison_message),
        )

        dead_letter_message = (
            wait_for_correlation(
                dead_letter_consumer,
                poison_correlation_id,
            )
        )

        print(
            "DEAD_LETTER_RECEIVE |",
            json.dumps(
                dead_letter_message
            ),
        )

        produce_json(
            producer,
            TASKS_TOPIC,
            valid_message,
            valid_correlation_id,
        )

        print(
            "VALID_SEND |",
            json.dumps(valid_message),
        )

        valid_draft = (
            wait_for_correlation(
                draft_consumer,
                valid_correlation_id,
            )
        )

        print(
            "VALID_DRAFT_RECEIVE |",
            json.dumps(valid_draft),
        )

    finally:
        producer.flush(timeout=2.0)
        dead_letter_consumer.close()
        draft_consumer.close()

    retry_limit_passed = (
        dead_letter_message.get(
            "attempts"
        )
        == 3
    )

    dead_letter_passed = (
        dead_letter_message.get(
            "correlation_id"
        )
        == poison_correlation_id
        and dead_letter_message.get(
            "source_topic"
        )
        == TASKS_TOPIC
    )

    worker_recovery_passed = (
        valid_draft.get(
            "correlation_id"
        )
        == valid_correlation_id
        and valid_draft.get(
            "stage"
        )
        == "drafted"
    )

    overall_passed = all([
        retry_limit_passed,
        dead_letter_passed,
        worker_recovery_passed,
    ])

    results = {
        "experiment": (
            "hw8_poison_message"
        ),
        "poison_correlation_id": (
            poison_correlation_id
        ),
        "valid_correlation_id": (
            valid_correlation_id
        ),
        "maximum_attempts": 3,
        "dead_letter_message": (
            dead_letter_message
        ),
        "valid_draft": valid_draft,
        "retry_limit_passed": (
            retry_limit_passed
        ),
        "dead_letter_passed": (
            dead_letter_passed
        ),
        "worker_recovery_passed": (
            worker_recovery_passed
        ),
        "overall_passed": (
            overall_passed
        ),
        "generated_at": utc_timestamp(),
    }

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_PATH.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Retries exhausted:",
        retry_limit_passed,
    )
    print(
        "Dead letter produced:",
        dead_letter_passed,
    )
    print(
        "Next valid message processed:",
        worker_recovery_passed,
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
        RESULT_PATH.resolve(),
    )

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()