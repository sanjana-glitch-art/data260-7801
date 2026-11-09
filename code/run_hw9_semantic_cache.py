from __future__ import annotations

import json
from code.hw7_agent import run_agent
from code.hw9_semantic_cache import (
    SemanticResponseCache,
)
from pathlib import Path
from statistics import mean
from typing import Any

OUTPUT_PATH = Path(
    "reports/hw09/raw/"
    "semantic_cache_results.json"
)


QUERIES = [
    "Find the sleep clinical trial.",
    "Find the sleep clinical trial.",
    "Which trial studies sleep quality?",
    "Summarize the clinical trial phases.",
    "Summarize the clinical trial phases.",
    "Find the digital wellness trial.",
    "Find the digital wellness trial.",
    "Find the remote monitoring study.",
    "Which study uses remote monitoring?",
    "Find the memory and cognitive trial.",
]


def agent_answer(
    question: str,
) -> str:
    """Run the existing local-model agent."""

    result = run_agent(
        question,
        run_label="hw9-semantic-cache",
    )

    return str(result["answer"])


def main() -> None:
    """Run the Part 2 cache demonstration."""

    cache = SemanticResponseCache(
        threshold=0.85
    )

    try:
        deleted = (
            cache.clear_semantic_cache()
        )

        print(
            "DATA-260 Homework 9 Part 2"
        )
        print(
            "Student: Sanjana Thummalapalli"
        )
        print("SID4: 7801")
        print(
            "Threshold: 0.85"
        )
        print(
            f"Cleared entries: {deleted}"
        )

        results: list[dict[str, Any]] = []

        for number, query in enumerate(
            QUERIES,
            start=1,
        ):
            print(
                f"\n=== Query {number} ==="
            )
            print(f"Question: {query}")

            response = cache.answer(
                query,
                agent_answer,
            )

            results.append(response)

            print(
                "Cached: "
                f"{response['is_cached']}"
            )
            print(
                "Similarity: "
                f"{response['similarity']}"
            )
            print(
                "Latency: "
                f"{response['latency_ms']} ms"
            )
            print(
                "Answer: "
                f"{response['answer']}"
            )

        hits = [
            result
            for result in results
            if result["is_cached"]
        ]

        misses = [
            result
            for result in results
            if not result["is_cached"]
        ]

        hit_rate = (
            len(hits)
            / len(results)
            * 100
        )

        average_hit_latency = (
            mean(
                result["latency_ms"]
                for result in hits
            )
            if hits
            else 0.0
        )

        average_miss_latency = (
            mean(
                result["latency_ms"]
                for result in misses
            )
            if misses
            else 0.0
        )

        summary = {
            "experiment": (
                "hw9_semantic_cache"
            ),
            "threshold": 0.85,
            "query_count": len(results),
            "cache_hits": len(hits),
            "cache_misses": len(misses),
            "cache_hit_rate_percent": round(
                hit_rate,
                2,
            ),
            "average_cached_latency_ms": round(
                average_hit_latency,
                3,
            ),
            "average_non_cached_latency_ms": (
                round(
                    average_miss_latency,
                    3,
                )
            ),
            "results": results,
        }

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT_PATH.write_text(
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "\n=== CACHE PERFORMANCE ==="
        )
        print(
            f"Queries: {len(results)}"
        )
        print(
            f"Cache hits: {len(hits)}"
        )
        print(
            f"Cache misses: {len(misses)}"
        )
        print(
            "Cache hit rate: "
            f"{hit_rate:.2f}%"
        )
        print(
            "Average cached latency: "
            f"{average_hit_latency:.3f} ms"
        )
        print(
            "Average non-cached latency: "
            f"{average_miss_latency:.3f} ms"
        )
        print(f"Saved: {OUTPUT_PATH}")
    finally:
        cache.close()


if __name__ == "__main__":
    main()
