from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Any, Generator

from fastapi import APIRouter, Depends, Query
from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload

from code.database import engine, get_db
from code.models import ClinicalTrial, TrialSite


router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
)


@contextmanager
def count_database_queries() -> Generator[
    dict[str, int],
    None,
    None,
]:
    """Count SQL statements executed inside this context."""

    counter = {
        "count": 0,
    }

    def before_cursor_execute(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        del (
            connection,
            cursor,
            statement,
            parameters,
            context,
            executemany,
        )

        counter["count"] += 1

    event.listen(
        engine,
        "before_cursor_execute",
        before_cursor_execute,
    )

    try:
        yield counter
    finally:
        event.remove(
            engine,
            "before_cursor_execute",
            before_cursor_execute,
        )


def trial_record(
    trial: ClinicalTrial,
    sites: list[TrialSite],
) -> dict[str, Any]:
    """Convert a trial and its sites to JSON-compatible data."""

    return {
        "id": trial.id,
        "trial_title": trial.trial_title,
        "sponsor_name": trial.sponsor_name,
        "trial_phase": trial.trial_phase,
        "sites": [
            {
                "id": site.id,
                "site_name": site.site_name,
                "city": site.city,
                "state_code": site.state_code,
                "principal_investigator": (
                    site.principal_investigator
                ),
            }
            for site in sites
        ],
    }


@router.get("/trials/naive")
def read_trials_naive(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=1000,
    ),
    database: Session = Depends(
        get_db
    ),
) -> dict[str, Any]:
    """
    Return trials using a deliberate N+1 query pattern.

    One query loads the trials, followed by one additional
    query per trial to load its related sites.
    """

    offset = (
        page - 1
    ) * page_size

    started_at = perf_counter()

    with count_database_queries() as counter:
        trials = list(
            database.scalars(
                select(
                    ClinicalTrial
                )
                .order_by(
                    ClinicalTrial.id
                )
                .offset(
                    offset
                )
                .limit(
                    page_size
                )
            ).all()
        )

        records: list[dict[str, Any]] = []

        for trial in trials:
            sites = list(
                database.scalars(
                    select(
                        TrialSite
                    ).where(
                        TrialSite.clinical_trial_id
                        == trial.id
                    )
                ).all()
            )

            records.append(
                trial_record(
                    trial,
                    sites,
                )
            )

    latency_ms = (
        perf_counter()
        - started_at
    ) * 1000

    return {
        "version": "naive",
        "page": page,
        "page_size": page_size,
        "record_count": len(records),
        "query_count": counter["count"],
        "latency_ms": round(
            latency_ms,
            3,
        ),
        "records": records,
    }


@router.get("/trials/optimized")
def read_trials_optimized(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=1000,
    ),
    database: Session = Depends(
        get_db
    ),
) -> dict[str, Any]:
    """
    Return trials using select-in eager loading.

    One query loads the trials and a second query loads all
    related site records for the selected trials.
    """

    offset = (
        page - 1
    ) * page_size

    started_at = perf_counter()

    with count_database_queries() as counter:
        trials = list(
            database.scalars(
                select(
                    ClinicalTrial
                )
                .options(
                    selectinload(
                        ClinicalTrial.sites
                    )
                )
                .order_by(
                    ClinicalTrial.id
                )
                .offset(
                    offset
                )
                .limit(
                    page_size
                )
            ).all()
        )

        records = [
            trial_record(
                trial,
                list(trial.sites),
            )
            for trial in trials
        ]

    latency_ms = (
        perf_counter()
        - started_at
    ) * 1000

    return {
        "version": "optimized",
        "page": page,
        "page_size": page_size,
        "record_count": len(records),
        "query_count": counter["count"],
        "latency_ms": round(
            latency_ms,
            3,
        ),
        "records": records,
    }