from __future__ import annotations

import json
from typing import Any

from langgraph.graph import END, StateGraph

from .nodes import (
    planner_node,
    reviewer_node,
    supervisor_node
)
from .router import (
    route_after_planner,
    route_after_reviewer,
    route_after_supervisor
)
from .state import AgentState


def build_workflow():
    """Build and compile the stateful agent graph."""

    workflow = StateGraph(
        AgentState
    )

    workflow.add_node(
        "supervisor",
        supervisor_node
    )

    workflow.add_node(
        "planner",
        planner_node
    )

    workflow.add_node(
        "reviewer",
        reviewer_node
    )

    workflow.set_entry_point(
        "supervisor"
    )

    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "planner": "planner",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "reviewer": "reviewer",
            "supervisor": "supervisor",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "supervisor": "supervisor",
            "end": END
        }
    )

    return workflow.compile()


def printable_update(
    update: dict[str, Any]
) -> dict[str, Any]:
    """Remove the model-client object from printed state."""

    return {
        key: value
        for key, value in update.items()
        if key != "llm"
    }


def run_workflow(
    initial_state: AgentState,
    *,
    show_stream: bool = True
) -> AgentState:
    """Run the graph with stream() and return final state."""

    graph = build_workflow()
    final_state = AgentState(**initial_state)

    for event in graph.stream(
        initial_state,
        config={
            "recursion_limit": 100
        },
        stream_mode="updates"
    ):
        for node_name, update in event.items():
            final_state.update(update)

            if show_stream:
                print(
                    f"\n--- STREAM UPDATE: "
                    f"{node_name} ---"
                )

                print(
                    json.dumps(
                        printable_update(update),
                        indent=2,
                        default=str
                    )
                )

    return final_state