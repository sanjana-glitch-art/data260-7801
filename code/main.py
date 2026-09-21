from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.sessions import SessionMiddleware

from code.auth import router as auth_router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIRECTORY = PROJECT_ROOT / "code" / "web_application"

PORT_BASE = 8601
PREFIX = "s7801"

SESSION_SECRET = os.getenv(
    "SESSION_SECRET",
    "s7801-hw3-local-secret-change-me"
)

SESSION_IDLE_SECONDS = int(
    os.getenv(
        "SESSION_IDLE_SECONDS",
        "120"
    )
)


class ClinicalTrial(BaseModel):
    """A clinical-trial listing stored by the application."""

    model_config = ConfigDict(
        validate_assignment=True
    )

    id: int
    trial_title: str
    sponsor_name: str
    submitter_email: str = ""
    trial_description: str = ""
    trial_phase: str = "Phase I"


class TrialCreate(BaseModel):
    """Values accepted when creating a trial."""

    trial_title: str = Field(min_length=1)
    sponsor_name: str = Field(min_length=1)
    submitter_email: str = ""
    trial_description: str = ""
    trial_phase: str = "Phase I"


class TrialUpdate(BaseModel):
    """Values accepted when updating a trial."""

    trial_title: str = Field(min_length=1)
    sponsor_name: str = Field(min_length=1)


app = FastAPI(
    title="Clinical Trial Listing API",
    version="3.0.0"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie=f"{PREFIX}_session",
    max_age=SESSION_IDLE_SECONDS,
    same_site="lax",
    https_only=True,
    path="/"
)

app.include_router(auth_router)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIRECTORY),
    name="static"
)


trials: list[ClinicalTrial] = [
    ClinicalTrial(
        id=1,
        trial_title=(
            "Sleep Quality and Academic Performance Study"
        ),
        sponsor_name="San Jose State University",
        submitter_email="research@example.edu",
        trial_description=(
            "This clinical trial examines how sleep quality "
            "affects university students."
        ),
        trial_phase="Phase II"
    ),
    ClinicalTrial(
        id=2,
        trial_title="Digital Wellness Intervention Study",
        sponsor_name=(
            "California Student Health Research Center"
        ),
        submitter_email="wellness@example.edu",
        trial_description=(
            "This study evaluates a digital wellness "
            "intervention for college students."
        ),
        trial_phase="Phase I"
    )
]


def cleaned_required_value(
    value: str,
    field_name: str
) -> str:
    """Strip a required string or raise an HTTP 400 error."""

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required."
        )

    return cleaned


def find_trial(trial_id: int) -> ClinicalTrial:
    """Return a trial by ID or raise an HTTP 404 error."""

    trial = next(
        (
            current_trial
            for current_trial in trials
            if current_trial.id == trial_id
        ),
        None
    )

    if trial is None:
        raise HTTPException(
            status_code=404,
            detail="Clinical trial not found."
        )

    return trial


def matching_trials(
    search: str = ""
) -> list[ClinicalTrial]:
    """Return trials matching a title or sponsor."""

    query = search.strip().casefold()

    if not query:
        return list(trials)

    return [
        trial
        for trial in trials
        if (
            query in trial.trial_title.casefold()
            or query in trial.sponsor_name.casefold()
        )
    ]


@app.get("/trials")
async def read_trials_page() -> FileResponse:
    """Serve the clinical-trial web application."""

    return FileResponse(
        STATIC_DIRECTORY / "index.html"
    )


@app.get(
    "/api/trials",
    response_model=list[ClinicalTrial]
)
async def get_trials(
    response: Response,
    search: Annotated[str, Query()] = ""
) -> list[ClinicalTrial]:
    """Return all trials or title/sponsor matches."""

    response.headers["Cache-Control"] = (
        "no-cache, no-store, must-revalidate"
    )

    return matching_trials(search)


@app.get(
    "/api/trials/{trial_id}",
    response_model=ClinicalTrial
)
async def get_trial(
    trial_id: int
) -> ClinicalTrial:
    """Return one clinical trial."""

    return find_trial(trial_id)


@app.post(
    "/api/trials",
    response_model=ClinicalTrial,
    status_code=201
)
async def create_trial_api(
    trial_data: TrialCreate
) -> ClinicalTrial:
    """Create a clinical trial through the JSON API."""

    trial_title = cleaned_required_value(
        trial_data.trial_title,
        "Trial title"
    )

    sponsor_name = cleaned_required_value(
        trial_data.sponsor_name,
        "Sponsor name"
    )

    new_id = max(
        (trial.id for trial in trials),
        default=0
    ) + 1

    new_trial = ClinicalTrial(
        id=new_id,
        trial_title=trial_title,
        sponsor_name=sponsor_name,
        submitter_email=(
            trial_data.submitter_email.strip()
        ),
        trial_description=(
            trial_data.trial_description.strip()
        ),
        trial_phase=(
            trial_data.trial_phase.strip()
            or "Phase I"
        )
    )

    trials.append(new_trial)

    return new_trial


@app.put(
    "/api/trials/{trial_id}",
    response_model=ClinicalTrial
)
async def update_trial_api(
    trial_id: int,
    trial_data: TrialUpdate
) -> ClinicalTrial:
    """Update a trial through the JSON API."""

    trial = find_trial(trial_id)

    trial.trial_title = cleaned_required_value(
        trial_data.trial_title,
        "Trial title"
    )

    trial.sponsor_name = cleaned_required_value(
        trial_data.sponsor_name,
        "Sponsor name"
    )

    return trial


@app.delete(
    "/api/trials/{trial_id}",
    status_code=204
)
async def delete_trial_api(
    trial_id: int
) -> Response:
    """Delete a clinical trial through the JSON API."""

    trial = find_trial(trial_id)
    trials.remove(trial)

    return Response(status_code=204)


@app.post("/trials")
async def create_trial_form(
    trial_title: Annotated[str, Form()],
    sponsor_name: Annotated[str, Form()],
    submitter_email: Annotated[str, Form()],
    trial_description: Annotated[str, Form()],
    trial_phase: Annotated[str, Form()]
) -> RedirectResponse:
    """Create a trial from the HTML form."""

    await create_trial_api(
        TrialCreate(
            trial_title=trial_title,
            sponsor_name=sponsor_name,
            submitter_email=submitter_email,
            trial_description=trial_description,
            trial_phase=trial_phase
        )
    )

    return RedirectResponse(
        url="/trials",
        status_code=303
    )


@app.post("/trials/1/update")
async def update_trial_one_form(
    trial_title: Annotated[str, Form()],
    sponsor_name: Annotated[str, Form()]
) -> RedirectResponse:
    """Update trial ID 1 from the HTML form."""

    await update_trial_api(
        1,
        TrialUpdate(
            trial_title=trial_title,
            sponsor_name=sponsor_name
        )
    )

    return RedirectResponse(
        url="/trials",
        status_code=303
    )


@app.post("/trials/delete-highest")
async def delete_highest_trial_form() -> RedirectResponse:
    """Delete the trial with the highest ID."""

    if not trials:
        raise HTTPException(
            status_code=404,
            detail=(
                "There are no clinical trials to delete."
            )
        )

    highest_id = max(
        trial.id
        for trial in trials
    )

    await delete_trial_api(highest_id)

    return RedirectResponse(
        url="/trials",
        status_code=303
    )


if __name__ == "__main__":
    uvicorn.run(
        "code.main:app",
        host="0.0.0.0",
        port=PORT_BASE,
        reload=True
    )