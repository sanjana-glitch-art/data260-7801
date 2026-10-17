from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

import yaml

from code.memory_api import (
    update_summaries_if_needed,
)
from code.memory_service import (
    SYSTEM_PRIMER,
    approximate_tokens,
    assemble_chat_prompt,
    latest_summary,
    load_short_term_messages,
    retrieve_relevant_episodes,
    save_message,
    store_episode_facts,
)
from code.mongo_database import (
    episodes_collection,
    messages_collection,
    summaries_collection,
)
from src.model_client import ModelClient


ROOT = Path(
    __file__
).resolve().parents[1]

CASES_DIRECTORY = (
    ROOT
    / "reports"
    / "hw06"
    / "cases"
)

RAW_DIRECTORY = (
    ROOT
    / "reports"
    / "hw06"
    / "raw"
)

CONVERSATION_PATH = (
    CASES_DIRECTORY
    / "memory_conversation.json"
)

PROBES_PATH = (
    CASES_DIRECTORY
    / "memory_probes.yaml"
)

TURN_JSON_PATH = (
    RAW_DIRECTORY
    / "short_term_sweep_results.json"
)

TURN_CSV_PATH = (
    RAW_DIRECTORY
    / "short_term_sweep_results.csv"
)

PROBE_RESULTS_PATH = (
    RAW_DIRECTORY
    / "memory_probe_results.json"
)

COMPRESSION_PATH = (
    RAW_DIRECTORY
    / "compression_results.json"
)

METRICS_PATH = (
    RAW_DIRECTORY
    / "memory_experiment_metrics.json"
)


MODEL_NAME = "qwen3:4b"

VERIFY_SEED = 267801

EPISODIC_TOP_K = 3


CONFIGURATIONS = [
    {
        "name": "SHORT_TERM_N=4",
        "short_term_n": 4,
        "compression": False,
    },
    {
        "name": "SHORT_TERM_N=12",
        "short_term_n": 12,
        "compression": False,
    },
    {
        "name": "SHORT_TERM_N=30",
        "short_term_n": 30,
        "compression": False,
    },
    {
        "name": "compression_policy",
        "short_term_n": 30,
        "compression": True,
    },
]


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def load_conversation() -> list[str]:
    """Load the fixed 30-message conversation."""

    data = json.loads(
        CONVERSATION_PATH.read_text(
            encoding="utf-8"
        )
    )

    messages = [
        item["message"]
        for item in data["messages"]
    ]

    if len(messages) != 30:
        raise ValueError(
            "The experiment requires "
            "exactly 30 messages."
        )

    return messages


def load_probes() -> list[
    dict[str, Any]
]:
    """Load the five fixed memory probes."""

    data = yaml.safe_load(
        PROBES_PATH.read_text(
            encoding="utf-8"
        )
    )

    probes = data["probes"]

    if len(probes) != 5:
        raise ValueError(
            "The experiment requires "
            "exactly five probes."
        )

    return probes


def clear_experiment_user(
    user_id: str,
) -> None:
    """Delete records belonging only to one experiment user."""

    messages_collection().delete_many({
        "user_id": user_id
    })

    summaries_collection().delete_many({
        "user_id": user_id
    })

    episodes_collection().delete_many({
        "user_id": user_id
    })


def compression_keywords() -> tuple[
    str,
    ...,
]:
    """Return markers for durable facts."""

    return (
        "prefer",
        "preferred",
        "remember",
        "never",
        "must",
        "privacy",
        "interested",
        "main study",
        "san jose state",
        "no more than",
        "clinical trial phase",
        "recruitment status",
    )


def compress_older_messages(
    messages: list[dict[str, Any]],
) -> str:
    """
    Compress older conversation into short durable bullets.

    Only user messages containing preference, safety, identity,
    or research markers are retained. Duplicate lines are
    removed.
    """

    markers = compression_keywords()

    selected: list[str] = []
    seen: set[str] = set()

    for message in messages:
        if message.get("role") != "user":
            continue

        content = " ".join(
            str(
                message.get(
                    "content",
                    "",
                )
            ).split()
        )

        lowered = content.casefold()

        if not any(
            marker in lowered
            for marker in markers
        ):
            continue

        if lowered in seen:
            continue

        seen.add(
            lowered
        )

        if len(content) > 180:
            content = (
                content[:177].rstrip()
                + "..."
            )

        selected.append(
            f"- {content}"
        )

    if not selected:
        return "(no durable older facts)"

    return "\n".join(
        selected[:10]
    )


