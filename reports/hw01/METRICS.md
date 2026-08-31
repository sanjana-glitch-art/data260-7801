# Homework 1 Metrics

## Experiment Configuration

| Setting | Value |
|---|---|
| Model | qwen3:4b |
| Fixed input file | `reports/hw01/cases/nondeterminism_input.json` |
| Runs at temperature 0.7 | 20 |
| Runs at temperature 0.0 | 20 |
| Total successful runs | 40 |
| Percentile method | Linear interpolation |

## Tag Variation

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---:|---:|
| Distinct tag sets | 11 | 1 |
| Tags appearing in all 20 runs | None | `academic_performance`, `concentration_effects`, `sleep_duration` |
| Tags appearing in exactly one run | `academic_concentration`, `concentration_impact`, `concentration_metrics`, `concentration_outcomes`, `student_cognitive_function`, `student_concentration_studies`, `university_sleep_studies` | None |

## Latency

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---:|---:|
| Latency p50 | 5526.03 ms | 5105.43 ms |
| Latency p95 | 7654.37 ms | 5529.57 ms |
| Latency p99 | 18532.39 ms | 7052.89 ms |

## Interpretation

At temperature 0.7, two users submitting the same title and content may
receive different but related tag sets. For example, one user may receive
`sleep_quality`, `academic_performance`, and `university_students`, while
another may receive `sleep_duration`, `academic_performance`, and
`student_concentration`.

At temperature 0.0, identical input produced the same tag set in all 20
runs. This setting is more appropriate when repeatability is important.

Run-to-run variation is acceptable when generating alternative topical
tags for discovery or brainstorming because multiple descriptions may be
equally useful.

Variation is not acceptable when an output is used to determine clinical
trial eligibility, safety status, or another consequential decision. Those
cases require consistent rules, validation, and human review.

## Raw Data

The complete per-run results are stored in:

- `reports/hw01/raw/nondeterminism_results.json`
- `reports/hw01/raw/nondeterminism_results.csv`
- `reports/hw01/raw/nondeterminism_metrics.json`

## Model Client and Token Accounting

### Per-Turn Results

| Turn | Input Tokens | Output Tokens | Total Tokens | Cumulative Input | Cumulative Output | Serialized History Length |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 134 | 46 | 180 | 134 | 46 | 249 |
| 2 | 191 | 33 | 224 | 325 | 79 | 469 |
| 3 | 241 | 61 | 302 | 566 | 140 | 881 |
| 4 | 313 | 73 | 386 | 879 | 213 | 1,298 |
| 5 | 403 | 53 | 456 | 1,282 | 266 | 1,667 |

### Statistics After Turn 3

- Turn count: 3
- Cumulative input tokens: 566
- Cumulative output tokens: 140
- Cumulative total tokens: 706
- Serialized conversation-history length: 881 characters

### Statistics After Turn 5

- Turn count: 5
- Cumulative input tokens: 1,282
- Cumulative output tokens: 266
- Cumulative total tokens: 1,548
- Serialized conversation-history length: 1,667 characters

### AGENT.md Verification

All five model responses passed the strict bullet-only verification.