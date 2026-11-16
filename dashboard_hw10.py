from __future__ import annotations

import json
from code.hw10_config import (
    JUDGE_VALIDATION_PATH,
    LATENCY_RESULTS_PATH,
    LATENCY_SUMMARY_PATH,
    PIPELINE_EVALUATION_PATH,
    REQUIRED_TRACES_PATH,
    STUDENT_NAME,
    TRACE_PATH,
)
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="DATA-260 HW10 Dashboard",
    page_icon="📊",
    layout="wide",
)


def file_version(path: Path) -> float:
    """Return a file timestamp for cache invalidation."""

    if not path.exists():
        return 0.0

    return path.stat().st_mtime


@st.cache_data
def load_json(
    path_text: str,
    modified_time: float,
) -> dict[str, Any]:
    """Load one JSON document."""

    del modified_time

    path = Path(path_text)

    if not path.exists():
        return {}

    value = json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )

    if not isinstance(value, dict):
        return {}

    return value


@st.cache_data
def load_jsonl(
    path_text: str,
    modified_time: float,
) -> list[dict[str, Any]]:
    """Load valid JSON objects from JSON Lines."""

    del modified_time

    path = Path(path_text)

    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    with path.open(
        encoding="utf-8-sig",
    ) as input_file:
        for line in input_file:
            stripped = line.strip()

            if not stripped:
                continue

            value = json.loads(stripped)

            if isinstance(value, dict):
                rows.append(value)

    return rows


@st.cache_data
def load_csv(
    path_text: str,
    modified_time: float,
) -> pd.DataFrame:
    """Load one CSV file."""

    del modified_time

    path = Path(path_text)

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def parse_timestamp(
    value: Any,
) -> datetime | None:
    """Parse one ISO timestamp."""

    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def recent_trace_metrics(
    spans: list[dict[str, Any]],
    *,
    hours: int = 24,
) -> dict[str, Any]:
    """Calculate metrics for a recent time window."""

    cutoff = datetime.now(UTC) - timedelta(
        hours=hours
    )

    recent_spans = []

    for span in spans:
        timestamp = parse_timestamp(
            span.get("start_time")
        )

        if (
            timestamp is not None
            and timestamp >= cutoff
        ):
            recent_spans.append(span)

    trace_ids = {
        str(span["trace_id"])
        for span in recent_spans
        if span.get("trace_id")
    }

    failed_trace_ids = {
        str(span["trace_id"])
        for span in recent_spans
        if (
            span.get("trace_id")
            and span.get("status") == "failed"
        )
    }

    cache_spans = [
        span
        for span in recent_spans
        if span.get("stage") == "cache_lookup"
    ]

    cache_hits = sum(
        span.get("cache_result") == "hit"
        for span in cache_spans
    )
    cache_misses = sum(
        span.get("cache_result") == "miss"
        for span in cache_spans
    )

    cache_total = cache_hits + cache_misses

    if cache_total:
        hit_rate = (
            cache_hits
            / cache_total
            * 100
        )
    else:
        hit_rate = 0.0

    if trace_ids:
        error_rate = (
            len(failed_trace_ids)
            / len(trace_ids)
            * 100
        )
    else:
        error_rate = 0.0

    return {
        "window_hours": hours,
        "request_count": len(trace_ids),
        "span_count": len(recent_spans),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate_percent": round(
            hit_rate,
            2,
        ),
        "failed_trace_count": len(
            failed_trace_ids
        ),
        "error_rate_percent": round(
            error_rate,
            2,
        ),
    }


def find_stage(
    summaries: list[dict[str, Any]],
    stage: str,
) -> dict[str, Any]:
    """Find one stage summary."""

    for summary in summaries:
        if summary.get("stage") == stage:
            return summary

    return {}


