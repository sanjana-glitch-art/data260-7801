import argparse
import json
import re
import time
from typing import Any

from src.model_client import ModelClient


PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3
        },
        "summary": {
            "type": "string"
        }
    },
    "required": ["tags", "summary"],
    "additionalProperties": False
}


REVIEWER_SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3
        },
        "summary": {
            "type": "string"
        },
        "changed": {
            "type": "boolean"
        },
        "changes": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "tags",
        "summary",
        "changed",
        "changes"
    ],
    "additionalProperties": False
}


def extract_json(text: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from a model response."""
    cleaned = text.strip()

    # Remove optional Markdown code fences.
    cleaned = re.sub(
        r"^```(?:json)?",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError(
            "The model response did not contain a JSON object."
        )

    return json.loads(cleaned[start : end + 1])


def clean_tag(tag: Any) -> str:
    """Normalize one tag into a short readable string."""
    cleaned = re.sub(r"\s+", " ", str(tag)).strip()
    cleaned = cleaned.strip(".,;:!?\"'[]{}()")

    return cleaned.lower()


def input_tag_candidates(
    title: str,
    content: str
) -> list[str]:
    """
    Create fallback tags derived only from the supplied title
    and content.
    """
    text = f"{title} {content}".lower()

    words = re.findall(
        r"[A-Za-z][A-Za-z-]+",
        text
    )

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "into",
        "this",
        "that",
        "are",
        "was",
        "were",
        "will",
        "has",
        "have",
        "had",
        "its",
        "their",
        "about",
        "among",
        "how",
        "what",
        "when",
        "where",
        "who",
        "why",
        "a",
        "an",
        "is",
        "of",
        "to",
        "in",
        "on",
        "by",
        "at",
        "as",
        "it"
    }

    useful_words = [
        word
        for word in words
        if word not in stop_words
    ]

    candidates: list[str] = []

    # Generate two-word candidates.
    for index in range(len(useful_words) - 1):
        candidate = (
            f"{useful_words[index]} "
            f"{useful_words[index + 1]}"
        )

        if candidate not in candidates:
            candidates.append(candidate)

    # Use individual words as additional fallbacks.
    for word in useful_words:
        if word not in candidates:
            candidates.append(word)

    return candidates


def normalize_tags(
    raw_tags: Any,
    title: str,
    content: str
) -> list[str]:
    """Guarantee exactly three distinct nonempty tags."""
    tags: list[str] = []

    if isinstance(raw_tags, list):
        for raw_tag in raw_tags:
            tag = clean_tag(raw_tag)

            if tag and tag not in tags:
                tags.append(tag)

    # Add input-derived fallbacks if the model returned fewer
    # than three valid tags.
    for candidate in input_tag_candidates(title, content):
        if len(tags) >= 3:
            break

        cleaned_candidate = clean_tag(candidate)

        if (
            cleaned_candidate
            and cleaned_candidate not in tags
        ):
            tags.append(cleaned_candidate)

    if len(tags) < 3:
        raise ValueError(
            "The input did not provide enough information "
            "to create three tags."
        )

    return tags[:3]


def normalize_summary(
    summary: Any,
    title: str,
    content: str
) -> str:
    """
    Guarantee a nonempty summary containing no more than
    25 words.
    """
    cleaned = re.sub(
        r"\s+",
        " ",
        str(summary)
    ).strip()

    if not cleaned:
        cleaned = f"{title}. {content}".strip()

    words = cleaned.split()

    if len(words) > 25:
        cleaned = " ".join(words[:25])

    cleaned = cleaned.rstrip(" ,;:-")

    if not cleaned.endswith((".", "!", "?")):
        cleaned += "."

    return cleaned


def model_content(response: Any) -> str:
    """Convert a LangChain model response into plain text."""
    content = response.content

    if isinstance(content, str):
        return content

    return json.dumps(content)


def call_planner(
    model: ModelClient,
    title: str,
    content: str
) -> dict[str, Any]:
    """Ask the Planner agent for an initial proposal."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are the Planner agent. Analyze only the "
                "supplied title and content. Propose exactly "
                "three distinct topical tags and one summary "
                "containing no more than 25 words. Do not use "
                "fixed domain keywords. Return only valid JSON "
                'with the keys "tags" and "summary".'
            )
        },
        {
            "role": "user",
            "content": (
                f"Title:\n{title}\n\n"
                f"Content:\n{content}\n\n"
                "Return exactly three topical tags and one "
                "summary containing at most 25 words."
            )
        }
    ]

    result = model.complete(
        messages,
        response_format=PLANNER_SCHEMA
    )

    return extract_json(result.content)


