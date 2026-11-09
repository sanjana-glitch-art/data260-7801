from __future__ import annotations

import csv
import json
from code.hw9_self_improving_agents import (
    SelfImprovingSystem,
)
from pathlib import Path
from statistics import mean
from typing import Any

TRAINING_PATH = Path(
    "training_data.json"
)

VALIDATION_PATH = Path(
    "validation_data.json"
)

TEST_PATH = Path(
    "test_data.json"
)

JSON_OUTPUT = Path(
    "reports/hw09/raw/"
    "self_improvement_results.json"
)

CSV_OUTPUT = Path(
    "reports/hw09/raw/"
    "self_improvement_variants.csv"
)

REVISION_OUTPUT = Path(
    "reports/hw09/raw/"
    "revision_sequence.json"
)

LESSON_REUSE_OUTPUT = Path(
    "reports/hw09/raw/"
    "lesson_reuse_example.json"
)


def load_inputs(
    path: Path,
) -> list[dict[str, Any]]:
    """Load an input-only dataset."""

    document = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    if not isinstance(document, list):
        raise TypeError(
            f"{path} must contain a list."
        )

    return document


def evaluate_dataset(
    system: SelfImprovingSystem,
    dataset: list[dict[str, Any]],
    *,
    evaluator_enabled: bool,
    lessons_enabled: bool,
    update_lesson_count: bool = False,
) -> list[dict[str, Any]]:
    """Evaluate one fixed dataset."""

    return [
        {
            "input_id": item["input_id"],
            **system.run(
                item["question"],
                evaluator_enabled=(
                    evaluator_enabled
                ),
                lessons_enabled=(
                    lessons_enabled
                ),
                update_lesson_count=(
                    update_lesson_count
                ),
            ),
        }
        for item in dataset
    ]


