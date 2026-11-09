from __future__ import annotations

import ast
import hashlib
import json
import math
import operator
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import duckdb
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIRECTORY = PROJECT_ROOT / "reports" / "hw07" / "raw"

SNAPSHOT_DIRECTORY = RAW_DIRECTORY / "pricing_snapshots"

DEFAULT_PRICING_URL = "https://citibikenyc.com/pricing"

CURRENT_CSV_PATH: Path | None = None


CSV_SQL_SCHEMA: dict[str, Any] = {
    "name": "csv_sql",
    "description": (
        "Run one read-only SELECT query over the currently uploaded Bike Share CSV."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
            },
        },
        "required": [
            "sql",
        ],
        "additionalProperties": False,
    },
}


POLICY_RETRIEVER_SCHEMA: dict[str, Any] = {
    "name": "policy_retriever",
    "description": (
        "Retrieve short pricing and policy passages "
        "from an official Bike Share webpage."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
            },
            "query": {
                "type": "string",
            },
            "k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": [
            "url",
            "query",
        ],
        "additionalProperties": False,
    },
}


CALCULATOR_SCHEMA: dict[str, Any] = {
    "name": "calculator",
    "description": ("Safely evaluate a basic arithmetic expression."),
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "pattern": (r"^[0-9+\-*/().\s]+$"),
            },
            "units": {
                "type": "string",
            },
        },
        "required": [
            "expression",
        ],
        "additionalProperties": False,
    },
}


TOOL_SCHEMAS: tuple[
    dict[str, Any],
    ...,
] = (
    CSV_SQL_SCHEMA,
    POLICY_RETRIEVER_SCHEMA,
    CALCULATOR_SCHEMA,
)


ALLOWED_EXPRESSION_PATTERN = re.compile(r"^[0-9+\-*/().\s]+$")


PROHIBITED_SQL_PATTERN = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|"
    r"replace|truncate|attach|detach|copy|"
    r"export|import|pragma|call|install|load"
    r")\b",
    re.IGNORECASE,
)


ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC).isoformat()


