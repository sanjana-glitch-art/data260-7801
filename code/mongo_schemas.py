from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class TrialPhase(str, Enum):
    """Allowed clinical-trial phases."""

    PHASE_I = "Phase I"
    PHASE_II = "Phase II"
    PHASE_III = "Phase III"
    PHASE_IV = "Phase IV"


class RecruitmentStatus(str, Enum):
    """Allowed recruitment-status values."""

    PLANNING = "Planning"
    RECRUITING = "Recruiting"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    SUSPENDED = "Suspended"


class TrialDocumentCreate(BaseModel):
    """Values accepted when creating a trial document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    trial_title: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    trial_phase: TrialPhase

    recruitment_status: RecruitmentStatus = (
        RecruitmentStatus.PLANNING
    )

    start_date: datetime

    @field_validator(
        "trial_title",
    )
    @classmethod
    def title_must_not_be_blank(
        cls,
        value: str,
    ) -> str:
        """Reject a title containing only whitespace."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Trial title must not be blank."
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_optional_description(
        cls,
        value: str | None,
    ) -> str | None:
        """Convert an empty optional description to None."""

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    @field_validator(
        "start_date",
    )
    @classmethod
    def normalize_start_date(
        cls,
        value: datetime,
    ) -> datetime:
        """Store date-time values with a UTC timezone."""

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )


class TrialDocumentUpdate(BaseModel):
    """Values accepted when updating a trial document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    trial_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    trial_phase: TrialPhase | None = None

    recruitment_status: (
        RecruitmentStatus | None
    ) = None

    start_date: datetime | None = None

    @field_validator(
        "trial_title",
    )
    @classmethod
    def title_must_not_be_blank(
        cls,
        value: str | None,
    ) -> str | None:
        """Reject a blank title if one is provided."""

        if value is None:
            return None

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Trial title must not be blank."
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_optional_description(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional description."""

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    @field_validator(
        "start_date",
    )
    @classmethod
    def normalize_start_date(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Normalize an optional date-time to UTC."""

        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    @model_validator(
        mode="after",
    )
    def require_at_least_one_field(
        self,
    ) -> TrialDocumentUpdate:
        """Reject an update containing no fields."""

        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be supplied."
            )

        return self


class TrialDocumentResponse(BaseModel):
    """A clinical-trial document returned by the API."""

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str

    trial_title: str

    description: str | None = None

    trial_phase: TrialPhase

    recruitment_status: RecruitmentStatus

    start_date: datetime

    created_at: datetime

    updated_at: datetime


def serialize_trial_document(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Convert a MongoDB document into API-safe values."""

    return {
        "id": str(
            document["_id"]
        ),
        "trial_title": document[
            "trial_title"
        ],
        "description": document.get(
            "description"
        ),
        "trial_phase": document[
            "trial_phase"
        ],
        "recruitment_status": document[
            "recruitment_status"
        ],
        "start_date": document[
            "start_date"
        ],
        "created_at": document[
            "created_at"
        ],
        "updated_at": document[
            "updated_at"
        ],
    }