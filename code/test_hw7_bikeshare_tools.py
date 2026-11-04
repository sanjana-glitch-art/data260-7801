from __future__ import annotations

import csv
import inspect
import json
import os
import tempfile
import threading
from code import hw7_bikeshare_tools as tools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIRECTORY = PROJECT_ROOT / "reports" / "hw07" / "raw"

RESULTS_PATH = RESULTS_DIRECTORY / "bikeshare_tool_test_results.json"


ToolFunction = Callable[
    ...,
    dict[str, Any],
]


def create_trip_csv(
    path: Path,
    row_count: int = 600,
) -> None:
    """Create a deterministic Bike Share test CSV."""

    fieldnames = [
        "ride_id",
        "started_at",
        "ended_at",
        "duration_minutes",
        "week_number",
        "member_type",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for index in range(
            1,
            row_count + 1,
        ):
            week_number = ((index - 1) % 4) + 1

            duration = 8 + (index % 28)

            writer.writerow(
                {
                    "ride_id": (f"ride-{index:04d}"),
                    "started_at": (f"2026-10-{((index - 1) % 28) + 1:02d}T08:00:00"),
                    "ended_at": (f"2026-10-{((index - 1) % 28) + 1:02d}T08:30:00"),
                    "duration_minutes": (duration),
                    "week_number": (week_number),
                    "member_type": ("casual" if index % 3 else "member"),
                }
            )


def create_pricing_page(
    path: Path,
) -> None:
    """Create a local pricing-policy test page."""

    path.write_text(
        """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bike Share Pricing Test</title>
</head>
<body>
    <main>
        <h1>Bike Share Pricing</h1>

        <section>
            <h2>Pay per ride</h2>
            <p>
                A single ride costs $4.99 and includes
                the first 30 minutes.
            </p>
        </section>

        <section>
            <h2>Monthly membership</h2>
            <p>
                Monthly membership costs $19.00.
                Membership includes rides up to
                45 minutes.
            </p>
        </section>

        <section>
            <h2>Overage policy</h2>
            <p>
                Additional ride time costs $0.25
                per minute after the included time.
            </p>
        </section>
    </main>
</body>
</html>
        """.strip()
        + "\n",
        encoding="utf-8",
    )


class QuietRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler without console request logs."""

    def log_message(
        self,
        format_string: str,
        *args: object,
    ) -> None:
        """Suppress HTTP server logging."""


@contextmanager
def local_http_server(
    directory: Path,
) -> Iterator[str]:
    """Serve a temporary directory over localhost."""

    handler = partial(
        QuietRequestHandler,
        directory=str(directory),
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        handler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def configure_csv_path(
    csv_path: Path,
) -> None:
    """
    Configure the uploaded CSV for common implementations.

    The Homework 7 tool accepts only a SQL object, so the
    uploaded file is normally configured separately.
    """

    os.environ["HW7_BIKESHARE_CSV"] = str(csv_path)

    os.environ["BIKESHARE_CSV_PATH"] = str(csv_path)

    os.environ["UPLOADED_CSV_PATH"] = str(csv_path)

    setter_names = (
        "configure_csv",
        "configure_csv_path",
        "set_csv_path",
        "set_uploaded_csv",
        "set_uploaded_csv_path",
    )

    for setter_name in setter_names:
        setter = getattr(
            tools,
            setter_name,
            None,
        )

        if callable(setter):
            setter(csv_path)
            return

    path_attribute_names = (
        "ACTIVE_CSV_PATH",
        "CSV_PATH",
        "UPLOADED_CSV_PATH",
    )

    for attribute_name in path_attribute_names:
        if hasattr(
            tools,
            attribute_name,
        ):
            setattr(
                tools,
                attribute_name,
                csv_path,
            )


def call_tool(
    function: ToolFunction,
    payload: dict[str, Any],
    *,
    csv_path: Path | None = None,
) -> dict[str, Any]:
    """
    Call a tool using its declared signature.

    This supports either pure keyword parameters or one
    dictionary input object.
    """

    signature = inspect.signature(function)

    parameters = list(signature.parameters.values())

    keyword_arguments: dict[
        str,
        Any,
    ] = {}

    for parameter in parameters:
        name = parameter.name

        if name in payload:
            keyword_arguments[name] = payload[name]

        elif csv_path is not None and name in {
            "csv_path",
            "file_path",
            "uploaded_csv",
            "uploaded_csv_path",
        }:
            keyword_arguments[name] = csv_path

    required_parameters = [
        parameter
        for parameter in parameters
        if (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }
        )
    ]

    if (
        len(required_parameters) == 1
        and required_parameters[0].name not in payload
        and required_parameters[0].name not in keyword_arguments
    ):
        result = function(payload)
    else:
        result = function(**keyword_arguments)

    if not isinstance(
        result,
        dict,
    ):
        raise TypeError("Tool result must be a dictionary.")

    return result


def validate_common_shape(
    result: dict[str, Any],
) -> None:
    """Validate the required common tool envelope."""

    assert "success" in result, "Missing required success field."

    assert isinstance(
        result["success"],
        bool,
    )

    if result["success"]:
        assert "data" in result, "A successful result must contain data."
    else:
        assert result.get("error"), "A failed result must contain an error."


def successful_data(
    result: dict[str, Any],
) -> Any:
    """Return data from a successful tool result."""

    validate_common_shape(result)

    assert result["success"] is True, result.get("error") or "Tool call failed."

    return result["data"]


def run_csv_sql_test(
    csv_path: Path,
) -> dict[str, Any]:
    """Test successful and blocked CSV SQL calls."""

    csv_sql = getattr(
        tools,
        "csv_sql",
        None,
    )

    assert callable(csv_sql), "hw7_bikeshare_tools.py must define csv_sql."

    configure_csv_path(csv_path)

    candidate_table_names = (
        "trips",
        "uploaded",
        "uploaded_csv",
    )

    select_result: dict[str, Any] | None = None

    selected_table: str | None = None

    errors: list[str] = []

    for table_name in candidate_table_names:
        result = call_tool(
            csv_sql,
            {
                "sql": (
                    "SELECT "
                    "COUNT(*) AS trip_count, "
                    "ROUND("
                    "AVG(duration_minutes), 2"
                    ") AS average_duration "
                    f"FROM {table_name}"
                ),
            },
            csv_path=csv_path,
        )

        validate_common_shape(result)

        if result["success"]:
            select_result = result
            selected_table = table_name
            break

        errors.append(str(result.get("error")))

    assert select_result is not None, (
        f"csv_sql could not query an uploaded table. Errors: {errors}"
    )

    select_data = successful_data(select_result)

    assert isinstance(
        select_data,
        dict,
    )

    rows = select_data.get("rows")

    assert isinstance(
        rows,
        list,
    )

    assert rows, "csv_sql returned no aggregate row."

    trip_count = int(rows[0]["trip_count"])

    assert trip_count == 600, f"Expected 600 CSV rows, received {trip_count}."

    assert select_data.get("row_count") == 1

    blocked_result = call_tool(
        csv_sql,
        {
            "sql": (f"DELETE FROM {selected_table}"),
        },
        csv_path=csv_path,
    )

    validate_common_shape(blocked_result)

    assert blocked_result["success"] is False, "csv_sql allowed a DELETE statement."

    assert blocked_result.get("error")

    return {
        "passed": True,
        "selected_table": (selected_table),
        "trip_count": trip_count,
        "average_duration": rows[0].get("average_duration"),
        "delete_blocked": True,
        "delete_error": (blocked_result["error"]),
    }


def run_policy_retriever_test(
    pricing_url: str,
) -> dict[str, Any]:
    """Test retrieval from the local pricing page."""

    previous_setting = os.environ.get("HW7_ALLOW_LOCAL_POLICY_TEST")

    os.environ["HW7_ALLOW_LOCAL_POLICY_TEST"] = "1"

    retriever = getattr(
        tools,
        "policy_retriever",
        None,
    )

    assert callable(retriever), "hw7_bikeshare_tools.py must define policy_retriever."

    try:
        result = call_tool(
            retriever,
            {
                "url": pricing_url,
                "query": ("monthly membership price included minutes overage fee"),
                "k": 3,
            },
        )
    finally:
        if previous_setting is None:
            os.environ.pop(
                "HW7_ALLOW_LOCAL_POLICY_TEST",
                None,
            )
        else:
            os.environ["HW7_ALLOW_LOCAL_POLICY_TEST"] = previous_setting

    data = successful_data(result)

    assert isinstance(
        data,
        dict,
    )

    passages = data.get("passages")

    assert isinstance(
        passages,
        list,
    )

    assert passages, "policy_retriever returned no passages."

    for passage in passages:
        assert isinstance(
            passage,
            dict,
        )

        assert passage.get("text")

        assert passage.get("source")

        assert isinstance(
            passage.get("score"),
            (int, float),
        )

    joined_text = " ".join(str(passage["text"]) for passage in passages).casefold()

    assert "membership" in joined_text or "$19.00" in joined_text

    return {
        "passed": True,
        "passage_count": len(passages),
        "first_passage": (passages[0]),
    }


def run_calculator_test() -> dict[str, Any]:
    """Test safe arithmetic and expression blocking."""

    calculator = getattr(
        tools,
        "calculator",
        None,
    )

    assert callable(calculator), "hw7_bikeshare_tools.py must define calculator."

    valid_result = call_tool(
        calculator,
        {
            "expression": ("(4.99 * 12) + (0.25 * 8)"),
            "units": "USD",
        },
    )

    valid_data = successful_data(valid_result)

    assert isinstance(
        valid_data,
        dict,
    )

    value = float(valid_data["value"])

    assert abs(value - 61.88) < 0.0001

    assert valid_data.get("units") == "USD"

    unsafe_result = call_tool(
        calculator,
        {
            "expression": ("__import__('os').system('echo unsafe')"),
            "units": "USD",
        },
    )

    validate_common_shape(unsafe_result)

    assert unsafe_result["success"] is False, (
        "Calculator allowed a non-arithmetic expression."
    )

    return {
        "passed": True,
        "calculated_value": value,
        "units": (valid_data.get("units")),
        "unsafe_expression_blocked": True,
        "unsafe_error": (unsafe_result.get("error")),
    }


def run_schema_test() -> dict[str, Any]:
    """Check that the three JSON schemas are available."""

    possible_schema_names = {
        "csv_sql": (
            "CSV_SQL_SCHEMA",
            "CSV_SQL_JSON_SCHEMA",
        ),
        "policy_retriever": (
            "POLICY_RETRIEVER_SCHEMA",
            "POLICY_RETRIEVER_JSON_SCHEMA",
        ),
        "calculator": (
            "CALCULATOR_SCHEMA",
            "CALCULATOR_JSON_SCHEMA",
        ),
    }

    found: dict[str, str] = {}

    for tool_name, names in possible_schema_names.items():
        for name in names:
            schema = getattr(
                tools,
                name,
                None,
            )

            if isinstance(
                schema,
                dict,
            ):
                found[tool_name] = name
                break

    missing = sorted(set(possible_schema_names) - set(found))

    assert not missing, "Missing JSON schemas for: " + ", ".join(missing)

    return {
        "passed": True,
        "schemas": found,
    }


def main() -> None:
    """Run all Homework 7 Bike Share tool tests."""

    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("DATA-260 Homework 7 Part 4")

    print("Bike Share MRKL Tool Tests")

    results: dict[str, Any] = {
        "experiment": ("hw7_bikeshare_tool_tests"),
        "student": ("Sanjana Thummalapalli"),
        "sid4": 7801,
        "checks": {},
        "passed": False,
    }

    with tempfile.TemporaryDirectory(prefix="hw7_bikeshare_") as temporary_directory:
        sandbox = Path(temporary_directory)

        csv_path = sandbox / "uploaded.csv"

        pricing_path = sandbox / "pricing.html"

        create_trip_csv(csv_path)

        create_pricing_page(pricing_path)

        with local_http_server(sandbox) as base_url:
            pricing_url = f"{base_url}/{pricing_path.name}"

            checks: tuple[
                tuple[
                    str,
                    Callable[
                        [],
                        dict[str, Any],
                    ],
                ],
                ...,
            ] = (
                (
                    "json_schemas",
                    run_schema_test,
                ),
                (
                    "csv_sql",
                    lambda: (run_csv_sql_test(csv_path)),
                ),
                (
                    "policy_retriever",
                    lambda: (run_policy_retriever_test(pricing_url)),
                ),
                (
                    "calculator",
                    run_calculator_test,
                ),
            )

            all_passed = True

            for name, check in checks:
                try:
                    details = check()
                except Exception as error:  # noqa: BLE001
                    all_passed = False

                    results["checks"][name] = {
                        "passed": False,
                        "error": (f"{type(error).__name__}: {error}"),
                    }

                    print(f"FAIL | {name} | {type(error).__name__}: {error}")
                else:
                    results["checks"][name] = details

                    print(f"PASS | {name}")

    results["passed"] = all_passed

    RESULTS_PATH.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\nOverall:",
        ("PASS" if all_passed else "FAIL"),
    )

    print(f"Results: {RESULTS_PATH}")

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
