from __future__ import annotations

import csv
import json
import multiprocessing
from code.hw10_config import (
    CACHE_MISS,
    JUDGE_MODEL,
    PIPELINE_EVALUATION_CSV_PATH,
    PIPELINE_EVALUATION_PATH,
    RAW_DIR,
    STUDENT_NAME,
    ensure_hw10_directories,
)
from code.hw10_evaluator import evaluate_pipeline
from code.hw10_tracing import (
    generate_trace_id,
    trace_span,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVALUATION_LOG_PATH = (
    RAW_DIR / "pipeline_evaluation.log"
)


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(UTC).isoformat()


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    """Write one formatted JSON document."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    result: dict[str, Any],
) -> None:
    """Write the evaluation summary as CSV."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fields = [
        "trace_id",
        "question",
        "plan_score",
        "writer_score",
        "final_score",
        "score_difference",
        "plan_reason",
        "writer_reason",
        "final_reason",
        "improvement_interpretation",
        "success",
    ]

    row = {
        "trace_id": result["trace_id"],
        "question": result["question"],
        "plan_score": result[
            "plan_quality"
        ]["score"],
        "writer_score": result[
            "writer_helpfulness"
        ]["score"],
        "final_score": result[
            "final_answer_helpfulness"
        ]["score"],
        "score_difference": result[
            "score_difference"
        ],
        "plan_reason": result[
            "plan_quality"
        ]["reason"],
        "writer_reason": result[
            "writer_helpfulness"
        ]["reason"],
        "final_reason": result[
            "final_answer_helpfulness"
        ]["reason"],
        "improvement_interpretation": result[
            "improvement_interpretation"
        ],
        "success": result["success"],
    }

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerow(row)


def log_lines(
    result: dict[str, Any],
) -> list[str]:
    """Build readable evaluation log lines."""

    return [
        "DATA-260 Homework 10 Automated Evaluation",
        f"Student: {STUDENT_NAME}",
        f"Judge model: {JUDGE_MODEL}",
        f"Trace ID: {result['trace_id']}",
        "",
        "=== QUESTION ===",
        result["question"],
        "",
        "=== PLANNER PLAN ===",
        *[
            f"{index}. {step}"
            for index, step in enumerate(
                result["plan"],
                start=1,
            )
        ],
        "",
        "=== WRITER DRAFT ===",
        result["writer_draft"],
        "",
        "=== REVIEWER FINAL ANSWER ===",
        result["final_answer"],
        "",
        "=== DEEPEVAL GEVAL RESULTS ===",
        (
            "Plan Quality: "
            f"{result['plan_quality']['score']}/5"
        ),
        (
            "Plan reason: "
            f"{result['plan_quality']['reason']}"
        ),
        (
            "Writer Helpfulness: "
            f"{result['writer_helpfulness']['score']}/5"
        ),
        (
            "Writer reason: "
            f"{result['writer_helpfulness']['reason']}"
        ),
        (
            "Final Answer Helpfulness: "
            f"{result['final_answer_helpfulness']['score']}/5"
        ),
        (
            "Final reason: "
            f"{result['final_answer_helpfulness']['reason']}"
        ),
        (
            "Final minus draft: "
            f"{result['score_difference']}"
        ),
        result["improvement_interpretation"],
        "",
        f"Overall evaluation success: {result['success']}",
        (
            "JSON: "
            f"{PIPELINE_EVALUATION_PATH}"
        ),
        (
            "CSV: "
            f"{PIPELINE_EVALUATION_CSV_PATH}"
        ),
    ]


def main() -> None:
    """Run one complete pipeline evaluation."""

    ensure_hw10_directories()

    trace_id = generate_trace_id()

    question = (
        "Give the phase, sponsor, and enrollment "
        "target of the sleep quality trial."
    )

    reference_answer = (
        "The Sleep Quality and Academic Performance "
        "Study is a Phase II trial sponsored by "
        "San Jose State University with an enrollment "
        "target of 120 participants."
    )

    with trace_span(
        trace_id,
        "cache_lookup",
        cache_result=CACHE_MISS,
        metadata={
            "question": question,
            "cache_threshold": 0.90,
        },
    ):
        pass

    with trace_span(
        trace_id,
        "planner",
        metadata={
            "source_topic": "s7801_inbox",
            "destination_topic": "s7801_tasks",
        },
    ):
        plan = [
            (
                "Find the sleep quality clinical "
                "trial."
            ),
            (
                "Retrieve its phase, sponsor, and "
                "enrollment target."
            ),
            (
                "Return a concise answer containing "
                "all requested facts."
            ),
        ]

    with trace_span(
        trace_id,
        "writer",
        metadata={
            "source_topic": "s7801_tasks",
            "destination_topic": "s7801_drafts",
        },
    ):
        writer_draft = (
            "The Sleep Quality and Academic "
            "Performance Study is a Phase II trial."
        )

    with trace_span(
        trace_id,
        "reviewer",
        metadata={
            "source_topic": "s7801_drafts",
            "destination_topic": "s7801_final",
        },
    ):
        final_answer = (
            "The Sleep Quality and Academic "
            "Performance Study is a Phase II trial "
            "sponsored by San Jose State University "
            "with an enrollment target of 120 "
            "participants."
        )

    evaluation = evaluate_pipeline(
        trace_id=trace_id,
        question=question,
        plan=plan,
        writer_draft=writer_draft,
        final_answer=final_answer,
        reference_answer=reference_answer,
    )

    result = evaluation.to_dict()

    document = {
        "experiment": (
            "hw10_automated_pipeline_evaluation"
        ),
        "student": STUDENT_NAME,
        "sid4": 7801,
        "judge_framework": "DeepEval GEval",
        "judge_model": JUDGE_MODEL,
        "generated_at": utc_timestamp(),
        "trace_id": trace_id,
        "correlation_id": trace_id,
        "question": question,
        "plan": plan,
        "writer_draft": writer_draft,
        "final_answer": final_answer,
        "reference_answer": reference_answer,
        "evaluation": result,
        "success": result["success"],
    }

    write_json(
        PIPELINE_EVALUATION_PATH,
        document,
    )
    write_csv(
        PIPELINE_EVALUATION_CSV_PATH,
        result,
    )

    lines = log_lines(result)
    output = "\n".join(lines)

    EVALUATION_LOG_PATH.write_text(
        output + "\n",
        encoding="utf-8",
    )

    print(output)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()