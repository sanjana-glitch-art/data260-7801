from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from mcp.server.fastmcp import FastMCP

from code.hw5_domain_tools import (
    search_trials_operation,
    trial_details_operation,
    trial_phase_summary_operation,
)


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format=(
        "%(asctime)s %(levelname)s "
        "%(name)s: %(message)s"
    ),
)

logger = logging.getLogger(
    "clinical_trials_mcp"
)

mcp = FastMCP(
    "s7801_clinical_trials"
)


@mcp.tool()
def search_trials(
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Search trials by title, code, or sponsor."""

    result, _metadata = (
        search_trials_operation(
            query=query,
            limit=limit,
        )
    )

    return result


@mcp.tool()
def trial_details(
    trial_id: int,
) -> dict[str, Any]:
    """Return details for one clinical trial."""

    result, _metadata = (
        trial_details_operation(
            trial_id=trial_id,
        )
    )

    return result


@mcp.tool()
def trial_phase_summary(
    sponsor_id: int | None = None,
) -> dict[str, Any]:
    """Return trial counts grouped by phase."""

    result, _metadata = (
        trial_phase_summary_operation(
            sponsor_id=sponsor_id,
        )
    )

    return result


if __name__ == "__main__":
    logger.info(
        "Starting clinical-trial MCP server "
        "over STDIO."
    )

    mcp.run(
        transport="stdio"
    )