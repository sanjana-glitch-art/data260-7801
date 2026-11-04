from __future__ import annotations

import json
import os
import re
import time
from code.hw5_tool_entry import (
    TOOL_NAMES,
    execute_tool,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ollama import ResponseError

from src.model_client import (
    ModelClient,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOG_PATH = PROJECT_ROOT / "reports" / "hw07" / "raw" / "agent_tool_calls.jsonl"

MODEL_NAME = os.getenv(
    "HW7_MODEL",
    "qwen3:4b",
)

MAX_ITERATIONS = 8

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
        "arguments": {
            "type": "object",
        },
        "answer": {
            "type": "string",
        },
    },
    "required": [
        "action",
        "tool_name",
        "arguments",
        "answer",
    ],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """
You are a clinical-trial research assistant.

You must use tools whenever the user requests database facts.
Do not invent clinical-trial records, identifiers, phases,
sponsors, enrollment targets, or aggregate counts.

Available tools:

1. search_trials
Arguments:
{
  "query": "non-empty search text",
  "limit": positive integer from 1 through 10
}

2. trial_details
Arguments:
{
  "trial_id": positive integer
}

3. trial_phase_summary
Arguments:
{
  "sponsor_id": optional positive integer
}

Return exactly one JSON object matching this structure:

{
  "action": "tool" or "final",
  "tool_name": "tool name or empty string",
  "arguments": {},
  "answer": "final answer or empty string"
}

When action is "tool":
- tool_name must be one available tool.
- arguments must satisfy that tool's schema.
- answer must be an empty string.

When action is "final":
- tool_name must be an empty string.
- arguments must be an empty object.
- answer must directly answer the user using tool observations.

Multi-step requirements:
- Search-then-detail: search first, then call trial_details
  using the first returned ID.
- Aggregate-then-example: call trial_phase_summary first,
  then search for one supporting example.
- Compare-two: search first, then call trial_details once
  for each of two different returned IDs.
- A failed tool result is data, not a crash. Explain the
  useful error to the user and do not claim success.
- Never reveal submitter email addresses.
""".strip()


def utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC).isoformat()


def append_jsonl(
    path: Path,
    record: dict[str, Any],
) -> None:
    """Append one JSON object to a JSONL file."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
            + "\n"
        )


def parse_decision(
    content: str,
) -> dict[str, Any]:
    """Parse one model decision from JSON text."""

    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        object_match = re.search(
            r"\{.*\}",
            cleaned,
            flags=re.DOTALL,
        )

        if object_match is None:
            raise ValueError("Model response was not a JSON object.") from None

        try:
            parsed = json.loads(object_match.group(0))
        except json.JSONDecodeError as error:
            raise ValueError("Model response contained malformed JSON.") from error

    if not isinstance(
        parsed,
        dict,
    ):
        raise TypeError("Model decision must be a JSON object.")

    return parsed


def classify_decision_problem(
    decision: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Validate a decision and classify any problem."""

    required_fields = {
        "action",
        "tool_name",
        "arguments",
        "answer",
    }

    missing_fields = required_fields - set(decision)

    if missing_fields:
        return (
            "malformed_arguments",
            ("Missing fields: " + ", ".join(sorted(missing_fields))),
        )

    action = decision.get("action")

    if action not in {
        "tool",
        "final",
    }:
        return (
            "malformed_arguments",
            ("action must be either 'tool' or 'final'."),
        )

    tool_name = decision.get("tool_name")

    arguments = decision.get("arguments")

    answer = decision.get("answer")

    if not isinstance(
        tool_name,
        str,
    ):
        return (
            "malformed_arguments",
            "tool_name must be a string.",
        )

    if not isinstance(
        arguments,
        dict,
    ):
        return (
            "malformed_arguments",
            "arguments must be a JSON object.",
        )

    if not isinstance(
        answer,
        str,
    ):
        return (
            "malformed_arguments",
            "answer must be a string.",
        )

    if action == "tool":
        if tool_name not in TOOL_NAMES:
            return (
                "unknown_tool",
                (f"Unknown tool '{tool_name}'. Use only: " + ", ".join(TOOL_NAMES)),
            )

        if answer.strip():
            return (
                "malformed_arguments",
                ("answer must be empty during a tool call."),
            )

    if action == "final":
        if tool_name:
            return (
                "malformed_arguments",
                ("tool_name must be empty for a final answer."),
            )

        if arguments:
            return (
                "malformed_arguments",
                ("arguments must be empty for a final answer."),
            )

        if not answer.strip():
            return (
                "text_when_tool_required",
                ("A final response must contain a non-empty answer."),
            )

    return (
        None,
        None,
    )


def repair_message(
    problem: str,
) -> str:
    """Return one specific bounded repair instruction."""

    return (
        "Your previous decision was invalid. "
        f"Problem: {problem} "
        "Return exactly one corrected JSON object "
        "matching the required schema. Do not add "
        "markdown or explanation."
    )


def safe_json_result(
    result_text: str,
) -> dict[str, Any]:
    """Parse a tool envelope for logs and messages."""

    try:
        parsed = json.loads(result_text)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "data": None,
            "error": ("Tool returned malformed JSON."),
        }

    if not isinstance(
        parsed,
        dict,
    ):
        return {
            "ok": False,
            "data": None,
            "error": ("Tool returned a non-object result."),
        }

    return parsed