def summarize_variant(
    name: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize one system variant."""

    correct = sum(
        result["success"]
        for result in results
    )

    incorrect = (
        len(results) - correct
    )

    average_attempts = mean(
        result["attempt_count"]
        for result in results
    )

    average_latency = mean(
        result["latency_ms"]
        for result in results
    )

    return {
        "variant": name,
        "correct_answers": correct,
        "incorrect_answers": incorrect,
        "average_attempts": round(
            average_attempts,
            3,
        ),
        "average_latency_ms": round(
            average_latency,
            3,
        ),
        "results": results,
    }


def print_revision_sequence(
    result: dict[str, Any],
) -> None:
    """Print the required revision evidence."""

    print(
        "\n=== COMPLETE REVISION "
        "SEQUENCE ==="
    )
    print(
        f"Question: {result['question']}"
    )

    initial = result["attempts"][0]

    print(
        "Initial answer: "
        f"{initial['answer']}"
    )
    print(
        "Initial evaluation: "
        f"{initial['evaluation_result']}"
    )
    print(
        "Evaluator feedback: "
        f"{initial['feedback']}"
    )

    if len(result["attempts"]) > 1:
        revised = result["attempts"][1]

        print(
            "Revised answer: "
            f"{revised['answer']}"
        )
        print(
            "Final evaluation: "
            f"{revised['evaluation_result']}"
        )

    print(
        "Number of attempts: "
        f"{result['attempt_count']}"
    )
    print(
        "Final response: "
        f"{result['final_answer']}"
    )


def main() -> None:
    """Run all Part 4 experiments."""

    training_data = load_inputs(
        TRAINING_PATH
    )

    validation_data = load_inputs(
        VALIDATION_PATH
    )

    test_data = load_inputs(
        TEST_PATH
    )

    system = SelfImprovingSystem()
    system.lessons.clear()

    print(
        "DATA-260 Homework 9 Part 4"
    )
    print(
        "Student: Sanjana Thummalapalli"
    )
    print("SID4: 7801")
    print(
        "Maximum answer attempts: 2"
    )

    controlled_case = next(
        item
        for item in training_data
        if item.get(
            "controlled_failure",
            False,
        )
    )

    revision_sequence = system.run(
        controlled_case["question"],
        evaluator_enabled=True,
        lessons_enabled=False,
    )

    print_revision_sequence(
        revision_sequence
    )

    REVISION_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REVISION_OUTPUT.write_text(
        json.dumps(
            revision_sequence,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\n=== REPEATED FAILURE "
        "DETECTION ==="
    )

    repeated_failure_questions = [
        training_data[0],
        training_data[2],
    ]

    repeated_failures = []

    for item in repeated_failure_questions:
        result = system.run(
            item["question"],
            evaluator_enabled=False,
            lessons_enabled=False,
        )

        missing_fields = result[
            "attempts"
        ][0]["missing_fields"]

        if (
            "enrollment_target"
            in missing_fields
        ):
            repeated_failures.append(
                result
            )

        print(
            f"{item['input_id']} | "
            f"{result['final_evaluation']} | "
            f"missing={missing_fields}"
        )

    if len(repeated_failures) < 2:
        raise RuntimeError(
            "Repeated enrollment omission "
            "was not detected."
        )

    print(
        "Repeated failure pattern detected: "
        "enrollment target omitted."
    )

    print(
        "\n=== VALIDATION BEFORE "
        "LESSON ==="
    )

    validation_before = evaluate_dataset(
        system,
        validation_data,
        evaluator_enabled=False,
        lessons_enabled=False,
    )

    before_correct = sum(
        result["success"]
        for result in validation_before
    )

    print(
        "Correct before lesson: "
        f"{before_correct}/"
        f"{len(validation_before)}"
    )

    candidate_lesson = (
        system.lessons
        .add_enrollment_lesson()
    )

    print(
        "Candidate lesson created: "
        f"{candidate_lesson['lesson_id']}"
    )

    print(
        "\n=== VALIDATION AFTER "
        "LESSON ==="
    )

    validation_after = evaluate_dataset(
        system,
        validation_data,
        evaluator_enabled=False,
        lessons_enabled=True,
        update_lesson_count=False,
    )

    after_correct = sum(
        result["success"]
        for result in validation_after
    )

    regressions = [
        after_result["input_id"]
        for before_result, after_result in zip(
            validation_before,
            validation_after,
            strict=True,
        )
        if (
            before_result["success"]
            and not after_result["success"]
        )
    ]

    improved_cases = [
        after_result["input_id"]
        for before_result, after_result in zip(
            validation_before,
            validation_after,
            strict=True,
        )
        if (
            not before_result["success"]
            and after_result["success"]
        )
    ]

    lesson_kept = (
        after_correct >= before_correct
        and not regressions
        and bool(improved_cases)
    )

    if not lesson_kept:
        system.lessons.clear()

    print(
        "Correct after lesson: "
        f"{after_correct}/"
        f"{len(validation_after)}"
    )
    print(
        f"Improved cases: {improved_cases}"
    )
    print(
        f"Regressions: {regressions}"
    )
    print(
        f"Lesson kept: {lesson_kept}"
    )

    if not lesson_kept:
        raise RuntimeError(
            "Candidate lesson failed "
            "validation."
        )

    lesson_reuse_item = (
        validation_data[0]
    )

    lesson_reuse_example = system.run(
        lesson_reuse_item["question"],
        evaluator_enabled=True,
        lessons_enabled=True,
        update_lesson_count=True,
    )

    print(
        "\n=== LESSON REUSE ==="
    )
    print(
        "Later question: "
        f"{lesson_reuse_example['question']}"
    )
    print(
        "Loaded lessons: "
        f"{lesson_reuse_example['attempts'][0]['loaded_lesson_ids']}"
    )
    print(
        "Answer: "
        f"{lesson_reuse_example['final_answer']}"
    )
    print(
        "Attempts: "
        f"{lesson_reuse_example['attempt_count']}"
    )
    print(
        "Evaluation: "
        f"{lesson_reuse_example['final_evaluation']}"
    )

    LESSON_REUSE_OUTPUT.write_text(
        json.dumps(
            lesson_reuse_example,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\n=== HELD-OUT TEST: "
        "FOUR VARIANTS ==="
    )

    variants = [
        (
            "Baseline",
            False,
            False,
        ),
        (
            "Evaluator Repair",
            True,
            False,
        ),
        (
            "Lesson Memory",
            True,
            True,
        ),
        (
            "Validated Improvement",
            True,
            lesson_kept,
        ),
    ]

    variant_summaries = []

    for (
        variant_name,
        evaluator_enabled,
        lessons_enabled,
    ) in variants:
        results = evaluate_dataset(
            system,
            test_data,
            evaluator_enabled=(
                evaluator_enabled
            ),
            lessons_enabled=(
                lessons_enabled
            ),
            update_lesson_count=(
                lessons_enabled
            ),
        )

        summary = summarize_variant(
            variant_name,
            results,
        )

        variant_summaries.append(
            summary
        )

        print(
            f"{variant_name} | "
            f"correct="
            f"{summary['correct_answers']} | "
            f"incorrect="
            f"{summary['incorrect_answers']} | "
            f"attempts="
            f"{summary['average_attempts']:.3f} | "
            f"latency="
            f"{summary['average_latency_ms']:.3f} ms"
        )

    output = {
        "experiment": (
            "hw9_self_improving_agents"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "reference_dataset": (
            "reference_data.json"
        ),
        "training_dataset": (
            str(TRAINING_PATH)
        ),
        "validation_dataset": (
            str(VALIDATION_PATH)
        ),
        "test_dataset": (
            str(TEST_PATH)
        ),
        "maximum_attempts": 2,
        "revision_sequence": (
            revision_sequence
        ),
        "repeated_failure_count": (
            len(repeated_failures)
        ),
        "candidate_lesson": (
            candidate_lesson
        ),
        "validation": {
            "correct_before": (
                before_correct
            ),
            "correct_after": (
                after_correct
            ),
            "improved_cases": (
                improved_cases
            ),
            "regressions": regressions,
            "lesson_kept": lesson_kept,
        },
        "lesson_reuse_example": (
            lesson_reuse_example
        ),
        "variants": variant_summaries,
        "communication": (
            "The Answering Agent produces an "
            "answer. The Evaluator Agent compares "
            "it with the reference dataset and "
            "returns PASS or REVISE plus feedback. "
            "The feedback is passed back to the "
            "Answering Agent for at most one "
            "revision."
        ),
        "stopping_condition": (
            "Stop after PASS or after the "
            "second answer attempt."
        ),
        "validation_process": (
            "The candidate lesson is evaluated "
            "on validation_data.json before it "
            "is retained. It is kept only when "
            "failed cases improve, previously "
            "correct cases do not regress, and "
            "unrelated question types remain "
            "grounded."
        ),
        "limitation": (
            "The evaluator depends on curated "
            "reference facts and keyword-based "
            "trial identification, so unseen "
            "trial names require additional "
            "reference data or a stronger "
            "retrieval method."
        ),
    }

    JSON_OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with CSV_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "variant",
                "correct_answers",
                "incorrect_answers",
                "average_attempts",
                "average_latency_ms",
            ],
        )

        writer.writeheader()

        for summary in variant_summaries:
            writer.writerow({
                field: summary[field]
                for field in writer.fieldnames
            })

    print(
        "\n=== FINAL VARIANT TABLE ==="
    )
    print(
        "Variant | Correct | Incorrect | "
        "Average attempts | "
        "Average latency"
    )

    for summary in variant_summaries:
        print(
            f"{summary['variant']} | "
            f"{summary['correct_answers']} | "
            f"{summary['incorrect_answers']} | "
            f"{summary['average_attempts']:.3f} | "
            f"{summary['average_latency_ms']:.3f} ms"
        )

    print(f"\nJSON: {JSON_OUTPUT}")
    print(f"CSV: {CSV_OUTPUT}")
    print(f"Revision: {REVISION_OUTPUT}")
    print(
        f"Lesson reuse: {LESSON_REUSE_OUTPUT}"
    )
    print("Overall: PASS")


if __name__ == "__main__":
    main()

