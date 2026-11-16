from __future__ import annotations

import csv
import json
import shutil
import subprocess
from code.hw10_config import (
    EVAL_CASES_PATH,
    HUMAN_LABELS_PATH,
    JUDGE_MAX_ATTEMPTS,
    JUDGE_REPEAT_COUNT,
    JUDGE_TIMEOUT_SECONDS,
    JUDGE_VALIDATION_PATH,
    LATENCY_EXPERIMENT_REQUEST_COUNT,
    LATENCY_RESULTS_PATH,
    PIPELINE_EVALUATION_PATH,
    REQUIRED_TRACES_PATH,
    ROOT_DIR,
    SID4,
    STUDENT_NAME,
    TRACE_PATH,
    VERIFICATION_PATH,
)
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class VerificationCheck:
    """One Homework 10 verification result."""

    name: str
    passed: bool
    details: str


def load_json(
    path: Path,
) -> Any:
    """Load one JSON document."""

    return json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )


def add_check(
    checks: list[VerificationCheck],
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Add and print one verification result."""

    check = VerificationCheck(
        name=name,
        passed=passed,
        details=details,
    )
    checks.append(check)

    status = "PASS" if passed else "FAIL"

    print(
        f"{status} | {name} | {details}"
    )


def verify_configuration(
    checks: list[VerificationCheck],
) -> None:
    """Verify personalized configuration."""

    passed = (
        STUDENT_NAME
        == "Sanjana Thummalapalli"
        and SID4 == 7801
        and JUDGE_REPEAT_COUNT == 3
        and JUDGE_MAX_ATTEMPTS >= 1
        and JUDGE_TIMEOUT_SECONDS > 0
    )

    add_check(
        checks,
        "personal_configuration",
        passed,
        (
            f"student={STUDENT_NAME}, SID4={SID4}, "
            f"repeats={JUDGE_REPEAT_COUNT}, "
            f"attempts={JUDGE_MAX_ATTEMPTS}, "
            f"timeout={JUDGE_TIMEOUT_SECONDS}"
        ),
    )


def verify_evaluation_cases(
    checks: list[VerificationCheck],
) -> None:
    """Verify the frozen 20-case dataset."""

    cases = load_json(EVAL_CASES_PATH)

    identifiers = {
        case.get("case_id")
        for case in cases
        if isinstance(case, dict)
    }

    required_fields = {
        "case_id",
        "category",
        "question",
        "plan",
        "writer_draft",
        "reference_answer",
        "expected_fields",
    }

    complete = all(
        isinstance(case, dict)
        and required_fields.issubset(case)
        for case in cases
    )

    passed = (
        isinstance(cases, list)
        and len(cases) == 20
        and len(identifiers) == 20
        and complete
    )

    add_check(
        checks,
        "frozen_evaluation_cases",
        passed,
        (
            f"cases={len(cases)}, "
            f"unique_ids={len(identifiers)}, "
            f"complete={complete}"
        ),
    )


def verify_human_labels(
    checks: list[VerificationCheck],
) -> None:
    """Verify all human labels are complete."""

    with HUMAN_LABELS_PATH.open(
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        rows = list(
            csv.DictReader(csv_file)
        )

    valid_rows = [
        row
        for row in rows
        if (
            row.get("case_id", "").strip()
            and row.get(
                "human_score",
                "",
            ).strip()
            in {"1", "2", "3", "4", "5"}
            and row.get(
                "human_reason",
                "",
            ).strip()
        )
    ]

    passed = (
        len(rows) == 20
        and len(valid_rows) == 20
    )

    add_check(
        checks,
        "human_labels",
        passed,
        (
            f"rows={len(rows)}, "
            f"valid_rows={len(valid_rows)}"
        ),
    )


def verify_frozen_commit(
    checks: list[VerificationCheck],
) -> None:
    """Verify cases and labels were committed."""

    git_executable = shutil.which("git")

    if git_executable is None:
        add_check(
            checks,
            "labels_frozen_before_judge",
            False,
            "Git executable was not found.",
        )
        return

    result = subprocess.run(
        [
            git_executable,
            "log",
            "-1",
            "--format=%H|%s",
            "--",
            "eval_cases.json",
            "human_labels.csv",
        ],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )

    commit_text = result.stdout.strip()

    passed = bool(commit_text)

    add_check(
        checks,
        "labels_frozen_before_judge",
        passed,
        (
            commit_text
            if commit_text
            else "No commit found."
        ),
    )


def verify_pipeline_evaluation(
    checks: list[VerificationCheck],
) -> None:
    """Verify Planner, Writer, and Reviewer scores."""

    document = load_json(
        PIPELINE_EVALUATION_PATH
    )
    evaluation = document.get(
        "evaluation",
        {},
    )

    plan_score = evaluation.get(
        "plan_quality",
        {},
    ).get("score")
    writer_score = evaluation.get(
        "writer_helpfulness",
        {},
    ).get("score")
    final_score = evaluation.get(
        "final_answer_helpfulness",
        {},
    ).get("score")

    passed = (
        document.get("success") is True
        and plan_score is not None
        and writer_score is not None
        and final_score is not None
    )

    add_check(
        checks,
        "pipeline_geval_evaluation",
        passed,
        (
            f"plan={plan_score}, "
            f"writer={writer_score}, "
            f"final={final_score}, "
            f"success={document.get('success')}"
        ),
    )

    difference = evaluation.get(
        "score_difference"
    )

    improvement_passed = (
        isinstance(difference, int)
        and difference == final_score - writer_score
    )

    add_check(
        checks,
        "final_vs_draft_improvement",
        improvement_passed,
        (
            f"draft={writer_score}, "
            f"final={final_score}, "
            f"difference={difference}"
        ),
    )


def verify_bounded_judge(
    checks: list[VerificationCheck],
) -> None:
    """Verify evaluator timeout and retry controls."""

    evaluator_path = (
        ROOT_DIR / "code" / "hw10_evaluator.py"
    )
    source = evaluator_path.read_text(
        encoding="utf-8-sig",
    )

    passed = all(
        marker in source
        for marker in (
            "maximum_attempts",
            "timeout_seconds",
            "process.terminate()",
            "JudgeTimeoutError",
            "QwenOllamaJudge",
            "think",
        )
    )

    add_check(
        checks,
        "bounded_local_judge",
        passed,
        (
            f"max_attempts={JUDGE_MAX_ATTEMPTS}, "
            f"timeout={JUDGE_TIMEOUT_SECONDS}, "
            "thinking_disabled=True"
        ),
    )


def verify_judge_validation(
    checks: list[VerificationCheck],
) -> None:
    """Verify human agreement and repeatability."""

    document = load_json(
        JUDGE_VALIDATION_PATH
    )
    validation = document.get(
        "validation",
        {},
    )
    repeatability = document.get(
        "repeatability",
        {},
    )

    correlation = validation.get(
        "spearman_correlation"
    )
    difference = validation.get(
        "mean_absolute_difference"
    )

    passed = (
        document.get("case_count") == 20
        and document.get("repeat_count") == 3
        and validation.get("complete") is True
        and correlation is not None
        and difference is not None
    )

    add_check(
        checks,
        "human_vs_judge_validation",
        passed,
        (
            f"cases={document.get('case_count')}, "
            f"Spearman={correlation}, "
            f"MAD={difference}"
        ),
    )

    change_frequency = repeatability.get(
        "score_change_frequency_percent"
    )
    mean_change = repeatability.get(
        "mean_absolute_score_change"
    )
    maximum_change = repeatability.get(
        "maximum_absolute_score_change"
    )

    repeatability_passed = (
        repeatability.get("complete") is True
        and change_frequency is not None
        and mean_change is not None
        and maximum_change is not None
    )

    add_check(
        checks,
        "judge_repeatability",
        repeatability_passed,
        (
            f"change_frequency={change_frequency}%, "
            f"mean_change={mean_change}, "
            f"max_change={maximum_change}"
        ),
    )

    gate = document.get(
        "deployment_gate",
        {},
    )

    gate_passed = (
        isinstance(gate.get("passed"), bool)
        and bool(gate.get("decision"))
        and bool(
            gate.get(
                "additional_evidence_needed"
            )
        )
    )

    add_check(
        checks,
        "judge_deployment_decision",
        gate_passed,
        (
            f"gate_passed={gate.get('passed')}; "
            f"decision={gate.get('decision')}"
        ),
    )


def verify_required_traces(
    checks: list[VerificationCheck],
) -> None:
    """Verify hit, miss, and failure traces."""

    document = load_json(
        REQUIRED_TRACES_PATH
    )

    cache_hit = document.get(
        "cache_hit_trace",
        {},
    )
    cache_miss = document.get(
        "successful_cache_miss_trace",
        {},
    )
    failed = document.get(
        "failed_trace",
        {},
    )

    passed = (
        document.get("overall_passed") is True
        and cache_hit.get("passed") is True
        and cache_miss.get("passed") is True
        and failed.get("passed") is True
    )

    add_check(
        checks,
        "required_trace_scenarios",
        passed,
        (
            f"hit={cache_hit.get('passed')}, "
            f"miss={cache_miss.get('passed')}, "
            f"failed={failed.get('passed')}"
        ),
    )

    expected_stages = [
        "cache_lookup",
        "planner",
        "writer",
        "reviewer",
        "evaluation",
    ]

    miss_trace_id = cache_miss.get(
        "trace_id"
    )
    miss_spans = cache_miss.get(
        "spans",
        [],
    )

    same_identifier = all(
        span.get("trace_id") == miss_trace_id
        for span in miss_spans
    )

    stage_order = [
        span.get("stage")
        for span in miss_spans
    ]

    propagation_passed = (
        same_identifier
        and stage_order == expected_stages
    )

    add_check(
        checks,
        "trace_id_propagation",
        propagation_passed,
        (
            f"trace_id={miss_trace_id}, "
            f"stages={stage_order}"
        ),
    )

    failed_spans = failed.get(
        "spans",
        [],
    )
    last_failed_span = (
        failed_spans[-1]
        if failed_spans
        else {}
    )

    failure_passed = (
        last_failed_span.get("status")
        == "failed"
        and bool(
            last_failed_span.get("error")
        )
        and bool(
            last_failed_span.get(
                "error_type"
            )
        )
    )

    add_check(
        checks,
        "failed_trace_error_details",
        failure_passed,
        (
            f"stage={last_failed_span.get('stage')}, "
            f"error_type="
            f"{last_failed_span.get('error_type')}, "
            f"error={last_failed_span.get('error')}"
        ),
    )


def verify_latency(
    checks: list[VerificationCheck],
) -> None:
    """Verify the 50-miss latency experiment."""

    document = load_json(
        LATENCY_RESULTS_PATH
    )

    request_count = document.get(
        "request_count"
    )
    miss_count = document.get(
        "confirmed_cache_miss_count"
    )
    unexpected_hits = document.get(
        "unexpected_cache_hit_count"
    )

    passed = (
        document.get("overall_passed") is True
        and request_count
        == LATENCY_EXPERIMENT_REQUEST_COUNT
        and miss_count
        == LATENCY_EXPERIMENT_REQUEST_COUNT
        and unexpected_hits == 0
    )

    add_check(
        checks,
        "fifty_confirmed_cache_misses",
        passed,
        (
            f"requests={request_count}, "
            f"misses={miss_count}, "
            f"unexpected_hits={unexpected_hits}"
        ),
    )

    summaries = document.get(
        "stage_summaries",
        [],
    )
    summary_by_stage = {
        summary.get("stage"): summary
        for summary in summaries
    }

    required_stages = {
        "cache_lookup",
        "planner",
        "writer",
        "reviewer",
        "queue_wait_total",
        "evaluation",
        "end_to_end",
    }

    stages_present = required_stages.issubset(
        summary_by_stage
    )

    percentiles_valid = all(
        summary_by_stage[stage].get(
            "p50_ms"
        )
        is not None
        and summary_by_stage[stage].get(
            "p95_ms"
        )
        is not None
        for stage in required_stages
        if stage in summary_by_stage
    )

    add_check(
        checks,
        "stage_p50_p95_metrics",
        stages_present and percentiles_valid,
        (
            f"stages={sorted(summary_by_stage)}, "
            f"percentiles_valid={percentiles_valid}"
        ),
    )

    cache_hit = document.get(
        "cache_hit_latency",
        {},
    )

    hit_passed = (
        cache_hit.get("sample_count", 0) > 0
        and cache_hit.get("p50_ms")
        is not None
        and cache_hit.get("p95_ms")
        is not None
    )

    add_check(
        checks,
        "separate_cache_hit_latency",
        hit_passed,
        (
            f"samples={cache_hit.get('sample_count')}, "
            f"p50={cache_hit.get('p50_ms')}, "
            f"p95={cache_hit.get('p95_ms')}"
        ),
    )

    dominant = document.get(
        "dominant_stage",
        {},
    )

    dominant_passed = (
        bool(dominant.get("stage"))
        and dominant.get(
            "percent_of_cache_miss_e2e"
        )
        is not None
        and bool(
            dominant.get("optimization")
        )
    )

    add_check(
        checks,
        "dominant_stage_analysis",
        dominant_passed,
        (
            f"stage={dominant.get('stage')}, "
            f"share="
            f"{dominant.get('percent_of_cache_miss_e2e')}%, "
            f"optimization="
            f"{dominant.get('optimization')}"
        ),
    )


def verify_dashboard(
    checks: list[VerificationCheck],
) -> None:
    """Verify required dashboard sections."""

    dashboard_path = (
        ROOT_DIR / "dashboard_hw10.py"
    )

    source = dashboard_path.read_text(
        encoding="utf-8-sig",
    )

    markers = [
        "@st.cache_data",
        "Summary",
        "Evaluation",
        "Trace Lookup",
        "Semantic Cache Hit Rate",
        "Spearman Correlation",
        "Enter a trace ID",
    ]

    passed = (
        dashboard_path.exists()
        and all(
            marker in source
            for marker in markers
        )
    )

    add_check(
        checks,
        "streamlit_dashboard",
        passed,
        (
            "summary, evaluation, trace lookup, "
            "cached loaders, and required metrics found"
        ),
    )


def verify_trace_file(
    checks: list[VerificationCheck],
) -> None:
    """Verify JSONL trace evidence exists."""

    if not TRACE_PATH.exists():
        add_check(
            checks,
            "jsonl_trace_evidence",
            False,
            "traces.jsonl was not found.",
        )
        return

    lines = [
        line
        for line in TRACE_PATH.read_text(
            encoding="utf-8-sig",
        ).splitlines()
        if line.strip()
    ]

    valid = True

    for line in lines:
        value = json.loads(line)

        required = {
            "trace_id",
            "stage",
            "start_time",
            "end_time",
            "duration_ms",
            "status",
            "error",
        }

        if not required.issubset(value):
            valid = False
            break

    add_check(
        checks,
        "jsonl_trace_evidence",
        bool(lines) and valid,
        (
            f"span_count={len(lines)}, "
            f"valid={valid}"
        ),
    )


def main() -> None:
    """Run all Homework 10 checks."""

    checks: list[VerificationCheck] = []

    print(
        "DATA-260 Homework 10 Verification"
    )

    verify_configuration(checks)
    verify_evaluation_cases(checks)
    verify_human_labels(checks)
    verify_frozen_commit(checks)
    verify_pipeline_evaluation(checks)
    verify_bounded_judge(checks)
    verify_judge_validation(checks)
    verify_required_traces(checks)
    verify_latency(checks)
    verify_dashboard(checks)
    verify_trace_file(checks)

    passed_count = sum(
        check.passed
        for check in checks
    )
    overall_passed = (
        passed_count == len(checks)
    )

    document = {
        "homework": 10,
        "student": STUDENT_NAME,
        "sid4": SID4,
        "checks": [
            asdict(check)
            for check in checks
        ],
        "passed_count": passed_count,
        "check_count": len(checks),
        "overall_passed": overall_passed,
        "generated_at": (
            datetime.now(UTC).isoformat()
        ),
    }

    VERIFICATION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    VERIFICATION_PATH.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        f"Passed: {passed_count}/{len(checks)}"
    )
    print(f"Overall: {overall_passed}")
    print(f"Saved: {VERIFICATION_PATH}")


if __name__ == "__main__":
    main()