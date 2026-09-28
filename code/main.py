from __future__ import annotations
from code.performance_api import router as performance_router
from typing import Annotated

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from code.auth_api import (
    CurrentUser,
    router as auth_router,
)
from code.database import get_db
from code.models import ClinicalTrial, User
from code.schemas import (
    ClinicalTrialResponse,
    TrialCreate,
    TrialUpdate,
)


PORT_BASE = 8601


app = FastAPI(
    title="Clinical Trial Listing API",
    description=(
        "DATA-260 clinical-trial application with "
        "React, FastAPI, MySQL, and server-side sessions."
    ),
    version="4.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=["*"],
)


app.include_router(
    auth_router
)

app.include_router(
    performance_router
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def required_string(
    value: str,
    field_name: str,
) -> str:
    """Strip a required string or raise HTTP 400."""

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )

    return cleaned


def find_trial(
    trial_id: int,
    database: Session,
) -> ClinicalTrial:
    """Return a trial by ID or raise HTTP 404."""

    trial = database.get(
        ClinicalTrial,
        trial_id,
    )

    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical trial not found.",
        )

    return trial


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic API information."""

    return {
        "application": "Clinical Trial Listing API",
        "student": "Sanjana Thummalapalli",
        "sid4": "7801",
        "documentation": "/docs",
        "frontend": "http://127.0.0.1:5173",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple application health response."""

    return {
        "status": "ok",
    }


@app.get(
    "/api/trials",
    response_model=list[ClinicalTrialResponse],
)
def get_trials(
    user: CurrentUser,
    database: DatabaseSession,
    search: Annotated[
        str,
        Query(max_length=255),
    ] = "",
) -> list[ClinicalTrial]:
    """Return all trials or matching title/sponsor records."""

    del user

    statement = select(
        ClinicalTrial
    ).order_by(
        ClinicalTrial.id
    )

    cleaned_search = search.strip()

    if cleaned_search:
        search_pattern = (
            f"%{cleaned_search}%"
        )

        statement = statement.where(
            or_(
                ClinicalTrial.trial_title.like(
                    search_pattern
                ),
                ClinicalTrial.sponsor_name.like(
                    search_pattern
                ),
            )
        )

    return list(
        database.scalars(
            statement
        ).all()
    )


@app.get(
    "/api/trials/{trial_id}",
    response_model=ClinicalTrialResponse,
)
def get_trial(
    trial_id: int,
    user: CurrentUser,
    database: DatabaseSession,
) -> ClinicalTrial:
    """Return one clinical trial."""

    del user

    return find_trial(
        trial_id,
        database,
    )


@app.post(
    "/api/trials",
    response_model=ClinicalTrialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trial(
    trial_data: TrialCreate,
    user: CurrentUser,
    database: DatabaseSession,
) -> ClinicalTrial:
    """Create a clinical-trial record."""

    new_trial = ClinicalTrial(
        trial_title=required_string(
            trial_data.trial_title,
            "Trial title",
        ),
        sponsor_name=required_string(
            trial_data.sponsor_name,
            "Sponsor name",
        ),
        submitter_email=(
            trial_data.submitter_email.strip()
        ),
        trial_description=(
            trial_data.trial_description.strip()
        ),
        trial_phase=(
            trial_data.trial_phase.strip()
            or "Phase I"
        ),
        created_by_user_id=user.id,
    )

    database.add(
        new_trial
    )

    database.commit()

    database.refresh(
        new_trial
    )

    return new_trial


@app.put(
    "/api/trials/{trial_id}",
    response_model=ClinicalTrialResponse,
)
def update_trial(
    trial_id: int,
    trial_data: TrialUpdate,
    user: CurrentUser,
    database: DatabaseSession,
) -> ClinicalTrial:
    """Update an existing clinical-trial record."""

    del user

    trial = find_trial(
        trial_id,
        database,
    )

    trial.trial_title = required_string(
        trial_data.trial_title,
        "Trial title",
    )

    trial.sponsor_name = required_string(
        trial_data.sponsor_name,
        "Sponsor name",
    )

    trial.submitter_email = (
        trial_data.submitter_email.strip()
    )

    trial.trial_description = (
        trial_data.trial_description.strip()
    )

    trial.trial_phase = (
        trial_data.trial_phase.strip()
        or "Phase I"
    )

    database.commit()

    database.refresh(
        trial
    )

    return trial


@app.delete(
    "/api/trials/{trial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_trial(
    trial_id: int,
    user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    """Delete an existing clinical-trial record."""

    del user

    trial = find_trial(
        trial_id,
        database,
    )

    database.delete(
        trial
    )

    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


if __name__ == "__main__":
    uvicorn.run(
        "code.main:app",
        host="127.0.0.1",
        port=PORT_BASE,
        reload=True,
    )