from __future__ import annotations

from typing import Any

from sqlalchemy import text

from code.database import engine


DATABASE_NAME = "s7801_rel"

SPONSOR_FOREIGN_KEY = (
    "fk_clinical_trials_sponsor"
)

TRIAL_CODE_INDEX = (
    "uq_clinical_trials_trial_code"
)

SPONSOR_ID_INDEX = (
    "idx_clinical_trials_sponsor_id"
)


def column_exists(
    table_name: str,
    column_name: str,
) -> bool:
    """Return whether a database column exists."""

    with engine.connect() as connection:
        count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :database_name
                  AND TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                """
            ),
            {
                "database_name": DATABASE_NAME,
                "table_name": table_name,
                "column_name": column_name,
            },
        )

    return bool(count)


def index_exists(
    table_name: str,
    index_name: str,
) -> bool:
    """Return whether a database index exists."""

    with engine.connect() as connection:
        count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = :database_name
                  AND TABLE_NAME = :table_name
                  AND INDEX_NAME = :index_name
                """
            ),
            {
                "database_name": DATABASE_NAME,
                "table_name": table_name,
                "index_name": index_name,
            },
        )

    return bool(count)


def foreign_key_exists(
    table_name: str,
    constraint_name: str,
) -> bool:
    """Return whether a foreign-key constraint exists."""

    with engine.connect() as connection:
        count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLE_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = :database_name
                  AND TABLE_NAME = :table_name
                  AND CONSTRAINT_NAME = :constraint_name
                  AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                """
            ),
            {
                "database_name": DATABASE_NAME,
                "table_name": table_name,
                "constraint_name": constraint_name,
            },
        )

    return bool(count)


def create_sponsors_table() -> None:
    """Create the related-entity table."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sponsors (
                    id INT NOT NULL AUTO_INCREMENT,
                    sponsor_name VARCHAR(255) NOT NULL,
                    headquarters VARCHAR(255) NOT NULL,
                    contact_email VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_sponsors_contact_email (
                        contact_email
                    ),
                    KEY idx_sponsors_sponsor_name (
                        sponsor_name
                    )
                ) ENGINE=InnoDB
                  DEFAULT CHARSET=utf8mb4
                  COLLATE=utf8mb4_0900_ai_ci
                """
            )
        )

        connection.execute(
            text(
                """
                ALTER TABLE sponsors
                CONVERT TO CHARACTER SET utf8mb4
                COLLATE utf8mb4_0900_ai_ci
                """
            )
        )

    print(
        "Sponsors table created or already present."
    )

def add_hw5_columns() -> None:
    """Add the required HW5 fields to clinical_trials."""

    if not column_exists(
        "clinical_trials",
        "trial_code",
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE clinical_trials
                    ADD COLUMN trial_code VARCHAR(50) NULL
                    AFTER trial_title
                    """
                )
            )

        print(
            "Added clinical_trials.trial_code."
        )
    else:
        print(
            "clinical_trials.trial_code already exists."
        )

    if not column_exists(
        "clinical_trials",
        "enrollment_target",
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE clinical_trials
                    ADD COLUMN enrollment_target INT
                    NOT NULL DEFAULT 0
                    AFTER trial_code
                    """
                )
            )

        print(
            "Added clinical_trials.enrollment_target."
        )
    else:
        print(
            "clinical_trials.enrollment_target already exists."
        )

    if not column_exists(
        "clinical_trials",
        "sponsor_id",
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE clinical_trials
                    ADD COLUMN sponsor_id INT NULL
                    AFTER enrollment_target
                    """
                )
            )

        print(
            "Added clinical_trials.sponsor_id."
        )
    else:
        print(
            "clinical_trials.sponsor_id already exists."
        )


