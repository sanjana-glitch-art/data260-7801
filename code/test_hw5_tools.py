from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from code.hw5_tool_entry import execute_tool
from pathlib import Path

from code.hw5_agent import (
    MockModel,
    run_agent,
)

TestFunction = Callable[[], None]


def parsed_result(
    name: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Execute and parse one tool response."""

    result = execute_tool(
        name,
        inputs,
    )

    parsed = json.loads(result)

    assert set(parsed) == {
        "ok",
        "data",
        "error",
    }

    return parsed


def test_search_valid() -> None:
    result = parsed_result(
        "search_trials",
        {
            "query": "Sleep",
            "limit": 3,
        },
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert isinstance(
        result["data"]["trials"],
        list,
    )


def test_search_invalid() -> None:
    result = parsed_result(
        "search_trials",
        {
            "query": "",
            "limit": 3,
        },
    )

    assert result["ok"] is False
    assert result["data"] is None
    assert (
        result["error"]
        == "query must not be empty."
    )


def test_details_valid() -> None:
    result = parsed_result(
        "trial_details",
        {
            "trial_id": 1,
        },
    )

    assert result["ok"] is True
    assert result["data"]["id"] == 1

    # Privacy-safe result must omit email.
    assert (
        "submitter_email"
        not in result["data"]
    )


def test_details_invalid() -> None:
    result = parsed_result(
        "trial_details",
        {
            "trial_id": 0,
        },
    )

    assert result["ok"] is False
    assert (
        result["error"]
        == (
            "trial_id must be a "
            "positive integer."
        )
    )


def test_summary_valid() -> None:
    result = parsed_result(
        "trial_phase_summary",
        {},
    )

    assert result["ok"] is True
    assert (
        result["data"]["total_trials"]
        >= 1
    )


def test_summary_invalid() -> None:
    result = parsed_result(
        "trial_phase_summary",
        {
            "sponsor_id": 0,
        },
    )

    assert result["ok"] is False
    assert (
        result["error"]
        == (
            "sponsor_id must be a "
            "positive integer."
        )
    )


def test_safety_rule_blocks_email() -> None:
    result = parsed_result(
        "trial_details",
        {
            "trial_id": 1,
            "include_submitter_email": True,
        },
    )

    assert result["ok"] is False
    assert "Safety rule blocked" in (
        result["error"]
    )


def test_unknown_tool() -> None:
    result = parsed_result(
        "delete_all_trials",
        {},
    )

    assert result["ok"] is False
    assert "Unknown tool" in (
        result["error"]
    )


def main() -> None:
    tests: list[
        tuple[str, TestFunction]
    ] = [
        (
            "valid search",
            test_search_valid,
        ),
        (
            "invalid search",
            test_search_invalid,
        ),
        (
            "valid details",
            test_details_valid,
        ),
        (
            "invalid details",
            test_details_invalid,
        ),
        (
            "valid aggregate",
            test_summary_valid,
        ),
        (
            "invalid aggregate",
            test_summary_invalid,
        ),
        (
            "safety-rule block",
            test_safety_rule_blocks_email,
        ),
        (
            "unknown-tool handling",
            test_unknown_tool,
        ),
                (
            "agent max-steps ceiling",
            test_agent_stops_at_max_steps,
        ),
    ]

    passed = 0

    print(
        "HW5 Offline Tool Tests"
    )
    print(
        "Student: Sanjana Thummalapalli"
    )

    for name, test_function in tests:
        try:
            test_function()
        except Exception as error:
            print(
                (
                    f"FAIL | {name} | "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )
        else:
            passed += 1
            print(
                f"PASS | {name}"
            )

    total = len(tests)

    print(
        f"\nFinal summary: {passed}/{total} passed"
    )

    if passed != total:
        raise SystemExit(1)

def test_agent_stops_at_max_steps() -> None:
    result = run_agent(
        "Keep searching forever.",
        model=MockModel(),
        max_steps=2,
        log_path=Path(
            "reports/hw05/raw/"
            "mock_agent_runs.jsonl"
        ),
        run_label="offline-max-steps",
    )

    assert result["step_count"] == 2
    assert (
        result["tool_call_count"]
        == 2
    )
    assert (
        result["stop_reason"]
        == "max_steps"
    )

if __name__ == "__main__":
    main()