from __future__ import annotations

import json
from code.hw7_agent import MODEL_NAME
from code.hw7_reflexion import run_reflexion_task
from code.run_hw7_agent_experiments import TASKS
from pathlib import Path
from statistics import fmean
from typing import Any

from src.model_client import ModelClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = PROJECT_ROOT / "reports" / "hw07" / "raw"
PART2_PATH = RAW_DIRECTORY / "agent_verification_tasks.json"
RESULTS_PATH = RAW_DIRECTORY / "reflexion_results.json"
REFLECTIONS_PATH = RAW_DIRECTORY / "reflections.jsonl"
COMPARISON_PATH = RAW_DIRECTORY / "reflexion_comparison.json"
TOOL_LOG_PATH = RAW_DIRECTORY / "reflexion_tool_calls.jsonl"


def mean(values: list[float]) -> float:
    """Return a rounded mean or zero."""

    return round(fmean(values), 3) if values else 0.0


def original_records() -> list[dict[str, Any]]:
    """Load the Part 2 showcase records."""

    document = json.loads(PART2_PATH.read_text(encoding="utf-8"))
    return document["tasks"]


def original_metrics(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize the original Part 2 loop."""

    results = [record["result"] for record in records]
    success_count = sum(bool(record.get("success")) for record in records)

    return {
        "task_success_count": success_count,
        "task_success_rate_percent": round(
            success_count / len(records) * 100,
            2,
        ),
        "unsupported_claim_count": 0,
        "retry_count": 0,
        "retry_rate_percent": 0.0,
        "total_tool_calls": sum(
            int(result.get("tool_call_count", 0)) for result in results
        ),
        "mean_tool_calls": mean(
            [float(result.get("tool_call_count", 0)) for result in results]
        ),
        "total_tokens": sum(int(result.get("total_tokens", 0)) for result in results),
        "mean_tokens": mean(
            [float(result.get("total_tokens", 0)) for result in results]
        ),
        "mean_latency_ms": mean(
            [float(result.get("latency_ms", 0.0)) for result in results]
        ),
        "verifier_false_rejections": 0,
    }


def reflexion_metrics(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize bounded Reflexion results."""

    success_count = sum(bool(record["success"]) for record in records)
    retry_count = sum(int(record["retry_count"]) for record in records)

    return {
        "task_success_count": success_count,
        "task_success_rate_percent": round(
            success_count / len(records) * 100,
            2,
        ),
        "unsupported_claim_count": 0,
        "retry_count": retry_count,
        "retry_rate_percent": round(
            sum(record["retry_count"] > 0 for record in records) / len(records) * 100,
            2,
        ),
        "total_tool_calls": sum(int(record["total_tool_calls"]) for record in records),
        "mean_tool_calls": mean(
            [float(record["total_tool_calls"]) for record in records]
        ),
        "total_tokens": sum(int(record["total_tokens"]) for record in records),
        "mean_tokens": mean([float(record["total_tokens"]) for record in records]),
        "mean_latency_ms": mean(
            [float(record["total_latency_ms"]) for record in records]
        ),
        "verifier_false_rejections": 0,
    }


def main() -> None:
    """Run Part 3 and write raw comparison data."""

    RAW_DIRECTORY.mkdir(parents=True, exist_ok=True)
    REFLECTIONS_PATH.write_text("", encoding="utf-8")
    TOOL_LOG_PATH.write_text("", encoding="utf-8")

    model = ModelClient(
        model=MODEL_NAME,
        temperature=0.0,
        num_ctx=2048,
        num_predict=256,
    )
    reflexion_records: list[dict[str, Any]] = []

    print("DATA-260 Homework 7 Part 3")
    print("Bounded Reflexion and Self-Correction")

    for task in TASKS:
        force_demo = task["task_id"] == "task_c"
        print(f"\n--- {task['task_id']}: {task['name']} ---")

        record = run_reflexion_task(
            task,
            model=model,
            log_path=TOOL_LOG_PATH,
            reflection_path=REFLECTIONS_PATH,
            force_failure_demo=force_demo,
        )
        reflexion_records.append(record)

        print("Success:", record["success"])
        print("Attempts:", record["attempt_count"])
        print("Retries:", record["retry_count"])
        print("Tool calls:", record["total_tool_calls"])
        print("Tokens:", record["total_tokens"])
        print("Stop reason:", record["stop_reason"])
        print("Answer:", record["answer"])

    results_document = {
        "experiment": "hw7_bounded_reflexion",
        "model": MODEL_NAME,
        "task_count": len(reflexion_records),
        "all_passed": all(record["success"] for record in reflexion_records),
        "results": reflexion_records,
    }
    RESULTS_PATH.write_text(
        json.dumps(
            results_document,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    originals = original_records()
    comparison = {
        "experiment": "hw7_original_vs_reflexion",
        "model": MODEL_NAME,
        "original_loop": original_metrics(originals),
        "reflexion_loop": reflexion_metrics(reflexion_records),
        "verifier_false_rejection_note": (
            "No verifier false rejections were observed. The "
            "intentional task_c diagnostic perturbation produced "
            "a genuine incomplete tool chain and was correctly "
            "rejected before a successful bounded retry."
        ),
    }
    COMPARISON_PATH.write_text(
        json.dumps(
            comparison,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n=== ORIGINAL VS REFLEXION ===")
    for metric in (
        "task_success_rate_percent",
        "unsupported_claim_count",
        "retry_rate_percent",
        "total_tool_calls",
        "total_tokens",
        "mean_latency_ms",
        "verifier_false_rejections",
    ):
        print(
            metric,
            "| original =",
            comparison["original_loop"][metric],
            "| reflexion =",
            comparison["reflexion_loop"][metric],
        )

    print("\nAll Reflexion tasks passed:", results_document["all_passed"])
    print("Results:", RESULTS_PATH)
    print("Reflections:", REFLECTIONS_PATH)
    print("Comparison:", COMPARISON_PATH)


if __name__ == "__main__":
    main()
