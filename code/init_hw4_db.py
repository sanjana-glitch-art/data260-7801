from __future__ import annotations

from sqlalchemy import select

from code.auth_api import hash_password
from code.database import (
    Base,
    db_session_basede26,
    engine,
)
from code.models import ClinicalTrial, User


DEMO_DISPLAY_NAME = "Sanjana Thummalapalli"

DEMO_EMAIL = "sanjana@example.edu"

DEMO_PASSWORD = "Data260!7801"


INITIAL_TRIALS = [
    {
        "trial_title": (
            "Sleep Quality and Academic Performance Study"
        ),
        "sponsor_name": (
            "San Jose State University"
        ),
        "submitter_email": (
            "research@example.edu"
        ),
        "trial_description": (
            "This clinical trial examines how sleep quality "
            "affects concentration, memory, and academic "
            "performance among university students."
        ),
        "trial_phase": "Phase II",
    },
    {
        "trial_title": (
            "Digital Wellness Intervention Study"
        ),
        "sponsor_name": (
            "California Student Health Research Center"
        ),
        "submitter_email": (
            "wellness@example.edu"
        ),
        "trial_description": (
            "This study evaluates a digital wellness "
            "intervention designed for college students."
        ),
        "trial_phase": "Phase I",
    },
]


def create_tables() -> None:
    """Create all tables defined by the SQLAlchemy models."""

    Base.metadata.create_all(
        bind=engine
    )


def create_demo_user() -> User:
    """Create or update the Homework 4 demonstration user."""

    with db_session_basede26() as database:
        user = database.scalar(
            select(User).where(
                User.email == DEMO_EMAIL
            )
        )

        if user is None:
            user = User(
                display_name=DEMO_DISPLAY_NAME,
                email=DEMO_EMAIL,
                password_hash=hash_password(
                    DEMO_PASSWORD
                ),
                is_active=True,
            )

            database.add(
                user
            )

            database.commit()

            database.refresh(
                user
            )

            print(
                "Created demo user:",
                DEMO_EMAIL,
            )
        else:
            user.display_name = (
                DEMO_DISPLAY_NAME
            )

            user.password_hash = (
                hash_password(
                    DEMO_PASSWORD
                )
            )

            user.is_active = True

            database.commit()

            database.refresh(
                user
            )

            print(
                "Updated demo user:",
                DEMO_EMAIL,
            )

        database.expunge(
            user
        )

        return user


def create_initial_trials(
    user_id: int,
) -> None:
    """Insert initial clinical-trial records when missing."""

    with db_session_basede26() as database:
        created_count = 0

        for trial_data in INITIAL_TRIALS:
            existing_trial = database.scalar(
                select(ClinicalTrial).where(
                    ClinicalTrial.trial_title
                    == trial_data["trial_title"]
                )
            )

            if existing_trial is not None:
                continue

            database.add(
                ClinicalTrial(
                    **trial_data,
                    created_by_user_id=user_id,
                )
            )

            created_count += 1

        database.commit()

        print(
            "Initial trial records created:",
            created_count,
        )


def print_summary() -> None:
    """Print the initialized database tables."""

    print("\nDatabase initialization complete.")
    print("Database: s7801_rel")
    print("Tables:")

    for table_name in sorted(
        Base.metadata.tables.keys()
    ):
        print(
            f"- {table_name}"
        )

    print("\nDemo login:")
    print(
        f"- Email: {DEMO_EMAIL}"
    )
    print(
        f"- Password: {DEMO_PASSWORD}"
    )


def main() -> None:
    """Initialize the Homework 4 MySQL database."""

    create_tables()

    user = create_demo_user()

    create_initial_trials(
        user.id
    )

    print_summary()


if __name__ == "__main__":
    main()