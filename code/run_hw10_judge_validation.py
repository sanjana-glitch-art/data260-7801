from __future__ import annotations

import csv
import json
import multiprocessing
from code.hw10_config import (
    EVAL_CASES_PATH,
    HUMAN_LABELS_PATH,
    JUDGE_MODEL,
    JUDGE_REPEAT_COUNT,
    JUDGE_REPEATABILITY_PATH,
    JUDGE_VALIDATION_PATH,
    JUDGE_VALIDATION_SCORES_PATH,
    STUDENT_NAME,
    ensure_hw10_directories,
)
from code.hw10_evaluator import evaluate_writer_draft
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any

from scipy.stats import spearmanr

CHECKPOINT_PATH = (
    JUDGE_VALIDATION_PATH.parent
    / "judge_validation_checkpoint.json"
)


def load_json(
    path: Path,
) -> Any:
    """Load one JSON document."""

    return json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )


def write_json(
    path: Path,
    value: Any,
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


def load_human_labels() -> dict[str, dict[str, Any]]:
    """Load and validate the frozen human labels."""

    labels: dict[str, dict[str, Any]] = {}

    with HUMAN_LABELS_PATH.open(
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            case_id = row["case_id"].strip()
            score_text = row["human_score"].strip()
            reason = row["human_reason"].strip()

            if not case_id:
                raise ValueError(
                    "A human-label row has no case ID."
                )

            if score_text not in {
                "1",
                "2",
                "3",
                "4",
                "5",
            }:
                raise ValueError(
                    f"{case_id} has an invalid human score."
                )

            if not reason:
                raise ValueError(
                    f"{case_id} has no human reason."
                )

            labels[case_id] = {
                "human_score": int(score_text),
                "human_reason": reason,
            }

    return labels


def write_score_csv(
    rows: list[dict[str, Any]],
) -> None:
    """Write raw scores from all three runs."""

    fields = [
        "run_number",
        "case_id",
        "category",
        "human_score",
        "judge_score",
        "absolute_difference",
        "judge_success",
        "judge_reason",
        "judge_error_type",
        "judge_error",
        "latency_ms",
    ]

    with JUDGE_VALIDATION_SCORES_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_repeatability_csv(
    rows: list[dict[str, Any]],
) -> None:
    """Write per-case repeatability evidence."""

    fields = [
        "case_id",
        "run_1_score",
        "run_2_score",
        "run_3_score",
        "score_changed",
        "mean_pairwise_absolute_change",
        "maximum_pairwise_absolute_change",
    ]

    with JUDGE_REPEATABILITY_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def calculate_validation_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate agreement for the first judge run."""

    first_run = [
        row
        for row in rows
        if (
            row["run_number"] == 1
            and row["judge_success"]
        )
    ]

    if len(first_run) != 20:
        return {
            "complete": False,
            "successful_case_count": len(
                first_run
            ),
            "spearman_correlation": None,
            "spearman_p_value": None,
            "mean_absolute_difference": None,
        }

    human_scores = [
        row["human_score"]
        for row in first_run
    ]
    judge_scores = [
        row["judge_score"]
        for row in first_run
    ]

    correlation = spearmanr(
        human_scores,
        judge_scores,
    )

    absolute_differences = [
        abs(human - judge)
        for human, judge in zip(
            human_scores,
            judge_scores,
            strict=True,
        )
    ]

    return {
        "complete": True,
        "successful_case_count": len(
            first_run
        ),
        "spearman_correlation": round(
            float(correlation.statistic),
            6,
        ),
        "spearman_p_value": round(
            float(correlation.pvalue),
            6,
        ),
        "mean_absolute_difference": round(
            mean(absolute_differences),
            6,
        ),
    }


def calculate_repeatability(
    rows: list[dict[str, Any]],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    """Calculate three-run judge repeatability."""

    scores_by_case: dict[str, list[int]] = {}

    for row in rows:
        if not row["judge_success"]:
            continue

        scores_by_case.setdefault(
            row["case_id"],
            [],
        ).append(row["judge_score"])

    case_rows: list[dict[str, Any]] = []
    all_pairwise_changes: list[int] = []
    changed_comparisons = 0
    total_comparisons = 0

    for case_id in sorted(scores_by_case):
        scores = scores_by_case[case_id]

        if len(scores) != JUDGE_REPEAT_COUNT:
            continue

        pairwise_changes = [
            abs(left - right)
            for left, right in combinations(
                scores,
                2,
            )
        ]

        changed = any(
            change > 0
            for change in pairwise_changes
        )

        changed_comparisons += sum(
            change > 0
            for change in pairwise_changes
        )
        total_comparisons += len(
            pairwise_changes
        )
        all_pairwise_changes.extend(
            pairwise_changes
        )

        case_rows.append(
            {
                "case_id": case_id,
                "run_1_score": scores[0],
                "run_2_score": scores[1],
                "run_3_score": scores[2],
                "score_changed": changed,
                "mean_pairwise_absolute_change": round(
                    mean(pairwise_changes),
                    6,
                ),
                "maximum_pairwise_absolute_change": max(
                    pairwise_changes
                ),
            }
        )

    if not all_pairwise_changes:
        return (
            {
                "complete": False,
                "complete_case_count": len(
                    case_rows
                ),
                "score_change_frequency_percent": None,
                "mean_absolute_score_change": None,
                "maximum_absolute_score_change": None,
            },
            case_rows,
        )

    return (
        {
            "complete": (
                len(case_rows) == 20
            ),
            "complete_case_count": len(
                case_rows
            ),
            "changed_comparison_count": (
                changed_comparisons
            ),
            "total_comparison_count": (
                total_comparisons
            ),
            "score_change_frequency_percent": round(
                changed_comparisons
                / total_comparisons
                * 100,
                2,
            ),
            "mean_absolute_score_change": round(
                mean(all_pairwise_changes),
                6,
            ),
            "maximum_absolute_score_change": max(
                all_pairwise_changes
            ),
        },
        case_rows,
    )


def deployment_decision(
    validation: dict[str, Any],
    repeatability: dict[str, Any],
) -> dict[str, Any]:
    """Determine whether the judge passes a gate."""

    correlation = validation.get(
        "spearman_correlation"
    )
    mean_difference = validation.get(
        "mean_absolute_difference"
    )
    change_frequency = repeatability.get(
        "score_change_frequency_percent"
    )

    passed = (
        validation.get("complete") is True
        and repeatability.get("complete") is True
        and correlation is not None
        and correlation >= 0.70
        and mean_difference is not None
        and mean_difference <= 0.75
        and change_frequency is not None
        and change_frequency <= 20.0
    )

    if passed:
        decision = (
            "The local judge passed the development "
            "deployment gate. Human review should still "
            "be retained for high-impact decisions."
        )
    else:
        decision = (
            "The local judge did not pass the full "
            "deployment gate. It may be used for "
            "development feedback, but additional human "
            "labels and review are required before using "
            "it as the only production-quality gate."
        )

    return {
        "passed": passed,
        "requirements": {
            "minimum_spearman_correlation": 0.70,
            "maximum_mean_absolute_difference": 0.75,
            "maximum_score_change_frequency_percent": 20.0,
        },
        "decision": decision,
        "additional_evidence_needed": (
            "Use more independently human-labeled "
            "clinical-trial cases, additional judges, "
            "and repeated tests on new questions."
        ),
    }


def main() -> None:
    """Judge 20 frozen cases three times."""

    ensure_hw10_directories()

    cases = load_json(
        EVAL_CASES_PATH
    )
    labels = load_human_labels()

    if not isinstance(cases, list):
        raise TypeError(
            "eval_cases.json must contain a list."
        )

    if len(cases) != 20:
        raise ValueError(
            "Exactly 20 evaluation cases are required."
        )

    raw_rows: list[dict[str, Any]] = []

    print(
        "DATA-260 Homework 10 Judge Validation"
    )
    print(f"Student: {STUDENT_NAME}")
    print(f"Judge: {JUDGE_MODEL}")
    print(f"Cases: {len(cases)}")
    print(f"Repeated runs: {JUDGE_REPEAT_COUNT}")

    for run_number in range(
        1,
        JUDGE_REPEAT_COUNT + 1,
    ):
        print(
            f"\n=== JUDGE RUN {run_number} ==="
        )

        for index, case in enumerate(
            cases,
            start=1,
        ):
            case_id = case["case_id"]
            label = labels.get(case_id)

            if label is None:
                raise ValueError(
                    f"No human label found for {case_id}."
                )

            print(
                f"[{index:02d}/20] {case_id}...",
                end=" ",
                flush=True,
            )

            result = evaluate_writer_draft(
                question=case["question"],
                writer_draft=case[
                    "writer_draft"
                ],
                reference_answer=case[
                    "reference_answer"
                ],
            )

            judge_score = result.score

            if judge_score is None:
                absolute_difference = None
            else:
                absolute_difference = abs(
                    label["human_score"]
                    - judge_score
                )

            row = {
                "run_number": run_number,
                "case_id": case_id,
                "category": case["category"],
                "human_score": label[
                    "human_score"
                ],
                "judge_score": judge_score,
                "absolute_difference": (
                    absolute_difference
                ),
                "judge_success": result.success,
                "judge_reason": result.reason,
                "judge_error_type": (
                    result.error_type
                ),
                "judge_error": result.error,
                "latency_ms": result.latency_ms,
            }

            raw_rows.append(row)

            print(
                
                    f"human={label['human_score']} "
                    f"judge={judge_score} "
                    f"success={result.success}"
                
            )

            write_json(
                CHECKPOINT_PATH,
                {
                    "completed_evaluations": len(
                        raw_rows
                    ),
                    "expected_evaluations": (
                        len(cases)
                        * JUDGE_REPEAT_COUNT
                    ),
                    "rows": raw_rows,
                },
            )

    validation = calculate_validation_metrics(
        raw_rows
    )
    repeatability, repeatability_rows = (
        calculate_repeatability(raw_rows)
    )
    gate = deployment_decision(
        validation,
        repeatability,
    )

    document = {
        "experiment": (
            "hw10_human_vs_judge_validation"
        ),
        "student": STUDENT_NAME,
        "sid4": 7801,
        "judge_framework": "DeepEval GEval",
        "judge_model": JUDGE_MODEL,
        "case_count": len(cases),
        "repeat_count": JUDGE_REPEAT_COUNT,
        "human_labels_frozen_before_judge": True,
        "validation": validation,
        "repeatability": repeatability,
        "deployment_gate": gate,
        "raw_results": raw_rows,
        "overall_passed": (
            validation["complete"]
            and repeatability["complete"]
        ),
    }

    write_json(
        JUDGE_VALIDATION_PATH,
        document,
    )
    write_score_csv(raw_rows)
    write_repeatability_csv(
        repeatability_rows
    )

    print("\n=== VALIDATION RESULTS ===")
    print(
        "Spearman correlation: "
        f"{validation['spearman_correlation']}"
    )
    print(
        "Mean absolute difference: "
        f"{validation['mean_absolute_difference']}"
    )
    print(
        "Score change frequency: "
        f"{repeatability['score_change_frequency_percent']}%"
    )
    print(
        "Mean absolute score change: "
        f"{repeatability['mean_absolute_score_change']}"
    )
    print(
        "Maximum absolute score change: "
        f"{repeatability['maximum_absolute_score_change']}"
    )
    print(
        "Deployment gate passed: "
        f"{gate['passed']}"
    )
    print(f"Decision: {gate['decision']}")
    print(
        f"Overall: {document['overall_passed']}"
    )
    print(f"JSON: {JUDGE_VALIDATION_PATH}")
    print(
        f"Scores: {JUDGE_VALIDATION_SCORES_PATH}"
    )
    print(
        f"Repeatability: {JUDGE_REPEATABILITY_PATH}"
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()