from __future__ import annotations

from typing import Literal

from .state import AgentState


RouteAfterSupervisor = Literal[
    "planner",
    "end"
]

RouteAfterPlanner = Literal[
    "reviewer",
    "supervisor",
    "end"
]

RouteAfterReviewer = Literal[
    "supervisor",
    "end"
]


def route_after_supervisor(
    state: AgentState
) -> RouteAfterSupervisor:
    """Send an allowed attempt to Planner."""

    if state.get("abandoned", False):
        return "end"

    return "planner"


def route_after_planner(
    state: AgentState
) -> RouteAfterPlanner:
    """Review valid output or retry invalid output."""

    if state.get("abandoned", False):
        return "end"

    if state.get("planner_proposal"):
        return "reviewer"

    return "supervisor"


def route_after_reviewer(
    state: AgentState
) -> RouteAfterReviewer:
    """Finish approved output or request another attempt."""

    if state.get("completed", False):
        return "end"

    if state.get("abandoned", False):
        return "end"

    return "supervisor"