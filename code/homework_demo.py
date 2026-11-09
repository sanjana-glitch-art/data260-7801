from __future__ import annotations

import json
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    CREATE_OPERATION,
    GET_OPERATION,
    REQUEST_TOPIC,
    RESPONSE_TOPIC,
)
from code.hw8_kafka_client import (
    KafkaRpcClient,
)
from uuid import uuid4


def pretty(
    value: object,
) -> str:
    """Return readable JSON for the demo log."""

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def main() -> None:
    """Demonstrate CREATE followed by GET over Kafka."""

    correlation_id = str(uuid4())

    trial_data = {
        "trial_title": (
            "Kafka Clinical Trial "
            "Coordination Study"
        ),
        "trial_description": (
            "This Homework 8 clinical trial "
            "demonstrates Kafka request and "
            "response message coordination."
        ),
        "trial_phase": "Phase II",
        "sponsor_name": (
            "San Jose State University"
        ),
        "enrollment_target": 150,
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
        "DATA-260 Homework 8 Part 1"
    )
    print(
        "Student: Sanjana Thummalapalli"
    )
    print("SID4: 7801")
    print(
        "Request topic:",
        REQUEST_TOPIC,
    )
    print(
        "Response topic:",
        RESPONSE_TOPIC,
    )
    print(
        "Correlation ID:",
        correlation_id,
    )

    create_request = {
        "correlation_id": (
            correlation_id
        ),
        "reply_to": RESPONSE_TOPIC,
        "operation": CREATE_OPERATION,
        "data": trial_data,
    }

    print(
        "\n=== CREATE_CLINICAL_TRIAL ==="
    )
    print(
        "DEMO_CREATE_REQUEST |"
    )
    print(
        pretty(create_request)
    )

    create_response = client.request(
        CREATE_OPERATION,
        trial_data,
        correlation_id=correlation_id,
    )

    print(
        "DEMO_CREATE_RESPONSE |"
    )
    print(
        pretty(create_response)
    )

    if not create_response.get(
        "success"
    ):
        raise RuntimeError(
            "CREATE_CLINICAL_TRIAL failed."
        )

    entity_id = str(
        create_response["entity_id"]
    )

    get_request = {
        "correlation_id": (
            correlation_id
        ),
        "reply_to": RESPONSE_TOPIC,
        "operation": GET_OPERATION,
        "data": {
            "entity_id": entity_id,
        },
    }

    print(
        "\n=== GET_CLINICAL_TRIAL ==="
    )
    print(
        "DEMO_GET_REQUEST |"
    )
    print(
        pretty(get_request)
    )

    get_response = client.request(
        GET_OPERATION,
        {
            "entity_id": entity_id,
        },
        correlation_id=correlation_id,
    )

    print(
        "DEMO_GET_RESPONSE |"
    )
    print(
        pretty(get_response)
    )

    if not get_response.get(
        "success"
    ):
        raise RuntimeError(
            "GET_CLINICAL_TRIAL failed."
        )

    if (
        create_response.get(
            "correlation_id"
        )
        != correlation_id
        or get_response.get(
            "correlation_id"
        )
        != correlation_id
    ):
        raise RuntimeError(
            "Correlation ID was not preserved."
        )

    entity = get_response.get(
        "entity"
    )

    if not isinstance(entity, dict):
        raise TypeError(
            "Retrieved entity was invalid."
        )

    if (
        entity.get("entity_id")
        != entity_id
    ):
        raise RuntimeError(
            "Entity ID round trip failed."
        )

    print(
        "\n=== FINAL CONFIRMATION ==="
    )
    print(
        "CREATE -> GET round trip: PASS"
    )
    print(
        "Correlation ID preserved: PASS"
    )
    print(
        "Generated entity ID:",
        entity_id,
    )
    print(
        "Retrieved entity:"
    )
    print(
        pretty(entity)
    )


if __name__ == "__main__":
    main()


