from __future__ import annotations

import re
import time
from code.hw7_bikeshare_tools import (
    calculator,
    configure_csv,
    csv_sql,
    fetch_policy_text,
    policy_retriever,
    save_policy_snapshot,
)
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class BikeShareState(TypedDict):
    """State passed between the MRKL graph nodes."""

    csv_path: str
    pricing_url: str
    scenario_label: str
    timeline: list[dict[str, Any]]
    dataset_row_count: int
    ride_count: int
    average_duration_minutes: float
    weekly_rows: list[dict[str, Any]]
    policy_passages: list[dict[str, Any]]
    policy_text: str
    policy_source: str
    snapshot: dict[str, str]
    pricing: dict[str, float]
    pay_per_use_cost: float
    membership_cost: float
    break_even_rides: float
    decision: str
    justification: str
    assumptions: list[str]
    citations: list[dict[str, Any]]
    step_count: int
    started_at: float
    total_time_ms: float
    stop_reason: str
    error: str | None


def tool_event(
    *,
    step: int,
    tool_name: str,
    inputs: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    """Create a visible tool-call timeline event."""

    return {
        "step": step,
        "tool": tool_name,
        "inputs": inputs,
        "observation": observation,
    }


def require_success(
    result: dict[str, Any],
    tool_name: str,
) -> dict[str, Any]:
    """Return tool data or raise a concise error."""

    if not result.get("success"):
        raise RuntimeError(
            f"{tool_name} failed: {result.get('error', 'unknown error')}"
        )

    data = result.get("data")

    if not isinstance(
        data,
        dict,
    ):
        raise TypeError(f"{tool_name} returned invalid data.")

    return data


def number_from_patterns(
    text: str,
    patterns: tuple[str, ...],
    label: str,
) -> float:
    """Extract one numeric pricing value."""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return float(match.group(1))

    raise ValueError(f"Could not determine {label} from the pricing policy.")


def parse_pricing_policy(
    policy_text: str,
) -> dict[str, float]:
    """Extract pricing values from retrieved policy text."""

    normalized = " ".join(policy_text.split())

    pay_per_ride = number_from_patterns(
        normalized,
        (
            (
                r"single\s+ride"
                r".{0,100}?"
                r"\$(\d+(?:\.\d+)?)"
            ),
            (
                r"pay\s+per\s+ride"
                r".{0,100}?"
                r"\$(\d+(?:\.\d+)?)"
            ),
            (
                r"PAY_PER_RIDE_PRICE_USD"
                r"\s*=\s*"
                r"(\d+(?:\.\d+)?)"
            ),
        ),
        "pay-per-ride price",
    )

    monthly_membership = number_from_patterns(
        normalized,
        (
            (
                r"monthly\s+membership"
                r".{0,100}?"
                r"\$(\d+(?:\.\d+)?)"
            ),
            (
                r"membership"
                r".{0,50}?"
                r"\$(\d+(?:\.\d+)?)"
                r".{0,40}?"
                r"(?:month|monthly)"
            ),
            (
                r"MONTHLY_MEMBERSHIP_PRICE_USD"
                r"\s*=\s*"
                r"(\d+(?:\.\d+)?)"
            ),
        ),
        "monthly membership price",
    )

    overage_per_minute = number_from_patterns(
        normalized,
        (
            (
                r"\$(\d+(?:\.\d+)?)"
                r"\s*(?:per|/)\s*minute"
            ),
            (
                r"OVERAGE_PER_MINUTE_USD"
                r"\s*=\s*"
                r"(\d+(?:\.\d+)?)"
            ),
        ),
        "overage price per minute",
    )

    pay_included_minutes = number_from_patterns(
        normalized,
        (
            (
                r"(?:single\s+ride|pay\s+per\s+ride)"
                r".{0,150}?"
                r"(?:first|includes?)"
                r".{0,20}?"
                r"(\d+(?:\.\d+)?)"
                r"\s*minutes?"
            ),
            (
                r"PAY_INCLUDED_MINUTES"
                r"\s*=\s*"
                r"(\d+(?:\.\d+)?)"
            ),
        ),
        "pay-per-use included minutes",
    )

    membership_included_minutes = number_from_patterns(
        normalized,
        (
            (
                r"(?:monthly\s+membership|membership)"
                r".{0,150}?"
                r"(?:up\s+to|includes?)"
                r".{0,20}?"
                r"(\d+(?:\.\d+)?)"
                r"\s*minutes?"
            ),
            (
                r"MEMBERSHIP_INCLUDED_MINUTES"
                r"\s*=\s*"
                r"(\d+(?:\.\d+)?)"
            ),
        ),
        "membership included minutes",
    )

    return {
        "pay_per_ride_price": (pay_per_ride),
        "monthly_membership_price": (monthly_membership),
        "overage_per_minute": (overage_per_minute),
        "pay_included_minutes": (pay_included_minutes),
        "membership_included_minutes": (membership_included_minutes),
    }


def usage_node(
    state: BikeShareState,
) -> dict[str, Any]:
    """Use csv_sql to calculate usage statistics."""

    timeline = list(state["timeline"])

    configure_csv(state["csv_path"])

    summary_sql = """
        SELECT
            COUNT(*) AS dataset_row_count,
            SUM(
                CASE
                    WHEN analysis_target = true
                    THEN 1
                    ELSE 0
                END
            ) AS ride_count,
            ROUND(
                AVG(
                    CASE
                        WHEN analysis_target = true
                        THEN duration_minutes
                    END
                ),
                2
            ) AS average_duration_minutes
        FROM trips
    """

    summary_result = csv_sql(summary_sql)

    summary_data = require_success(
        summary_result,
        "csv_sql",
    )

    timeline.append(
        tool_event(
            step=1,
            tool_name="csv_sql",
            inputs={
                "sql": "Monthly usage summary",
            },
            observation=summary_data,
        )
    )

    rows = summary_data["rows"]

    if not rows:
        raise ValueError("CSV summary returned no rows.")

    summary = rows[0]

    weekly_sql = """
        SELECT
            week_number,
            COUNT(*) AS ride_count,
            ROUND(
                AVG(duration_minutes),
                2
            ) AS average_duration_minutes
        FROM trips
        WHERE analysis_target = true
        GROUP BY week_number
        ORDER BY week_number
    """

    weekly_result = csv_sql(weekly_sql)

    weekly_data = require_success(
        weekly_result,
        "csv_sql",
    )

    timeline.append(
        tool_event(
            step=2,
            tool_name="csv_sql",
            inputs={
                "sql": "Weekly usage breakdown",
            },
            observation=weekly_data,
        )
    )

    return {
        "timeline": timeline,
        "dataset_row_count": int(summary["dataset_row_count"]),
        "ride_count": int(summary["ride_count"] or 0),
        "average_duration_minutes": float(summary["average_duration_minutes"] or 0),
        "weekly_rows": (weekly_data["rows"]),
        "step_count": 2,
    }


def policy_node(
    state: BikeShareState,
) -> dict[str, Any]:
    """Retrieve policy passages and save exact evidence."""

    timeline = list(state["timeline"])

    query = (
        "single ride price monthly membership price "
        "included ride minutes overage per-minute fee"
    )

    result = policy_retriever(
        url=state["pricing_url"],
        query=query,
        k=8,
    )

    data = require_success(
        result,
        "policy_retriever",
    )

    passages = data.get("passages")

    if not isinstance(
        passages,
        list,
    ):
        raise TypeError("Policy passages must be a list.")

    timeline.append(
        tool_event(
            step=3,
            tool_name="policy_retriever",
            inputs={
                "url": state["pricing_url"],
                "query": query,
                "k": 8,
            },
            observation={
                "passage_count": len(passages),
                "passages": passages,
            },
        )
    )

    page_text, final_url = fetch_policy_text(state["pricing_url"])

    snapshot = save_policy_snapshot(
        page_text,
        final_url,
        label=state["scenario_label"],
    )

    pricing = parse_pricing_policy(page_text)

    return {
        "timeline": timeline,
        "policy_passages": passages,
        "policy_text": page_text,
        "policy_source": final_url,
        "snapshot": snapshot,
        "pricing": pricing,
        "step_count": 3,
    }


def cost_node(
    state: BikeShareState,
) -> dict[str, Any]:
    """Calculate both pricing alternatives."""

    timeline = list(state["timeline"])

    pricing = state["pricing"]

    configure_csv(state["csv_path"])

    minutes_sql = f"""
        SELECT
            SUM(
                CASE
                    WHEN analysis_target = true
                    THEN GREATEST(
                        duration_minutes
                        - {pricing["pay_included_minutes"]},
                        0
                    )
                    ELSE 0
                END
            ) AS pay_overage_minutes,
            SUM(
                CASE
                    WHEN analysis_target = true
                    THEN GREATEST(
                        duration_minutes
                        - {pricing["membership_included_minutes"]},
                        0
                    )
                    ELSE 0
                END
            ) AS membership_overage_minutes
        FROM trips
    """

    minutes_result = csv_sql(minutes_sql)

    minutes_data = require_success(
        minutes_result,
        "csv_sql",
    )

    minutes = minutes_data["rows"][0]

    pay_overage_minutes = float(minutes["pay_overage_minutes"] or 0)

    membership_overage_minutes = float(minutes["membership_overage_minutes"] or 0)

    timeline.append(
        tool_event(
            step=4,
            tool_name="csv_sql",
            inputs={
                "sql": ("Calculate overage minutes"),
            },
            observation=minutes_data,
        )
    )

    pay_expression = (
        f"({state['ride_count']} * "
        f"{pricing['pay_per_ride_price']}) "
        f"+ ({pay_overage_minutes} * "
        f"{pricing['overage_per_minute']})"
    )

    pay_result = calculator(
        expression=pay_expression,
        units="USD",
    )

    pay_data = require_success(
        pay_result,
        "calculator",
    )

    timeline.append(
        tool_event(
            step=5,
            tool_name="calculator",
            inputs={
                "expression": pay_expression,
                "units": "USD",
            },
            observation=pay_data,
        )
    )

    membership_expression = (
        f"{pricing['monthly_membership_price']} "
        f"+ ({membership_overage_minutes} * "
        f"{pricing['overage_per_minute']})"
    )

    membership_result = calculator(
        expression=membership_expression,
        units="USD",
    )

    membership_data = require_success(
        membership_result,
        "calculator",
    )

    timeline.append(
        tool_event(
            step=6,
            tool_name="calculator",
            inputs={
                "expression": (membership_expression),
                "units": "USD",
            },
            observation=membership_data,
        )
    )

    break_even_expression = (
        f"{pricing['monthly_membership_price']} / {pricing['pay_per_ride_price']}"
    )

    break_even_result = calculator(
        expression=break_even_expression,
        units="rides",
    )

    break_even_data = require_success(
        break_even_result,
        "calculator",
    )

    timeline.append(
        tool_event(
            step=7,
            tool_name="calculator",
            inputs={
                "expression": (break_even_expression),
                "units": "rides",
            },
            observation=break_even_data,
        )
    )

    return {
        "timeline": timeline,
        "pay_per_use_cost": round(
            float(pay_data["value"]),
            2,
        ),
        "membership_cost": round(
            float(membership_data["value"]),
            2,
        ),
        "break_even_rides": round(
            float(break_even_data["value"]),
            2,
        ),
        "step_count": 7,
    }


def finalize_node(
    state: BikeShareState,
) -> dict[str, Any]:
    """Create the exact decision and concise rationale."""

    if state["membership_cost"] < state["pay_per_use_cost"]:
        decision = "Buy Monthly Membership"
    else:
        decision = "Pay Per Ride/Minute"

    savings = round(
        abs(state["pay_per_use_cost"] - state["membership_cost"]),
        2,
    )

    justification = (
        f"The uploaded dataset contains "
        f"{state['dataset_row_count']} rows, with "
        f"{state['ride_count']} rides included in this "
        f"rider scenario. Pay-per-use is estimated at "
        f"${state['pay_per_use_cost']:.2f}, while monthly "
        f"membership plus residual charges is estimated "
        f"at ${state['membership_cost']:.2f}. The "
        f"estimated break-even point is "
        f"{state['break_even_rides']:.2f} rides, compared "
        f"with {state['ride_count']} actual rides. "
        f"Therefore, the recommendation is "
        f"{decision}, with estimated savings of "
        f"${savings:.2f}. Pricing evidence was retrieved "
        f"from {state['policy_source']}."
    )

    assumptions = [
        (
            "Rows with analysis_target=true represent "
            "the rider being evaluated; remaining rows "
            "provide the required dataset context."
        ),
        ("Each target row represents one completed ride during the analyzed month."),
        (
            "Taxes, promotions, credits, e-bike fees, "
            "and station availability are excluded unless "
            "explicitly stated in the retrieved policy."
        ),
    ]

    citations = [
        {
            "source": passage.get("source"),
            "text": passage.get("text"),
            "score": passage.get("score"),
        }
        for passage in (state["policy_passages"][:3])
    ]

    elapsed_ms = round(
        (time.perf_counter() - state["started_at"]) * 1000,
        3,
    )

    return {
        "decision": decision,
        "justification": justification,
        "assumptions": assumptions,
        "citations": citations,
        "total_time_ms": elapsed_ms,
        "stop_reason": "success",
    }


def build_bikeshare_graph() -> Any:
    """Compile the Bike Share MRKL workflow."""

    graph = StateGraph(BikeShareState)

    graph.add_node(
        "analyze_usage",
        usage_node,
    )

    graph.add_node(
        "retrieve_policy",
        policy_node,
    )

    graph.add_node(
        "calculate_costs",
        cost_node,
    )

    graph.add_node(
        "finalize",
        finalize_node,
    )

    graph.set_entry_point("analyze_usage")

    graph.add_edge(
        "analyze_usage",
        "retrieve_policy",
    )

    graph.add_edge(
        "retrieve_policy",
        "calculate_costs",
    )

    graph.add_edge(
        "calculate_costs",
        "finalize",
    )

    graph.add_edge(
        "finalize",
        END,
    )

    return graph.compile()


BIKESHARE_GRAPH = build_bikeshare_graph()


def run_bikeshare_agent(
    csv_path: str | Path,
    pricing_url: str,
    *,
    scenario_label: str,
) -> dict[str, Any]:
    """Run the framework-based Bike Share MRKL agent."""

    started_at = time.perf_counter()

    initial_state: BikeShareState = {
        "csv_path": str(Path(csv_path).resolve()),
        "pricing_url": pricing_url,
        "scenario_label": (scenario_label),
        "timeline": [],
        "dataset_row_count": 0,
        "ride_count": 0,
        "average_duration_minutes": 0.0,
        "weekly_rows": [],
        "policy_passages": [],
        "policy_text": "",
        "policy_source": "",
        "snapshot": {},
        "pricing": {},
        "pay_per_use_cost": 0.0,
        "membership_cost": 0.0,
        "break_even_rides": 0.0,
        "decision": "",
        "justification": "",
        "assumptions": [],
        "citations": [],
        "step_count": 0,
        "started_at": started_at,
        "total_time_ms": 0.0,
        "stop_reason": "",
        "error": None,
    }

    try:
        final_state = BIKESHARE_GRAPH.invoke(initial_state)
    except (
        FileNotFoundError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        return {
            **initial_state,
            "started_at": None,
            "stop_reason": "error",
            "error": (f"{type(error).__name__}: {error}"),
            "total_time_ms": round(
                (time.perf_counter() - started_at) * 1000,
                3,
            ),
        }

    final_state["started_at"] = None

    return dict(final_state)
