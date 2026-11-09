from __future__ import annotations

import os

SID4 = 7801
PORT_BASE = 8601
PREFIX = "s7801"
SEED = 7801
VERIFY_SEED = 267801
DOMAIN_ID = 1

CREATE_OPERATION = "CREATE_CLINICAL_TRIAL"
GET_OPERATION = "GET_CLINICAL_TRIAL"

REQUEST_TOPIC = os.getenv(
    "HW8_REQUEST_TOPIC",
    f"{PREFIX}_entity_requests",
)

RESPONSE_TOPIC = os.getenv(
    "HW8_RESPONSE_TOPIC",
    f"{PREFIX}_entity_responses",
)

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

WORKER_GROUP = os.getenv(
    "HW8_WORKER_GROUP",
    f"{PREFIX}_entity_worker_group",
)

API_TIMEOUT_SECONDS = float(
    os.getenv(
        "HW8_API_TIMEOUT_SECONDS",
        "15",
    )
)

REQUIRED_TRIAL_FIELDS = (
    "trial_title",
    "trial_description",
    "trial_phase",
    "sponsor_name",
    "enrollment_target",
)

ALLOWED_PHASES = {
    "Phase I",
    "Phase II",
    "Phase III",
    "Phase IV",
}

INBOX_TOPIC = f"{PREFIX}_inbox"
TASKS_TOPIC = f"{PREFIX}_tasks"
DRAFTS_TOPIC = f"{PREFIX}_drafts"
FINAL_TOPIC = f"{PREFIX}_final"
DEAD_LETTER_TOPIC = f"{PREFIX}_dead_letter"

PLANNER_GROUP = f"{PREFIX}_planner_group"
WRITER_GROUP = f"{PREFIX}_writer_group"
REVIEWER_GROUP = f"{PREFIX}_reviewer_group"
