from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING

from code.mongo_database import (
    MONGODB_DATABASE,
    mongo_database,
    ping_mongodb,
)


TRIAL_DOCUMENT_VALIDATOR: dict[
    str,
    Any,
] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": (
            "Clinical Trial Document"
        ),
        "required": [
            "trial_title",
            "trial_phase",
            "recruitment_status",
            "start_date",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "trial_title": {
                "bsonType": "string",
                "description": (
                    "Required clinical-trial "
                    "title."
                ),
                "minLength": 1,
                "maxLength": 100,
            },
            "description": {
                "bsonType": [
                    "string",
                    "null",
                ],
                "description": (
                    "Optional trial "
                    "description."
                ),
                "maxLength": 2000,
            },
            "trial_phase": {
                "bsonType": "string",
                "enum": [
                    "Phase I",
                    "Phase II",
                    "Phase III",
                    "Phase IV",
                ],
            },
            "recruitment_status": {
                "bsonType": "string",
                "enum": [
                    "Planning",
                    "Recruiting",
                    "Active",
                    "Completed",
                    "Suspended",
                ],
            },
            "start_date": {
                "bsonType": "date",
            },
            "created_at": {
                "bsonType": "date",
            },
            "updated_at": {
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

    collection_names = (
        mongo_database.list_collection_names()
    )

    if name in collection_names:
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


def create_indexes() -> None:
    """Create useful indexes for Part 1."""

    collection = mongo_database[
        "trial_documents"
    ]

    collection.create_index(
        [
            (
                "trial_title",
                ASCENDING,
            )
        ],
        name=(
            "idx_trial_documents_title"
        ),
    )

    collection.create_index(
        [
            (
                "trial_phase",
                ASCENDING,
            ),
            (
                "recruitment_status",
                ASCENDING,
            ),
        ],
        name=(
            "idx_trial_documents_"
            "phase_status"
        ),
    )

    collection.create_index(
        [
            (
                "start_date",
                DESCENDING,
            )
        ],
        name=(
            "idx_trial_documents_"
            "start_date"
        ),
    )

    print(
        "Created or verified indexes."
    )


def main() -> None:
    """Initialize the Homework 6 MongoDB database."""

    print(
        "DATA-260 Homework 6 "
        "MongoDB Initialization"
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
        "trial_documents",
        TRIAL_DOCUMENT_VALIDATOR,
    )

    create_indexes()

    print(
        "MongoDB initialization complete."
    )

    print(
        "Collections:",
        mongo_database.list_collection_names(),
    )


if __name__ == "__main__":
    main()