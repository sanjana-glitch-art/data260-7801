from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Student and assignment configuration
# ---------------------------------------------------------------------------

STUDENT_NAME = "Sanjana Thummalapalli"
SID4 = 7801
PREFIX = "s7801"
SEED = 7801
VERIFY_SEED = 267801
DOMAIN_ID = 1
DOMAIN_NAME = "Clinical Trials"

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

REPORT_DIR = ROOT_DIR / "reports" / "hw10"
RAW_DIR = REPORT_DIR / "raw"
SCREENSHOT_DIR = REPORT_DIR / "screenshots"

EVAL_CASES_PATH = ROOT_DIR / "eval_cases.json"
HUMAN_LABELS_PATH = ROOT_DIR / "human_labels.csv"

TRACE_PATH = RAW_DIR / "traces.jsonl"
PIPELINE_EVALUATION_PATH = (
    RAW_DIR / "pipeline_evaluation.json"
)
PIPELINE_EVALUATION_CSV_PATH = (
    RAW_DIR / "pipeline_evaluation.csv"
)

JUDGE_VALIDATION_PATH = (
    RAW_DIR / "judge_validation_results.json"
)
JUDGE_VALIDATION_SCORES_PATH = (
    RAW_DIR / "judge_validation_scores.csv"
)
JUDGE_REPEATABILITY_PATH = (
    RAW_DIR / "judge_repeatability.csv"
)

REQUIRED_TRACES_PATH = (
    RAW_DIR / "required_trace_examples.json"
)

LATENCY_RESULTS_PATH = (
    RAW_DIR / "latency_experiment.json"
)
LATENCY_SPANS_PATH = (
    RAW_DIR / "latency_spans.csv"
)
LATENCY_SUMMARY_PATH = (
    RAW_DIR / "latency_summary.csv"
)

VERIFICATION_PATH = REPORT_DIR / "verification.json"
RUN_LOG_PATH = REPORT_DIR / "RUN_LOG.txt"

# ---------------------------------------------------------------------------
# Redis and semantic-cache configuration
# ---------------------------------------------------------------------------

REDIS_HOST = os.getenv(
    "HW10_REDIS_HOST",
    os.getenv("REDIS_HOST", "localhost"),
)
REDIS_PORT = int(
    os.getenv(
        "HW10_REDIS_PORT",
        os.getenv("REDIS_PORT", "6379"),
    )
)
REDIS_DB = int(
    os.getenv(
        "HW10_REDIS_DB",
        os.getenv("REDIS_DB", "0"),
    )
)

SEMANTIC_CACHE_PREFIX = (
    f"{PREFIX}:semantic_cache:"
)
SEMANTIC_CACHE_INDEX = (
    f"{PREFIX}:semantic_cache:index"
)
SEMANTIC_CACHE_THRESHOLD = float(
    os.getenv(
        "HW10_CACHE_THRESHOLD",
        "0.90",
    )
)
EMBEDDING_DIMENSIONS = 384

# ---------------------------------------------------------------------------
# Kafka pipeline configuration
# ---------------------------------------------------------------------------

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

INBOX_TOPIC = f"{PREFIX}_inbox"
TASKS_TOPIC = f"{PREFIX}_tasks"
DRAFTS_TOPIC = f"{PREFIX}_drafts"
FINAL_TOPIC = f"{PREFIX}_final"
DEAD_LETTER_TOPIC = f"{PREFIX}_dead_letter"

PIPELINE_STAGES = (
    "cache_lookup",
    "planner",
    "writer",
    "reviewer",
    "evaluation",
)

# ---------------------------------------------------------------------------
# Local judge configuration
# ---------------------------------------------------------------------------

JUDGE_PROVIDER = "ollama"
JUDGE_MODEL = os.getenv(
    "HW10_JUDGE_MODEL",
    "qwen3:4b",
)
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_ATTEMPTS = 2
JUDGE_TIMEOUT_SECONDS = float(
    os.getenv(
        "HW10_JUDGE_TIMEOUT_SECONDS",
        "45",
    )
)
JUDGE_SCORE_MINIMUM = 1
JUDGE_SCORE_MAXIMUM = 5
JUDGE_REPEAT_COUNT = 3

# ---------------------------------------------------------------------------
# Evaluation and experiment configuration
# ---------------------------------------------------------------------------

EXPECTED_EVALUATION_CASE_COUNT = 20
EXPECTED_HUMAN_LABEL_COUNT = 20
LATENCY_EXPERIMENT_REQUEST_COUNT = 50

TRACE_STATUS_SUCCESS = "success"
TRACE_STATUS_FAILED = "failed"

CACHE_HIT = "hit"
CACHE_MISS = "miss"
CACHE_ERROR = "error"

DEFAULT_RECENT_WINDOW_MINUTES = 60

EVALUATION_CRITERIA = (
    "plan_quality",
    "writer_helpfulness",
    "final_answer_helpfulness",
    "final_vs_draft_improvement",
)


def ensure_hw10_directories() -> None:
    """Create all Homework 10 output directories."""

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    SCREENSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


ensure_hw10_directories()