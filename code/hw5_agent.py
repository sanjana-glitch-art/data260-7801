from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from src.model_client import ModelClient

from code.hw5_tool_entry import (
    TOOL_NAMES,
    execute_tool,
)


ROOT = Path(
    __file__
).resolve().parents[1]

DEFAULT_LOG_PATH = (
    ROOT
    / "reports"
    / "hw05"
    / "raw"
    / "agent_runs.jsonl"
)

DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "tool",
                "final",
            ],
        },
        "tool_name": {
            "type": "string",
        },
        "inputs": {
            "type": "object",
        },
        "answer": {
            "type": "string",
        },
    },
    "required": [
        "action",
        "tool_name",
        "inputs",
        "answer",
    ],
    "additionalProperties": False,
}


@dataclass
class MockCompletion:
    """Minimal ModelClient-compatible result."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class MockModel:
    """Offline model that repeatedly requests a tool."""

    def __init__(
        self,
        decisions: list[dict[str, Any]]
        | None = None,
    ) -> None:
        self.decisions = decisions or [
            {
                "action": "tool",
                "tool_name": "search_trials",
                "inputs": {
                    "query": "Sleep",
                    "limit": 1,
                },
                "answer": "",
            }
        ]

        self.position = 0

    def complete(
        self,
        messages: list[dict[str, str]],
        response_format: (
            dict[str, Any] | None
        ) = None,
    ) -> MockCompletion:
        """Return the next deterministic decision."""

        del messages
        del response_format

        decision = self.decisions[
            self.position
            % len(self.decisions)
        ]

        self.position += 1

        return MockCompletion(
            content=json.dumps(
                decision
            )
        )


def utc_timestamp() -> str:
    """Return an ISO UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def append_log(
    record: dict[str, Any],
    log_path: Path,
) -> None:
    """Append one JSON object to the run log."""

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as log_file:
        log_file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


def safe_parse_decision(
    content: str,
) -> dict[str, Any]:
    """Parse and validate a model decision."""

    try:
        decision = json.loads(content)
    except json.JSONDecodeError:
        return {
            "action": "final",
            "tool_name": "",
            "inputs": {},
            "answer": (
                "The model returned invalid JSON."
            ),
        }

    if not isinstance(decision, dict):
        return {
            "action": "final",
            "tool_name": "",
            "inputs": {},
            "answer": (
                "The model returned an invalid decision."
            ),
        }

    return {
        "action": decision.get(
            "action",
            "final",
        ),
        "tool_name": str(
            decision.get(
                "tool_name",
                "",
            )
        ),
        "inputs": (
            decision.get(
                "inputs",
                {},
            )
            if isinstance(
                decision.get(
                    "inputs",
                    {},
                ),
                dict,
            )
            else {}
        ),
        "answer": str(
            decision.get(
                "answer",
                "",
            )
        ),
    }


def system_prompt() -> str:
    """Return agent instructions."""

    return """
You are a clinical-trial assistant.

You may use exactly these tools:
- search_trials(query, limit)
- trial_details(trial_id)
- trial_phase_summary(sponsor_id)

Return only a JSON decision matching the provided schema.

Use action "tool" when information must be retrieved.
Use action "final" when you can answer the user.

When a user asks for a submitter email or other submitter
contact information, request trial_details with:
{"trial_id": ID, "include_submitter_email": true}
The tool harness will apply its privacy safety rule.

Never invent clinical-trial facts. Base the final answer only
on tool results.
""".strip()


