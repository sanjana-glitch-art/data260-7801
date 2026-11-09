from __future__ import annotations

import os

SID4 = 7801
PREFIX = "s7801"

REDIS_URL = os.getenv(
    "HW9_REDIS_URL",
    "redis://localhost:6379/0",
)

VIEW_SYNC_INTERVAL = 10

SEMANTIC_CACHE_INDEX = (
    f"{PREFIX}:semantic_cache:index"
)

SEMANTIC_CACHE_PREFIX = (
    f"{PREFIX}:semantic_cache:"
)

EMBEDDING_MODEL = (
    "all-MiniLM-L6-v2"
)

EMBEDDING_DIMENSIONS = 384

DEFAULT_SIMILARITY_THRESHOLD = 0.85
