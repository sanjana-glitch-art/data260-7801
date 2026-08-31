
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.model_client import ModelClient


BULLET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bullets": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "minItems": 1,
            "maxItems": 8
        }
    },
    "required": ["bullets"],
    "additionalProperties": False
}

TOKEN_LOG_PATH = Path(
    "reports/hw01/raw/client_token_counts.json"
)

def load_system_prompt() -> str:
    """Load code-review instructions from AGENT.md."""
    path = Path("AGENT.md")

    if not path.exists():
        raise FileNotFoundError(
            "AGENT.md was not found."
        )

    return path.read_text(
        encoding="utf-8"
    ).strip()


def render_bullets(content: str) -> str:
    """Convert the structured model response into bullet lines."""
    parsed = json.loads(content)
    raw_bullets = parsed.get("bullets", [])

    bullets: list[str] = []

    for raw_bullet in raw_bullets:
        bullet = str(raw_bullet).strip()

        # Prevent duplicate bullet markers.
        bullet = bullet.removeprefix("-").strip()
        bullet = bullet.removeprefix("*").strip()

        if bullet:
            bullets.append(f"- {bullet}")

    if not bullets:
        raise ValueError(
            "The model returned no review bullets."
        )

    return "\n".join(bullets)


def is_bullet_only(text: str) -> bool:
    """Verify every nonempty line begins with a bullet."""
    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    return bool(lines) and all(
        line.startswith("- ")
        for line in lines
    )


def serialized_history_length(
    history: list[dict[str, str]]
) -> int:
    """Return serialized conversation-history length."""
    serialized = json.dumps(
        history,
        ensure_ascii=False
    )

    return len(serialized)


def print_stats(
    client: ModelClient,
    history: list[dict[str, str]]
) -> None:
    """Print statistics without changing history."""
    stats = client.get_stats()

    print("\n--- Statistics ---")
    print(f'Model: {stats["model"]}')
    print(f'Turn count: {stats["turn_count"]}')
    print(
        "Cumulative input tokens:",
        stats["cumulative_input_tokens"]
    )
    print(
        "Cumulative output tokens:",
        stats["cumulative_output_tokens"]
    )
    print(
        "Cumulative total tokens:",
        stats["cumulative_total_tokens"]
    )
    print(
        "Serialized conversation-history length:",
        serialized_history_length(history),
        "characters"
    )

def save_token_records(
    records: list[dict[str, Any]]
) -> None:
    """Save per-turn token counts as machine-readable JSON."""
    TOKEN_LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    payload = {
        "model": "qwen3:4b",
        "turns": records
    }

    TOKEN_LOG_PATH.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8"
    )

def main() -> None:
    system_prompt = load_system_prompt()

    client = ModelClient(
        model="qwen3:4b",
        temperature=0.0,
        num_ctx=4096,
        num_predict=256
    )

    history: list[dict[str, str]] = []
    token_records: list[dict[str, Any]] = []

    print("HW1 Local Code-Review Client")
    print("Model: qwen3:4b")
    print("Commands: /stats, /exit")
    print(
        "Enter code or a code-review question."
    )

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        command = user_input.lower()

        if command in {
            "/exit",
            "exit",
            "quit"
        }:
            break

        if command == "/stats":
            print_stats(
                client,
                history
            )
            continue

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "system",
                "content": (
                    "Transport requirement: return a JSON "
                    "object containing a bullets array. Put "
                    "one code-review bullet in each array item."
                )
            },
            *history,
            {
                "role": "user",
                "content": user_input
            }
        ]

        result = client.complete(
            messages,
            response_format=BULLET_SCHEMA
        )

        try:
            review = render_bullets(
                result.content
            )
        except (
            json.JSONDecodeError,
            ValueError
        ) as error:
            print(
                "\nModel response could not be rendered:",
                error
            )
            print("Raw response:")
            print(result.content)
            continue

        print("\nAssistant:")
        print(review)

        bullet_check = is_bullet_only(review)

        print(
            "\nBullet-only verification:",
            "PASS" if bullet_check else "FAIL"
        )

        print(
            "Input tokens:",
            result.input_tokens
        )
        print(
            "Output tokens:",
            result.output_tokens
        )
        print(
            "Total tokens:",
            result.total_tokens
        )

        history.append({
            "role": "user",
            "content": user_input
        })

        history.append({
            "role": "assistant",
            "content": review
        })

        stats = client.get_stats()

        token_records.append({
            "turn": client.turn_count,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "total_tokens": result.total_tokens,
            "cumulative_input_tokens": (
                stats["cumulative_input_tokens"]
            ),
            "cumulative_output_tokens": (
                stats["cumulative_output_tokens"]
            ),
            "cumulative_total_tokens": (
                stats["cumulative_total_tokens"]
            ),
            "serialized_history_length": (
                serialized_history_length(history)
            ),
            "bullet_only_passed": bullet_check
        })

        save_token_records(token_records)   

    print("\n=== Final Session Statistics ===")

    final_stats = client.get_stats()

    print(
        "Turn count:",
        final_stats["turn_count"]
    )
    print(
        "Cumulative input tokens:",
        final_stats[
            "cumulative_input_tokens"
        ]
    )
    print(
        "Cumulative output tokens:",
        final_stats[
            "cumulative_output_tokens"
        ]
    )
    print(
        "Cumulative total tokens:",
        final_stats[
            "cumulative_total_tokens"
        ]
    )
    print(
        "Serialized conversation-history length:",
        serialized_history_length(history),
        "characters"
    )


if __name__ == "__main__":
    main()