def memory_for_configuration(
    user_id: str,
    session_id: str,
    current_message: str,
    short_term_n: int,
    compression: bool,
) -> tuple[
    list[dict[str, str]],
    dict[str, int],
    dict[str, Any],
]:
    """Load memory and assemble a prompt."""

    if compression:
        full_window = (
            load_short_term_messages(
                user_id=user_id,
                session_id=session_id,
                limit=30,
            )
        )

        short_term = full_window[
            -4:
        ]

        older_messages = full_window[
            :-4
        ]

        compressed_text = (
            compress_older_messages(
                older_messages
            )
        )
    else:
        short_term = (
            load_short_term_messages(
                user_id=user_id,
                session_id=session_id,
                limit=short_term_n,
            )
        )

        compressed_text = ""

    session_summary = latest_summary(
        user_id=user_id,
        session_id=session_id,
        scope="session",
    )

    lifetime_summary = latest_summary(
        user_id=user_id,
        scope="user",
    )

    if compression:
        existing_summary = (
            session_summary["text"]
            if session_summary
            else "(none)"
        )

        session_summary = {
            "text": (
                f"{existing_summary}\n\n"
                "Compressed older memory:\n"
                f"{compressed_text}"
            )
        }

    episodes = retrieve_relevant_episodes(
        user_id=user_id,
        query=current_message,
        top_k=EPISODIC_TOP_K,
    )

    model_messages, components = (
        assemble_chat_prompt(
            current_message=(
                current_message
            ),
            short_term_messages=(
                short_term
            ),
            session_summary=(
                session_summary
            ),
            lifetime_summary=(
                lifetime_summary
            ),
            episodes=episodes,
        )
    )

    memory_details = {
        "short_term_count": len(
            short_term
        ),
        "episode_count": len(
            episodes
        ),
        "compression": compression,
        "compressed_text": (
            compressed_text
        ),
    }

    return (
        model_messages,
        components,
        memory_details,
    )


def normalize_for_scoring(
    text: str,
) -> str:
    """Normalize model text for deterministic scoring."""

    normalized = " ".join(
        text.casefold().split()
    )

    normalized = normalized.replace(
        "never reveal",
        "not reveal",
    )

    normalized = normalized.replace(
        "must not reveal",
        "not reveal",
    )

    normalized = normalized.replace(
        "do not reveal",
        "not reveal",
    )

    return normalized


def score_probe(
    answer: str,
    probe: dict[str, Any],
) -> dict[str, Any]:
    """
    Score a probe from 1 to 5 using expected keywords.

    The YAML file remains the authoritative human-readable
    rubric. Keyword coverage makes repeated scoring
    deterministic.
    """

    normalized = normalize_for_scoring(
        answer
    )

    keywords: list[str] = []

    for criterion in probe[
        "expected_criteria"
    ]:
        keywords.extend(
            criterion.get(
                "keywords",
                [],
            )
        )

    keyword_results = {
        keyword: (
            keyword.casefold()
            in normalized
        )
        for keyword in keywords
    }

    matched = sum(
        keyword_results.values()
    )

    total = len(
        keyword_results
    )

    coverage = (
        matched / total
        if total
        else 0
    )

    score = round(
        1 + 4 * coverage
    )

    score = max(
        1,
        min(
            5,
            score,
        ),
    )

    return {
        "score": score,
        "matched_keywords": [
            keyword
            for keyword, passed
            in keyword_results.items()
            if passed
        ],
        "missing_keywords": [
            keyword
            for keyword, passed
            in keyword_results.items()
            if not passed
        ],
        "coverage": round(
            coverage,
            4,
        ),
    }


def run_model_turn(
    client: ModelClient,
    user_id: str,
    session_id: str,
    message: str,
    setting: dict[str, Any],
    turn_type: str,
    turn_number: int,
    save_conversation: bool,
) -> dict[str, Any]:
    """Run one conversation or probe turn."""

    if save_conversation:
        save_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=message,
        )

    (
        model_messages,
        component_tokens,
        memory_details,
    ) = memory_for_configuration(
        user_id=user_id,
        session_id=session_id,
        current_message=message,
        short_term_n=setting[
            "short_term_n"
        ],
        compression=setting[
            "compression"
        ],
    )

    started = perf_counter()

    result = client.complete(
        model_messages
    )

    latency_ms = (
        perf_counter()
        - started
    ) * 1000

    answer = result.content.strip()

    if not answer:
        answer = (
            "No answer was generated."
        )

    if save_conversation:
        save_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=answer,
        )

        store_episode_facts(
            user_id=user_id,
            session_id=session_id,
            message=message,
        )

        update_summaries_if_needed(
            user_id=user_id,
            session_id=session_id,
        )

    return {
        "setting": setting["name"],
        "short_term_n": setting[
            "short_term_n"
        ],
        "compression": setting[
            "compression"
        ],
        "user_id": user_id,
        "session_id": session_id,
        "turn_type": turn_type,
        "turn": turn_number,
        "message": message,
        "answer": answer,
        "prompt_tokens": (
            result.input_tokens
        ),
        "completion_tokens": (
            result.output_tokens
        ),
        "total_tokens": (
            result.total_tokens
        ),
        **component_tokens,
        **memory_details,
        "latency_ms": round(
            latency_ms,
            3,
        ),
    }


def configuration_metrics(
    records: list[dict[str, Any]],
    probe_results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """Calculate metrics for one configuration."""

    conversation_records = [
        record
        for record in records
        if record["turn_type"]
        == "conversation"
    ]

    probes = [
        result
        for result in probe_results
        if result["setting"]
        == records[0]["setting"]
    ]

    mean_prompt_tokens = fmean(
        record["prompt_tokens"]
        for record
        in conversation_records
    )

    mean_completion_tokens = fmean(
        record["completion_tokens"]
        for record
        in conversation_records
    )

    mean_latency = fmean(
        record["latency_ms"]
        for record
        in conversation_records
    )

    mean_probe_quality = fmean(
        result["score"]
        for result in probes
    )

    input_tokens_per_conversation = (
        mean_prompt_tokens * 30
    )

    output_tokens_per_conversation = (
        mean_completion_tokens * 30
    )

    cost_per_conversation = (
        input_tokens_per_conversation
        / 1_000_000
        * 1
        + output_tokens_per_conversation
        / 1_000_000
        * 5
    )

    cost_for_10000 = (
        cost_per_conversation
        * 10_000
    )

    return {
        "setting": records[0][
            "setting"
        ],
        "shortTermN": records[0][
            "short_term_n"
        ],
        "compression": records[0][
            "compression"
        ],
        "conversationTurns": len(
            conversation_records
        ),
        "probeCount": len(
            probes
        ),
        "meanPromptTokensPerTurn": round(
            mean_prompt_tokens,
            3,
        ),
        "meanCompletionTokensPerTurn": round(
            mean_completion_tokens,
            3,
        ),
        "meanLatencyMs": round(
            mean_latency,
            3,
        ),
        "meanProbeQuality": round(
            mean_probe_quality,
            3,
        ),
        "estimatedInputTokensPerConversation": round(
            input_tokens_per_conversation,
            3,
        ),
        "estimatedOutputTokensPerConversation": round(
            output_tokens_per_conversation,
            3,
        ),
        "estimatedCostPerConversationUsd": round(
            cost_per_conversation,
            6,
        ),
        "estimatedCostFor10000ConversationsUsd": round(
            cost_for_10000,
            2,
        ),
    }


def write_turn_csv(
    records: list[dict[str, Any]],
) -> None:
    """Write per-turn experiment records to CSV."""

    fieldnames = [
        "setting",
        "short_term_n",
        "compression",
        "user_id",
        "session_id",
        "turn_type",
        "turn",
        "message",
        "answer",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "system_primer_tokens",
        "long_term_summary_tokens",
        "short_term_tokens",
        "episodic_fact_tokens",
        "short_term_count",
        "episode_count",
        "latency_ms",
    ]

    with TURN_CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(
            records
        )


def main() -> None:
    """Run the complete Homework 6 memory experiment."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    conversation = load_conversation()
    probes = load_probes()

    all_records: list[
        dict[str, Any]
    ] = []

    all_probe_results: list[
        dict[str, Any]
    ] = []

    metrics_by_setting: dict[
        str,
        dict[str, Any],
    ] = {}

    print(
        "DATA-260 Homework 6 "
        "Memory Cost Experiment"
    )

    print(
        "Model:",
        MODEL_NAME
    )

    print(
        "Conversation messages:",
        len(conversation)
    )

    print(
        "Memory probes:",
        len(probes)
    )

    for configuration_number, setting in enumerate(
        CONFIGURATIONS,
        start=1,
    ):
        safe_name = (
            setting["name"]
            .replace(
                "=",
                "_",
            )
            .replace(
                " ",
                "_",
            )
            .lower()
        )

        user_id = (
            f"hw6-experiment-"
            f"{safe_name}"
        )

        session_id = (
            f"session-{VERIFY_SEED}-"
            f"{configuration_number}"
        )

        clear_experiment_user(
            user_id
        )

        client = ModelClient(
            model=MODEL_NAME,
            temperature=0.0,
            num_ctx=2048,
            num_predict=160,
        )

        print(
            "\n=== CONFIGURATION:",
            setting["name"],
            "===",
        )

        configuration_records: list[
            dict[str, Any]
        ] = []

        for turn_number, message in enumerate(
            conversation,
            start=1,
        ):
            record = run_model_turn(
                client=client,
                user_id=user_id,
                session_id=session_id,
                message=message,
                setting=setting,
                turn_type="conversation",
                turn_number=turn_number,
                save_conversation=True,
            )

            configuration_records.append(
                record
            )

            all_records.append(
                record
            )

            print(
                f"Turn {turn_number:02d}/30",
                "| prompt tokens:",
                record["prompt_tokens"],
                "| latency ms:",
                record["latency_ms"],
            )

        for probe_number, probe in enumerate(
            probes,
            start=1,
        ):
            record = run_model_turn(
                client=client,
                user_id=user_id,
                session_id=session_id,
                message=probe["question"],
                setting=setting,
                turn_type="probe",
                turn_number=probe_number,
                save_conversation=False,
            )

            score_details = score_probe(
                record["answer"],
                probe,
            )

            probe_result = {
                "setting": setting["name"],
                "probe_id": probe["id"],
                "question": probe[
                    "question"
                ],
                "answer": record["answer"],
                **score_details,
                "prompt_tokens": record[
                    "prompt_tokens"
                ],
                "latency_ms": record[
                    "latency_ms"
                ],
            }

            all_probe_results.append(
                probe_result
            )

            all_records.append(
                record
            )

            print(
                "Probe",
                probe["id"],
                "| score:",
                score_details["score"],
            )

        setting_metrics = (
            configuration_metrics(
                configuration_records,
                all_probe_results,
            )
        )

        metrics_by_setting[
            setting["name"]
        ] = setting_metrics

        print(
            "Mean prompt tokens:",
            setting_metrics[
                "meanPromptTokensPerTurn"
            ],
        )

        print(
            "Mean latency ms:",
            setting_metrics[
                "meanLatencyMs"
            ],
        )

        print(
            "Mean probe quality:",
            setting_metrics[
                "meanProbeQuality"
            ],
        )

    baseline = metrics_by_setting[
        "SHORT_TERM_N=30"
    ]

    compressed = metrics_by_setting[
        "compression_policy"
    ]

    token_savings_percent = (
        (
            baseline[
                "meanPromptTokensPerTurn"
            ]
            - compressed[
                "meanPromptTokensPerTurn"
            ]
        )
        / baseline[
            "meanPromptTokensPerTurn"
        ]
        * 100
    )

    quality_change = (
        compressed[
            "meanProbeQuality"
        ]
        - baseline[
            "meanProbeQuality"
        ]
    )

    compression_result = {
        "policy": (
            "Keep the four newest messages "
            "and compress durable older user "
            "facts into deduplicated bullets."
        ),
        "baselineSetting": (
            "SHORT_TERM_N=30"
        ),
        "baselineMeanPromptTokens": (
            baseline[
                "meanPromptTokensPerTurn"
            ]
        ),
        "compressedMeanPromptTokens": (
            compressed[
                "meanPromptTokensPerTurn"
            ]
        ),
        "tokenSavingsPercent": round(
            token_savings_percent,
            2,
        ),
        "baselineProbeQuality": (
            baseline[
                "meanProbeQuality"
            ]
        ),
        "compressedProbeQuality": (
            compressed[
                "meanProbeQuality"
            ]
        ),
        "probeQualityChange": round(
            quality_change,
            3,
        ),
    }

    ranked_settings = sorted(
        metrics_by_setting.values(),
        key=lambda item: (
            -item[
                "meanProbeQuality"
            ],
            item[
                "meanPromptTokensPerTurn"
            ],
        ),
    )

    best_setting = ranked_settings[0]

    worst_setting = sorted(
        metrics_by_setting.values(),
        key=lambda item: (
            item[
                "meanProbeQuality"
            ],
            -item[
                "meanPromptTokensPerTurn"
            ],
        ),
    )[0]

    final_metrics = {
        "experiment": (
            "hw6_memory_cost"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "verifySeed": VERIFY_SEED,
        "model": MODEL_NAME,
        "systemPrimerApproxTokens": (
            approximate_tokens(
                SYSTEM_PRIMER
            )
        ),
        "conversationMessageCount": (
            len(conversation)
        ),
        "probeCount": len(probes),
        "configurations": (
            metrics_by_setting
        ),
        "compressionComparison": (
            compression_result
        ),
        "bestSetting": (
            best_setting["setting"]
        ),
        "worstSetting": (
            worst_setting["setting"]
        ),
        "selectionMethod": (
            "Best prioritizes higher probe "
            "quality and then lower prompt "
            "tokens. Worst prioritizes lower "
            "probe quality and then higher "
            "prompt tokens."
        ),
        "pricing": {
            "inputPerMillionTokensUsd": 1,
            "outputPerMillionTokensUsd": 5,
        },
        "generatedAt": utc_timestamp(),
    }

    TURN_JSON_PATH.write_text(
        json.dumps(
            all_records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_turn_csv(
        all_records
    )

    PROBE_RESULTS_PATH.write_text(
        json.dumps(
            all_probe_results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    COMPRESSION_PATH.write_text(
        json.dumps(
            compression_result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    METRICS_PATH.write_text(
        json.dumps(
            final_metrics,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "\n=== FINAL RESULTS ==="
    )

    for name, metrics in (
        metrics_by_setting.items()
    ):
        print(
            name,
            "| prompt tokens:",
            metrics[
                "meanPromptTokensPerTurn"
            ],
            "| latency ms:",
            metrics[
                "meanLatencyMs"
            ],
            "| probe quality:",
            metrics[
                "meanProbeQuality"
            ],
            "| cost for 10,000: $",
            metrics[
                "estimatedCostFor10000ConversationsUsd"
            ],
        )

    print(
        "Compression token savings:",
        compression_result[
            "tokenSavingsPercent"
        ],
        "%",
    )

    print(
        "Probe-quality change:",
        compression_result[
            "probeQualityChange"
        ],
    )

    print(
        "Best setting:",
        final_metrics[
            "bestSetting"
        ],
    )

    print(
        "Worst setting:",
        final_metrics[
            "worstSetting"
        ],
    )

    print(
        "\nFiles created:"
    )

    for path in [
        TURN_JSON_PATH,
        TURN_CSV_PATH,
        PROBE_RESULTS_PATH,
        COMPRESSION_PATH,
        METRICS_PATH,
    ]:
        print(path)


if __name__ == "__main__":
    main()