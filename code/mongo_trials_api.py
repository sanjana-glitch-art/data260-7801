from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status,
)
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from code.mongo_database import (
    trial_documents_collection,
)
from code.mongo_schemas import (
    RecruitmentStatus,
    TrialDocumentCreate,
    TrialDocumentResponse,
    TrialDocumentUpdate,
    TrialPhase,
    serialize_trial_document,
)


router = APIRouter(
    prefix="/api/document-trials",
    tags=[
        "MongoDB Clinical Trials",
    ],
)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def parse_object_id(
    document_id: str,
) -> ObjectId:
    """Convert a URL ID into a MongoDB ObjectId."""

    try:
        return ObjectId(
            document_id
        )
    except (
        InvalidId,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "The supplied document ID "
                "is not valid."
            ),
        ) from error


def normalized_create_document(
    trial: TrialDocumentCreate,
) -> dict[str, Any]:
    """Convert a validated create model into MongoDB data."""

    now = utc_now()

    return {
        "trial_title": trial.trial_title,
        "description": trial.description,
        "trial_phase": (
            trial.trial_phase.value
        ),
        "recruitment_status": (
            trial.recruitment_status.value
        ),
        "start_date": trial.start_date,
        "created_at": now,
        "updated_at": now,
    }


def normalized_update_document(
    trial: TrialDocumentUpdate,
) -> dict[str, Any]:
    """Convert supplied update fields into MongoDB data."""

    values = trial.model_dump(
        exclude_unset=True,
        mode="python",
    )

    if isinstance(
        values.get("trial_phase"),
        TrialPhase,
    ):
        values[
            "trial_phase"
        ] = values[
            "trial_phase"
        ].value

    if isinstance(
        values.get(
            "recruitment_status"
        ),
        RecruitmentStatus,
    ):
        values[
            "recruitment_status"
        ] = values[
            "recruitment_status"
        ].value

    values["updated_at"] = utc_now()

    return values


def response_from_document(
    document: dict[str, Any],
) -> TrialDocumentResponse:
    """Create an API response from a MongoDB document."""

    return TrialDocumentResponse.model_validate(
        serialize_trial_document(
            document
        )
    )


@router.post(
    "",
    response_model=TrialDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document_trial(
    trial: TrialDocumentCreate,
) -> TrialDocumentResponse:
    """Create one clinical-trial document."""

    collection = (
        trial_documents_collection()
    )

    document = normalized_create_document(
        trial
    )

    try:
        result = collection.insert_one(
            document
        )

        created = collection.find_one({
            "_id": result.inserted_id
        })
    except PyMongoError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "MongoDB could not create "
                "the clinical-trial document."
            ),
        ) from error

    if created is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "The document was inserted but "
                "could not be retrieved."
            ),
        )

    return response_from_document(
        created
    )


@router.get(
    "",
    response_model=list[
        TrialDocumentResponse
    ],
)
def get_document_trials(
    search: Annotated[
        str,
        Query(
            max_length=100
        ),
    ] = "",
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 100,
) -> list[TrialDocumentResponse]:
    """Return all or matching trial documents."""

    collection = (
        trial_documents_collection()
    )

    mongo_filter: dict[
        str,
        Any,
    ] = {}

    cleaned_search = search.strip()

    if cleaned_search:
        mongo_filter = {
            "$or": [
                {
                    "trial_title": {
                        "$regex": (
                            cleaned_search
                        ),
                        "$options": "i",
                    }
                },
                {
                    "description": {
                        "$regex": (
                            cleaned_search
                        ),
                        "$options": "i",
                    }
                },
            ]
        }

    try:
        cursor = (
            collection.find(
                mongo_filter
            )
            .sort(
                "trial_title",
                ASCENDING,
            )
            .limit(
                limit
            )
        )

        documents = list(
            cursor
        )
    except PyMongoError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "MongoDB could not retrieve "
                "the clinical-trial documents."
            ),
        ) from error

    return [
        response_from_document(
            document
        )
        for document in documents
    ]


@router.get(
    "/{document_id}",
    response_model=TrialDocumentResponse,
)
def get_document_trial(
    document_id: str,
) -> TrialDocumentResponse:
    """Return one clinical-trial document."""

    object_id = parse_object_id(
        document_id
    )

    collection = (
        trial_documents_collection()
    )

    try:
        document = collection.find_one({
            "_id": object_id
        })
    except PyMongoError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "MongoDB could not retrieve "
                "the clinical-trial document."
            ),
        ) from error

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Clinical-trial document "
                "not found."
            ),
        )

    return response_from_document(
        document
    )


@router.put(
    "/{document_id}",
    response_model=TrialDocumentResponse,
)
def update_document_trial(
    document_id: str,
    trial: TrialDocumentUpdate,
) -> TrialDocumentResponse:
    """Update one clinical-trial document."""

    object_id = parse_object_id(
        document_id
    )

    collection = (
        trial_documents_collection()
    )

    update_values = (
        normalized_update_document(
            trial
        )
    )

    try:
        result = collection.update_one(
            {
                "_id": object_id
            },
            {
                "$set": update_values
            },
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Clinical-trial document "
                    "not found."
                ),
            )

        updated = collection.find_one({
            "_id": object_id
        })
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "MongoDB could not update "
                "the clinical-trial document."
            ),
        ) from error

    if updated is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "The document was updated but "
                "could not be retrieved."
            ),
        )

    return response_from_document(
        updated
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_trial(
    document_id: str,
) -> Response:
    """Delete one clinical-trial document."""

    object_id = parse_object_id(
        document_id
    )

    collection = (
        trial_documents_collection()
    )

    try:
        result = collection.delete_one({
            "_id": object_id
        })
    except PyMongoError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "MongoDB could not delete "
                "the clinical-trial document."
            ),
        ) from error

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "Clinical-trial document "
                "not found."
            ),
        )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )