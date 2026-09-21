from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
import yaml
from llama_index.core import (
    Document,
    StorageContext,
    VectorStoreIndex
)
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter
)
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores import (
    SimpleVectorStore
)
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw03"
)

CORPUS_DIRECTORY = (
    REPORT_DIRECTORY
    / "corpus"
)

QUESTIONS_PATH = (
    REPORT_DIRECTORY
    / "questions.yaml"
)

RAW_DIRECTORY = (
    REPORT_DIRECTORY
    / "raw"
)

JSONL_PATH = (
    RAW_DIRECTORY
    / "retrieval_results.jsonl"
)

CSV_PATH = (
    RAW_DIRECTORY
    / "retrieval_results.csv"
)

METRICS_PATH = (
    RAW_DIRECTORY
    / "retrieval_metrics.json"
)

RUN_LOG_PATH = (
    REPORT_DIRECTORY
    / "RUN_LOG.txt"
)

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

TOP_K = 5


def load_documents() -> list[Document]:
    """Load every extracted corpus text file."""

    text_files = sorted(
        CORPUS_DIRECTORY.glob("*.txt")
    )

    if not text_files:
        raise FileNotFoundError(
            "No corpus text files were found in "
            "reports/hw03/corpus."
        )

    documents: list[Document] = []

    for path in text_files:
        text = path.read_text(
            encoding="utf-8"
        )

        if not text.strip():
            raise ValueError(
                f"Corpus file is empty: {path}"
            )

        document = Document(
            text=text,
            metadata={
                "source_file": path.name,
                "relative_path": str(
                    path.relative_to(
                        PROJECT_ROOT
                    )
                ).replace("\\", "/")
            },
            excluded_embed_metadata_keys=[
                "source_file",
                "relative_path"
            ],
            excluded_llm_metadata_keys=[
                "source_file",
                "relative_path"
            ]
        )

        documents.append(document)

    return documents


def load_questions() -> list[dict[str, Any]]:
    """Load and validate the preregistered questions."""

    data = yaml.safe_load(
        QUESTIONS_PATH.read_text(
            encoding="utf-8"
        )
    )

    questions = data.get(
        "questions",
        []
    )

    if len(questions) < 5:
        raise ValueError(
            "questions.yaml must contain at least "
            "five questions."
        )

    required_fields = {
        "id",
        "question",
        "expected_answer",
        "expected_source_file"
    }

    for question in questions:
        missing = (
            required_fields
            - set(question)
        )

        if missing:
            raise ValueError(
                f"Question is missing fields: "
                f"{sorted(missing)}"
            )

    return questions


def cosine_similarity(
    first: list[float] | np.ndarray,
    second: list[float] | np.ndarray
) -> float:
    """Calculate cosine similarity between vectors."""

    first_array = np.asarray(
        first,
        dtype=np.float64
    )

    second_array = np.asarray(
        second,
        dtype=np.float64
    )

    denominator = (
        np.linalg.norm(first_array)
        * np.linalg.norm(second_array)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(
            first_array,
            second_array
        )
        / denominator
    )


def text_preview(
    text: str,
    length: int = 160
) -> str:
    """Return a compact single-line preview."""

    compact = " ".join(
        text.split()
    )

    if len(compact) <= length:
        return compact

    return (
        compact[:length].rstrip()
        + "..."
    )


def retrieval_text(
    node: BaseNode,
    technique: str
) -> str:
    """
    Return the text used for explicit document embedding.

    Sentence-window nodes are indexed by their central sentence,
    but the attached surrounding window is used as the returned
    retrieval context.
    """

    if technique == "sentence_window":
        window = node.metadata.get(
            "window"
        )

        if isinstance(window, str):
            if window.strip():
                return window.strip()

    return node.get_content().strip()


def build_nodes(
    documents: list[Document],
    embed_model: HuggingFaceEmbedding
) -> dict[str, list[BaseNode]]:
    """Create nodes using all three required techniques."""

    print()
    print("Creating token-based chunks...")

    token_splitter = TokenTextSplitter(
        chunk_size=512,
        chunk_overlap=64
    )

    token_nodes = (
        token_splitter
        .get_nodes_from_documents(
            documents,
            show_progress=True
        )
    )

    print()
    print("Creating semantic chunks...")

    semantic_splitter = (
        SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=embed_model
        )
    )

    semantic_nodes = (
        semantic_splitter
        .get_nodes_from_documents(
            documents,
            show_progress=True
        )
    )

    print()
    print("Creating sentence-window chunks...")

    sentence_window_splitter = (
        SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key=(
                "original_sentence"
            )
        )
    )

    sentence_window_nodes = (
        sentence_window_splitter
        .get_nodes_from_documents(
            documents,
            show_progress=True
        )
    )

    return {
        "token": token_nodes,
        "semantic": semantic_nodes,
        "sentence_window": (
            sentence_window_nodes
        )
    }


def build_index(
    nodes: list[BaseNode],
    embed_model: HuggingFaceEmbedding
) -> VectorStoreIndex:
    """Build an in-memory vector index."""

    vector_store = SimpleVectorStore()

    storage_context = (
        StorageContext.from_defaults(
            vector_store=vector_store
        )
    )

    return VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True
    )


def retrieve_for_question(
    technique: str,
    index: VectorStoreIndex,
    question_data: dict[str, Any],
    embed_model: HuggingFaceEmbedding,
    top_k: int
) -> dict[str, Any]:
    """Retrieve and measure one question."""

    question_id = str(
        question_data["id"]
    )

    query = str(
        question_data["question"]
    ).strip()

    expected_answer = str(
        question_data["expected_answer"]
    ).strip()

    expected_source = str(
        question_data[
            "expected_source_file"
        ]
    )

    query_embedding = (
        embed_model.get_query_embedding(
            query
        )
    )

    retriever = index.as_retriever(
        similarity_top_k=top_k
    )

    started = time.perf_counter()

    retrieved_nodes = retriever.retrieve(
        query
    )

    retrieval_latency_ms = (
        time.perf_counter()
        - started
    ) * 1000

    result_rows: list[
        dict[str, Any]
    ] = []

    document_vectors: list[
        np.ndarray
    ] = []

    for rank, node_with_score in enumerate(
        retrieved_nodes,
        start=1
    ):
        node = node_with_score.node

        returned_text = retrieval_text(
            node,
            technique
        )

        document_embedding = (
            embed_model.get_text_embedding(
                returned_text
            )
        )

        document_vectors.append(
            np.asarray(
                document_embedding,
                dtype=np.float64
            )
        )

        cosine = cosine_similarity(
            query_embedding,
            document_embedding
        )

        source_file = str(
            node.metadata.get(
                "source_file",
                ""
            )
        )

        source_matches = (
            source_file
            == expected_source
        )

        result_rows.append({
            "question_id": question_id,
            "technique": technique,
            "rank": rank,
            "query": query,
            "expected_answer": (
                expected_answer
            ),
            "expected_source_file": (
                expected_source
            ),
            "retrieved_source_file": (
                source_file
            ),
            "source_match": source_matches,
            "store_score": (
                float(node_with_score.score)
                if node_with_score.score
                is not None
                else None
            ),
            "cosine_similarity": cosine,
            "chunk_length": len(
                returned_text
            ),
            "preview": text_preview(
                returned_text
            ),
            "node_id": node.node_id,
            "retrieval_latency_ms": (
                retrieval_latency_ms
            )
        })

    query_shape = (
        len(query_embedding),
    )

    if document_vectors:
        stacked_vectors = np.vstack(
            document_vectors
        )

        document_shape = (
            stacked_vectors.shape
        )
    else:
        document_shape = (
            0,
            len(query_embedding)
        )

    cosines = [
        row["cosine_similarity"]
        for row in result_rows
    ]

    recall_at_k = int(
        any(
            row["source_match"]
            for row in result_rows
        )
    )

    print()
    print("=" * 78)
    print(
        "TECHNIQUE:",
        technique
    )
    print(
        "QUESTION:",
        question_id
    )
    print(
        "QUERY:",
        query
    )
    print(
        "Query embedding dimension:",
        len(query_embedding)
    )
    print(
        "Query embedding first 8 values:",
        [
            round(value, 6)
            for value in query_embedding[:8]
        ]
    )
    print(
        "Query vector shape:",
        query_shape
    )
    print(
        "Stacked document-vector shape:",
        document_shape
    )
    print(
        "Retrieval latency:",
        f"{retrieval_latency_ms:.2f} ms"
    )
    print()
    print(
        f"{'Rank':<6}"
        f"{'Store':<12}"
        f"{'Cosine':<12}"
        f"{'Length':<10}"
        f"{'Source':<38}"
        "Preview"
    )
    print("-" * 150)

    for row in result_rows:
        score = row["store_score"]

        score_text = (
            f"{score:.6f}"
            if score is not None
            else "N/A"
        )

        print(
            f"{row['rank']:<6}"
            f"{score_text:<12}"
            f"{row['cosine_similarity']:<12.6f}"
            f"{row['chunk_length']:<10}"
            f"{row['retrieved_source_file']:<38}"
            f"{row['preview']}"
        )

    print()
    print(
        "Recall@k:",
        recall_at_k
    )

    return {
        "question_id": question_id,
        "technique": technique,
        "query": query,
        "expected_answer": expected_answer,
        "expected_source_file": (
            expected_source
        ),
        "query_embedding_dimension": (
            len(query_embedding)
        ),
        "query_embedding_first_8": [
            float(value)
            for value in query_embedding[:8]
        ],
        "query_vector_shape": list(
            query_shape
        ),
        "document_vector_shape": list(
            document_shape
        ),
        "retrieval_latency_ms": (
            retrieval_latency_ms
        ),
        "top_1_cosine": (
            max(cosines)
            if cosines
            else 0.0
        ),
        "mean_at_k_cosine": (
            mean(cosines)
            if cosines
            else 0.0
        ),
        "recall_at_k": recall_at_k,
        "results": result_rows
    }


