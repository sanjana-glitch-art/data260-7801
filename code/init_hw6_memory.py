from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING

from code.mongo_database import (
    MONGODB_DATABASE,
    mongo_database,
    ping_mongodb,
)


MESSAGE_VALIDATOR: dict[
    str,
    Any,
] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Conversation Message",
        "required": [
            "user_id",
            "session_id",
            "role",
            "content",
            "created_at",
        ],
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "user_id": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "session_id": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "role": {
                "bsonType": "string",
                "enum": [
                    "user",
                    "assistant",
                ],
            },
            "content": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 10000,
            },
            "created_at": {
                "bsonType": "date",
            },
        },
    },
}


SUMMARY_VALIDATOR: dict[
    str,
    Any,
] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Conversation Summary",
        "required": [
            "user_id",
            "session_id",
            "scope",
            "text",
            "created_at",
        ],
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "user_id": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "session_id": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "scope": {
                "bsonType": "string",
                "enum": [
                    "session",
                    "user",
                ],
            },
            "text": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 10000,
            },
            "created_at": {
                "bsonType": "date",
            },
        },
    },
}


EPISODE_VALIDATOR: dict[
    str,
    Any,
] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Episodic Memory Fact",
        "required": [
            "user_id",
            "session_id",
            "fact",
            "importance",
            "embedding",
            "created_at",
        ],
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "user_id": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "session_id": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "fact": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 500,
            },
            "importance": {
                "bsonType": [
                    "double",
                    "int",
                    "long",
                    "decimal",
                ],
                "minimum": 0,
                "maximum": 1,
            },
            "embedding": {
                "bsonType": "array",
                "minItems": 1,
                "items": {
                    "bsonType": "double",
                },
            },
            "created_at": {
                "bsonType": "date",
            },
        },
    },
}


def create_or_update_collection(
    name: str,
    validator: dict[str, Any],
) -> None:
    """Create a collection or update its validator."""

    existing = (
        mongo_database.list_collection_names()
    )

    if name in existing:
        mongo_database.command({
            "collMod": name,
            "validator": validator,
            "validationLevel": "strict",
            "validationAction": "error",
        })

        print(
            f"Updated validator: {name}"
        )
    else:
        mongo_database.create_collection(
            name,
            validator=validator,
            validationLevel="strict",
            validationAction="error",
        )

        print(
            f"Created collection: {name}"
        )


def create_message_indexes() -> None:
    """Create indexes for short-term message retrieval."""

    collection = mongo_database[
        "messages"
    ]

    collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "session_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=(
            "idx_messages_user_"
            "session_created"
        ),
    )

    collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=(
            "idx_messages_user_created"
        ),
    )


def create_summary_indexes() -> None:
    """Create indexes for summary retrieval."""

    collection = mongo_database[
        "summaries"
    ]

    collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "session_id",
                ASCENDING,
            ),
            (
                "scope",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=(
            "idx_summaries_user_"
            "session_scope_created"
        ),
    )


def create_episode_indexes() -> None:
    """Create indexes for episodic-memory retrieval."""

    collection = mongo_database[
        "episodes"
    ]

    collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=(
            "idx_episodes_user_created"
        ),
    )

    collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "session_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=(
            "idx_episodes_user_"
            "session_created"
        ),
    )


def main() -> None:
    """Initialize the Homework 6 memory collections."""

    print(
        "DATA-260 Homework 6 "
        "Memory Initialization"
    )

    print(
        f"Database: {MONGODB_DATABASE}"
    )

    if not ping_mongodb():
        raise RuntimeError(
            "MongoDB ping failed."
        )

    print(
        "MongoDB ping: PASS"
    )

    create_or_update_collection(
        "messages",
        MESSAGE_VALIDATOR,
    )

    create_or_update_collection(
        "summaries",
        SUMMARY_VALIDATOR,
    )

    create_or_update_collection(
        "episodes",
        EPISODE_VALIDATOR,
    )

    create_message_indexes()
    create_summary_indexes()
    create_episode_indexes()

    print(
        "Created or verified memory indexes."
    )

    print(
        "Collections:",
        sorted(
            mongo_database.list_collection_names()
        ),
    )

    print(
        "Memory initialization complete."
    )


if __name__ == "__main__":
    main()