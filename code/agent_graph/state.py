from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared memory passed between every graph node."""

    # Required assignment inputs
    title: str
    content: str
    email: str
    strict: bool
    task: str
    llm: Any

    # Agent outputs
    planner_proposal: dict[str, Any]
    reviewer_feedback: dict[str, Any]

    # Loop control
    turn_count: int
    turn_ceiling: int

    # Validation and completion state
    validation_error: str
    status: str
    completed: bool
    abandoned: bool

    # Used to demonstrate the correction loop
    force_reviewer_issue: bool

    # Machine-readable execution evidence
    trace: list[dict[str, Any]]


def initialize_state(
    *,
    title: str,
    content: str,
    email: str,
    task: str,
    llm: Any,
    strict: bool = True,
    turn_ceiling: int = 2,
    force_reviewer_issue: bool = False
) -> AgentState:
    """Create a complete initial state for one graph run."""

    if turn_ceiling < 1:
        raise ValueError(
            "turn_ceiling must be at least 1."
        )

    return AgentState(
        title=title.strip(),
        content=content.strip(),
        email=email.strip(),
        strict=strict,
        task=task.strip(),
        llm=llm,
        planner_proposal={},
        reviewer_feedback={},
        turn_count=0,
        turn_ceiling=turn_ceiling,
        validation_error="",
        status="not_started",
        completed=False,
        abandoned=False,
        force_reviewer_issue=force_reviewer_issue,
        trace=[]
    )