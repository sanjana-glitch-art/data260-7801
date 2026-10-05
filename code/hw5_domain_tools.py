from __future__ import annotations

import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import func, or_, select
from sqlalchemy.exc import (
    OperationalError,
    SQLAlchemyError,
)

from code.database import db_session_basede26
from code.models import ClinicalTrial, Sponsor


DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_BACKOFF_SECONDS = 0.025


class InjectedFailure(RuntimeError):
    """Failure created by the HW5 experiment."""


def envelope(
    *,
    ok: bool,
    data: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Return the shared tool-response envelope."""

    return {
        "ok": ok,
        "data": data,
        "error": error,
    }


def success(
    data: Any,
) -> dict[str, Any]:
    """Return a successful result."""

    return envelope(
        ok=True,
        data=data,
        error=None,
    )


def failure(
    message: str,
) -> dict[str, Any]:
    """Return a clean failure result."""

    return envelope(
        ok=False,
        data=None,
        error=message,
    )


def serialize_value(
    value: Any,
) -> Any:
    """Convert database values to JSON-safe values."""

    if isinstance(
        value,
        (
            date,
            datetime,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        Decimal,
    ):
        if value == value.to_integral_value():
            return int(value)

        return float(value)

    return value


def row_to_dict(
    row: Any,
) -> dict[str, Any]:
    """Convert a SQLAlchemy row into a dictionary."""

    return {
        key: serialize_value(value)
        for key, value
        in row._mapping.items()
    }


def positive_integer(
    value: Any,
    field_name: str,
) -> tuple[int | None, str | None]:
    """Validate and return a positive integer."""

    if isinstance(value, bool):
        return (
            None,
            f"{field_name} must be a positive integer.",
        )

    try:
        parsed = int(value)
    except (
        TypeError,
        ValueError,
    ):
        return (
            None,
            f"{field_name} must be a positive integer.",
        )

    if parsed < 1:
        return (
            None,
            f"{field_name} must be a positive integer.",
        )

    return parsed, None


def run_with_retry(
    operation: Callable[[], dict[str, Any]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    should_inject_failure: (
        Callable[[], bool] | None
    ) = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Execute an operation with timeout and bounded retries.

    The delay doubles after each failed attempt.
    """

    if max_attempts < 1:
        return (
            failure(
                "max_attempts must be at least 1."
            ),
            {
                "attempts": 0,
                "retried": False,
                "errors": [],
            },
        )

    errors: list[str] = []
    attempts = 0

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        attempts = attempt
        executor = ThreadPoolExecutor(
            max_workers=1
        )

        try:
            if (
                should_inject_failure
                is not None
                and should_inject_failure()
            ):
                raise InjectedFailure(
                    "Reproducible injected failure."
                )

            future = executor.submit(
                operation
            )

            result = future.result(
                timeout=timeout_seconds
            )

            return (
                result,
                {
                    "attempts": attempts,
                    "retried": attempts > 1,
                    "errors": errors,
                },
            )

        except InjectedFailure as error:
            errors.append(
                f"attempt {attempt}: {error}"
            )

        except FutureTimeoutError:
            errors.append(
                (
                    f"attempt {attempt}: operation "
                    f"timed out after "
                    f"{timeout_seconds:.3f} seconds"
                )
            )

        except (
            OperationalError,
            SQLAlchemyError,
        ) as error:
            errors.append(
                (
                    f"attempt {attempt}: "
                    f"{type(error).__name__}"
                )
            )

        except Exception as error:
            errors.append(
                (
                    f"attempt {attempt}: "
                    f"{type(error).__name__}: {error}"
                )
            )

        finally:
            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

        if attempt < max_attempts:
            delay = (
                backoff_seconds
                * (2 ** (attempt - 1))
            )

            time.sleep(delay)

    return (
        failure(
            (
                "Operation failed after "
                f"{max_attempts} attempts."
            )
        ),
        {
            "attempts": attempts,
            "retried": attempts > 1,
            "errors": errors,
        },
    )


def search_trials_once(
    query: str,
    limit: int,
) -> dict[str, Any]:
    """Perform one database search attempt."""

    pattern = f"%{query}%"

    with db_session_basede26() as session:
        statement = (
            select(
                ClinicalTrial.id,
                ClinicalTrial.trial_code,
                ClinicalTrial.trial_title,
                ClinicalTrial.trial_phase,
                ClinicalTrial.enrollment_target,
                Sponsor.id.label(
                    "sponsor_id"
                ),
                Sponsor.sponsor_name,
            )
            .join(
                Sponsor,
                Sponsor.id
                == ClinicalTrial.sponsor_id,
            )
            .where(
                or_(
                    ClinicalTrial.trial_title.like(
                        pattern
                    ),
                    ClinicalTrial.trial_code.like(
                        pattern
                    ),
                    Sponsor.sponsor_name.like(
                        pattern
                    ),
                )
            )
            .order_by(
                ClinicalTrial.id
            )
            .limit(limit)
        )

        rows = session.execute(
            statement
        ).all()

        return success({
            "query": query,
            "count": len(rows),
            "trials": [
                row_to_dict(row)
                for row in rows
            ],
        })


def search_trials_operation(
    query: str,
    limit: int = 10,
    *,
    should_inject_failure: (
        Callable[[], bool] | None
    ) = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    """Validate and reliably search trials."""

    cleaned_query = str(query).strip()

    if not cleaned_query:
        return (
            failure(
                "query must not be empty."
            ),
            {
                "attempts": 0,
                "retried": False,
                "errors": [],
            },
        )

    checked_limit, limit_error = (
        positive_integer(
            limit,
            "limit",
        )
    )

    if limit_error:
        return (
            failure(limit_error),
            {
                "attempts": 0,
                "retried": False,
                "errors": [],
            },
        )

    if checked_limit > 25:
        return (
            failure(
                "limit must be between 1 and 25."
            ),
            {
                "attempts": 0,
                "retried": False,
                "errors": [],
            },
        )

    return run_with_retry(
        lambda: search_trials_once(
            cleaned_query,
            checked_limit,
        ),
        should_inject_failure=(
            should_inject_failure
        ),
    )


def trial_details_once(
    trial_id: int,
) -> dict[str, Any]:
    """Perform one trial-detail lookup attempt."""

    with db_session_basede26() as session:
        statement = (
            select(
                ClinicalTrial.id,
                ClinicalTrial.trial_code,
                ClinicalTrial.trial_title,
                ClinicalTrial.trial_description,
                ClinicalTrial.trial_phase,
                ClinicalTrial.enrollment_target,
                ClinicalTrial.submitter_email,
                ClinicalTrial.created_at,
                ClinicalTrial.updated_at,
                Sponsor.id.label(
                    "sponsor_id"
                ),
                Sponsor.sponsor_name,
                Sponsor.headquarters,
                Sponsor.contact_email.label(
                    "sponsor_contact_email"
                ),
            )
            .join(
                Sponsor,
                Sponsor.id
                == ClinicalTrial.sponsor_id,
            )
            .where(
                ClinicalTrial.id
                == trial_id
            )
        )

        row = session.execute(
            statement
        ).first()

        if row is None:
            return failure(
                "Clinical trial not found."
            )

        return success(
            row_to_dict(row)
        )


def trial_details_operation(
    trial_id: int,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    """Validate and reliably retrieve one trial."""

    checked_id, id_error = (
        positive_integer(
            trial_id,
            "trial_id",
        )
    )

    if id_error:
        return (
            failure(id_error),
            {
                "attempts": 0,
                "retried": False,
                "errors": [],
            },
        )

    return run_with_retry(
        lambda: trial_details_once(
            checked_id
        )
    )


def trial_phase_summary_once(
    sponsor_id: int | None,
) -> dict[str, Any]:
    """Perform one aggregate database attempt."""

    with db_session_basede26() as session:
        if sponsor_id is not None:
            sponsor_exists = session.scalar(
                select(
                    Sponsor.id
                ).where(
                    Sponsor.id == sponsor_id
                )
            )

            if sponsor_exists is None:
                return failure(
                    "Sponsor not found."
                )

        statement = (
            select(
                ClinicalTrial.trial_phase,
                func.count(
                    ClinicalTrial.id
                ).label(
                    "trial_count"
                ),
                func.sum(
                    ClinicalTrial.enrollment_target
                ).label(
                    "total_enrollment_target"
                ),
            )
            .group_by(
                ClinicalTrial.trial_phase
            )
            .order_by(
                ClinicalTrial.trial_phase
            )
        )

        if sponsor_id is not None:
            statement = statement.where(
                ClinicalTrial.sponsor_id
                == sponsor_id
            )

        rows = session.execute(
            statement
        ).all()

        phases = [
            row_to_dict(row)
            for row in rows
        ]

        total_trials = sum(
            int(
                item["trial_count"] or 0
            )
            for item in phases
        )

        return success({
            "sponsor_id": sponsor_id,
            "total_trials": total_trials,
            "phases": phases,
        })

def trial_phase_summary_operation(
    sponsor_id: int | None = None,
) -> dict[str, Any]:
    """Return trial counts grouped by phase."""

    if sponsor_id is not None:
        if (
            not isinstance(sponsor_id, int)
            or sponsor_id <= 0
        ):
            return failure(
                "sponsor_id must be a positive integer."
            )

    database = db_session_basede26()

    try:
        statement = (
            select(
                ClinicalTrial.trial_phase,
                func.count(
                    ClinicalTrial.id
                ).label("trial_count"),
            )
            .group_by(
                ClinicalTrial.trial_phase
            )
            .order_by(
                ClinicalTrial.trial_phase
            )
        )

        if sponsor_id is not None:
            statement = statement.where(
                ClinicalTrial.sponsor_id
                == sponsor_id
            )

        rows = database.execute(
            statement
        ).all()

        phases = [
            {
                "trial_phase": row.trial_phase,
                "trial_count": int(
                    row.trial_count
                ),
            }
            for row in rows
        ]

        return success({
            "sponsor_id": sponsor_id,
            "phase_count": len(phases),
            "phases": phases,
        })
    except Exception as error:
        return failure(
            f"{type(error).__name__}: {error}"
        )
    finally:
        database.close()