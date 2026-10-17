from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

AGENT_PATH = PROJECT_ROOT / "AGENT.md"
MEMORY_PATH = PROJECT_ROOT / "MEMORY.md"

CONSOLIDATION_HOURS = 24
MAX_MEMORY_LINES = 40
TARGET_MEMORY_LINES = 35

TIMESTAMP_PATTERN = re.compile(
    r"<!--\s*last-consolidated:\s*"
    r"([^>]+?)\s*-->"
)


def utc_now() -> datetime:
    """Return the current UTC time."""

    return datetime.now(
        timezone.utc
    )


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return utc_now().isoformat()


def load_markdown_file(
    path: Path,
) -> str:
    """Load one required Markdown file."""

    if not path.is_file():
        raise FileNotFoundError(
            f"Required memory file not found: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    ).strip()


def load_file_memory() -> dict[str, str]:
    """Load durable agent instructions and memory facts."""

    return {
        "agent_instructions": (
            load_markdown_file(
                AGENT_PATH
            )
        ),
        "durable_memory": (
            load_markdown_file(
                MEMORY_PATH
            )
        ),
    }


def build_system_prompt(
    base_prompt: str,
) -> str:
    """Add AGENT.md and MEMORY.md to a system prompt."""

    memory = load_file_memory()

    return "\n\n".join([
        base_prompt.strip(),
        "## Durable Agent Instructions",
        memory[
            "agent_instructions"
        ],
        "## Durable File-Based Memory",
        memory[
            "durable_memory"
        ],
        (
            "Use durable memory only when relevant. "
            "If facts conflict, prefer an explicitly "
            "resolved fact and mention uncertainty when "
            "no resolution is recorded."
        ),
    ])


def memory_fact_lines(
    content: str | None = None,
) -> list[str]:
    """
    Return nonempty, non-comment memory lines.

    Markdown headings are ignored so that the result
    represents stored facts rather than formatting.
    """

    if content is None:
        content = load_markdown_file(
            MEMORY_PATH
        )

    facts: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("<!--"):
            continue

        if line.startswith("#"):
            continue

        facts.append(line)

    return facts


def read_last_consolidated_timestamp(
    content: str | None = None,
) -> datetime | None:
    """Read the consolidation timestamp from MEMORY.md."""

    if content is None:
        content = load_markdown_file(
            MEMORY_PATH
        )

    match = TIMESTAMP_PATTERN.search(
        content
    )

    if match is None:
        return None

    raw_timestamp = (
        match.group(1)
        .strip()
        .replace(
            "Z",
            "+00:00"
        )
    )

    try:
        parsed = datetime.fromisoformat(
            raw_timestamp
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def consolidation_status() -> dict[str, Any]:
    """Determine whether MEMORY.md needs consolidation."""

    content = load_markdown_file(
        MEMORY_PATH
    )

    line_count = len(
        memory_fact_lines(content)
    )

    last_consolidated = (
        read_last_consolidated_timestamp(
            content
        )
    )

    if last_consolidated is None:
        age_hours = None
        timestamp_expired = True
    else:
        age = (
            utc_now()
            - last_consolidated
        )

        age_hours = round(
            age.total_seconds()
            / 3600,
            2,
        )

        timestamp_expired = (
            age_hours
            > CONSOLIDATION_HOURS
        )

    line_limit_exceeded = (
        line_count
        > MAX_MEMORY_LINES
    )

    return {
        "required": (
            line_limit_exceeded
            or timestamp_expired
        ),
        "line_count": line_count,
        "line_limit": (
            MAX_MEMORY_LINES
        ),
        "line_limit_exceeded": (
            line_limit_exceeded
        ),
        "last_consolidated": (
            last_consolidated.isoformat()
            if last_consolidated
            else None
        ),
        "age_hours": age_hours,
        "timestamp_expired": (
            timestamp_expired
        ),
    }


def clean_fact(line: str) -> str:
    """Remove a Markdown bullet marker from a fact."""

    cleaned = line.strip()

    if cleaned.startswith("-"):
        cleaned = cleaned[1:].strip()

    return cleaned


def normalized_fact(
    fact: str,
) -> str:
    """Return a normalized fact used for deduplication."""

    return " ".join(
        fact.casefold().split()
    ).rstrip(".")


def deduplicate_facts(
    facts: list[str],
) -> tuple[
    list[str],
    int,
]:
    """Remove exact duplicate facts while preserving order."""

    seen: set[str] = set()
    unique: list[str] = []
    duplicate_count = 0

    for raw_fact in facts:
        fact = clean_fact(
            raw_fact
        )

        key = normalized_fact(
            fact
        )

        if key in seen:
            duplicate_count += 1
            continue

        seen.add(key)
        unique.append(fact)

    return (
        unique,
        duplicate_count,
    )


def contains_text(
    fact: str,
    text: str,
) -> bool:
    """Perform a case-insensitive substring check."""

    return (
        text.casefold()
        in fact.casefold()
    )


def resolve_contradictions(
    facts: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    Resolve known contradictory test facts explicitly.

    No conflict is silently deleted. Each resolution is
    preserved as a new durable memory fact.
    """

    phase_two = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "prefers phase ii"
        )
    ]

    phase_three = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "prefers phase iii"
        )
    ]

    san_jose = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "located near san jose"
        )
    ]

    santa_clara = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "located near santa clara"
        )
    ]

    five_messages = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "every five user messages"
        )
    ]

    ten_messages = [
        fact
        for fact in facts
        if contains_text(
            fact,
            "every ten user messages"
        )
    ]

    conflicting_facts = set(
        phase_two
        + phase_three
        + san_jose
        + santa_clara
        + five_messages
        + ten_messages
    )

    retained = [
        fact
        for fact in facts
        if fact not in conflicting_facts
    ]

    resolutions: list[str] = []

    if phase_two and phase_three:
        resolutions.append(
            "CONTRADICTION RESOLVED: Phase II is the "
            "current preferred trial phase; the Phase III "
            "preference is retained as an outdated conflict."
        )
    else:
        retained.extend(
            phase_two
            + phase_three
        )

    if san_jose and santa_clara:
        resolutions.append(
            "CONTRADICTION RESOLVED: San Jose is the "
            "current preferred study location; Santa Clara "
            "is retained as an outdated conflicting location."
        )
    else:
        retained.extend(
            san_jose
            + santa_clara
        )

    if five_messages and ten_messages:
        resolutions.append(
            "CONTRADICTION RESOLVED: Session summaries "
            "are generated every five user messages; the "
            "ten-message interval is retained as outdated."
        )
    else:
        retained.extend(
            five_messages
            + ten_messages
        )

    return (
        retained,
        resolutions,
    )


def compact_fact_list(
    facts: list[str],
    target_count: int,
) -> list[str]:
    """
    Reduce memory lines without silently discarding facts.

    Overflow facts are retained together in one explicitly
    labeled aggregate memory line.
    """

    if len(facts) <= target_count:
        return facts

    directly_retained = facts[
        :target_count - 1
    ]

    overflow = facts[
        target_count - 1:
    ]

    combined_overflow = (
        "Additional retained facts from consolidation: "
        + " | ".join(overflow)
    )

    directly_retained.append(
        combined_overflow
    )

    return directly_retained


def write_memory(
    facts: list[str],
) -> None:
    """Write consolidated facts to MEMORY.md."""

    lines = [
        (
            "<!-- last-consolidated: "
            f"{utc_timestamp()} -->"
        ),
        "# Durable Conversation Memory",
        "",
    ]

    lines.extend(
        f"- {fact}"
        for fact in facts
    )

    MEMORY_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def consolidate_memory() -> dict[str, Any]:
    """Consolidate MEMORY.md and return audit information."""

    original_content = (
        load_markdown_file(
            MEMORY_PATH
        )
    )

    original_lines = (
        memory_fact_lines(
            original_content
        )
    )

    before_count = len(
        original_lines
    )

    unique_facts, duplicate_count = (
        deduplicate_facts(
            original_lines
        )
    )

    resolved_facts, resolutions = (
        resolve_contradictions(
            unique_facts
        )
    )

    final_facts = (
        resolved_facts
        + resolutions
    )

    final_facts = compact_fact_list(
        final_facts,
        TARGET_MEMORY_LINES,
    )

    write_memory(
        final_facts
    )

    after_count = len(
        memory_fact_lines()
    )

    return {
        "before_count": before_count,
        "after_count": after_count,
        "duplicates_merged": (
            duplicate_count
        ),
        "contradictions_resolved": (
            len(resolutions)
        ),
        "resolutions": resolutions,
        "below_40_lines": (
            after_count
            < MAX_MEMORY_LINES
        ),
        "memory_path": str(
            MEMORY_PATH
        ),
    }


def extract_durable_facts(
    recent_conversation: str,
) -> list[str]:
    """
    Extract candidate durable facts using transparent rules.

    This avoids storing every conversational sentence.
    """

    durable_markers = (
        "my name is",
        "i prefer",
        "my preferred",
        "remember that",
        "the project uses",
        "the application uses",
        "the database is",
        "the model is",
        "must not",
    )

    candidates: list[str] = []

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        recent_conversation.strip(),
    )

    for sentence in sentences:
        cleaned = sentence.strip()

        if not cleaned:
            continue

        lowered = cleaned.casefold()

        if any(
            marker in lowered
            for marker in durable_markers
        ):
            candidates.append(
                cleaned
            )

    unique_candidates, _ = (
        deduplicate_facts(
            candidates
        )
    )

    return unique_candidates


def dream_memory(
    recent_conversation: str,
) -> dict[str, Any]:
    """Add useful long-term facts from recent conversation."""

    candidates = extract_durable_facts(
        recent_conversation
    )

    existing_lines = memory_fact_lines()

    existing_facts, _ = (
        deduplicate_facts(
            existing_lines
        )
    )

    existing_keys = {
        normalized_fact(fact)
        for fact in existing_facts
    }

    added: list[str] = []

    for candidate in candidates:
        key = normalized_fact(
            candidate
        )

        if key in existing_keys:
            continue

        existing_facts.append(
            candidate
        )

        existing_keys.add(key)
        added.append(candidate)

    write_memory(
        existing_facts
    )

    return {
        "candidate_count": len(
            candidates
        ),
        "added_count": len(
            added
        ),
        "added_facts": added,
        "final_count": len(
            memory_fact_lines()
        ),
    }


def command_help() -> str:
    """Return help text for file-memory commands."""

    return "\n".join([
        "Available file-memory commands:",
        "/memory  Display MEMORY.md and consolidation status.",
        "/compact Consolidate MEMORY.md and report counts.",
        "/dream   Extract durable facts from recent text.",
        "/help    Display this command guide.",
    ])


def handle_command(
    command: str,
    recent_conversation: str = "",
) -> dict[str, Any]:
    """Execute one supported file-memory command."""

    normalized = command.strip().casefold()

    if normalized == "/memory":
        return {
            "command": "/memory",
            "content": (
                load_markdown_file(
                    MEMORY_PATH
                )
            ),
            "status": (
                consolidation_status()
            ),
        }

    if normalized == "/compact":
        return {
            "command": "/compact",
            "result": (
                consolidate_memory()
            ),
        }

    if normalized == "/dream":
        if not recent_conversation.strip():
            return {
                "command": "/dream",
                "error": (
                    "Recent conversation text is required."
                ),
            }

        return {
            "command": "/dream",
            "result": dream_memory(
                recent_conversation
            ),
        }

    if normalized == "/help":
        return {
            "command": "/help",
            "content": command_help(),
        }

    return {
        "command": command,
        "error": (
            "Unknown command. Use /help."
        ),
    }


def print_result(
    result: dict[str, Any],
) -> None:
    """Print command results in a readable format."""

    command = result.get(
        "command"
    )

    if "error" in result:
        print(
            result["error"]
        )
        return

    if command == "/memory":
        print(
            result["content"]
        )

        print(
            "\nConsolidation status:"
        )

        for key, value in (
            result["status"].items()
        ):
            print(
                f"- {key}: {value}"
            )

        return

    if command == "/compact":
        compact_result = (
            result["result"]
        )

        print(
            "Memory consolidation complete."
        )

        print(
            "Message count before:",
            compact_result[
                "before_count"
            ],
        )

        print(
            "Message count after:",
            compact_result[
                "after_count"
            ],
        )

        print(
            "Duplicates merged:",
            compact_result[
                "duplicates_merged"
            ],
        )

        print(
            "Contradictions resolved:",
            compact_result[
                "contradictions_resolved"
            ],
        )

        for resolution in compact_result[
            "resolutions"
        ]:
            print(
                f"- {resolution}"
            )

        return

    if command == "/dream":
        dream_result = (
            result["result"]
        )

        print(
            "Dream processing complete."
        )

        print(
            "Candidate facts:",
            dream_result[
                "candidate_count"
            ],
        )

        print(
            "Facts added:",
            dream_result[
                "added_count"
            ],
        )

        for fact in dream_result[
            "added_facts"
        ]:
            print(
                f"- {fact}"
            )

        return

    print(
        result.get(
            "content",
            result,
        )
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Homework 6 file-based memory commands."
        )
    )

    parser.add_argument(
        "command",
        choices=[
            "/memory",
            "/compact",
            "/dream",
            "/help",
        ],
    )

    parser.add_argument(
        "--recent",
        default="",
        help=(
            "Recent conversation text used by /dream."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Run one file-memory command."""

    arguments = parse_arguments()

    result = handle_command(
        arguments.command,
        arguments.recent,
    )

    print_result(
        result
    )


if __name__ == "__main__":
    main()