from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from .schemas import (
    PlannerProposal,
    ReviewerFeedback
)
from .state import AgentState


def _append_trace(
    state: AgentState,
    event: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return a new trace containing one additional event."""

    return [
        *state.get("trace", []),
        event
    ]


def supervisor_node(
    state: AgentState
) -> dict[str, Any]:
    """Increment the number of Planner attempts."""

    next_turn = state.get(
        "turn_count",
        0
    ) + 1

    turn_ceiling = state.get(
        "turn_ceiling",
        2
    )

    print(
        "\n--- NODE: Supervisor ---"
    )

    if next_turn > turn_ceiling:
        print(
            "Turn ceiling exceeded."
        )

        return {
            "status": "abandoned",
            "completed": False,
            "abandoned": True,
            "validation_error": (
                "The configured turn ceiling was exceeded."
            )
        }

    print(
        f"Planner attempt: {next_turn}/{turn_ceiling}"
    )

    return {
        "turn_count": next_turn,
        "status": "planning"
    }


def planner_node(
    state: AgentState
) -> dict[str, Any]:
    """Generate and validate a three-tag proposal."""

    print(
        "\n--- NODE: Planner ---"
    )

    llm = state["llm"]

    correction_context: list[str] = []

    validation_error = state.get(
        "validation_error",
        ""
    ).strip()

    if validation_error:
        correction_context.append(
            "A previous response failed validation:\n"
            f"{validation_error}"
        )

    reviewer_feedback = state.get(
        "reviewer_feedback",
        {}
    )

    reviewer_issues = reviewer_feedback.get(
        "issues",
        []
    )

    if reviewer_issues:
        correction_context.append(
            "Reviewer issues from the previous attempt:\n"
            + "\n".join(
                f"- {issue}"
                for issue in reviewer_issues
            )
        )

    correction_text = (
        "\n\n".join(correction_context)
        if correction_context
        else "There is no previous correction feedback."
    )

    system_prompt = (
        "You are the Planner in a clinical-trial metadata "
        "workflow. Produce a concise structured proposal. "
        "Return exactly three distinct topical tags. Every tag "
        "must contain between 3 and 30 characters. Return one "
        "summary containing no more than 25 whitespace-separated "
        "words. The tags should be reasonably relevant to the "
        "title and content, but they do not need to come from a "
        "standard controlled vocabulary. Do not add fields "
        "outside the required JSON schema."
    )

    user_prompt = (
        f"Task: {state.get('task', '')}\n"
        f"Title: {state.get('title', '')}\n"
        f"Content: {state.get('content', '')}\n"
        f"Submitter email: {state.get('email', '')}\n"
        f"Strict mode: {state.get('strict', True)}\n\n"
        f"Correction context:\n{correction_text}"
    )

    started = perf_counter()

    try:
        result = llm.complete(
            [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format=(
                PlannerProposal.model_json_schema()
            )
        )

        latency_ms = (
            perf_counter() - started
        ) * 1000

        proposal_model = (
            PlannerProposal.model_validate_json(
                result.content
            )
        )

        proposal = proposal_model.model_dump()

        print(
            json.dumps(
                proposal,
                indent=2
            )
        )

        trace = _append_trace(
            state,
            {
                "node": "planner",
                "turn": state.get(
                    "turn_count",
                    0
                ),
                "valid": True,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "input_tokens": (
                    result.input_tokens
                ),
                "output_tokens": (
                    result.output_tokens
                ),
                "total_tokens": (
                    result.total_tokens
                )
            }
        )

        return {
            "planner_proposal": proposal,
            "reviewer_feedback": {},
            "validation_error": "",
            "status": "reviewing",
            "trace": trace
        }

    except (
        ValidationError,
        json.JSONDecodeError,
        ValueError
    ) as error:
        latency_ms = (
            perf_counter() - started
        ) * 1000

        error_text = str(error)

        print(
            "Planner validation failed:"
        )

        print(
            error_text
        )

        reached_ceiling = (
            state.get("turn_count", 0)
            >= state.get("turn_ceiling", 2)
        )

        trace = _append_trace(
            state,
            {
                "node": "planner",
                "turn": state.get(
                    "turn_count",
                    0
                ),
                "valid": False,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "error": error_text
            }
        )

        return {
            "planner_proposal": {},
            "validation_error": error_text,
            "status": (
                "abandoned"
                if reached_ceiling
                else "retry_planner"
            ),
            "completed": False,
            "abandoned": reached_ceiling,
            "trace": trace
        }

    except Exception as error:
        latency_ms = (
            perf_counter() - started
        ) * 1000

        error_text = (
            f"{type(error).__name__}: {error}"
        )

        print(
            "Planner call failed:"
        )

        print(
            error_text
        )

        reached_ceiling = (
            state.get("turn_count", 0)
            >= state.get("turn_ceiling", 2)
        )

        trace = _append_trace(
            state,
            {
                "node": "planner",
                "turn": state.get(
                    "turn_count",
                    0
                ),
                "valid": False,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "error": error_text
            }
        )

        return {
            "planner_proposal": {},
            "validation_error": error_text,
            "status": (
                "abandoned"
                if reached_ceiling
                else "retry_planner"
            ),
            "completed": False,
            "abandoned": reached_ceiling,
            "trace": trace
        }


def reviewer_node(
    state: AgentState
) -> dict[str, Any]:
    """Review a valid proposal for relevance and accuracy."""

    print(
        "\n--- NODE: Reviewer ---"
    )

    turn_count = state.get(
        "turn_count",
        0
    )

    turn_ceiling = state.get(
        "turn_ceiling",
        2
    )

    if state.get(
        "force_reviewer_issue",
        False
    ):
        forced_feedback = {
            "approved": False,
            "issues": [
                (
                    "Forced correction-loop test: revise "
                    "the proposal before approval."
                )
            ]
        }

        reached_ceiling = (
            turn_count >= turn_ceiling
        )

        print(
            json.dumps(
                forced_feedback,
                indent=2
            )
        )

        return {
            "reviewer_feedback": forced_feedback,
            "status": (
                "abandoned"
                if reached_ceiling
                else "revision_requested"
            ),
            "completed": False,
            "abandoned": reached_ceiling,
            "trace": _append_trace(
                state,
                {
                    "node": "reviewer",
                    "turn": turn_count,
                    "approved": False,
                    "forced_issue": True,
                    "latency_ms": 0.0
                }
            )
        }

    proposal = state.get(
        "planner_proposal",
        {}
    )

    summary = str(
        proposal.get(
            "summary",
            ""
        )
    )

    summary_word_count = len(
        summary.split()
    )

    system_prompt = (
        "You are the semantic Reviewer in a clinical-trial "
        "metadata workflow. The proposal has already passed "
        "deterministic Pydantic validation. Therefore, it "
        "already contains exactly three distinct tags, every "
        "tag is between 3 and 30 characters, and the summary "
        "contains no more than 25 whitespace-separated words. "
        "Do not reject the proposal for any of those validated "
        "conditions. Tags do not need to come from a standard "
        "controlled vocabulary. Review only whether the tags "
        "and summary are reasonably relevant to and supported "
        "by the supplied title and content. Minor wording or "
        "style preferences are not reasons for rejection. "
        "Return approved=true with an empty issues list when "
        "the proposal is factually supported and relevant. "
        "Return approved=false only for a clear factual or "
        "relevance problem, and provide specific actionable "
        "issues. Return only JSON matching the required schema."
    )

    user_prompt = (
        f"Title: {state.get('title', '')}\n"
        f"Content: {state.get('content', '')}\n"
        f"Strict mode: {state.get('strict', True)}\n"
        f"Deterministic summary word count: "
        f"{summary_word_count}\n"
        "Pydantic validation result: PASSED\n"
        "Planner proposal:\n"
        + json.dumps(
            proposal,
            indent=2
        )
    )

    llm = state["llm"]
    started = perf_counter()

    try:
        result = llm.complete(
            [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format=(
                ReviewerFeedback.model_json_schema()
            )
        )

        latency_ms = (
            perf_counter() - started
        ) * 1000

        feedback_model = (
            ReviewerFeedback.model_validate_json(
                result.content
            )
        )

        feedback = feedback_model.model_dump()

        if (
            not feedback["approved"]
            and not feedback["issues"]
        ):
            feedback["issues"] = [
                (
                    "Reviewer rejected the proposal without "
                    "providing an actionable reason."
                )
            ]

        if (
            feedback["approved"]
            and feedback["issues"]
        ):
            feedback["issues"] = []

        print(
            json.dumps(
                feedback,
                indent=2
            )
        )

        approved = feedback["approved"]

        reached_ceiling = (
            not approved
            and turn_count >= turn_ceiling
        )

        trace = _append_trace(
            state,
            {
                "node": "reviewer",
                "turn": turn_count,
                "approved": approved,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "input_tokens": (
                    result.input_tokens
                ),
                "output_tokens": (
                    result.output_tokens
                ),
                "total_tokens": (
                    result.total_tokens
                ),
                "summary_word_count": (
                    summary_word_count
                )
            }
        )

        return {
            "reviewer_feedback": feedback,
            "status": (
                "completed"
                if approved
                else (
                    "abandoned"
                    if reached_ceiling
                    else "revision_requested"
                )
            ),
            "completed": approved,
            "abandoned": reached_ceiling,
            "trace": trace
        }

    except (
        ValidationError,
        json.JSONDecodeError,
        ValueError
    ) as error:
        latency_ms = (
            perf_counter() - started
        ) * 1000

        error_text = str(error)

        print(
            "Reviewer validation failed:"
        )

        print(
            error_text
        )

        reached_ceiling = (
            turn_count >= turn_ceiling
        )

        feedback = {
            "approved": False,
            "issues": [
                (
                    "Reviewer output could not be validated: "
                    f"{error_text}"
                )
            ]
        }

        trace = _append_trace(
            state,
            {
                "node": "reviewer",
                "turn": turn_count,
                "approved": False,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "error": error_text,
                "summary_word_count": (
                    summary_word_count
                )
            }
        )

        return {
            "reviewer_feedback": feedback,
            "status": (
                "abandoned"
                if reached_ceiling
                else "revision_requested"
            ),
            "completed": False,
            "abandoned": reached_ceiling,
            "trace": trace
        }

    except Exception as error:
        latency_ms = (
            perf_counter() - started
        ) * 1000

        error_text = (
            f"{type(error).__name__}: {error}"
        )

        print(
            "Reviewer call failed:"
        )

        print(
            error_text
        )

        reached_ceiling = (
            turn_count >= turn_ceiling
        )

        feedback = {
            "approved": False,
            "issues": [
                (
                    "Reviewer call failed: "
                    f"{error_text}"
                )
            ]
        }

        trace = _append_trace(
            state,
            {
                "node": "reviewer",
                "turn": turn_count,
                "approved": False,
                "latency_ms": round(
                    latency_ms,
                    2
                ),
                "error": error_text,
                "summary_word_count": (
                    summary_word_count
                )
            }
        )

        return {
            "reviewer_feedback": feedback,
            "status": (
                "abandoned"
                if reached_ceiling
                else "revision_requested"
            ),
            "completed": False,
            "abandoned": reached_ceiling,
            "trace": trace
        }