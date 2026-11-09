from __future__ import annotations

import json
from code.hw8_pipeline import (
    send_question_and_wait,
)
from pathlib import Path

RAW_DIRECTORY = (
    Path(__file__).resolve().parent
    / "reports"
    / "hw08"
    / "raw"
)

RESULT_PATH = (
    RAW_DIRECTORY
    / "pipeline_result.json"
)


def main() -> None:
    """Send one question through all three agents."""

    question = (
        "How does Kafka improve coordination "
        "and reliability in a distributed "
        "clinical-trial processing system?"
    )

    print(
        "DATA-260 Homework 8 Part 2"
    )
    print(
        "Student: Sanjana Thummalapalli"
    )
    print(
        "Pipeline: "
        "s7801_inbox -> "
        "s7801_tasks -> "
        "s7801_drafts -> "
        "s7801_final"
    )
    print(
        "Question:",
        question,
    )

    result = send_question_and_wait(
        question,
        entity_key="clinical-trials",
        timeout_seconds=60.0,
    )

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    document = {
        "experiment": (
            "hw8_three_agent_pipeline"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "question": question,
        "result": result,
    }

    RESULT_PATH.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\n=== FINAL PIPELINE RESULT ==="
    )
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    print(
        "\nStatus:",
        result.get("status"),
    )
    print(
        "Correlation ID:",
        result.get(
            "correlation_id"
        ),
    )
    print(
        "Answer:",
        result.get("answer"),
    )
    print(
        "Saved:",
        RESULT_PATH,
    )


if __name__ == "__main__":
    main()