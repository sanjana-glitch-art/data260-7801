from __future__ import annotations

import math
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from code.auth_api import CurrentUser
from code.database import get_db
from code.models import (
    ClinicalTrial,
    Sponsor,
)
from code.schemas import (
    ClinicalTrialResponse,
    TrialCreate,
    TrialListResponse,
    TrialUpdate,
)


router = APIRouter(
    prefix="/api/trials",
    tags=["clinical trials"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def find_trial(
    trial_id: int,
    database: Session,
) -> ClinicalTrial:
    """Return a clinical trial or raise HTTP 404."""

    trial = database.scalar(
        select(
            ClinicalTrial
        )
        .options(
            selectinload(
                ClinicalTrial.sponsor
            )
        )
        .where(
            ClinicalTrial.id
            == trial_id
        )
    )

    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical trial not found.",
        )

    return trial


def find_sponsor(
    sponsor_id: int,
    database: Session,
) -> Sponsor:
    """Return a sponsor or raise HTTP 404."""

    sponsor = database.get(
        Sponsor,
        sponsor_id,
    )

    if sponsor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sponsor not found.",
        )

    return sponsor


def normalized_trial_code(
    trial_code: str,
) -> str:
    """Normalize a validated trial code."""

    return trial_code.strip().upper()


def trial_code_is_used(
    database: Session,
    trial_code: str,
    excluded_trial_id: int | None = None,
) -> bool:
    """Return whether another trial uses a trial code."""

    statement = select(
        ClinicalTrial.id
    ).where(
        ClinicalTrial.trial_code
        == trial_code
    )

    if excluded_trial_id is not None:
        statement = statement.where(
            ClinicalTrial.id
            != excluded_trial_id
        )

    return (
        database.scalar(statement)
        is not None
    )


@router.post(
    "",
    response_model=ClinicalTrialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trial(
    trial_data: TrialCreate,
    user: CurrentUser,
    database: DatabaseSession,
) -> ClinicalTrial:
    """Create a clinical-trial record."""

    sponsor = find_sponsor(
        trial_data.sponsor_id,
        database,
    )

    trial_code = normalized_trial_code(
        trial_data.trial_code
    )

    if trial_code_is_used(
        database,
        trial_code,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A clinical trial with this "
                "trial code already exists."
            ),
        )

    trial = ClinicalTrial(
        trial_title=trial_data.trial_title,
        trial_code=trial_code,
        enrollment_target=(
            trial_data.enrollment_target
        ),
        sponsor_id=sponsor.id,
        sponsor_name=(
            sponsor.sponsor_name
        ),
        submitter_email=str(
            trial_data.submitter_email
        ).strip().casefold(),
        trial_description=(
            trial_data.trial_description
        ),
        trial_phase=(
            trial_data.trial_phase
        ),
        created_by_user_id=user.id,
    )

    database.add(
        trial
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The clinical trial could not be created "
                "because a unique or related value "
                "is invalid."
            ),
        ) from error

    database.refresh(
        trial
    )

    # Load the related sponsor for response serialization.
    trial = find_trial(
        trial.id,
        database,
    )

    return trial


@router.get(
    "",
    response_model=TrialListResponse,
)
def list_trials(
    user: CurrentUser,
    database: DatabaseSession,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    search: Annotated[
        str,
        Query(max_length=255),
    ] = "",
    sponsor_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
) -> TrialListResponse:
    """Return a paginated clinical-trial list."""

    del user

    filters = []

    cleaned_search = search.strip()

    if cleaned_search:
        pattern = (
            f"%{cleaned_search}%"
        )

        filters.append(
            or_(
                ClinicalTrial.trial_title.like(
                    pattern
                ),
                ClinicalTrial.trial_code.like(
                    pattern
                ),
                ClinicalTrial.sponsor_name.like(
                    pattern
                ),
            )
        )

    if sponsor_id is not None:
        find_sponsor(
            sponsor_id,
            database,
        )

        filters.append(
            ClinicalTrial.sponsor_id
            == sponsor_id
        )

    count_statement = select(
        func.count(
            ClinicalTrial.id
        )
    )

    statement = (
        select(
            ClinicalTrial
        )
        .options(
            selectinload(
                ClinicalTrial.sponsor
            )
        )
    )

    if filters:
        count_statement = (
            count_statement.where(
                *filters
            )
        )

        statement = statement.where(
            *filters
        )

    total = int(
        database.scalar(
            count_statement
        )
        or 0
    )

    offset = (
        page - 1
    ) * page_size

    trials = list(
        database.scalars(
            statement
            .order_by(
                ClinicalTrial.id
            )
            .offset(offset)
            .limit(page_size)
        ).all()
    )

    total_pages = (
        math.ceil(
            total / page_size
        )
        if total
        else 0
    )

    return TrialListResponse(
        items=trials,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{trial_id}",
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


@router.put(
    "/{trial_id}",
    response_model=ClinicalTrialResponse,
)
def update_trial(
    trial_id: int,
    trial_data: TrialUpdate,
    user: CurrentUser,
    database: DatabaseSession,
) -> ClinicalTrial:
    """Update an existing clinical trial."""

    del user

    trial = find_trial(
        trial_id,
        database,
    )

    sponsor = find_sponsor(
        trial_data.sponsor_id,
        database,
    )

    trial_code = normalized_trial_code(
        trial_data.trial_code
    )

    if trial_code_is_used(
        database,
        trial_code,
        excluded_trial_id=trial.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Another clinical trial already "
                "uses this trial code."
            ),
        )

    trial.trial_title = (
        trial_data.trial_title
    )

    trial.trial_code = trial_code

    trial.enrollment_target = (
        trial_data.enrollment_target
    )

    trial.sponsor_id = sponsor.id

    # Keep the legacy value synchronized.
    trial.sponsor_name = (
        sponsor.sponsor_name
    )

    trial.submitter_email = str(
        trial_data.submitter_email
    ).strip().casefold()

    trial.trial_description = (
        trial_data.trial_description
    )

    trial.trial_phase = (
        trial_data.trial_phase
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The clinical trial could not be updated "
                "because a unique or related value "
                "is invalid."
            ),
        ) from error

    database.refresh(
        trial
    )

    return find_trial(
        trial.id,
        database,
    )


@router.delete(
    "/{trial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_trial(
    trial_id: int,
    user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    """Delete an existing clinical trial."""

    del user

    trial = find_trial(
        trial_id,
        database,
    )

    database.delete(
        trial
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The clinical trial could not be deleted "
                "because another record references it."
            ),
        ) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )