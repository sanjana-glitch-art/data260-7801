from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from code.database import Base


def utc_now() -> datetime:
    """Return the current UTC time without timezone metadata."""

    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


class User(Base):
    """An application user who can log in."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    sessions: Mapped[list["ServerSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ServerSession(Base):
    """A server-side login session."""

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="sessions",
    )


class Sponsor(Base):
    """An organization that sponsors clinical trials."""

    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    sponsor_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    headquarters: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    contact_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    trials: Mapped[list["ClinicalTrial"]] = relationship(
        back_populates="sponsor",
        passive_deletes=True,
    )


class ClinicalTrial(Base):
    """A clinical-trial listing stored in MySQL."""

    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    trial_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    trial_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    enrollment_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    sponsor_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sponsors.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # Retained for compatibility with the earlier frontend and
    # Homework 4 data. The authoritative sponsor relationship
    # is now sponsor_id.
    sponsor_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    submitter_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    trial_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    trial_phase: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Phase I",
    )

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    sponsor: Mapped["Sponsor"] = relationship(
        back_populates="trials",
    )

    sites: Mapped[list["TrialSite"]] = relationship(
        back_populates="trial",
        cascade="all, delete-orphan",
    )


class TrialSite(Base):
    """A location participating in a clinical trial."""

    __tablename__ = "trial_sites"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    clinical_trial_id: Mapped[int] = mapped_column(
        ForeignKey(
            "clinical_trials.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    site_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    state_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    principal_investigator: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    trial: Mapped["ClinicalTrial"] = relationship(
        back_populates="sites",
    )