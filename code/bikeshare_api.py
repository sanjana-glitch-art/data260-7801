from __future__ import annotations

import re
import tempfile
from code.hw7_bikeshare_agent import (
    run_bikeshare_agent,
)
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from starlette.concurrency import (
    run_in_threadpool,
)

router = APIRouter(
    prefix="/api/bikeshare",
    tags=["Homework 7 Bike Share"],
)

MAXIMUM_CSV_BYTES = (
    25 * 1024 * 1024
)

DEFAULT_PRICING_URL = (
    "https://citibikenyc.com/pricing"
)


def safe_scenario_label(
    value: str,
) -> str:
    """Create a filesystem-safe scenario label."""

    cleaned = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip(),
    ).strip("_")

    return (
        cleaned[:80]
        or "bikeshare_ui_run"
    )


@router.get("/configuration")
def read_bikeshare_configuration() -> dict[str, Any]:
    """Return UI defaults and upload constraints."""

    return {
        "default_pricing_url": (
            DEFAULT_PRICING_URL
        ),
        "maximum_csv_bytes": (
            MAXIMUM_CSV_BYTES
        ),
        "required_columns": [
            "ride_id",
            "duration_minutes",
            "week_number",
            "analysis_target",
        ],
        "decisions": [
            "Buy Monthly Membership",
            "Pay Per Ride/Minute",
        ],
    }


@router.post("/analyze")
async def analyze_bikeshare_csv(
    csv_file: Annotated[
        UploadFile,
        File(...),
    ],
    pricing_url: Annotated[
        str,
        Form(...),
    ],
    scenario_label: Annotated[
        str,
        Form(),
    ] = "bikeshare_ui_run",
) -> dict[str, Any]:
    """Run the Bike Share MRKL workflow on an uploaded CSV."""

    filename = (
        csv_file.filename
        or "uploaded.csv"
    )

    if not filename.casefold().endswith(
        ".csv"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "The uploaded file must have "
                "a .csv extension."
            ),
        )

    cleaned_url = pricing_url.strip()

    if not cleaned_url:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Pricing URL is required."
            ),
        )

    content = await csv_file.read(
        MAXIMUM_CSV_BYTES + 1
    )

    await csv_file.close()

    if not content:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "The uploaded CSV is empty."
            ),
        )

    if len(content) > MAXIMUM_CSV_BYTES:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "The uploaded CSV exceeds "
                "the 25 MB limit."
            ),
        )

    label = safe_scenario_label(
        scenario_label
    )

    with tempfile.TemporaryDirectory(
        prefix="hw7_bikeshare_upload_"
    ) as temporary_directory:
        temporary_path = (
            Path(temporary_directory)
            / "uploaded.csv"
        )

        temporary_path.write_bytes(
            content
        )

        result = await run_in_threadpool(
            run_bikeshare_agent,
            temporary_path,
            cleaned_url,
            scenario_label=label,
        )

    if (
        result.get("stop_reason")
        != "success"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "message": (
                    "Bike Share analysis "
                    "did not complete."
                ),
                "stop_reason": result.get(
                    "stop_reason"
                ),
                "error": result.get(
                    "error"
                ),
                "timeline": result.get(
                    "timeline",
                    [],
                ),
            },
        )

    return {
        "success": True,
        "data": result,
        "error": None,
    }