from __future__ import annotations

import json
import os
import time
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    DEAD_LETTER_TOPIC,
    DRAFTS_TOPIC,
    FINAL_TOPIC,
    INBOX_TOPIC,
    PLANNER_GROUP,
    REVIEWER_GROUP,
    TASKS_TOPIC,
    WRITER_GROUP,
)
from code.hw8_kafka_client import (
    json_bytes,
    parse_json_bytes,
)
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    Producer,
    TopicPartition,
)


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def create_consumer(
    group_id: str,
) -> Consumer:
    """Create a manual-commit Kafka consumer."""

    return Consumer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })


def create_producer() -> Producer:
    """Create a Kafka JSON producer."""

    return Producer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
    })


def send_json(
    producer: Producer,
    topic: str,
    message: dict[str, Any],
    *,
    key: str,
) -> None:
    """Send one JSON message and require delivery."""

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
            f"Message delivery to {topic} failed."
        )


def log_event(
    event: str,
    message: dict[str, Any],
) -> None:
    """Print one structured pipeline log event."""

    print(
        event
        + " | "
        + json.dumps(
            message,
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


def validate_envelope(
    message: dict[str, Any],
) -> tuple[str, str]:
    """Validate shared pipeline fields."""

    correlation_id = message.get(
        "correlation_id"
    )

    if (
        not isinstance(correlation_id, str)
        or not correlation_id.strip()
    ):
        raise ValueError(
            "correlation_id must be "
            "a non-empty string."
        )

    question = message.get(
        "question"
    )

    if (
        not isinstance(question, str)
        or not question.strip()
    ):
        raise ValueError(
            "question must be "
            "a non-empty string."
        )

    return (
        correlation_id,
        question.strip(),
    )


def build_plan(
    question: str,
) -> list[str]:
    """Create a deterministic clinical-trial plan."""

    return [
        (
            "Identify the main clinical-trial "
            "coordination concept in the question."
        ),
        (
            "Explain how Kafka topics and "
            "correlation IDs support the workflow."
        ),
        (
            "Provide a concise answer grounded "
            "in the clinical-trial domain."
        ),
        (
            "Check that the answer directly "
            f"addresses: {question}"
        ),
    ]


def build_draft(
    question: str,
    plan: list[str],
) -> str:
    """Create a deterministic draft answer."""

    plan_summary = " ".join(
        f"{index + 1}) {step}"
        for index, step in enumerate(plan)
    )

    return (
        "Kafka improves clinical-trial coordination "
        "by decoupling request producers from the "
        "services that process trial work. Each "
        "message keeps a correlation ID, allowing "
        "the system to connect plans, drafts, and "
        "reviewed answers even though the agents run "
        "as independent processes. Kafka also stores "
        "messages durably so work can continue after "
        "a consumer restart. The response to the "
        f"question '{question}' follows this plan: "
        f"{plan_summary}"
    )


def review_draft(
    draft: str,
) -> tuple[str, str]:
    """Review a draft and return status and answer."""

    if len(draft.strip()) < 80:
        return (
            "rejected",
            (
                "The draft was too short to "
                "provide a complete answer."
            ),
        )

    answer = (
        draft.strip()
        + " Reviewer conclusion: the answer is "
        "complete, relevant, and approved."
    )

    return "approved", answer


def run_planner() -> None:
    """Consume inbox questions and produce plans."""

    consumer = create_consumer(
        PLANNER_GROUP
    )
    producer = create_producer()

    consumer.subscribe([
        INBOX_TOPIC
    ])

    print(
        "Planner is ready and listening...",
        flush=True,
    )

    try:
        while True:
            kafka_message = consumer.poll(1.0)

            if kafka_message is None:
                continue

            if kafka_message.error():
                print(
                    "PLANNER_ERROR | "
                    + str(kafka_message.error()),
                    flush=True,
                )
                continue

            message = parse_json_bytes(
                kafka_message.value()
            )

            log_event(
                "PLANNER_RECEIVE",
                message,
            )

            delay_seconds = float(
                os.getenv(
                    "HW8_WRITER_DELAY_SECONDS",
                    "0",
                )
            )

            if delay_seconds > 0:
                print(
                    "WRITER_PROCESSING_DELAY"
                    f" | seconds={delay_seconds}"
                    f" | partition={kafka_message.partition()}"
                    f" | offset={kafka_message.offset()}",
                    flush=True,
                )

                time.sleep(delay_seconds)

            correlation_id, question = (
                validate_envelope(message)
            )

            task_message = {
                "correlation_id": (
                    correlation_id
                ),
                "question": question,
                "plan": build_plan(
                    question
                ),
                "entity_key": message.get(
                    "entity_key",
                    "clinical-trials",
                ),
                "stage": "planned",
                "created_at": (
                    utc_timestamp()
                ),
            }

            send_json(
                producer,
                TASKS_TOPIC,
                task_message,
                key=str(
                    task_message[
                        "entity_key"
                    ]
                ),
            )

            log_event(
                "PLANNER_SEND",
                task_message,
            )

            consumer.commit(
                message=kafka_message,
                asynchronous=False,
            )
    except KeyboardInterrupt:
        print(
            "Planner stopped.",
            flush=True,
        )
    finally:
        producer.flush(timeout=2.0)
        consumer.close()


def run_writer() -> None:
    """Consume plans, retry failures, and produce drafts."""

    max_processing_attempts = 3

    consumer = create_consumer(
        WRITER_GROUP
    )
    producer = create_producer()

    consumer.subscribe([
        TASKS_TOPIC
    ])

    print(
        "Writer is ready and listening...",
        flush=True,
    )

    try:
        while True:
            kafka_message = consumer.poll(1.0)

            if kafka_message is None:
                continue

            if kafka_message.error():
                print(
                    "WRITER_ERROR | "
                    + str(kafka_message.error()),
                    flush=True,
                )
                continue

            try:
                message = parse_json_bytes(
                    kafka_message.value()
                )
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
            ) as error:
                message = {
                    "raw_value": (
                        kafka_message.value().decode(
                            "utf-8",
                            errors="replace",
                        )
                    ),
                    "parse_error": str(error),
                }

            log_event(
                "WRITER_RECEIVE",
                message,
            )

            delay_seconds = float(
                os.getenv(
                    "HW8_WRITER_DELAY_SECONDS",
                    "0",
                )
            )

            if delay_seconds > 0:
                print(
                    "WRITER_PROCESSING_DELAY"
                    f" | seconds={delay_seconds}"
                    f" | partition={kafka_message.partition()}"
                    f" | offset={kafka_message.offset()}",
                    flush=True,
                )

                time.sleep(delay_seconds)

            correlation_value = message.get(
                "correlation_id"
            )

            if (
                isinstance(correlation_value, str)
                and correlation_value.strip()
            ):
                message_key = correlation_value
            else:
                message_key = (
                    "poison-"
                    f"{kafka_message.partition()}-"
                    f"{kafka_message.offset()}"
                )

            for attempt in range(
                1,
                max_processing_attempts + 1,
            ):
                try:
                    correlation_id, question = (
                        validate_envelope(message)
                    )

                    plan = message.get("plan")

                    if not isinstance(plan, list):
                        raise TypeError(
                            "plan must be a list."
                        )

                    if not plan:
                        raise ValueError(
                            "plan must not be empty."
                        )

                    processing_delay_ms = (
                        message.get(
                            "processing_delay_ms",
                            0,
                        )
                    )

                    if not isinstance(
                        processing_delay_ms,
                        (int, float),
                    ):
                        raise TypeError(
                            "processing_delay_ms "
                            "must be numeric."
                        )

                    if processing_delay_ms < 0:
                        raise ValueError(
                            "processing_delay_ms "
                            "must not be negative."
                        )

                    if processing_delay_ms > 0:
                        time.sleep(
                            processing_delay_ms
                            / 1000
                        )

                    draft_message = {
                        "correlation_id": (
                            correlation_id
                        ),
                                                "experiment_label": (
                            message.get(
                                "experiment_label"
                            )
                        ),
                        "sequence": message.get(
                            "sequence"
                        ),
                        "source_partition": (
                            kafka_message.partition()
                        ),
                        "source_offset": (
                            kafka_message.offset()
                        ),
                        "writer_instance": (
                            f"writer-{os.getpid()}"
                        ),
                        "draft": build_draft(
                            question,
                            [
                                str(step)
                                for step in plan
                            ],
                        ),
                        "entity_key": message.get(
                            "entity_key",
                            "clinical-trials",
                        ),
                        "stage": "drafted",
                        "created_at": (
                            utc_timestamp()
                        ),
                    }

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as error:
                    if (
                        attempt
                        < max_processing_attempts
                    ):
                        retry_event = {
                            "correlation_id": (
                                message_key
                            ),
                            "attempt": attempt,
                            "maximum_attempts": (
                                max_processing_attempts
                            ),
                            "error_type": (
                                type(error).__name__
                            ),
                            "error": str(error),
                        }

                        log_event(
                            "WRITER_RETRY",
                            retry_event,
                        )

                        time.sleep(0.25)
                        continue

                    dead_letter_message = {
                        "correlation_id": (
                            message_key
                        ),
                        "source_topic": (
                            TASKS_TOPIC
                        ),
                        "source_partition": (
                            kafka_message.partition()
                        ),
                        "source_offset": (
                            kafka_message.offset()
                        ),
                        "attempts": (
                            max_processing_attempts
                        ),
                        "error_type": (
                            type(error).__name__
                        ),
                        "error": str(error),
                        "original_message": message,
                        "failed_at": utc_timestamp(),
                    }

                    send_json(
                        producer,
                        DEAD_LETTER_TOPIC,
                        dead_letter_message,
                        key=message_key,
                    )

                    log_event(
                        "WRITER_DEAD_LETTER",
                        dead_letter_message,
                    )

                    consumer.commit(
                        message=kafka_message,
                        asynchronous=False,
                    )

                    print(
                        "WRITER_COMMIT_DEAD_LETTER"
                        f" | {message_key}",
                        flush=True,
                    )
                    break

                else:
                    send_json(
                        producer,
                        DRAFTS_TOPIC,
                        draft_message,
                        key=correlation_id,
                    )

                    log_event(
                        "WRITER_SEND",
                        draft_message,
                    )

                    consumer.commit(
                        message=kafka_message,
                        asynchronous=False,
                    )

                    print(
                        "WRITER_COMMIT"
                        f" | {correlation_id}",
                        flush=True,
                    )
                    break

    except KeyboardInterrupt:
        print(
            "Writer stopped.",
            flush=True,
        )
    finally:
        producer.flush(timeout=2.0)
        consumer.close()


def run_reviewer() -> None:
    """Consume drafts and produce final messages."""

    consumer = create_consumer(
        REVIEWER_GROUP
    )
    producer = create_producer()

    consumer.subscribe([
        DRAFTS_TOPIC
    ])

    print(
        "Reviewer is ready and listening...",
        flush=True,
    )

    try:
        while True:
            kafka_message = consumer.poll(1.0)

            if kafka_message is None:
                continue

            if kafka_message.error():
                print(
                    "REVIEWER_ERROR | "
                    + str(kafka_message.error()),
                    flush=True,
                )
                continue

            message = parse_json_bytes(
                kafka_message.value()
            )

            log_event(
                "REVIEWER_RECEIVE",
                message,
            )

            correlation_id, question = (
                validate_envelope(message)
            )

            draft = message.get("draft")

            if not isinstance(draft, str):
                raise TypeError(
                    "draft must be a string."
                )

            status, answer = review_draft(
                draft
            )

            final_message = {
                "correlation_id": (
                    correlation_id
                ),
                "question": question,
                "status": status,
                "answer": answer,
                "entity_key": message.get(
                    "entity_key",
                    "clinical-trials",
                ),
                "stage": "reviewed",
                "created_at": (
                    utc_timestamp()
                ),
            }

            send_json(
                producer,
                FINAL_TOPIC,
                final_message,
                key=correlation_id,
            )

            log_event(
                "REVIEWER_SEND",
                final_message,
            )

            consumer.commit(
                message=kafka_message,
                asynchronous=False,
            )
    except KeyboardInterrupt:
        print(
            "Reviewer stopped.",
            flush=True,
        )
    finally:
        producer.flush(timeout=2.0)
        consumer.close()


def send_question_and_wait(
    question: str,
    *,
    entity_key: str = "clinical-trials",
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Send one question and wait for its final answer."""

    correlation_id = str(uuid4())

    consumer = create_consumer(
        "s7801_final_reader_"
        + uuid4().hex
    )

    producer = create_producer()

    final_partition = TopicPartition(
        FINAL_TOPIC,
        0,
    )

    _low_offset, high_offset = (
        consumer.get_watermark_offsets(
            final_partition,
            timeout=5.0,
            cached=False,
        )
    )

    consumer.assign([
        TopicPartition(
            FINAL_TOPIC,
            0,
            high_offset,
        )
    ])

    inbox_message = {
        "correlation_id": (
            correlation_id
        ),
        "question": question,
        "entity_key": entity_key,
        "stage": "submitted",
        "created_at": utc_timestamp(),
    }

    try:
        send_json(
            producer,
            INBOX_TOPIC,
            inbox_message,
            key=correlation_id,
        )

        log_event(
            "QUESTION_SEND",
            inbox_message,
        )

        deadline = (
            time.monotonic()
            + timeout_seconds
        )

        while time.monotonic() < deadline:
            kafka_message = consumer.poll(
                0.25
            )

            if kafka_message is None:
                continue

            if kafka_message.error():
                raise RuntimeError(
                    str(
                        kafka_message.error()
                    )
                )

            result = parse_json_bytes(
                kafka_message.value()
            )

            if (
                result.get(
                    "correlation_id"
                )
                != correlation_id
            ):
                continue

            log_event(
                "FINAL_RECEIVE",
                result,
            )

            return result

        raise TimeoutError(
            "Timed out waiting for "
            "the final pipeline result."
        )
    finally:
        producer.flush(timeout=2.0)
        consumer.close()
