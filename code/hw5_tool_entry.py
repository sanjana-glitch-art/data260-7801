from __future__ import annotations

import json
from typing import Any

from code.hw5_domain_tools import (
    search_trials_operation,
    trial_details_operation,
    trial_phase_summary_operation,
)


TOOL_NAMES = (
    "search_trials",
    "trial_details",
    "trial_phase_summary",
)


def error_envelope(
    message: str,
) -> dict[str, Any]:
    """Create a standard error response."""

    return {
        "ok": False,
        "data": None,
        "error": message,
    }


def serialize_result(
    result: dict[str, Any],
) -> str:
    """Convert a tool response to JSON."""

    return json.dumps(
        result,
        ensure_ascii=False,
        default=str,
    )


def execute_tool(
    name: str,
    inputs: dict[str, Any] | None,
) -> str:
    """Execute a domain tool and return a JSON string."""

    if not isinstance(name, str):
        return serialize_result(
            error_envelope(
                "Tool name must be a string."
            )
        )

    if inputs is None:
        inputs = {}

    if not isinstance(inputs, dict):
        return serialize_result(
            error_envelope(
                "Tool inputs must be a JSON object."
            )
        )

    tool_name = name.strip()

    if tool_name not in TOOL_NAMES:
        return serialize_result(
            error_envelope(
                f"Unknown tool: {tool_name}"
            )
        )

    try:
        if tool_name == "search_trials":
            query = inputs.get(
                "query",
                "",
            )

            raw_limit = inputs.get(
                "limit",
                5,
            )

            try:
                limit = int(
                    raw_limit
                )
            except (
                TypeError,
                ValueError,
            ):
                return serialize_result(
                    error_envelope(
                        "limit must be a positive integer."
                    )
                )

            result, _metadata = (
                search_trials_operation(
                    query=str(query),
                    limit=limit,
                )
            )

            return serialize_result(
                result
            )

        if tool_name == "trial_details":
            include_email = bool(
                inputs.get(
                    "include_submitter_email",
                    False,
                )
            )

            if include_email:
                return serialize_result({
                    "ok": False,
                    "data": None,
                    "error": (
                        "Safety rule blocked disclosure "
                        "of submitter contact information."
                    ),
                })

            raw_trial_id = inputs.get(
                "trial_id"
            )

            try:
                trial_id = int(
                    raw_trial_id
                )
            except (
                TypeError,
                ValueError,
            ):
                return serialize_result(
                    error_envelope(
                        "trial_id must be a "
                        "positive integer."
                    )
                )

            result, _metadata = (
                trial_details_operation(
                    trial_id=trial_id
                )
            )

            if (
                result.get("ok")
                and isinstance(
                    result.get("data"),
                    dict,
                )
            ):
                safe_data = dict(
                    result["data"]
                )

                safe_data.pop(
                    "submitter_email",
                    None,
                )

                result = {
                    "ok": True,
                    "data": safe_data,
                    "error": None,
                }

            return serialize_result(
                result
            )

        if tool_name == "trial_phase_summary":
            raw_sponsor_id = inputs.get(
                "sponsor_id"
            )

            if (
                raw_sponsor_id is None
                or raw_sponsor_id == ""
            ):
                sponsor_id = None
            else:
                try:
                    sponsor_id = int(
                        raw_sponsor_id
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    return serialize_result(
                        error_envelope(
                            "sponsor_id must be a "
                            "positive integer."
                        )
                    )

            result = (
                trial_phase_summary_operation(
                    sponsor_id=sponsor_id
                )
            )

            if (
                result.get("ok")
                and isinstance(
                    result.get("data"),
                    dict,
                )
            ):
                summary_data = dict(
                    result["data"]
                )

                phase_rows = (
                    summary_data.get("phases")
                    or summary_data.get(
                        "phase_counts"
                    )
                    or summary_data.get(
                        "summary"
                    )
                    or []
                )

                if (
                    "total_trials"
                    not in summary_data
                ):
                    total_trials = 0

                    for row in phase_rows:
                        if not isinstance(
                            row,
                            dict,
                        ):
                            continue

                        raw_count = row.get(
                            "trial_count",
                            row.get(
                                "count",
                                0,
                            ),
                        )

                        try:
                            total_trials += int(
                                raw_count
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            continue

                    summary_data[
                        "total_trials"
                    ] = total_trials

                result = {
                    "ok": True,
                    "data": summary_data,
                    "error": None,
                }

            return serialize_result(
                result
            )

        return serialize_result(
            error_envelope(
                f"Unknown tool: {tool_name}"
            )
        )

    except Exception as error:
        return serialize_result(
            error_envelope(
                "Tool execution failed safely: "
                f"{type(error).__name__}."
            )
        )