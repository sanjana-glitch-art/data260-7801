from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


TrialPhase = Literal[
    "Phase I",
    "Phase II",
    "Phase III",
    "Phase IV",
]


class LoginRequest(BaseModel):
    """Email and password submitted during login."""

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=255,
    )


class UserResponse(BaseModel):
    """Safe user information returned to the client."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    display_name: str
    email: EmailStr
    is_active: bool


class AuthResponse(BaseModel):
    """Authentication response containing the user."""

    user: UserResponse


class MessageResponse(BaseModel):
    """Simple API message."""

    message: str


class SponsorBase(BaseModel):
    """Shared sponsor fields."""

    sponsor_name: str = Field(
        min_length=2,
        max_length=255,
    )

    headquarters: str = Field(
        min_length=2,
        max_length=255,
    )

    contact_email: EmailStr

    @field_validator(
        "sponsor_name",
        "headquarters",
    )
    @classmethod
    def clean_required_text(
        cls,
        value: str,
    ) -> str:
        """Strip and validate required text."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Value cannot be blank."
            )

        return cleaned


class SponsorCreate(SponsorBase):
    """Values accepted when creating a sponsor."""


class SponsorUpdate(SponsorBase):
    """Values accepted when updating a sponsor."""


class SponsorSummary(BaseModel):
    """Compact sponsor information included with a trial."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    sponsor_name: str
    headquarters: str
    contact_email: EmailStr


class SponsorResponse(SponsorBase):
    """Complete sponsor response."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    created_at: datetime
    updated_at: datetime


class SponsorListResponse(BaseModel):
    """Paginated sponsor results."""

    items: list[SponsorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TrialBase(BaseModel):
    """Shared clinical-trial fields."""

    trial_title: str = Field(
        min_length=2,
        max_length=255,
    )

    trial_code: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Z0-9][A-Z0-9-]*$",
        examples=[
            "S7801-CT-005001"
        ],
    )

    enrollment_target: int = Field(
        default=0,
        ge=0,
        le=1_000_000,
    )

    sponsor_id: int = Field(
        gt=0,
    )

    submitter_email: EmailStr

    trial_description: str = Field(
        min_length=10,
        max_length=10000,
    )

    trial_phase: TrialPhase = "Phase I"

    @field_validator(
        "trial_title",
        "trial_description",
    )
    @classmethod
    def clean_trial_text(
        cls,
        value: str,
    ) -> str:
        """Strip and validate clinical-trial text."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Value cannot be blank."
            )

        return cleaned

    @field_validator(
        "trial_code",
        mode="before",
    )
    @classmethod
    def normalize_trial_code(
        cls,
        value: str,
    ) -> str:
        """Normalize trial codes before pattern validation."""

        return str(
            value
        ).strip().upper()


class TrialCreate(TrialBase):
    """Values accepted when creating a clinical trial."""


class TrialUpdate(TrialBase):
    """Values accepted when updating a clinical trial."""


class ClinicalTrialResponse(BaseModel):
    """Clinical-trial information returned by the API."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    trial_title: str
    trial_code: str
    enrollment_target: int
    sponsor_id: int

    # Retained for the existing frontend.
    sponsor_name: str

    submitter_email: EmailStr
    trial_description: str
    trial_phase: TrialPhase
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    sponsor: SponsorSummary | None = None


class TrialListResponse(BaseModel):
    """Paginated clinical-trial results."""

    items: list[ClinicalTrialResponse]
    total: int
    page: int
    page_size: int
    total_pages: int