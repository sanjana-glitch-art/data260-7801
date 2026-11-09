from __future__ import annotations

import json
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    TASKS_TOPIC,
)
from code.hw8_kafka_client import json_bytes
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from confluent_kafka import Producer

RESULT_PATH = Path(
    "reports/hw08/raw/"
    "consumer_death_task.json"
)


def main() -> None:
    """Send one task directly to the Writer."""

    correlation_id = str(uuid4())

    message = {
        "correlation_id": correlation_id,
        "question": (
            "How does Kafka redeliver "
            "unfinished clinical-trial work?"
        ),
        "plan": [
            (
                "Explain uncommitted Kafka "
                "offset behavior."
            ),
            (
                "Explain redelivery after "
                "a Writer restart."
            ),
        ],
        "entity_key": "consumer-death-test",
        "stage": "planned",
        "created_at": (
            datetime.now(UTC).isoformat()
        ),
    }

    producer = Producer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
    })

    producer.produce(
        TASKS_TOPIC,
        key=correlation_id,
        value=json_bytes(message),
    )

    undelivered = producer.flush(
        timeout=10.0
    )

    if undelivered:
        raise RuntimeError(
            "Consumer-death task delivery failed."
        )

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_PATH.write_text(
        json.dumps(
            message,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "CONSUMER_DEATH_TASK_SEND | "
        + json.dumps(message)
    )
    print(
        "Correlation ID:",
        correlation_id,
    )
    print(
        "Saved:",
        RESULT_PATH.resolve(),
    )


if __name__ == "__main__":
    main()