from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from code.agent_graph import (  # noqa: E402
    initialize_state,
    run_workflow
)
from src.model_client import ModelClient  # noqa: E402


DEFAULT_TITLE = (
    "Sleep Quality and Academic Performance Study"
)

DEFAULT_CONTENT = (
    "This clinical trial studies how sleep duration "
    "and sleep quality affect concentration, memory, "
    "and academic performance among university students."
)


def parse_arguments() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run the HW2 stateful Planner-Reviewer graph."
        )
    )

    parser.add_argument(
        "--model",
        default="qwen3:4b"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0
    )

    parser.add_argument(
        "--turn-ceiling",
        type=int,
        default=2
    )

    parser.add_argument(
        "--title",
        default=DEFAULT_TITLE
    )

    parser.add_argument(
        "--content",
        default=DEFAULT_CONTENT
    )

    parser.add_argument(
        "--email",
        default="sanjana@example.edu"
    )

    parser.add_argument(
        "--force-reviewer-issue",
        action="store_true"
    )

    return parser.parse_args()


def public_final_state(
    final_state: dict
) -> dict:
    """Remove the nonserializable model client."""

    return {
        key: value
        for key, value in final_state.items()
        if key != "llm"
    }


def main() -> None:
    """Create the client, initialize state, and stream the graph."""

    arguments = parse_arguments()

    client = ModelClient(
        model=arguments.model,
        temperature=arguments.temperature,
        num_ctx=4096,
        num_predict=256
    )

    initial_state = initialize_state(
        title=arguments.title,
        content=arguments.content,
        email=arguments.email,
        task=(
            "Generate three topical tags and a concise "
            "summary for this clinical-trial listing."
        ),
        llm=client,
        strict=True,
        turn_ceiling=arguments.turn_ceiling,
        force_reviewer_issue=(
            arguments.force_reviewer_issue
        )
    )

    started = perf_counter()

    final_state = run_workflow(
        initial_state,
        show_stream=True
    )

    elapsed_ms = (
        perf_counter() - started
    ) * 1000

    print(
        "\n=== FINAL GRAPH STATE ==="
    )

    print(
        json.dumps(
            public_final_state(final_state),
            indent=2,
            default=str
        )
    )

    print(
        f"\nTotal graph latency: "
        f"{elapsed_ms:.2f} ms"
    )

    print(
        "Model statistics:"
    )

    print(
        json.dumps(
            client.get_stats(),
            indent=2
        )
    )


if __name__ == "__main__":
    main()