def show_summary_tab(
    spans: list[dict[str, Any]],
    latency: dict[str, Any],
) -> None:
    """Render the operational summary."""

    st.header("Operational Summary")

    recent = recent_trace_metrics(
        spans,
        hours=24,
    )

    summaries = latency.get(
        "stage_summaries",
        [],
    )
    end_to_end = find_stage(
        summaries,
        "end_to_end",
    )
    cache_hit = latency.get(
        "cache_hit_latency",
        {},
    )

    first_row = st.columns(4)

    first_row[0].metric(
        "Recent Requests",
        recent["request_count"],
        help=(
            "Unique trace IDs during the last "
            "24 hours."
        ),
    )
    first_row[1].metric(
        "Cache Hits",
        recent["cache_hits"],
    )
    first_row[2].metric(
        "Cache Misses",
        recent["cache_misses"],
    )
    first_row[3].metric(
        "Semantic Cache Hit Rate",
        (
            f"{recent['cache_hit_rate_percent']}"
            "%"
        ),
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Error Rate",
        f"{recent['error_rate_percent']}%",
    )
    second_row[1].metric(
        "Cache-Miss E2E p50",
        (
            f"{end_to_end.get('p50_ms', 0):,.3f}"
            " ms"
        ),
    )
    second_row[2].metric(
        "Cache-Miss E2E p95",
        (
            f"{end_to_end.get('p95_ms', 0):,.3f}"
            " ms"
        ),
    )
    second_row[3].metric(
        "Cache-Hit p50",
        (
            f"{cache_hit.get('p50_ms', 0):,.3f}"
            " ms"
        ),
    )

    st.subheader("Metric Definitions and Sources")

    source_rows = [
        {
            "Metric": "Recent request count",
            "Time window": "Last 24 hours",
            "Data source": (
                "Unique trace_id values in "
                "reports/hw10/raw/traces.jsonl"
            ),
        },
        {
            "Metric": "Cache hits and misses",
            "Time window": "Last 24 hours",
            "Data source": (
                "cache_lookup spans in traces.jsonl"
            ),
        },
        {
            "Metric": "Error rate",
            "Time window": "Last 24 hours",
            "Data source": (
                "Unique traces containing at least "
                "one failed span"
            ),
        },
        {
            "Metric": "Cache-miss latency",
            "Time window": (
                "Fixed 50-request experiment"
            ),
            "Data source": (
                "latency_experiment.json"
            ),
        },
        {
            "Metric": "Cache-hit latency",
            "Time window": (
                "Fixed 20-request Redis sample"
            ),
            "Data source": (
                "latency_experiment.json"
            ),
        },
    ]

    st.dataframe(
        pd.DataFrame(source_rows),
        hide_index=True,
        width="stretch",
    )

    if summaries:
        st.subheader(
            "Cache-Miss Stage Latency"
        )

        summary_frame = pd.DataFrame(
            summaries
        )

        st.dataframe(
            summary_frame,
            hide_index=True,
            width="stretch",
        )

        chart_frame = (
            summary_frame[
                summary_frame["stage"]
                != "end_to_end"
            ][
                [
                    "stage",
                    "p50_ms",
                    "p95_ms",
                ]
            ]
            .set_index("stage")
        )

        st.bar_chart(chart_frame)

    dominant = latency.get(
        "dominant_stage",
        {},
    )

    if dominant:
        st.info(
            
                f"Dominant stage: "
                f"**{dominant.get('stage')}** at "
                f"{dominant.get('percent_of_cache_miss_e2e')}% "
                "of cache-miss end-to-end latency.\n\n"
                f"Optimization: "
                f"{dominant.get('optimization')}"
            
        )