def call_reviewer(
    model: ModelClient,
    title: str,
    content: str,
    planner_output: dict[str, Any]
) -> dict[str, Any]:
    """Ask the Reviewer to inspect and correct the proposal."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are the Reviewer agent. Check whether the "
                "proposed tags are distinct and topical and "
                "whether the summary contains no more than "
                "25 words. Correct any problems. Base everything "
                "only on the supplied title and content. Return "
                'only valid JSON with the keys "tags", "summary", '
                '"changed", and "changes".'
            )
        },
        {
            "role": "user",
            "content": (
                f"Title:\n{title}\n\n"
                f"Content:\n{content}\n\n"
                "Planner proposal:\n"
                f"{json.dumps(planner_output, indent=2)}"
            )
        }
    ]

    result = model.complete(
        messages,
        response_format=REVIEWER_SCHEMA
    )

    reviewer_output = extract_json(
        result.content
    )

    tags_changed = (
        reviewer_output.get("tags")
        != planner_output.get("tags")
    )

    summary_changed = (
        reviewer_output.get("summary")
        != planner_output.get("summary")
    )

    actually_changed = (
        tags_changed or summary_changed
    )

    reviewer_output["changed"] = actually_changed

    if not actually_changed:
        reviewer_output["changes"] = []
    elif not reviewer_output.get("changes"):
        reviewer_output["changes"] = [
            "The Reviewer modified the proposed tags or summary."
        ]

    return reviewer_output

def finalize_output(
    reviewer_output: dict[str, Any],
    title: str,
    content: str
) -> dict[str, Any]:
    """
    Apply deterministic validation without creating a third
    model agent.
    """
    return {
        "tags": normalize_tags(
            reviewer_output.get("tags", []),
            title,
            content
        ),
        "summary": normalize_summary(
            reviewer_output.get("summary", ""),
            title,
            content
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Planner and Reviewer local agent pipeline"
        )
    )

    parser.add_argument(
        "--title",
        required=True
    )

    parser.add_argument(
        "--content",
        required=True
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
        "--base-url",
        default="http://localhost:11434"
    )

    args = parser.parse_args()

    # Limit the context and response length for local hardware.
    model = ModelClient(
    model=args.model,
    base_url=args.base_url,
    temperature=args.temperature,
    num_ctx=2048,
    num_predict=256
    )

    # Planner agent
    planner_start = time.perf_counter()

    planner_output = call_planner(
        model,
        args.title,
        args.content
    )

    planner_latency = round(
        (time.perf_counter() - planner_start) * 1000,
        2
    )

    print("\n--- Planner Output ---")
    print(json.dumps(planner_output, indent=2))
    print(
        f"Planner latency: {planner_latency} ms"
    )

    # Reviewer agent
    reviewer_start = time.perf_counter()

    reviewer_output = call_reviewer(
        model,
        args.title,
        args.content,
        planner_output
    )

    reviewer_latency = round(
        (time.perf_counter() - reviewer_start) * 1000,
        2
    )

    print("\n--- Reviewer Output ---")
    print(json.dumps(reviewer_output, indent=2))
    print(
        f"Reviewer latency: {reviewer_latency} ms"
    )

    # Non-agent finalization step
    finalized_output = finalize_output(
        reviewer_output,
        args.title,
        args.content
    )

    total_latency = round(
        planner_latency + reviewer_latency,
        2
    )

    print("\n--- Finalized Output ---")
    print(
        json.dumps(
            finalized_output,
            indent=2
        )
    )

    # Complete publish object
    publish_output = {
        "title": args.title,
        "content": args.content,
        "model": args.model,
        "temperature": args.temperature,
        "planner": planner_output,
        "reviewer": reviewer_output,
        "final": finalized_output,
        "latencyMs": total_latency
    }

    print("\n--- Publish Output ---")
    print(
        json.dumps(
            publish_output,
            indent=2
        )
    )


if __name__ == "__main__":
    main()