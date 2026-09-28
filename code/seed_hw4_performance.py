from __future__ import annotations

import random

from sqlalchemy import func, insert, select

from code.database import db_session_basede26
from code.models import ClinicalTrial, TrialSite, User


SEED = 7801

TARGET_TRIAL_COUNT = 5000
TARGET_SITE_COUNT = 200


SPONSORS = [
    "San Jose State University",
    "California Clinical Research Institute",
    "Bay Area Medical Center",
    "Pacific Health Research Network",
    "Silicon Valley Biomedical Institute",
    "Northern California University Hospital",
    "West Coast Clinical Research Group",
    "California Student Health Center",
]


PHASES = [
    "Phase I",
    "Phase II",
    "Phase III",
    "Phase IV",
]


STUDY_AREAS = [
    "Sleep Quality",
    "Digital Wellness",
    "Cardiovascular Health",
    "Memory Improvement",
    "Diabetes Prevention",
    "Student Mental Health",
    "Nutrition and Wellness",
    "Physical Activity",
    "Stress Management",
    "Cognitive Performance",
]


SITE_LOCATIONS = [
    (
        "San Jose",
        "CA",
    ),
    (
        "Santa Clara",
        "CA",
    ),
    (
        "Milpitas",
        "CA",
    ),
    (
        "Sunnyvale",
        "CA",
    ),
    (
        "Fremont",
        "CA",
    ),
    (
        "Oakland",
        "CA",
    ),
    (
        "San Francisco",
        "CA",
    ),
    (
        "Sacramento",
        "CA",
    ),
]


INVESTIGATORS = [
    "Dr. Maya Patel",
    "Dr. Daniel Kim",
    "Dr. Elena Garcia",
    "Dr. Michael Chen",
    "Dr. Priya Shah",
    "Dr. Jordan Williams",
    "Dr. Sophia Martinez",
    "Dr. David Nguyen",
]


def get_demo_user_id() -> int:
    """Return the ID of the demonstration user."""

    with db_session_basede26() as database:
        user_id = database.scalar(
            select(User.id).where(
                User.email
                == "sanjana@example.edu"
            )
        )

        if user_id is None:
            raise RuntimeError(
                "The demo user does not exist. Run "
                "'python -m code.init_hw4_db' first."
            )

        return user_id


def count_trials() -> int:
    """Return the current number of clinical trials."""

    with db_session_basede26() as database:
        return int(
            database.scalar(
                select(
                    func.count(
                        ClinicalTrial.id
                    )
                )
            )
            or 0
        )


def count_sites() -> int:
    """Return the current number of trial sites."""

    with db_session_basede26() as database:
        return int(
            database.scalar(
                select(
                    func.count(
                        TrialSite.id
                    )
                )
            )
            or 0
        )


def seed_trials(
    user_id: int,
) -> None:
    """Insert records until the database has 5,000 trials."""

    current_count = count_trials()

    records_needed = max(
        TARGET_TRIAL_COUNT - current_count,
        0,
    )

    if records_needed == 0:
        print(
            "Clinical trials already meet the target:",
            current_count,
        )
        return

    random_generator = random.Random(
        SEED
    )

    with db_session_basede26() as database:
        existing_titles = set(
            database.scalars(
                select(
                    ClinicalTrial.trial_title
                )
            ).all()
        )

        trial_rows: list[dict[str, object]] = []

        sequence = 1

        while len(trial_rows) < records_needed:
            title = (
                f"{random_generator.choice(STUDY_AREAS)} "
                f"Clinical Study {sequence:05d}"
            )

            sequence += 1

            if title in existing_titles:
                continue

            existing_titles.add(
                title
            )

            sponsor = random_generator.choice(
                SPONSORS
            )

            phase = random_generator.choice(
                PHASES
            )

            trial_rows.append({
                "trial_title": title,
                "sponsor_name": sponsor,
                "submitter_email": (
                    f"research{sequence:05d}"
                    "@example.edu"
                ),
                "trial_description": (
                    f"This clinical trial evaluates "
                    f"{title.lower()} and its outcomes "
                    f"among eligible research participants."
                ),
                "trial_phase": phase,
                "created_by_user_id": user_id,
            })

        database.execute(
            insert(ClinicalTrial),
            trial_rows,
        )

        database.commit()

    print(
        "Clinical trials inserted:",
        records_needed,
    )


def seed_trial_sites() -> None:
    """Insert records until the database has 200 trial sites."""

    current_count = count_sites()

    records_needed = max(
        TARGET_SITE_COUNT - current_count,
        0,
    )

    if records_needed == 0:
        print(
            "Trial sites already meet the target:",
            current_count,
        )
        return

    random_generator = random.Random(
        SEED + 1
    )

    with db_session_basede26() as database:
        trial_ids = list(
            database.scalars(
                select(
                    ClinicalTrial.id
                )
                .order_by(
                    ClinicalTrial.id
                )
                .limit(
                    TARGET_SITE_COUNT
                )
            ).all()
        )

        if not trial_ids:
            raise RuntimeError(
                "No clinical trials were found."
            )

        site_rows: list[dict[str, object]] = []

        for offset in range(
            records_needed
        ):
            sequence = (
                current_count
                + offset
                + 1
            )

            city, state_code = (
                random_generator.choice(
                    SITE_LOCATIONS
                )
            )

            trial_id = trial_ids[
                (sequence - 1)
                % len(trial_ids)
            ]

            site_rows.append({
                "clinical_trial_id": trial_id,
                "site_name": (
                    f"Clinical Research Site "
                    f"{sequence:03d}"
                ),
                "city": city,
                "state_code": state_code,
                "principal_investigator": (
                    random_generator.choice(
                        INVESTIGATORS
                    )
                ),
            })

        database.execute(
            insert(TrialSite),
            site_rows,
        )

        database.commit()

    print(
        "Trial sites inserted:",
        records_needed,
    )


def print_final_counts() -> None:
    """Print final table counts."""

    print("\nPerformance-data seeding complete.")
    print(
        "Clinical trials:",
        count_trials(),
    )
    print(
        "Trial sites:",
        count_sites(),
    )


def main() -> None:
    """Create the Homework 4 performance dataset."""

    user_id = get_demo_user_id()

    seed_trials(
        user_id
    )

    seed_trial_sites()

    print_final_counts()


if __name__ == "__main__":
    main()