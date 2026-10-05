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
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from code.auth_api import CurrentUser
from code.database import get_db
from code.models import ClinicalTrial, Sponsor
from code.schemas import (
    SponsorCreate,
    SponsorListResponse,
    SponsorResponse,
    SponsorUpdate,
    TrialListResponse,
)


router = APIRouter(
    prefix="/api/sponsors",
    tags=["sponsors"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


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


def normalized_email(
    email: object,
) -> str:
    """Normalize a validated email address."""

    return str(
        email
    ).strip().casefold()


def email_is_used(
    database: Session,
    email: str,
    excluded_sponsor_id: int | None = None,
) -> bool:
    """Return whether another sponsor uses an email."""

    statement = select(
        Sponsor.id
    ).where(
        Sponsor.contact_email == email
    )

    if excluded_sponsor_id is not None:
        statement = statement.where(
            Sponsor.id != excluded_sponsor_id
        )

    return (
        database.scalar(statement)
        is not None
    )


@router.post(
    "",
    response_model=SponsorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sponsor(
    sponsor_data: SponsorCreate,
    user: CurrentUser,
    database: DatabaseSession,
) -> Sponsor:
    """Create a sponsor."""

    del user

    email = normalized_email(
        sponsor_data.contact_email
    )

    if email_is_used(
        database,
        email,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A sponsor with this contact email "
                "already exists."
            ),
        )

    sponsor = Sponsor(
        sponsor_name=(
            sponsor_data.sponsor_name
        ),
        headquarters=(
            sponsor_data.headquarters
        ),
        contact_email=email,
    )

    database.add(
        sponsor
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The sponsor could not be created "
                "because a unique value is already used."
            ),
        ) from error

    database.refresh(
        sponsor
    )

    return sponsor


@router.get(
    "",
    response_model=SponsorListResponse,
)
def list_sponsors(
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
) -> SponsorListResponse:
    """Return a paginated sponsor list."""

    del user

    cleaned_search = search.strip()

    filters = []

    if cleaned_search:
        pattern = (
            f"%{cleaned_search}%"
        )

        filters.append(
            Sponsor.sponsor_name.like(
                pattern
            )
        )

    count_statement = select(
        func.count(
            Sponsor.id
        )
    )

    statement = select(
        Sponsor
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

    sponsors = list(
        database.scalars(
            statement
            .order_by(
                Sponsor.id
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

    return SponsorListResponse(
        items=[
            SponsorResponse.model_validate(
                sponsor
            )
            for sponsor in sponsors
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{sponsor_id}",
    response_model=SponsorResponse,
)
def get_sponsor(
    sponsor_id: int,
    user: CurrentUser,
    database: DatabaseSession,
) -> Sponsor:
    """Return one sponsor."""

    del user

    return find_sponsor(
        sponsor_id,
        database,
    )


@router.put(
    "/{sponsor_id}",
    response_model=SponsorResponse,
)
def update_sponsor(
    sponsor_id: int,
    sponsor_data: SponsorUpdate,
    user: CurrentUser,
    database: DatabaseSession,
) -> Sponsor:
    """Update a sponsor."""

    del user

    sponsor = find_sponsor(
        sponsor_id,
        database,
    )

    email = normalized_email(
        sponsor_data.contact_email
    )

    if email_is_used(
        database,
        email,
        excluded_sponsor_id=sponsor_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Another sponsor already uses "
                "this contact email."
            ),
        )

    sponsor.sponsor_name = (
        sponsor_data.sponsor_name
    )

    sponsor.headquarters = (
        sponsor_data.headquarters
    )

    sponsor.contact_email = email

    # Keep the legacy sponsor_name column synchronized
    # for the existing React application.
    database.execute(
        update(
            ClinicalTrial
        )
        .where(
            ClinicalTrial.sponsor_id
            == sponsor.id
        )
        .values(
            sponsor_name=(
                sponsor_data.sponsor_name
            )
        )
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The sponsor could not be updated "
                "because a unique value is already used."
            ),
        ) from error

    database.refresh(
        sponsor
    )

    return sponsor


@router.delete(
    "/{sponsor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_sponsor(
    sponsor_id: int,
    user: CurrentUser,
    database: DatabaseSession,
) -> Response:
    """Delete a sponsor only when it has no trials."""

    del user

    sponsor = find_sponsor(
        sponsor_id,
        database,
    )

    associated_trial_count = int(
        database.scalar(
            select(
                func.count(
                    ClinicalTrial.id
                )
            ).where(
                ClinicalTrial.sponsor_id
                == sponsor.id
            )
        )
        or 0
    )

    if associated_trial_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This sponsor cannot be deleted because "
                f"it has {associated_trial_count} "
                "associated clinical-trial record(s)."
            ),
        )

    database.delete(
        sponsor
    )

    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This sponsor cannot be deleted because "
                "it is referenced by another record."
            ),
        ) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/{sponsor_id}/trials",
    response_model=TrialListResponse,
)
def list_sponsor_trials(
    sponsor_id: int,
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
) -> TrialListResponse:
    """Return trials associated with a sponsor."""

    del user

    sponsor = find_sponsor(
        sponsor_id,
        database,
    )

    del sponsor

    total = int(
        database.scalar(
            select(
                func.count(
                    ClinicalTrial.id
                )
            ).where(
                ClinicalTrial.sponsor_id
                == sponsor_id
            )
        )
        or 0
    )

    offset = (
        page - 1
    ) * page_size

    trials = list(
        database.scalars(
            select(
                ClinicalTrial
            )
            .options(
                selectinload(
                    ClinicalTrial.sponsor
                )
            )
            .where(
                ClinicalTrial.sponsor_id
                == sponsor_id
            )
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