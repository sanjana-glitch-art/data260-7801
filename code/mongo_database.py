from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

load_dotenv(
    PROJECT_ROOT / ".env.hw6"
)


MONGODB_URL = os.getenv(
    "MONGODB_URL",
    (
        "mongodb://s7801_app:"
        "s7801_mongo_7801"
        "@127.0.0.1:27017/"
        "?authSource=admin"
    ),
)

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "s7801_doc",
)


mongo_client: MongoClient[
    dict[str, Any]
] = MongoClient(
    MONGODB_URL,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    tz_aware=True,
)

mongo_database: Database[
    dict[str, Any]
] = mongo_client[
    MONGODB_DATABASE
]


def ping_mongodb() -> bool:
    """Return True when MongoDB responds to a ping."""

    result = mongo_client.admin.command(
        "ping"
    )

    return bool(
        result.get("ok")
    )


def get_mongo_database() -> Generator[
    Database[dict[str, Any]],
    None,
    None,
]:
    """Provide the shared MongoDB database."""

    yield mongo_database


def trial_documents_collection() -> Collection[
    dict[str, Any]
]:
    """Return the clinical-trial document collection."""

    return mongo_database[
        "trial_documents"
    ]


def messages_collection() -> Collection[
    dict[str, Any]
]:
    """Return the memory-message collection."""

    return mongo_database[
        "messages"
    ]


def summaries_collection() -> Collection[
    dict[str, Any]
]:
    """Return the long-term summary collection."""

    return mongo_database[
        "summaries"
    ]


def episodes_collection() -> Collection[
    dict[str, Any]
]:
    """Return the episodic-memory collection."""

    return mongo_database[
        "episodes"
    ]