def success_envelope(
    data: Any,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    """Create a common successful tool response."""

    response: dict[str, Any] = {
        "success": True,
        "data": data,
        "ts": utc_timestamp(),
    }

    if source is not None:
        response["source"] = source

    return response


def error_envelope(
    message: str,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    """Create a common unsuccessful tool response."""

    response: dict[str, Any] = {
        "success": False,
        "error": message,
        "ts": utc_timestamp(),
    }

    if source is not None:
        response["source"] = source

    return response


def configure_csv(
    csv_path: str | Path,
) -> Path:
    """Configure the uploaded CSV used by csv_sql."""

    global CURRENT_CSV_PATH

    resolved_path = Path(csv_path).resolve()

    if not resolved_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {resolved_path}")

    if not resolved_path.is_file():
        raise ValueError("CSV path must identify a file.")

    if resolved_path.suffix.casefold() != ".csv":
        raise ValueError("Uploaded file must have a .csv extension.")

    CURRENT_CSV_PATH = resolved_path

    return resolved_path


def validate_read_only_select(
    sql: str,
) -> tuple[bool, str]:
    """Validate the single read-only SELECT contract."""

    normalized_sql = " ".join(sql.strip().split())

    if not normalized_sql:
        return (
            False,
            "SQL query must not be empty.",
        )

    if not normalized_sql.casefold().startswith(
        (
            "select ",
            "with ",
        )
    ):
        return (
            False,
            ("csv_sql accepts only one read-only SELECT query."),
        )

    without_final_semicolon = normalized_sql.rstrip(";")

    if ";" in without_final_semicolon:
        return (
            False,
            ("csv_sql accepts exactly one SQL statement."),
        )

    if PROHIBITED_SQL_PATTERN.search(normalized_sql):
        return (
            False,
            ("csv_sql rejected a prohibited non-read-only SQL keyword."),
        )

    return (
        True,
        "Read-only SQL validation passed.",
    )


def csv_sql(
    sql: str,
) -> dict[str, Any]:
    """
    Run a read-only query over the uploaded CSV.

    The CSV is exposed to DuckDB as the table trips.
    """

    if CURRENT_CSV_PATH is None:
        return error_envelope(
            "No CSV has been configured.",
            source="uploaded.csv",
        )

    valid, validation_message = validate_read_only_select(sql)

    if not valid:
        return error_envelope(
            validation_message,
            source="uploaded.csv",
        )

    csv_path_text = str(CURRENT_CSV_PATH).replace(
        "'",
        "''",
    )

    connection = duckdb.connect(database=":memory:")

    try:
        connection.execute(
            "CREATE VIEW trips AS "
            "SELECT * FROM read_csv_auto("
            f"'{csv_path_text}', "
            "header = true, "
            "sample_size = -1"
            ")"
        )

        result = connection.execute(sql)

        column_names = [description[0] for description in (result.description or [])]

        raw_rows = result.fetchall()

        rows = [
            dict(
                zip(
                    column_names,
                    row,
                    strict=True,
                )
            )
            for row in raw_rows
        ]

        return success_envelope(
            {
                "rows": rows,
                "row_count": len(rows),
                "source": "uploaded.csv",
            },
            source="uploaded.csv",
        )
    except duckdb.Error as error:
        return error_envelope(
            (f"CSV query failed safely: {type(error).__name__}: {error}"),
            source="uploaded.csv",
        )
    finally:
        connection.close()


def allowed_policy_url(
    url: str,
) -> bool:
    """
    Restrict retrieval to approved HTTPS domains.

    Loopback HTTP URLs are permitted only when the explicit
    automated-test environment variable is enabled.
    """

    parsed = urlparse(url)

    host = (parsed.hostname or "").casefold()

    allow_local_test_url = (
        os.getenv(
            "HW7_ALLOW_LOCAL_POLICY_TEST",
            "0",
        )
        == "1"
    )

    if (
        allow_local_test_url
        and parsed.scheme == "http"
        and host
        in {
            "127.0.0.1",
            "localhost",
        }
    ):
        return True

    if parsed.scheme != "https":
        return False

    allowed_hosts = {
        "citibikenyc.com",
        "www.citibikenyc.com",
    }

    return host in allowed_hosts


def split_passages(
    text: str,
) -> list[str]:
    """Split webpage text into short quotable passages."""

    pieces = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    passages: list[str] = []

    for piece in pieces:
        cleaned = " ".join(piece.split())

        if len(cleaned) < 25:
            continue

        if len(cleaned) > 500:
            cleaned = cleaned[:500]

        passages.append(cleaned)

    return passages


def lexical_score(
    passage: str,
    query: str,
) -> float:
    """Calculate a simple deterministic retrieval score."""

    query_terms = {
        term
        for term in re.findall(
            r"[a-z0-9$]+",
            query.casefold(),
        )
        if len(term) > 1
    }

    passage_terms = set(
        re.findall(
            r"[a-z0-9$]+",
            passage.casefold(),
        )
    )

    if not query_terms:
        return 0.0

    matches = len(query_terms & passage_terms)

    return round(
        matches / len(query_terms),
        4,
    )


def fetch_policy_text(
    url: str,
) -> tuple[str, str]:
    """Fetch and extract text from an allowed policy URL."""

    if not allowed_policy_url(url):
        raise ValueError("Policy URL is not in the allowed HTTPS domain list.")

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": ("DATA260-HW7-S7801/1.0"),
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        element.decompose()

    page_text = " ".join(
        soup.get_text(
            " ",
            strip=True,
        ).split()
    )

    return (
        page_text,
        str(response.url),
    )


def save_policy_snapshot(
    text: str,
    url: str,
    *,
    label: str,
) -> dict[str, str]:
    """Save policy evidence with URL, timestamp, and hash."""

    SNAPSHOT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_label = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        label,
    ).strip("_")

    if not safe_label:
        safe_label = "snapshot"

    snapshot_path = SNAPSHOT_DIRECTORY / f"{safe_label}.txt"

    metadata_path = SNAPSHOT_DIRECTORY / f"{safe_label}.json"

    snapshot_path.write_text(
        text + "\n",
        encoding="utf-8",
    )

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    metadata = {
        "source_url": url,
        "accessed_at": utc_timestamp(),
        "sha256": digest,
        "snapshot_path": str(snapshot_path),
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return metadata


def policy_retriever(
    url: str,
    query: str,
    k: int = 5,
) -> dict[str, Any]:
    """Retrieve short pricing passages from an official page."""

    cleaned_query = query.strip()

    if not cleaned_query:
        return error_envelope(
            "Policy query must not be empty.",
            source=url,
        )

    if not isinstance(k, int) or k < 1 or k > 10:
        return error_envelope(
            "k must be an integer from 1 through 10.",
            source=url,
        )

    try:
        page_text, final_url = fetch_policy_text(url)
    except (
        requests.RequestException,
        ValueError,
    ) as error:
        return error_envelope(
            (f"Policy retrieval failed safely: {type(error).__name__}: {error}"),
            source=url,
        )

    ranked_passages = sorted(
        (
            {
                "text": passage,
                "source": final_url,
                "score": lexical_score(
                    passage,
                    cleaned_query,
                ),
            }
            for passage in split_passages(page_text)
        ),
        key=lambda item: (
            item["score"],
            len(item["text"]),
        ),
        reverse=True,
    )

    selected = ranked_passages[:k]

    return success_envelope(
        {
            "passages": selected,
        },
        source=final_url,
    )


def evaluate_expression_node(
    node: ast.AST,
) -> float:
    """Safely evaluate one parsed arithmetic node."""

    if isinstance(
        node,
        ast.Expression,
    ):
        return evaluate_expression_node(node.body)

    if isinstance(
        node,
        ast.Constant,
    ):
        if not isinstance(
            node.value,
            (
                int,
                float,
            ),
        ):
            raise TypeError("Only numeric constants are allowed.")

        return float(node.value)

    if isinstance(
        node,
        ast.BinOp,
    ):
        operator_function = ALLOWED_BINARY_OPERATORS.get(type(node.op))

        if operator_function is None:
            raise ValueError("Arithmetic operator is not allowed.")

        left_value = evaluate_expression_node(node.left)

        right_value = evaluate_expression_node(node.right)

        return float(
            operator_function(
                left_value,
                right_value,
            )
        )

    if isinstance(
        node,
        ast.UnaryOp,
    ):
        operator_function = ALLOWED_UNARY_OPERATORS.get(type(node.op))

        if operator_function is None:
            raise ValueError("Unary operator is not allowed.")

        return float(operator_function(evaluate_expression_node(node.operand)))

    raise ValueError("Expression contains an unsupported element.")


def calculator(
    expression: str,
    units: str | None = None,
) -> dict[str, Any]:
    """Safely evaluate basic arithmetic without eval."""

    cleaned_expression = expression.strip()

    if not cleaned_expression:
        return error_envelope("Expression must not be empty.")

    if not ALLOWED_EXPRESSION_PATTERN.fullmatch(cleaned_expression):
        return error_envelope(
            "Expression contains characters outside the arithmetic allowlist."
        )

    try:
        expression_tree = ast.parse(
            cleaned_expression,
            mode="eval",
        )

        value = evaluate_expression_node(expression_tree)
    except (
        SyntaxError,
        TypeError,
        ValueError,
        ZeroDivisionError,
        OverflowError,
    ) as error:
        return error_envelope(
            f"Calculation failed safely: {type(error).__name__}: {error}"
        )

    if not math.isfinite(value):
        return error_envelope("Calculation produced a non-finite value.")

    data: dict[str, Any] = {
        "value": value,
    }

    if units:
        data["units"] = units

    return success_envelope(data)