def write_jsonl(
    retrieval_runs: list[dict[str, Any]]
) -> None:
    """Write one JSON object per retrieval run."""

    with JSONL_PATH.open(
        "w",
        encoding="utf-8"
    ) as output:
        for run in retrieval_runs:
            output.write(
                json.dumps(
                    run,
                    ensure_ascii=False
                )
            )
            output.write("\n")


def write_csv(
    retrieval_runs: list[dict[str, Any]]
) -> None:
    """Write one CSV row per retrieved chunk."""

    fieldnames = [
        "question_id",
        "technique",
        "rank",
        "query",
        "expected_answer",
        "expected_source_file",
        "retrieved_source_file",
        "source_match",
        "store_score",
        "cosine_similarity",
        "chunk_length",
        "preview",
        "node_id",
        "retrieval_latency_ms"
    ]

    with CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for run in retrieval_runs:
            for row in run["results"]:
                writer.writerow(row)


def summarize_metrics(
    nodes_by_technique: dict[
        str,
        list[BaseNode]
    ],
    retrieval_runs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Calculate the required comparison metrics."""

    summary: dict[str, Any] = {
        "embedding_model": (
            EMBEDDING_MODEL_NAME
        ),
        "top_k": TOP_K,
        "question_count": len({
            run["question_id"]
            for run in retrieval_runs
        }),
        "techniques": {}
    }

    for technique, nodes in (
        nodes_by_technique.items()
    ):
        technique_runs = [
            run
            for run in retrieval_runs
            if run["technique"] == technique
        ]

        chunk_lengths = [
            len(
                retrieval_text(
                    node,
                    technique
                )
            )
            for node in nodes
        ]

        summary["techniques"][
            technique
        ] = {
            "chunk_count": len(nodes),
            "average_chunk_length": (
                mean(chunk_lengths)
                if chunk_lengths
                else 0.0
            ),
            "mean_top_1_cosine": mean(
                run["top_1_cosine"]
                for run in technique_runs
            ),
            "mean_at_k_cosine": mean(
                run["mean_at_k_cosine"]
                for run in technique_runs
            ),
            "recall_at_k": mean(
                run["recall_at_k"]
                for run in technique_runs
            ),
            "recall_at_k_percent": (
                mean(
                    run["recall_at_k"]
                    for run in technique_runs
                )
                * 100
            ),
            "mean_retrieval_latency_ms": (
                mean(
                    run[
                        "retrieval_latency_ms"
                    ]
                    for run in technique_runs
                )
            )
        }

    return summary


def main() -> None:
    """Run the complete retrieval experiment."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "Loading embedding model:",
        EMBEDDING_MODEL_NAME
    )

    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL_NAME,
        device="cpu"
    )

    documents = load_documents()
    questions = load_questions()

    print(
        "Corpus documents:",
        len(documents)
    )

    print(
        "Questions:",
        len(questions)
    )

    nodes_by_technique = build_nodes(
        documents,
        embed_model
    )

    retrieval_runs: list[
        dict[str, Any]
    ] = []

    for technique, nodes in (
        nodes_by_technique.items()
    ):
        print()
        print("=" * 78)
        print(
            "BUILDING INDEX:",
            technique
        )
        print(
            "Number of nodes:",
            len(nodes)
        )

        index = build_index(
            nodes,
            embed_model
        )

        for question in questions:
            run = retrieve_for_question(
                technique=technique,
                index=index,
                question_data=question,
                embed_model=embed_model,
                top_k=TOP_K
            )

            retrieval_runs.append(run)

    write_jsonl(
        retrieval_runs
    )

    write_csv(
        retrieval_runs
    )

    metrics = summarize_metrics(
        nodes_by_technique,
        retrieval_runs
    )

    METRICS_PATH.write_text(
        json.dumps(
            metrics,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print("=" * 78)
    print("FINAL RETRIEVAL METRICS")
    print(
        json.dumps(
            metrics,
            indent=2
        )
    )

    print()
    print("Created:")
    print(JSONL_PATH)
    print(CSV_PATH)
    print(METRICS_PATH)


if __name__ == "__main__":
    main()