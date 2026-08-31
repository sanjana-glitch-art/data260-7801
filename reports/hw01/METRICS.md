# Homework 1 Metrics

## Experiment Configuration

| Setting | Value |
|---|---|
| Model | qwen3:4b |
| Fixed input file | reports/hw01/cases/nondeterminism_input.json |
| Runs at temperature 0.7 | 20 |
| Runs at temperature 0.0 | 20 |
| Total successful runs | 40 |
| Percentile method | Linear interpolation |

## Tag Variation

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---:|---:|
| Distinct tag sets | 11 | 1 |
| Tags appearing in all 20 runs | None | academic_performance, concentration_effects, sleep_duration |
| Tags appearing in exactly one run | academic_concentration, concentration_impact, concentration_metrics, concentration_outcomes, student_cognitive_function, student_concentration_studies, university_sleep_studies | None |

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
trial eligibility, safety status, or another consequential decision.
Those cases require consistent rules, validation, and human review.

## Raw Data

The complete per-run results are stored in:

- `reports/hw01/raw/nondeterminism_results.json`
- `reports/hw01/raw/nondeterminism_results.csv`
- `reports/hw01/raw/nondeterminism_metrics.json`