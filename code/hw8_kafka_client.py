from __future__ import annotations

import json
import time
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    REQUEST_TOPIC,
    RESPONSE_TOPIC,
)
from typing import Any
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    Producer,
    TopicPartition,
)


class KafkaRequestError(RuntimeError):
    """Raised when the Kafka request/response flow fails."""


def json_bytes(
    value: dict[str, Any],
) -> bytes:
    """Serialize one dictionary to UTF-8 JSON bytes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def parse_json_bytes(
    value: bytes | None,
) -> dict[str, Any]:
    """Deserialize one Kafka JSON message."""

    if value is None:
        raise KafkaRequestError(
            "Kafka message did not contain a value."
        )

    decoded = json.loads(
        value.decode("utf-8")
    )

    if not isinstance(decoded, dict):
        raise KafkaRequestError(
            "Kafka message must contain a JSON object."
        )

    return decoded


class KafkaRpcClient:
    """Send a Kafka request and wait for its correlated response."""

    def __init__(
        self,
        bootstrap_servers: str = BOOTSTRAP_SERVERS,
        request_topic: str = REQUEST_TOPIC,
        response_topic: str = RESPONSE_TOPIC,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.request_topic = request_topic
        self.response_topic = response_topic
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        operation: str,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Send one request and return the matching response."""

        request_correlation_id = (
            correlation_id or str(uuid4())
        )

        request_message = {
            "correlation_id": (
                request_correlation_id
            ),
            "reply_to": self.response_topic,
            "operation": operation,
            "data": data,
        }

        consumer = Consumer({
            "bootstrap.servers": (
                self.bootstrap_servers
            ),
            "group.id": (
                "s7801_rpc_"
                + request_correlation_id
                + "_"
                + uuid4().hex
            ),
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        })

        producer = Producer({
            "bootstrap.servers": (
                self.bootstrap_servers
            ),
        })

        try:
            response_partition = (
                TopicPartition(
                    self.response_topic,
                    0,
                )
            )

            _low_offset, high_offset = (
                consumer.get_watermark_offsets(
                    response_partition,
                    timeout=5.0,
                    cached=False,
                )
            )

            consumer.assign([
                TopicPartition(
                    self.response_topic,
                    0,
                    high_offset,
                )
            ])

            print(
                "CLIENT_SEND | "
                + json.dumps(
                    request_message,
                    ensure_ascii=False,
                ),
                flush=True,
            )

            producer.produce(
                self.request_topic,
                key=request_correlation_id,
                value=json_bytes(
                    request_message
                ),
            )

            undelivered = producer.flush(
                timeout=10.0
            )

            if undelivered:
                raise KafkaRequestError(
                    "Kafka request could not be delivered."
                )

            deadline = (
                time.monotonic()
                + self.timeout_seconds
            )

            while time.monotonic() < deadline:
                message = consumer.poll(0.25)

                if message is None:
                    continue

                if message.error():
                    raise KafkaRequestError(
                        str(message.error())
                    )

                response = parse_json_bytes(
                    message.value()
                )

                if (
                    response.get(
                        "correlation_id"
                    )
                    != request_correlation_id
                ):
                    continue

                print(
                    "CLIENT_RECEIVE | "
                    + json.dumps(
                        response,
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

                return response

            raise KafkaRequestError(
                "Timed out waiting for the "
                "correlated Kafka response."
            )
        finally:
            producer.flush(timeout=2.0)
            consumer.close()