def show_evaluation_tab(
    pipeline: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    """Render pipeline and judge evaluation results."""

    st.header("Automated Evaluation")

    evaluation = pipeline.get(
        "evaluation",
        {},
    )

    score_columns = st.columns(4)

    score_columns[0].metric(
        "Plan Quality",
        (
            f"{evaluation.get('plan_quality', {}).get('score', 0)}/5"
        ),
    )
    score_columns[1].metric(
        "Writer Helpfulness",
        (
            f"{evaluation.get('writer_helpfulness', {}).get('score', 0)}/5"
        ),
    )
    score_columns[2].metric(
        "Final Helpfulness",
        (
            f"{evaluation.get('final_answer_helpfulness', {}).get('score', 0)}/5"
        ),
    )
    score_columns[3].metric(
        "Final − Draft",
        evaluation.get(
            "score_difference",
            0,
        ),
    )

    st.subheader("Planner–Writer–Reviewer Result")

    st.markdown("**Question**")
    st.write(pipeline.get("question", ""))

    st.markdown("**Planner plan**")

    for index, step in enumerate(
        pipeline.get("plan", []),
        start=1,
    ):
        st.write(f"{index}. {step}")

    left, right = st.columns(2)

    with left:
        st.markdown("**Writer draft**")
        st.write(
            pipeline.get(
                "writer_draft",
                "",
            )
        )
        st.caption(
            evaluation.get(
                "writer_helpfulness",
                {},
            ).get(
                "reason",
                "",
            )
        )

    with right:
        st.markdown("**Reviewer final answer**")
        st.write(
            pipeline.get(
                "final_answer",
                "",
            )
        )
        st.caption(
            evaluation.get(
                "final_answer_helpfulness",
                {},
            ).get(
                "reason",
                "",
            )
        )

    st.success(
        evaluation.get(
            "improvement_interpretation",
            "",
        )
    )

    st.divider()
    st.subheader("Human-versus-Judge Validation")

    validation_metrics = validation.get(
        "validation",
        {},
    )
    repeatability = validation.get(
        "repeatability",
        {},
    )
    gate = validation.get(
        "deployment_gate",
        {},
    )

    validation_columns = st.columns(4)

    validation_columns[0].metric(
        "Spearman Correlation",
        validation_metrics.get(
            "spearman_correlation",
            0,
        ),
    )
    validation_columns[1].metric(
        "Mean Absolute Difference",
        validation_metrics.get(
            "mean_absolute_difference",
            0,
        ),
    )
    validation_columns[2].metric(
        "Score-Change Frequency",
        (
            f"{repeatability.get('score_change_frequency_percent', 0)}%"
        ),
    )
    validation_columns[3].metric(
        "Maximum Score Change",
        repeatability.get(
            "maximum_absolute_score_change",
            0,
        ),
    )

    if gate.get("passed"):
        st.success(
            "Development deployment gate: PASS"
        )
    else:
        st.warning(
            "Development deployment gate: REVIEW"
        )

    st.write(gate.get("decision", ""))

    raw_results = validation.get(
        "raw_results",
        [],
    )

    if raw_results:
        score_frame = pd.DataFrame(
            raw_results
        )

        first_run = score_frame[
            score_frame["run_number"] == 1
        ][
            [
                "case_id",
                "category",
                "human_score",
                "judge_score",
                "absolute_difference",
                "judge_success",
            ]
        ]

        st.subheader(
            "Per-Case Scores: First Judge Run"
        )

        st.dataframe(
            first_run,
            hide_index=True,
            width="stretch",
        )

        comparison_chart = first_run[
            [
                "case_id",
                "human_score",
                "judge_score",
            ]
        ].set_index("case_id")

        st.line_chart(comparison_chart)

    st.info(
        
            "Interpretation: the Planner produced a "
            "complete plan, the Writer draft omitted "
            "two requested facts, and the Reviewer "
            "corrected the omission. Human-versus-judge "
            "agreement was strong, and three repeated "
            "runs showed low score variability."
        
    )


def show_trace_tab(
    spans: list[dict[str, Any]],
    required: dict[str, Any],
) -> None:
    """Render trace lookup and full stage journey."""

    st.header("Trace Lookup")

    required_ids = required.get(
        "trace_ids",
        {},
    )

    st.markdown("**Required demonstration traces**")

    st.code(
        "\n".join(
            [
                (
                    "Cache hit: "
                    f"{required_ids.get('cache_hit', '')}"
                ),
                (
                    "Successful cache miss: "
                    f"{required_ids.get('successful_cache_miss', '')}"
                ),
                (
                    "Failed trace: "
                    f"{required_ids.get('failed', '')}"
                ),
            ]
        ),
        language="text",
    )

    default_trace = required_ids.get(
        "successful_cache_miss",
        "",
    )

    trace_id = st.text_input(
        "Enter a trace ID",
        value=default_trace,
    ).strip()

    if not trace_id:
        st.info("Enter a trace ID.")
        return

    matching = [
        span
        for span in spans
        if span.get("trace_id") == trace_id
    ]

    matching.sort(
        key=lambda span: str(
            span.get("start_time", "")
        )
    )

    if not matching:
        st.error(
            "No spans were found for this trace ID."
        )
        return

    cache_result = next(
        (
            span.get("cache_result")
            for span in matching
            if span.get("stage")
            == "cache_lookup"
        ),
        None,
    )

    failed = any(
        span.get("status") == "failed"
        for span in matching
    )

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        "Span Count",
        len(matching),
    )
    summary_columns[1].metric(
        "Cache Result",
        cache_result or "not applicable",
    )
    summary_columns[2].metric(
        "Final Status",
        "failed" if failed else "success",
    )
    summary_columns[3].metric(
        "Total Span Duration",
        (
            f"{sum(float(span.get('duration_ms', 0)) for span in matching):,.3f} ms"
        ),
    )

    display_rows = []

    for order, span in enumerate(
        matching,
        start=1,
    ):
        display_rows.append(
            {
                "Order": order,
                "Stage": span.get("stage"),
                "Start": span.get("start_time"),
                "End": span.get("end_time"),
                "Duration ms": span.get(
                    "duration_ms"
                ),
                "Status": span.get("status"),
                "Cache": span.get(
                    "cache_result"
                ),
                "Error type": span.get(
                    "error_type"
                ),
                "Error": span.get("error"),
            }
        )

    st.subheader("Stage Journey")

    st.dataframe(
        pd.DataFrame(display_rows),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Span Metadata")

    for span in matching:
        label = (
            f"{span.get('stage')} — "
            f"{span.get('status')}"
        )

        with st.expander(label):
            st.json(span)


def main() -> None:
    """Render the Homework 10 dashboard."""

    spans = load_jsonl(
        str(TRACE_PATH),
        file_version(TRACE_PATH),
    )
    latency = load_json(
        str(LATENCY_RESULTS_PATH),
        file_version(LATENCY_RESULTS_PATH),
    )
    pipeline = load_json(
        str(PIPELINE_EVALUATION_PATH),
        file_version(
            PIPELINE_EVALUATION_PATH
        ),
    )
    validation = load_json(
        str(JUDGE_VALIDATION_PATH),
        file_version(
            JUDGE_VALIDATION_PATH
        ),
    )
    required = load_json(
        str(REQUIRED_TRACES_PATH),
        file_version(
            REQUIRED_TRACES_PATH
        ),
    )

    # Load once so the dashboard cache also covers
    # the stage-summary CSV required by the assignment.
    load_csv(
        str(LATENCY_SUMMARY_PATH),
        file_version(
            LATENCY_SUMMARY_PATH
        ),
    )

    st.title(
        "DATA-260 Homework 10 Dashboard"
    )
    st.caption(
        
            f"{STUDENT_NAME} | SID4: 7801 | "
            "Clinical Trials"
        
    )

    summary_tab, evaluation_tab, trace_tab = (
        st.tabs(
            [
                "Summary",
                "Evaluation",
                "Trace Lookup",
            ]
        )
    )

    with summary_tab:
        show_summary_tab(
            spans,
            latency,
        )

    with evaluation_tab:
        show_evaluation_tab(
            pipeline,
            validation,
        )

    with trace_tab:
        show_trace_tab(
            spans,
            required,
        )


if __name__ == "__main__":
    main()