from __future__ import annotations

import json
from code.hw8_config import (
    API_TIMEOUT_SECONDS,
    BOOTSTRAP_SERVERS,
    CREATE_OPERATION,
    GET_OPERATION,
    PORT_BASE,
    PREFIX,
    REQUEST_TOPIC,
    RESPONSE_TOPIC,
)
from code.hw8_kafka_client import (
    KafkaRequestError,
    KafkaRpcClient,
)
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="DATA-260 Homework 8 Kafka API",
    description=(
        "Kafka request/response API for "
        "clinical-trial entities."
    ),
    version="8.0.0",
)


class ClinicalTrialData(BaseModel):
    """Clinical-trial fields sent to the Kafka worker."""

    trial_title: str = Field(
        min_length=2,
        max_length=255,
    )
    trial_description: str = Field(
        min_length=10,
        max_length=10000,
    )
    trial_phase: str
    sponsor_name: str = Field(
        min_length=2,
        max_length=255,
    )
    enrollment_target: int = Field(
        gt=0,
        le=1000000,
    )


class CreateTrialRequest(BaseModel):
    """API input for CREATE_CLINICAL_TRIAL."""

    operation: str = CREATE_OPERATION
    correlation_id: str | None = None
    data: ClinicalTrialData


def rpc_client() -> KafkaRpcClient:
    """Create one Kafka request/response client."""

    return KafkaRpcClient(
        bootstrap_servers=(
            BOOTSTRAP_SERVERS
        ),
        request_topic=REQUEST_TOPIC,
        response_topic=RESPONSE_TOPIC,
        timeout_seconds=(
            API_TIMEOUT_SECONDS
        ),
    )


def send_request(
    operation: str,
    data: dict[str, Any],
    correlation_id: str,
) -> dict[str, Any]:
    """Send one request through Kafka."""

    print(
        "API_REQUEST | "
        + json.dumps({
            "correlation_id": (
                correlation_id
            ),
            "operation": operation,
            "data": data,
        }),
        flush=True,
    )

    try:
        response = rpc_client().request(
            operation,
            data,
            correlation_id=correlation_id,
        )
    except KafkaRequestError as error:
        raise HTTPException(
            status_code=504,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Kafka service unavailable: "
                + str(error)
            ),
        ) from error

    print(
        "API_RESPONSE | "
        + json.dumps(
            response,
            ensure_ascii=False,
        ),
        flush=True,
    )

    if not response.get("success"):
        error_message = str(
            response.get(
                "error",
                "Kafka worker request failed.",
            )
        )

        status_code = (
            404
            if "not found"
            in error_message.lower()
            else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=response,
        )

    return response


@app.get("/")
def read_root() -> dict[str, Any]:
    """Return Homework 8 service information."""

    return {
        "application": (
            "DATA-260 Homework 8 Kafka API"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "prefix": PREFIX,
        "port": PORT_BASE,
        "request_topic": REQUEST_TOPIC,
        "response_topic": RESPONSE_TOPIC,
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Return the API process health state."""

    return {
        "status": "ok",
        "kafka_bootstrap_servers": (
            BOOTSTRAP_SERVERS
        ),
        "request_topic": REQUEST_TOPIC,
        "response_topic": RESPONSE_TOPIC,
    }


@app.post(
    "/hw8/trials",
    status_code=201,
)
def create_trial(
    request: CreateTrialRequest,
) -> dict[str, Any]:
    """Create a clinical trial through Kafka."""

    correlation_id = (
        request.correlation_id
        or str(uuid4())
    )

    return send_request(
        CREATE_OPERATION,
        request.data.model_dump(),
        correlation_id,
    )


@app.get("/hw8/trials/{entity_id}")
def get_trial(
    entity_id: str,
    correlation_id: str | None = Query(
        default=None,
    ),
) -> dict[str, Any]:
    """Retrieve one clinical trial through Kafka."""

    request_correlation_id = (
        correlation_id
        or str(uuid4())
    )

    return send_request(
        GET_OPERATION,
        {
            "entity_id": entity_id,
        },
        request_correlation_id,
    )
