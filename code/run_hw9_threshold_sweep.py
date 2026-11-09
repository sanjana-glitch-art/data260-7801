from __future__ import annotations

import csv
import json
import time
from code.hw9_semantic_cache import (
    SemanticResponseCache,
)
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

CASES_PATH = Path("cache_cases.yaml")

JSON_OUTPUT = Path(
    "reports/hw09/raw/"
    "threshold_sweep_results.json"
)

CSV_OUTPUT = Path(
    "reports/hw09/raw/"
    "threshold_sweep_results.csv"
)

FALSE_HIT_OUTPUT = Path(
    "reports/hw09/raw/"
    "false_hit_example.json"
)

THRESHOLDS = [
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
]

OBSERVED_CACHE_HIT_LATENCY_MS = 7.922

OBSERVED_CACHE_MISS_LATENCY_MS = (
    7105.463
)

CACHE_MISS_COST = 0.02
FALSE_HIT_SUPPORT_COST = 1.00


def load_cases() -> list[dict[str, Any]]:
    """Load the committed labeled cases."""

    document = yaml.safe_load(
        CASES_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    cases = document["cases"]

    if len(cases) != 40:
        raise ValueError(
            "cache_cases.yaml must contain "
            "exactly 40 cases."
        )

    return cases


def run_case(
    cache: SemanticResponseCache,
    case: dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
    """Evaluate one isolated query pair."""

    cache.clear_semantic_cache()

    data_version = (
        cache.current_data_version()
    )

    cache.store(
        case["cached_query"],
        case["cached_answer"],
        data_version,
    )

    started_at = time.perf_counter()

    match = cache.search(
        case["incoming_query"]
    )

    lookup_latency_ms = (
        time.perf_counter()
        - started_at
    ) * 1000

    similarity = (
        float(match["similarity"])
        if match is not None
        else 0.0
    )

    predicted_hit = (
        match is not None
        and similarity >= threshold
    )

    should_hit = bool(
        case["should_hit"]
    )

    false_hit = (
        predicted_hit
        and not should_hit
    )

    false_miss = (
        not predicted_hit
        and should_hit
    )

    if predicted_hit:
        returned_answer = (
            match["answer"]
        )

        estimated_latency_ms = (
            lookup_latency_ms
        )
    else:
        returned_answer = (
            case["correct_answer"]
        )

        estimated_latency_ms = (
            lookup_latency_ms
            + OBSERVED_CACHE_MISS_LATENCY_MS
        )

    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "cached_query": (
            case["cached_query"]
        ),
        "incoming_query": (
            case["incoming_query"]
        ),
        "should_hit": should_hit,
        "predicted_hit": predicted_hit,
        "similarity": round(
            similarity,
            6,
        ),
        "false_hit": false_hit,
        "false_miss": false_miss,
        "lookup_latency_ms": round(
            lookup_latency_ms,
            3,
        ),
        "estimated_end_to_end_latency_ms": (
            round(
                estimated_latency_ms,
                3,
            )
        ),
        "cached_answer": (
            case["cached_answer"]
        ),
        "returned_answer": returned_answer,
        "correct_answer": (
            case["correct_answer"]
        ),
    }


def run_threshold(
    cache: SemanticResponseCache,
    cases: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    """Evaluate all cases at one threshold."""

    case_results = [
        run_case(
            cache,
            case,
            threshold,
        )
        for case in cases
    ]

    hits = [
        result
        for result in case_results
        if result["predicted_hit"]
    ]

    misses = [
        result
        for result in case_results
        if not result["predicted_hit"]
    ]

    false_hits = [
        result
        for result in case_results
        if result["false_hit"]
    ]

    false_misses = [
        result
        for result in case_results
        if result["false_miss"]
    ]

    should_miss_count = sum(
        not bool(case["should_hit"])
        for case in cases
    )

    hit_rate = (
        len(hits)
        / len(case_results)
        * 100
    )

    false_hit_rate = (
        len(false_hits)
        / should_miss_count
        * 100
    )

    mean_latency = mean(
        result[
            "estimated_end_to_end_latency_ms"
        ]
        for result in case_results
    )

    total_cost = (
        len(misses)
        * CACHE_MISS_COST
        + len(false_hits)
        * FALSE_HIT_SUPPORT_COST
    )

    return {
        "threshold": threshold,
        "case_count": len(case_results),
        "hit_count": len(hits),
        "miss_count": len(misses),
        "false_hit_count": len(
            false_hits
        ),
        "false_miss_count": len(
            false_misses
        ),
        "hit_rate_percent": round(
            hit_rate,
            2,
        ),
        "false_hit_rate_percent": round(
            false_hit_rate,
            2,
        ),
        "mean_latency_ms": round(
            mean_latency,
            3,
        ),
        "total_cost": round(
            total_cost,
            2,
        ),
        "case_results": case_results,
    }


def main() -> None:
    """Run the five-threshold experiment."""

    cases = load_cases()
    cache = SemanticResponseCache()

    try:
        print(
            "DATA-260 Homework 9 Part 3"
        )
        print(
            "Student: Sanjana Thummalapalli"
        )
        print("SID4: 7801")
        print(f"Cases: {len(cases)}")
        print(
            "Cache-miss cost: "
            f"${CACHE_MISS_COST:.2f}"
        )
        print(
            "False-hit support cost: "
            f"${FALSE_HIT_SUPPORT_COST:.2f}"
        )

        threshold_results = []

        for threshold in THRESHOLDS:
            print(
                "\nRunning threshold "
                f"{threshold:.2f}..."
            )

            result = run_threshold(
                cache,
                cases,
                threshold,
            )

            threshold_results.append(
                result
            )

            print(
                "Hit rate: "
                f"{result['hit_rate_percent']:.2f}%"
            )
            print(
                "False-hit rate: "
                f"{result['false_hit_rate_percent']:.2f}%"
            )
            print(
                "Mean latency: "
                f"{result['mean_latency_ms']:.3f} ms"
            )
            print(
                "Total cost: "
                f"${result['total_cost']:.2f}"
            )

        best_result = min(
            threshold_results,
            key=lambda item: (
                item["total_cost"],
                item["false_hit_rate_percent"],
                item["mean_latency_ms"],
            ),
        )

        all_false_hits = [
            {
                "threshold": result[
                    "threshold"
                ],
                **case_result,
            }
            for result in threshold_results
            for case_result in result[
                "case_results"
            ]
            if case_result["false_hit"]
        ]

        false_hit_example = (
            max(
                all_false_hits,
                key=lambda item: item[
                    "similarity"
                ],
            )
            if all_false_hits
            else None
        )

        output = {
            "experiment": (
                "hw9_threshold_sweep"
            ),
            "student": (
                "Sanjana Thummalapalli"
            ),
            "sid4": 7801,
            "case_count": len(cases),
            "thresholds": THRESHOLDS,
            "latency_method": (
                "Measured Redis vector lookup "
                "latency plus the observed Part 2 "
                "non-cached agent latency for "
                "cache misses."
            ),
            "observed_cache_hit_latency_ms": (
                OBSERVED_CACHE_HIT_LATENCY_MS
            ),
            "observed_cache_miss_latency_ms": (
                OBSERVED_CACHE_MISS_LATENCY_MS
            ),
            "cost_model": {
                "cache_miss_cost": (
                    CACHE_MISS_COST
                ),
                "false_hit_support_cost": (
                    FALSE_HIT_SUPPORT_COST
                ),
                "justification": (
                    "A miss costs local model "
                    "compute and latency. A false "
                    "hit has a larger support and "
                    "correction cost because an "
                    "incorrect clinical-trial "
                    "answer reaches the user."
                ),
            },
            "recommended_threshold": (
                best_result["threshold"]
            ),
            "recommended_threshold_reason": (
                "This threshold produced the "
                "lowest total modeled cost, with "
                "false-hit rate used as the first "
                "safety tie-breaker."
            ),
            "results": threshold_results,
        }

        JSON_OUTPUT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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
                    "threshold",
                    "hit_rate_percent",
                    "false_hit_rate_percent",
                    "mean_latency_ms",
                    "total_cost",
                    "hit_count",
                    "miss_count",
                    "false_hit_count",
                    "false_miss_count",
                ],
            )

            writer.writeheader()

            for result in threshold_results:
                writer.writerow({
                    key: result[key]
                    for key in writer.fieldnames
                })

        FALSE_HIT_OUTPUT.write_text(
            json.dumps(
                false_hit_example,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "\n=== THRESHOLD TABLE ==="
        )
        print(
            "Threshold | Hit rate | "
            "False-hit rate | "
            "Mean latency | Total cost"
        )

        for result in threshold_results:
            print(
                f"{result['threshold']:.2f}"
                " | "
                f"{result['hit_rate_percent']:.2f}%"
                " | "
                f"{result['false_hit_rate_percent']:.2f}%"
                " | "
                f"{result['mean_latency_ms']:.3f} ms"
                " | "
                f"${result['total_cost']:.2f}"
            )

        print(
            "\nRecommended threshold: "
            f"{best_result['threshold']:.2f}"
        )
        print(f"JSON: {JSON_OUTPUT}")
        print(f"CSV: {CSV_OUTPUT}")
        print(
            "False hit: "
            f"{FALSE_HIT_OUTPUT}"
        )
    finally:
        cache.clear_semantic_cache()
        cache.close()


if __name__ == "__main__":
    main()