def populate_sponsors() -> None:
    """Create sponsor rows from existing sponsor names."""

    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO sponsors (
                    sponsor_name,
                    headquarters,
                    contact_email,
                    created_at,
                    updated_at
                )
                SELECT DISTINCT
                    clinical_trials.sponsor_name,
                    'California, USA',
                    CONCAT(
                        'sponsor-',
                        LEFT(
                            SHA2(
                                clinical_trials.sponsor_name,
                                256
                            ),
                            20
                        ),
                        '@example.org'
                    ),
                    UTC_TIMESTAMP(),
                    UTC_TIMESTAMP()
                FROM clinical_trials
                LEFT JOIN sponsors
                    ON sponsors.sponsor_name
                     = clinical_trials.sponsor_name
                WHERE sponsors.id IS NULL
                  AND clinical_trials.sponsor_name IS NOT NULL
                  AND TRIM(
                      clinical_trials.sponsor_name
                  ) <> ''
                """
            )
        )

    print(
        "Sponsor records inserted:",
        result.rowcount,
    )


def populate_trial_fields() -> None:
    """Populate codes, counts, and sponsor relationships."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE clinical_trials
                SET trial_code = CONCAT(
                    'S7801-CT-',
                    LPAD(id, 6, '0')
                )
                WHERE trial_code IS NULL
                   OR TRIM(trial_code) = ''
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE clinical_trials
                SET enrollment_target = (
                    50 + MOD(id * 17, 451)
                )
                WHERE enrollment_target = 0
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE clinical_trials
                INNER JOIN sponsors
                    ON sponsors.sponsor_name
                     = clinical_trials.sponsor_name
                SET clinical_trials.sponsor_id
                    = sponsors.id
                WHERE clinical_trials.sponsor_id IS NULL
                """
            )
        )

    print(
        "Existing clinical-trial records populated."
    )


def verify_required_values() -> None:
    """Ensure all existing records can accept constraints."""

    with engine.connect() as connection:
        missing_trial_codes = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM clinical_trials
                    WHERE trial_code IS NULL
                       OR TRIM(trial_code) = ''
                    """
                )
            )
            or 0
        )

        missing_sponsors = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM clinical_trials
                    WHERE sponsor_id IS NULL
                    """
                )
            )
            or 0
        )

        duplicate_trial_codes = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT trial_code
                        FROM clinical_trials
                        GROUP BY trial_code
                        HAVING COUNT(*) > 1
                    ) AS duplicate_codes
                    """
                )
            )
            or 0
        )

    if missing_trial_codes:
        raise RuntimeError(
            "Some trials do not have trial codes."
        )

    if missing_sponsors:
        raise RuntimeError(
            "Some trials do not have sponsors."
        )

    if duplicate_trial_codes:
        raise RuntimeError(
            "Duplicate trial codes were detected."
        )

    print(
        "Required-value validation passed."
    )


def apply_constraints() -> None:
    """Apply NOT NULL, unique, index, and FK constraints."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE clinical_trials
                MODIFY COLUMN trial_code
                VARCHAR(50) NOT NULL
                """
            )
        )

        connection.execute(
            text(
                """
                ALTER TABLE clinical_trials
                MODIFY COLUMN sponsor_id
                INT NOT NULL
                """
            )
        )

    if not index_exists(
        "clinical_trials",
        TRIAL_CODE_INDEX,
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    CREATE UNIQUE INDEX
                    {TRIAL_CODE_INDEX}
                    ON clinical_trials (trial_code)
                    """
                )
            )

        print(
            "Created unique trial-code index."
        )
    else:
        print(
            "Unique trial-code index already exists."
        )

    if not index_exists(
        "clinical_trials",
        SPONSOR_ID_INDEX,
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    CREATE INDEX
                    {SPONSOR_ID_INDEX}
                    ON clinical_trials (sponsor_id)
                    """
                )
            )

        print(
            "Created sponsor-id index."
        )
    else:
        print(
            "Sponsor-id index already exists."
        )

    if not foreign_key_exists(
        "clinical_trials",
        SPONSOR_FOREIGN_KEY,
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE clinical_trials
                    ADD CONSTRAINT
                    {SPONSOR_FOREIGN_KEY}
                    FOREIGN KEY (sponsor_id)
                    REFERENCES sponsors(id)
                    ON DELETE RESTRICT
                    ON UPDATE CASCADE
                    """
                )
            )

        print(
            "Created sponsor foreign key."
        )
    else:
        print(
            "Sponsor foreign key already exists."
        )


def collect_summary() -> dict[str, Any]:
    """Return final migration counts."""

    with engine.connect() as connection:
        trial_count = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM clinical_trials
                    """
                )
            )
            or 0
        )

        sponsor_count = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM sponsors
                    """
                )
            )
            or 0
        )

        linked_trial_count = int(
            connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM clinical_trials
                    WHERE sponsor_id IS NOT NULL
                    """
                )
            )
            or 0
        )

    return {
        "clinical_trials": trial_count,
        "sponsors": sponsor_count,
        "linked_trials": linked_trial_count,
    }


def main() -> None:
    """Run the complete HW5 database migration."""

    print(
        "Starting Homework 5 database migration."
    )

    create_sponsors_table()
    add_hw5_columns()
    populate_sponsors()
    populate_trial_fields()
    verify_required_values()
    apply_constraints()

    summary = collect_summary()

    print(
        "\nHomework 5 migration complete."
    )

    print(
        "Clinical trials:",
        summary["clinical_trials"],
    )

    print(
        "Sponsors:",
        summary["sponsors"],
    )

    print(
        "Trials linked to sponsors:",
        summary["linked_trials"],
    )


if __name__ == "__main__":
    main()