def run_agent(
    user_input: str,
    *,
    model: ModelClient | None = None,
    max_iterations: int = MAX_ITERATIONS,
    log_path: Path = DEFAULT_LOG_PATH,
    run_label: str = "hw7-agent",
) -> dict[str, Any]:
    """
    Run the bounded handwritten clinical-trial agent.

    Tool observations are appended using role='tool'.
    One malformed decision may be repaired. A second
    malformed decision stops the run cleanly.
    """

    cleaned_input = user_input.strip()

    if not cleaned_input:
        raise ValueError("user_input must not be empty.")

    if max_iterations < 1:
        raise ValueError("max_iterations must be positive.")

    active_model = (
        model
        if model is not None
        else ModelClient(
            model=MODEL_NAME,
            temperature=0.0,
            num_ctx=2048,
            num_predict=256,
        )
    )

    run_id = f"{run_label}-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}"

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": cleaned_input,
        },
    ]

    started_at = time.perf_counter()

    tool_calls: list[dict[str, Any]] = []

    failures: list[str] = []

    repair_count = 0
    initial_decision_count = 0
    valid_initial_decision_count = 0
    input_tokens = 0
    output_tokens = 0

    for iteration in range(
        1,
        max_iterations + 1,
    ):
        try:
            completion = active_model.complete(
                messages=messages,
                response_format=(DECISION_SCHEMA),
            )
        except ResponseError as error:
            return {
                "run_id": run_id,
                "answer": ("The agent stopped cleanly after a model runtime error."),
                "messages": messages,
                "tool_calls": tool_calls,
                "tool_call_count": len(tool_calls),
                "iteration_count": iteration,
                "repair_count": repair_count,
                "failure_classification": ["runtime_error"],
                "well_formed_before_repair": (
                    valid_initial_decision_count == initial_decision_count
                    and initial_decision_count > 0
                ),
                "well_formed_after_repair": False,
                "input_tokens": input_tokens,
                "output_tokens": (output_tokens),
                "total_tokens": (input_tokens + output_tokens),
                "latency_ms": round(
                    (time.perf_counter() - started_at) * 1000,
                    3,
                ),
                "stop_reason": ("runtime_error"),
                "runtime_error": (f"{type(error).__name__}: {error}"),
            }

        input_tokens += completion.input_tokens

        output_tokens += completion.output_tokens

        initial_decision_count += 1

        try:
            decision = parse_decision(completion.content)
        except (
            TypeError,
            ValueError,
        ) as error:
            classification = "text_when_tool_required"

            problem = str(error)
        else:
            classification, problem = classify_decision_problem(decision)

        if problem is not None:
            failures.append(classification or "malformed_arguments")

            if repair_count >= 1:
                elapsed = round(
                    (time.perf_counter() - started_at) * 1000,
                    3,
                )

                return {
                    "run_id": run_id,
                    "answer": (
                        "The agent stopped cleanly "
                        "because its decision remained "
                        "invalid after one repair."
                    ),
                    "messages": messages,
                    "tool_calls": tool_calls,
                    "tool_call_count": len(tool_calls),
                    "iteration_count": (iteration),
                    "repair_count": (repair_count),
                    "failure_classification": (failures),
                    "well_formed_before_repair": (False),
                    "well_formed_after_repair": (False),
                    "input_tokens": (input_tokens),
                    "output_tokens": (output_tokens),
                    "total_tokens": (input_tokens + output_tokens),
                    "latency_ms": elapsed,
                    "stop_reason": ("repair_failed"),
                    "runtime_error": None,
                }

            repair_count += 1

            messages.append(
                {
                    "role": "assistant",
                    "content": (completion.content),
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (repair_message(problem)),
                }
            )

            continue

        valid_initial_decision_count += 1

        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    decision,
                    ensure_ascii=False,
                ),
            }
        )

        if decision["action"] == ("final"):
            elapsed = round(
                (time.perf_counter() - started_at) * 1000,
                3,
            )

            return {
                "run_id": run_id,
                "answer": (decision["answer"].strip()),
                "messages": messages,
                "tool_calls": tool_calls,
                "tool_call_count": len(tool_calls),
                "iteration_count": (iteration),
                "repair_count": (repair_count),
                "failure_classification": (failures),
                "well_formed_before_repair": (repair_count == 0),
                "well_formed_after_repair": True,
                "input_tokens": (input_tokens),
                "output_tokens": (output_tokens),
                "total_tokens": (input_tokens + output_tokens),
                "latency_ms": elapsed,
                "stop_reason": ("normal_completion"),
                "runtime_error": None,
            }

        tool_name = decision["tool_name"]

        arguments = decision["arguments"]

        tool_result_text = execute_tool(
            tool_name,
            arguments,
        )

        tool_result = safe_json_result(tool_result_text)

        invocation = {
            "run_id": run_id,
            "iteration": iteration,
            "tool_name": tool_name,
            "inputs": arguments,
            "result": tool_result,
            "timestamp": (utc_timestamp()),
        }

        tool_calls.append(invocation)

        append_jsonl(
            log_path,
            invocation,
        )

        messages.append(
            {
                "role": "tool",
                "content": json.dumps(
                    {
                        "tool_name": (tool_name),
                        "observation": (tool_result),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            }
        )

    elapsed = round(
        (time.perf_counter() - started_at) * 1000,
        3,
    )

    return {
        "run_id": run_id,
        "answer": ("The agent stopped after reaching the hard iteration ceiling."),
        "messages": messages,
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
        "iteration_count": (max_iterations),
        "repair_count": repair_count,
        "failure_classification": (failures),
        "well_formed_before_repair": (repair_count == 0),
        "well_formed_after_repair": (False),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (input_tokens + output_tokens),
        "latency_ms": elapsed,
        "stop_reason": ("iteration_ceiling"),
        "runtime_error": None,
    }
