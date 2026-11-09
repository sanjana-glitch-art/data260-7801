from __future__ import annotations

from code.database import engine
from code.hw9_config import (
    PREFIX,
    REDIS_URL,
    VIEW_SYNC_INTERVAL,
)

from redis import Redis
from sqlalchemy import text
from sqlalchemy.engine import Engine


class ClinicalTrialViewCounter:
    """Redis counter with periodic MySQL sync."""

    def __init__(
        self,
        database_engine: Engine = engine,
        redis_url: str = REDIS_URL,
    ) -> None:
        self.engine = database_engine
        self.redis_client = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        self.redis_client.ping()

    @staticmethod
    def view_key(
        trial_id: int,
    ) -> str:
        """Return the prefixed Redis view key."""

        return (
            f"{PREFIX}:views:"
            f"clinical_trial:{trial_id}"
        )

    def trial_exists(
        self,
        trial_id: int,
    ) -> bool:
        """Return whether the trial exists."""

        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM clinical_trials
                    WHERE id = :trial_id
                    """
                ),
                {
                    "trial_id": trial_id,
                },
            ).scalar_one()

        return bool(result)

    def database_view_count(
        self,
        trial_id: int,
    ) -> int:
        """Read the persisted database count."""

        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT view_count
                    FROM clinical_trials
                    WHERE id = :trial_id
                    """
                ),
                {
                    "trial_id": trial_id,
                },
            ).scalar_one_or_none()

        if result is None:
            raise ValueError(
                "Clinical trial not found."
            )

        return int(result)

    def increment_trial_views(
        self,
        trial_id: int,
    ) -> int:
        """Increment Redis and sync every ten views."""

        if not self.trial_exists(trial_id):
            raise ValueError(
                "Clinical trial not found."
            )

        key = self.view_key(trial_id)

        if not self.redis_client.exists(key):
            persisted_count = (
                self.database_view_count(trial_id)
            )

            self.redis_client.set(
                key,
                persisted_count,
                nx=True,
            )

        current_count = int(
            self.redis_client.incr(key)
        )

        if (
            current_count
            % VIEW_SYNC_INTERVAL
            == 0
        ):
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE clinical_trials
                        SET view_count = :view_count
                        WHERE id = :trial_id
                        """
                    ),
                    {
                        "trial_id": trial_id,
                        "view_count": current_count,
                    },
                )

            print(
                "Synced views to database "
                f"at count {current_count}"
            )

        return current_count

    def reset_counter(
        self,
        trial_id: int,
    ) -> None:
        """Reset Redis and database evidence."""

        if not self.trial_exists(trial_id):
            raise ValueError(
                "Clinical trial not found."
            )

        self.redis_client.delete(
            self.view_key(trial_id)
        )

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE clinical_trials
                    SET view_count = 0
                    WHERE id = :trial_id
                    """
                ),
                {
                    "trial_id": trial_id,
                },
            )

    def close(self) -> None:
        """Close the Redis client."""

        self.redis_client.close()
