from __future__ import annotations

from code.database import engine
from typing import Any

from sqlalchemy import text

TRIALS: tuple[
    dict[str, Any],
    ...,
] = (
    {
        "trial_title": ("Sleep Quality and Academic Performance Study"),
        "trial_code": "S7801-CT-000001",
        "enrollment_target": 120,
        "submitter_email": ("sleep@example.edu"),
        "trial_description": (
            "This clinical trial examines sleep "
            "quality, concentration, memory, and "
            "academic performance."
        ),
        "trial_phase": "Phase II",
    },
    {
        "trial_title": ("Digital Wellness Intervention Study"),
        "trial_code": "S7801-CT-000002",
        "enrollment_target": 180,
        "submitter_email": ("wellness@example.edu"),
        "trial_description": (
            "This study evaluates a digital wellness "
            "intervention for university students."
        ),
        "trial_phase": "Phase I",
    },
    {
        "trial_title": ("Student Memory and Cognitive Performance Trial"),
        "trial_code": "S7801-CT-000003",
        "enrollment_target": 90,
        "submitter_email": ("memory@example.edu"),
        "trial_description": (
            "This clinical trial evaluates memory "
            "and cognitive performance among "
            "university students."
        ),
        "trial_phase": "Phase III",
    },
    {
        "trial_title": ("Remote Clinical Monitoring Study"),
        "trial_code": "S7801-CT-000004",
        "enrollment_target": 250,
        "submitter_email": ("monitoring@example.edu"),
        "trial_description": (
            "This study evaluates remote monitoring "
            "methods for participants in clinical "
            "research."
        ),
        "trial_phase": "Phase IV",
    },
)


def main() -> None:
    """Seed deterministic Homework 7 trial records."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO sponsors (
                    sponsor_name,
                    headquarters,
                    contact_email,
                    created_at,
                    updated_at
                )
                VALUES (
                    'San Jose State University',
                    'San Jose, California',
                    'research@example.edu',
                    UTC_TIMESTAMP(),
                    UTC_TIMESTAMP()
                )
                ON DUPLICATE KEY UPDATE
                    sponsor_name = VALUES(
                        sponsor_name
                    )
                """
            )
        )

        sponsor_id = connection.execute(
            text(
                """
                SELECT id
                FROM sponsors
                WHERE sponsor_name =
                    'San Jose State University'
                LIMIT 1
                """
            )
        ).scalar_one()

        writer_id = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE username = 'writer7801'
                LIMIT 1
                """
            )
        ).scalar_one()

        for trial in TRIALS:
            connection.execute(
                text(
                    """
                    INSERT INTO clinical_trials (
                        trial_title,
                        trial_code,
                        enrollment_target,
                        sponsor_id,
                        sponsor_name,
                        submitter_email,
                        trial_description,
                        trial_phase,
                        created_by_user_id,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :trial_title,
                        :trial_code,
                        :enrollment_target,
                        :sponsor_id,
                        :sponsor_name,
                        :submitter_email,
                        :trial_description,
                        :trial_phase,
                        :created_by_user_id,
                        UTC_TIMESTAMP(),
                        UTC_TIMESTAMP()
                    )
                    ON DUPLICATE KEY UPDATE
                        trial_title = VALUES(
                            trial_title
                        ),
                        enrollment_target = VALUES(
                            enrollment_target
                        ),
                        sponsor_id = VALUES(
                            sponsor_id
                        ),
                        sponsor_name = VALUES(
                            sponsor_name
                        ),
                        submitter_email = VALUES(
                            submitter_email
                        ),
                        trial_description = VALUES(
                            trial_description
                        ),
                        trial_phase = VALUES(
                            trial_phase
                        ),
                        created_by_user_id = VALUES(
                            created_by_user_id
                        ),
                        updated_at = UTC_TIMESTAMP()
                    """
                ),
                {
                    **trial,
                    "sponsor_id": sponsor_id,
                    "sponsor_name": ("San Jose State University"),
                    "created_by_user_id": (writer_id),
                },
            )

            print(
                "Seeded:",
                trial["trial_code"],
                "|",
                trial["trial_title"],
            )

        count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM clinical_trials
                """
            )
        ).scalar_one()

    print(
        "\nClinical-trial records:",
        count,
    )


if __name__ == "__main__":
    main()
