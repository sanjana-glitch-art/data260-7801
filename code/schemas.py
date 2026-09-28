from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class LoginRequest(BaseModel):
    """Email and password submitted during login."""

    email: str = Field(
        min_length=3,
        max_length=255,
    )

    password: str = Field(
        min_length=1,
        max_length=255,
    )


class UserResponse(BaseModel):
    """Safe user information returned to the React client."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    display_name: str
    email: str
    is_active: bool


class AuthResponse(BaseModel):
    """Authentication response containing the current user."""

    user: UserResponse


class MessageResponse(BaseModel):
    """A simple API message."""

    message: str


class TrialCreate(BaseModel):
    """Values accepted when creating a clinical trial."""

    trial_title: str = Field(
        min_length=1,
        max_length=255,
    )

    sponsor_name: str = Field(
        min_length=1,
        max_length=255,
    )

    submitter_email: str = Field(
        default="",
        max_length=255,
    )

    trial_description: str = Field(
        default="",
        max_length=10000,
    )

    trial_phase: str = Field(
        default="Phase I",
        max_length=50,
    )


class TrialUpdate(BaseModel):
    """Values accepted when updating a clinical trial."""

    trial_title: str = Field(
        min_length=1,
        max_length=255,
    )

    sponsor_name: str = Field(
        min_length=1,
        max_length=255,
    )

    submitter_email: str = Field(
        default="",
        max_length=255,
    )

    trial_description: str = Field(
        default="",
        max_length=10000,
    )

    trial_phase: str = Field(
        default="Phase I",
        max_length=50,
    )


class ClinicalTrialResponse(BaseModel):
    """Clinical-trial information returned by the API."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    trial_title: str
    sponsor_name: str
    submitter_email: str
    trial_description: str
    trial_phase: str
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime