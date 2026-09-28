from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from src.model_client import ModelClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORPUS_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw04"
    / "rag_corpus"
)

QUESTIONS_PATH = (
    PROJECT_ROOT
    / "reports"
    / "hw04"
    / "cases"
    / "rag_questions.json"
)

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw04"
    / "raw"
)

RESULTS_JSON_PATH = (
    RAW_DIRECTORY
    / "rag_results.json"
)

RESULTS_CSV_PATH = (
    RAW_DIRECTORY
    / "rag_results.csv"
)

METRICS_PATH = (
    RAW_DIRECTORY
    / "rag_metrics.json"
)

MODEL_NAME = "qwen3:4b"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

K_VALUES = [1, 3, 5]

REFUSAL_PHRASE = (
    "I cannot answer from the provided context."
)

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string"
        }
    },
    "required": ["answer"],
    "additionalProperties": False
}


def utc_timestamp() -> str:
    """Return an ISO-formatted UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def percentile(
    values: list[float],
    fraction: float,
) -> float:
    """Calculate a percentile using linear interpolation."""

    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        len(ordered) - 1
    ) * fraction

    lower_index = int(position)

    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    weight = (
        position - lower_index
    )

    lower_value = ordered[
        lower_index
    ]

    upper_value = ordered[
        upper_index
    ]

    return (
        lower_value
        + (
            upper_value
            - lower_value
        )
        * weight
    )


def load_questions() -> list[dict[str, Any]]:
    """Load and validate the six evaluation questions."""

    data = json.loads(
        QUESTIONS_PATH.read_text(
            encoding="utf-8"
        )
    )

    questions = data.get(
        "questions",
        [],
    )

    if len(questions) != 6:
        raise ValueError(
            "Exactly six RAG questions are required."
        )

    return questions


def load_documents() -> list[dict[str, str]]:
    """Load all text documents from the RAG corpus."""

    document_paths = sorted(
        CORPUS_DIRECTORY.glob(
            "*.txt"
        )
    )

    if len(document_paths) < 5:
        raise ValueError(
            "At least five corpus documents are required."
        )

    documents: list[dict[str, str]] = []

    for path in document_paths:
        text_content = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        if not text_content:
            continue

        documents.append({
            "source": path.name,
            "text": text_content,
        })

    if len(documents) < 5:
        raise ValueError(
            "At least five nonempty corpus documents "
            "are required."
        )

    return documents


def split_text(
    text_content: str,
) -> list[str]:
    """Split a document into overlapping character chunks."""

    chunks: list[str] = []

    start = 0

    while start < len(text_content):
        end = min(
            start + CHUNK_SIZE,
            len(text_content),
        )

        chunk = text_content[
            start:end
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text_content):
            break

        start = max(
            end - CHUNK_OVERLAP,
            start + 1,
        )

    return chunks


def create_chunks(
    documents: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Create labeled chunks from all corpus documents."""

    chunks: list[dict[str, Any]] = []

    chunk_id = 1

    for document in documents:
        document_chunks = split_text(
            document["text"]
        )

        for position, chunk_text in enumerate(
            document_chunks,
            start=1,
        ):
            chunks.append({
                "chunk_id": chunk_id,
                "source": document["source"],
                "position": position,
                "text": chunk_text,
            })

            chunk_id += 1

    return chunks


def create_embeddings(
    embedding_model: SentenceTransformer,
    chunks: list[dict[str, Any]],
) -> np.ndarray:
    """Create normalized embeddings for every chunk."""

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        texts,
        batch_size=4,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(
        embeddings,
        dtype=np.float32,
    )


def retrieve_chunks(
    question: str,
    k: int,
    embedding_model: SentenceTransformer,
    chunks: list[dict[str, Any]],
    chunk_embeddings: np.ndarray,
) -> list[dict[str, Any]]:
    """Retrieve the k most similar chunks."""

    question_embedding = embedding_model.encode(
        [question],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]

    scores = np.dot(
        chunk_embeddings,
        question_embedding,
    )

    top_indices = np.argsort(
        scores
    )[::-1][:k]

    retrieved: list[dict[str, Any]] = []

    for rank, index in enumerate(
        top_indices,
        start=1,
    ):
        chunk = chunks[int(index)]

        retrieved.append({
            "rank": rank,
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "position": chunk["position"],
            "score": round(
                float(scores[index]),
                6,
            ),
            "text": chunk["text"],
        })

    return retrieved


def context_text(
    retrieved_chunks: list[dict[str, Any]],
) -> str:
    """Render retrieved chunks with source labels."""

    sections: list[str] = []

    for chunk in retrieved_chunks:
        sections.append(
            (
                f"[Source: {chunk['source']} | "
                f"Chunk: {chunk['position']}]\n"
                f"{chunk['text']}"
            )
        )

    return "\n\n---\n\n".join(
        sections
    )


def no_rag_messages(
    question: str,
) -> list[dict[str, str]]:
    """Build a model prompt without retrieved material."""

    return [
        {
            "role": "system",
            "content": (
                "Answer directly and concisely without "
                "showing analysis or reasoning. Return a "
                "JSON object containing only an answer field. "
                "If you do not know, state that directly."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]


def basic_rag_messages(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build a basic retrieval-augmented prompt."""

    context = context_text(
        retrieved_chunks
    )

    return [
        {
            "role": "system",
            "content": (
                "Answer directly and concisely using the "
                "supplied reference material. Do not show "
                "analysis or reasoning. Return a JSON object "
                "containing only an answer field."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Reference material:\n\n"
                f"{context}\n\n"
                f"Question:\n{question}"
            ),
        },
    ]


def context_engineered_messages(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build a strict, source-grounded RAG prompt."""

    context = context_text(
        retrieved_chunks
    )

    return [
        {
            "role": "system",
            "content": (
                "Answer directly without showing analysis "
                "or reasoning. Return a JSON object containing "
                "only an answer field. Use only facts "
                "explicitly stated in the supplied context. "
                "Do not use outside knowledge. When an answer "
                "is supported, answer concisely and include "
                "the source filename in square brackets. "
                "If the context does not directly contain the "
                "requested information, the answer field must "
                "contain exactly: "
                f"{REFUSAL_PHRASE} "
                "Do not add any other words to that refusal. "
                "Never invent exact numbers, medication names, "
                "dosages, medical recommendations, or "
                "verification phrases."
            ),
        },
        {
            "role": "user",
            "content": (
                f"CONTEXT START\n"
                f"{context}\n"
                f"CONTEXT END\n\n"
                f"QUESTION:\n"
                f"{question}"
            ),
        },
    ]


def evaluate_result(
    question: dict[str, Any],
    answer: str,
    retrieved_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply deterministic answer and retrieval checks."""

    expected_sources = question[
        "expectedSources"
    ]

    retrieved_sources = [
        chunk["source"]
        for chunk in retrieved_chunks
    ]

    if expected_sources:
        source_hit: bool | None = any(
            source in retrieved_sources
            for source in expected_sources
        )
    else:
        source_hit = None

    required_terms = question[
        "requiredAnswerTerms"
    ]

    normalized_answer = (
        answer.casefold()
    )

    terms_found = [
        term
        for term in required_terms
        if term.casefold()
        in normalized_answer
    ]

    if required_terms:
        term_coverage_percent = (
            len(terms_found)
            / len(required_terms)
            * 100
        )
    else:
        term_coverage_percent = 100.0

    exact_refusal = (
        answer.strip()
        == REFUSAL_PHRASE
    )

    if question["mustRefuse"]:
        answer_passed = exact_refusal
    else:
        answer_passed = (
            len(terms_found)
            == len(required_terms)
        )

    return {
        "retrievedSources": retrieved_sources,
        "expectedSourceHit": source_hit,
        "requiredTermsFound": terms_found,
        "requiredTermCoveragePercent": round(
            term_coverage_percent,
            2,
        ),
        "exactRefusal": exact_refusal,
        "answerPassed": answer_passed,
    }


def run_model_call(
    client: ModelClient,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Execute one timed structured model call."""

    started_at = perf_counter()

    result = client.complete(
        messages,
        response_format=ANSWER_SCHEMA,
    )

    latency_ms = (
        perf_counter()
        - started_at
    ) * 1000

    try:
        parsed = json.loads(
            result.content
        )

        answer = str(
            parsed.get(
                "answer",
                "",
            )
        ).strip()
    except (
        json.JSONDecodeError,
        AttributeError,
        TypeError,
    ):
        answer = (
            result.content.strip()
        )

    return {
        "answer": answer,
        "latency_ms": round(
            latency_ms,
            3,
        ),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
    }


def execute_experiment(
    questions: list[dict[str, Any]],
    embedding_model: SentenceTransformer,
    chunks: list[dict[str, Any]],
    chunk_embeddings: np.ndarray,
) -> list[dict[str, Any]]:
    """Run all No RAG and RAG configurations."""

    client = ModelClient(
        model=MODEL_NAME,
        temperature=0.0,
        num_ctx=1536,
        num_predict=160,
        num_gpu=4,
    )

    results: list[dict[str, Any]] = []

    configurations = [
        {
            "technique": "no_rag",
            "k": 0,
        },
        *[
            {
                "technique": "basic_rag",
                "k": k,
            }
            for k in K_VALUES
        ],
        *[
            {
                "technique": (
                    "context_engineered_rag"
                ),
                "k": k,
            }
            for k in K_VALUES
        ],
    ]

    total_calls = (
        len(configurations)
        * len(questions)
    )

    completed_calls = 0

    for configuration in configurations:
        technique = configuration[
            "technique"
        ]

        k = configuration["k"]

        print(
            f"\nTechnique: {technique}, k={k}"
        )

        for question in questions:
            if technique == "no_rag":
                retrieved: list[
                    dict[str, Any]
                ] = []

                messages = no_rag_messages(
                    question["question"]
                )
            else:
                retrieved = retrieve_chunks(
                    question=question["question"],
                    k=k,
                    embedding_model=embedding_model,
                    chunks=chunks,
                    chunk_embeddings=chunk_embeddings,
                )

                if technique == "basic_rag":
                    messages = basic_rag_messages(
                        question["question"],
                        retrieved,
                    )
                else:
                    messages = (
                        context_engineered_messages(
                            question["question"],
                            retrieved,
                        )
                    )

            call_result = run_model_call(
                client,
                messages,
            )

            evaluation = evaluate_result(
                question,
                call_result["answer"],
                retrieved,
            )

            completed_calls += 1

            record = {
                "timestamp": utc_timestamp(),
                "technique": technique,
                "k": k,
                "question_id": question["id"],
                "question_type": (
                    question["questionType"]
                ),
                "question": question["question"],
                "must_refuse": (
                    question["mustRefuse"]
                ),
                "answer": call_result["answer"],
                "latency_ms": (
                    call_result["latency_ms"]
                ),
                "input_tokens": (
                    call_result["input_tokens"]
                ),
                "output_tokens": (
                    call_result["output_tokens"]
                ),
                "total_tokens": (
                    call_result["total_tokens"]
                ),
                "retrieved_chunks": retrieved,
                **evaluation,
            }

            results.append(record)

            print(
                f"{completed_calls}/{total_calls}"
                f" | {question['id']}"
                f" | passed="
                f"{evaluation['answerPassed']}"
                f" | refusal="
                f"{evaluation['exactRefusal']}"
            )

    print(
        "\nModel cumulative statistics:"
    )

    print(
        json.dumps(
            client.get_stats(),
            indent=2,
        )
    )

    return results


def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate metrics for each technique and k."""

    metrics_by_configuration: dict[
        str,
        Any,
    ] = {}

    configuration_keys = sorted({
        (
            result["technique"],
            result["k"],
        )
        for result in results
    })

    for technique, k in configuration_keys:
        matching = [
            result
            for result in results
            if (
                result["technique"]
                == technique
                and result["k"] == k
            )
        ]

        latencies = [
            float(
                result["latency_ms"]
            )
            for result in matching
        ]

        passed_count = sum(
            bool(
                result["answerPassed"]
            )
            for result in matching
        )

        refusal_results = [
            result
            for result in matching
            if result["must_refuse"]
        ]

        refusal_passed_count = sum(
            bool(
                result["exactRefusal"]
            )
            for result in refusal_results
        )

        source_results = [
            result
            for result in matching
            if (
                result[
                    "expectedSourceHit"
                ]
                is not None
            )
        ]

        source_hit_count = sum(
            bool(
                result[
                    "expectedSourceHit"
                ]
            )
            for result in source_results
        )

        key = (
            f"{technique}_k_{k}"
        )

        if refusal_results:
            refusal_rate = round(
                refusal_passed_count
                / len(refusal_results)
                * 100,
                2,
            )
        else:
            refusal_rate = None

        if source_results:
            source_hit_rate = round(
                source_hit_count
                / len(source_results)
                * 100,
                2,
            )
        else:
            source_hit_rate = None

        metrics_by_configuration[key] = {
            "technique": technique,
            "k": k,
            "questionCount": len(
                matching
            ),
            "answerPassedCount": (
                passed_count
            ),
            "answerPassRatePercent": round(
                passed_count
                / len(matching)
                * 100,
                2,
            ),
            "refusalQuestionCount": len(
                refusal_results
            ),
            "exactRefusalCount": (
                refusal_passed_count
            ),
            "exactRefusalRatePercent": (
                refusal_rate
            ),
            "expectedSourceQuestionCount": len(
                source_results
            ),
            "expectedSourceHitCount": (
                source_hit_count
            ),
            "expectedSourceHitRatePercent": (
                source_hit_rate
            ),
            "meanLatencyMs": round(
                fmean(latencies),
                3,
            ),
            "p50LatencyMs": round(
                percentile(
                    latencies,
                    0.50,
                ),
                3,
            ),
            "p95LatencyMs": round(
                percentile(
                    latencies,
                    0.95,
                ),
                3,
            ),
            "meanInputTokens": round(
                fmean(
                    result["input_tokens"]
                    for result in matching
                ),
                2,
            ),
            "meanOutputTokens": round(
                fmean(
                    result["output_tokens"]
                    for result in matching
                ),
                2,
            ),
        }

    return {
        "experiment": "hw4_rag_comparison",
        "model": MODEL_NAME,
        "embeddingModel": (
            EMBEDDING_MODEL_NAME
        ),
        "documentCount": len(
            list(
                CORPUS_DIRECTORY.glob(
                    "*.txt"
                )
            )
        ),
        "questionCount": 6,
        "kValues": K_VALUES,
        "totalModelCalls": len(
            results
        ),
        "refusalPhrase": (
            REFUSAL_PHRASE
        ),
        "configurations": (
            metrics_by_configuration
        ),
        "generatedAt": utc_timestamp(),
    }


def save_results(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> None:
    """Save raw and summarized RAG experiment files."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_JSON_PATH.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    csv_fields = [
        "timestamp",
        "technique",
        "k",
        "question_id",
        "question_type",
        "question",
        "must_refuse",
        "answer",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "expectedSourceHit",
        "requiredTermCoveragePercent",
        "exactRefusal",
        "answerPassed",
        "retrievedSources",
    ]

    with RESULTS_CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=csv_fields,
        )

        writer.writeheader()

        for result in results:
            csv_record: dict[
                str,
                Any,
            ] = {}

            for field in csv_fields:
                value = result.get(field)

                if isinstance(
                    value,
                    (list, dict),
                ):
                    csv_record[field] = (
                        json.dumps(
                            value,
                            ensure_ascii=False,
                        )
                    )
                else:
                    csv_record[field] = value

            writer.writerow(
                csv_record
            )

    METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )


def print_metrics(
    metrics: dict[str, Any],
) -> None:
    """Print a compact RAG comparison."""

    print(
        "\n=== RAG Metrics ==="
    )

    for configuration in (
        metrics["configurations"].values()
    ):
        print(
            configuration["technique"],
            "| k=",
            configuration["k"],
            "| answer pass=",
            configuration[
                "answerPassRatePercent"
            ],
            "%",
            "| refusal=",
            configuration[
                "exactRefusalRatePercent"
            ],
            "%",
            "| source hit=",
            configuration[
                "expectedSourceHitRatePercent"
            ],
            "%",
            "| mean latency=",
            configuration[
                "meanLatencyMs"
            ],
            "ms",
        )

    print(
        "\nFiles created:"
    )

    print(
        RESULTS_JSON_PATH
    )

    print(
        RESULTS_CSV_PATH
    )

    print(
        METRICS_PATH
    )


def main() -> None:
    """Run the complete Homework 4 RAG experiment."""

    questions = load_questions()

    documents = load_documents()

    chunks = create_chunks(
        documents
    )

    print(
        "Documents loaded:",
        len(documents),
    )

    print(
        "Chunks created:",
        len(chunks),
    )

    print(
        "Loading embedding model:",
        EMBEDDING_MODEL_NAME,
    )

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    chunk_embeddings = create_embeddings(
        embedding_model,
        chunks,
    )

    results = execute_experiment(
        questions=questions,
        embedding_model=embedding_model,
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
    )

    metrics = calculate_metrics(
        results
    )

    save_results(
        results,
        metrics,
    )

    print_metrics(
        metrics
    )


if __name__ == "__main__":
    main()