def run_agent(
    user_input: str,
    *,
    model: Any | None = None,
    max_steps: int = 4,
    log_path: Path = DEFAULT_LOG_PATH,
    run_label: str = "interactive",
) -> dict[str, Any]:
    """Run the bounded local tool-using agent."""

    cleaned_input = str(
        user_input
    ).strip()

    if not cleaned_input:
        return {
            "answer": (
                "A user request is required."
            ),
            "step_count": 0,
            "tool_call_count": 0,
            "stop_reason": "invalid_input",
        }

    if max_steps < 1:
        return {
            "answer": (
                "The agent step limit must "
                "be at least one."
            ),
            "step_count": 0,
            "tool_call_count": 0,
            "stop_reason": "invalid_max_steps",
        }

    active_model = (
        model
        if model is not None
        else ModelClient(
            model="qwen3:4b",
            temperature=0.0,
            num_ctx=2048,
            num_predict=256,
        )
    )

    run_id = (
        f"{run_label}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )

    messages: list[
        dict[str, str]
    ] = [
        {
            "role": "system",
            "content": system_prompt(),
        },
        {
            "role": "user",
            "content": cleaned_input,
        },
    ]

    tool_call_count = 0

    append_log(
        {
            "timestamp": utc_timestamp(),
            "run_id": run_id,
            "event": "run_started",
            "user_input": cleaned_input,
            "max_steps": max_steps,
        },
        log_path,
    )

    for step in range(
        1,
        max_steps + 1,
    ):
        completion = active_model.complete(
            messages,
            response_format=(
                DECISION_SCHEMA
            ),
        )

        decision = safe_parse_decision(
            completion.content
        )

        append_log(
            {
                "timestamp": utc_timestamp(),
                "run_id": run_id,
                "event": "model_decision",
                "step": step,
                "decision": decision,
            },
            log_path,
        )

        if decision["action"] == "final":
            answer = (
                decision["answer"]
                or "The task is complete."
            )

            result = {
                "answer": answer,
                "step_count": step,
                "tool_call_count": (
                    tool_call_count
                ),
                "stop_reason": (
                    "normal_completion"
                ),
            }

            append_log(
                {
                    "timestamp": utc_timestamp(),
                    "run_id": run_id,
                    "event": "run_stopped",
                    **result,
                },
                log_path,
            )

            return result

        tool_name = decision[
            "tool_name"
        ]

        if tool_name not in TOOL_NAMES:
            tool_result = json.dumps({
                "ok": False,
                "data": None,
                "error": (
                    f"Unknown tool '{tool_name}'."
                ),
            })
        else:
            tool_result = execute_tool(
                tool_name,
                decision["inputs"],
            )

        tool_call_count += 1

        append_log(
            {
                "timestamp": utc_timestamp(),
                "run_id": run_id,
                "event": "tool_call",
                "step": step,
                "tool_name": tool_name,
                "inputs": decision[
                    "inputs"
                ],
                "result": json.loads(
                    tool_result
                ),
            },
            log_path,
        )

        parsed_tool_result = json.loads(
            tool_result
        )

        error_text = str(
            parsed_tool_result.get(
                "error"
            )
            or ""
        )

        if (
            parsed_tool_result.get(
                "ok"
            )
            is False
            and "Safety rule blocked"
            in error_text
        ):
            result = {
                "answer": error_text,
                "step_count": step,
                "tool_call_count": (
                    tool_call_count
                ),
                "stop_reason": (
                    "safety_rule_block"
                ),
            }

            append_log(
                {
                    "timestamp": utc_timestamp(),
                    "run_id": run_id,
                    "event": "run_stopped",
                    **result,
                },
                log_path,
            )

            return result

        messages.append({
            "role": "assistant",
            "content": json.dumps(
                decision
            ),
        })

        messages.append({
            "role": "user",
            "content": (
                "Tool result:\n"
                f"{tool_result}\n"
                "Decide whether to call another "
                "tool or provide the final answer."
            ),
        })

    result = {
        "answer": (
            "The agent stopped after reaching "
            "the maximum number of steps."
        ),
        "step_count": max_steps,
        "tool_call_count": (
            tool_call_count
        ),
        "stop_reason": "max_steps",
    }

    append_log(
        {
            "timestamp": utc_timestamp(),
            "run_id": run_id,
            "event": "run_stopped",
            **result,
        },
        log_path,
    )

    return result