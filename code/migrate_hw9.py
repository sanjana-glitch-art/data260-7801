from __future__ import annotations

from code.database import engine

from sqlalchemy import inspect, text


def main() -> None:
    """Add the persisted view counter required by HW9."""

    inspector = inspect(engine)
    columns = {
        column["name"]
        for column in inspector.get_columns(
            "clinical_trials"
        )
    }

    if "view_count" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE clinical_trials
                    ADD COLUMN view_count
                    INT NOT NULL DEFAULT 0
                    """
                )
            )

        print(
            "Added clinical_trials.view_count."
        )
    else:
        print(
            "clinical_trials.view_count "
            "already exists."
        )

    with engine.connect() as connection:
        count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM clinical_trials
                """
            )
        ).scalar_one()

    print(
        f"Clinical trials available: {count}"
    )
    print(
        "Homework 9 Part 1 migration complete."
    )


if __name__ == "__main__":
    main()
