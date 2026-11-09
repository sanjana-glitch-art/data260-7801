from __future__ import annotations

import json
from code.hw8_config import (
    ALLOWED_PHASES,
    BOOTSTRAP_SERVERS,
    CREATE_OPERATION,
    GET_OPERATION,
    REQUEST_TOPIC,
    REQUIRED_TRIAL_FIELDS,
    RESPONSE_TOPIC,
    WORKER_GROUP,
)
from code.hw8_kafka_client import (
    json_bytes,
    parse_json_bytes,
)
from typing import Any
from uuid import uuid4

from confluent_kafka import Consumer, Producer

TRIAL_STORE: dict[
    str,
    dict[str, Any],
] = {}

PROCESSED_CREATE_RESPONSES: dict[
    str,
    dict[str, Any],
] = {}


def error_response(
    correlation_id: str,
    message: str,
) -> dict[str, Any]:
    """Return one clean unsuccessful response."""

    return {
        "correlation_id": correlation_id,
        "success": False,
        "error": message,
    }


def validate_trial_data(
    data: Any,
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:
    """Validate clinical-trial creation data."""

    if not isinstance(data, dict):
        return (
            None,
            "data must be a JSON object.",
        )

    for field in REQUIRED_TRIAL_FIELDS:
        if field not in data:
            return (
                None,
                f"Missing required field: {field}",
            )

    for field in (
        "trial_title",
        "trial_description",
        "trial_phase",
        "sponsor_name",
    ):
        value = data.get(field)

        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            return (
                None,
                (f"{field} must be a "
                "non-empty string."),
            )

    phase = data["trial_phase"].strip()

    if phase not in ALLOWED_PHASES:
        return (
            None,
            ("trial_phase must be Phase I, "
            "Phase II, Phase III, or Phase IV."),
        )

    enrollment_target = data.get(
        "enrollment_target"
    )

    if (
        not isinstance(
            enrollment_target,
            int,
        )
        or isinstance(
            enrollment_target,
            bool,
        )
        or enrollment_target <= 0
    ):
        return (
            None,
            ("enrollment_target must be "
            "a positive integer."),
        )

    normalized = {
        "trial_title": (
            data["trial_title"].strip()
        ),
        "trial_description": (
            data[
                "trial_description"
            ].strip()
        ),
        "trial_phase": phase,
        "sponsor_name": (
            data["sponsor_name"].strip()
        ),
        "enrollment_target": (
            enrollment_target
        ),
    }

    return normalized, None


def process_request(
    request: dict[str, Any],
) -> dict[str, Any]:
    """Process one Homework 8 domain request."""

    correlation_id = str(
        request.get(
            "correlation_id",
            "",
        )
    )

    operation = request.get(
        "operation"
    )

    data = request.get(
        "data"
    )

    if not correlation_id:
        return error_response(
            correlation_id,
            "Missing correlation_id.",
        )

    if operation == CREATE_OPERATION:
        cached_response = (
            PROCESSED_CREATE_RESPONSES.get(
                correlation_id
            )
        )

        if cached_response is not None:
            return {
                **cached_response,
                "idempotent_replay": True,
            }

        trial_data, validation_error = (
            validate_trial_data(data)
        )

        if validation_error:
            return error_response(
                correlation_id,
                validation_error,
            )

        assert trial_data is not None

        entity_id = str(uuid4())

        stored_trial = {
            "entity_id": entity_id,
            **trial_data,
        }

        TRIAL_STORE[
            entity_id
        ] = stored_trial

        response = {
            "correlation_id": (
                correlation_id
            ),
            "success": True,
            "entity_id": entity_id,
            "message": (
                "Clinical trial created"
            ),
            "idempotent_replay": False,
        }

        PROCESSED_CREATE_RESPONSES[
            correlation_id
        ] = dict(response)

        return response

    if operation == GET_OPERATION:
        if not isinstance(data, dict):
            return error_response(
                correlation_id,
                "data must be a JSON object.",
            )

        entity_id = data.get(
            "entity_id"
        )

        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
        ):
            return error_response(
                correlation_id,
                "entity_id must be a "
                "non-empty string.",
            )

        trial = TRIAL_STORE.get(
            entity_id
        )

        if trial is None:
            return error_response(
                correlation_id,
                "Clinical trial not found.",
            )

        return {
            "correlation_id": (
                correlation_id
            ),
            "success": True,
            "entity": trial,
        }

    return error_response(
        correlation_id,
        "Unknown operation.",
    )


def run_worker() -> None:
    """Consume and process Kafka entity requests."""

    consumer = Consumer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
        "group.id": WORKER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    producer = Producer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
    })

    consumer.subscribe([
        REQUEST_TOPIC
    ])

    print(
        "Consumer is ready and listening...",
        flush=True,
    )

    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                print(
                    "WORKER_CONSUMER_ERROR | "
                    + str(message.error()),
                    flush=True,
                )
                continue

            try:
                request = parse_json_bytes(
                    message.value()
                )

                print(
                    "WORKER_RECEIVE | "
                    + json.dumps(
                        request,
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

                print(
                    "WORKER_PROCESS | "
                    + str(
                        request.get(
                            "operation"
                        )
                    ),
                    flush=True,
                )

                response = process_request(
                    request
                )

                if response.get(
                    "idempotent_replay"
                ):
                    print(
                        "WORKER_IDEMPOTENT_REPLAY | "
                        + str(
                            request.get(
                                "correlation_id"
                            )
                        ),
                        flush=True,
                    )

                reply_to = request.get(
                    "reply_to",
                    RESPONSE_TOPIC,
                )

                if (
                    not isinstance(
                        reply_to,
                        str,
                    )
                    or not reply_to.strip()
                ):
                    reply_to = (
                        RESPONSE_TOPIC
                    )

                producer.produce(
                    reply_to,
                    key=str(
                        request.get(
                            "correlation_id",
                            "",
                        )
                    ),
                    value=json_bytes(
                        response
                    ),
                )

                undelivered = (
                    producer.flush(
                        timeout=10.0
                    )
                )

                if undelivered:
                    raise RuntimeError(
                        "Worker response "
                        "delivery failed."
                    )

                print(
                    "WORKER_REPLY | "
                    + json.dumps(
                        response,
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

                consumer.commit(
                    message=message,
                    asynchronous=False,
                )

                print(
                    "WORKER_COMMIT | "
                    + str(
                        request.get(
                            "correlation_id"
                        )
                    ),
                    flush=True,
                )
            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
                TypeError,
                ValueError,
                RuntimeError,
            ) as error:
                print(
                    "WORKER_PROCESSING_ERROR | "
                    + type(error).__name__
                    + ": "
                    + str(error),
                    flush=True,
                )
    except KeyboardInterrupt:
        print(
            "Worker stopped.",
            flush=True,
        )
    finally:
        producer.flush(timeout=2.0)
        consumer.close()


if __name__ == "__main__":
    run_worker()
