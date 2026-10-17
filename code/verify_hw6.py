from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pymongo.errors import PyMongoError

from code.file_memory import (
    AGENT_PATH,
    MEMORY_PATH,
    build_system_prompt,
    consolidation_status,
    handle_command,
    memory_fact_lines,
)
from code.hw6_agent_instruction_demo import (
    filter_trials_by_phase,
)
from code.main import app
from code.mongo_database import (
    get_mongo_database,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw06"
)

RAW_DIRECTORY = (
    REPORT_DIRECTORY
    / "raw"
)

OUTPUT_PATH = (
    REPORT_DIRECTORY
    / "verification.json"
)

checks: list[dict[str, Any]] = []


def record(
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Record one verification check."""

    checks.append({
        "name": name,
        "passed": passed,
        "details": details,
    })


def load_json(
    path: Path,
) -> Any:
    """Load one JSON file."""

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def check_required_files() -> None:
    """Verify all required Homework 6 files exist."""

    required_files = [
        "AGENT.md",
        "MEMORY.md",
        "compose.hw6.yaml",
        "code/mongo_database.py",
        "code/init_hw6_mongodb.py",
        "code/mongo_schemas.py",
        "code/mongo_trials_api.py",
        "code/init_hw6_memory.py",
        "code/memory_schemas.py",
        "code/memory_service.py",
        "code/memory_api.py",
        "code/run_hw6_memory_experiments.py",
        "code/file_memory.py",
        "code/hw6_agent_instruction_demo.py",
        "code/verify_hw6.py",
        "reports/hw06/RUN_LOG.txt",
        "reports/hw06/METRICS.md",
        "reports/hw06/AI_USE.md",
        "reports/hw06/MEMORY_COMPARISON.md",
        "reports/hw06/cases/memory_probes.yaml",
        "reports/hw06/cases/memory_conversation.json",
        "reports/hw06/raw/part1_crud_results.json",
        "reports/hw06/raw/part2_conversation.json",
        "reports/hw06/raw/memory_snapshot.json",
        "reports/hw06/raw/aggregate_snapshot.json",
        "reports/hw06/raw/chat_turn_metrics.csv",
        "reports/hw06/raw/chat_turn_metrics.jsonl",
        "reports/hw06/raw/short_term_sweep_results.json",
        "reports/hw06/raw/short_term_sweep_results.csv",
        "reports/hw06/raw/memory_probe_results.json",
        "reports/hw06/raw/compression_results.json",
        "reports/hw06/raw/memory_experiment_metrics.json",
        "reports/hw06/raw/MEMORY_original.md",
        "reports/hw06/raw/MEMORY_consolidated.md",
    ]

    missing = [
        relative_path
        for relative_path in required_files
        if not (
            PROJECT_ROOT
            / relative_path
        ).is_file()
    ]

    record(
        "required_files",
        not missing,
        (
            "All required Homework 6 files exist."
            if not missing
            else (
                "Missing files: "
                + ", ".join(missing)
            )
        ),
    )


def check_python_version() -> None:
    """Verify the supported Python version."""

    version = sys.version_info

    passed = (
        version.major == 3
        and version.minor in {
            11,
            12,
        }
    )

    record(
        "python_version",
        passed,
        platform.python_version(),
    )


def check_agent_instructions() -> None:
    """Verify required AGENT.md instruction categories."""

    content = AGENT_PATH.read_text(
        encoding="utf-8"
    )

    required_categories = [
        "Project Description",
        "Technology Stack",
        "Coding Conventions",
        "Testing Approach",
        "Prohibited Actions",
    ]

    missing_categories = [
        category
        for category in required_categories
        if category not in content
    ]

    instruction_count = sum(
        1
        for line in content.splitlines()
        if line.strip().startswith("- ")
    )

    passed = (
        not missing_categories
        and instruction_count >= 5
    )

    record(
        "agent_instructions",
        passed,
        (
            f"Instruction count={instruction_count}; "
            f"missing categories={missing_categories}"
        ),
    )


def check_memory_versions() -> None:
    """Verify original and consolidated memory versions."""

    original_path = (
        RAW_DIRECTORY
        / "MEMORY_original.md"
    )

    consolidated_path = (
        RAW_DIRECTORY
        / "MEMORY_consolidated.md"
    )

    try:
        original_content = (
            original_path.read_text(
                encoding="utf-8"
            )
        )

        consolidated_content = (
            consolidated_path.read_text(
                encoding="utf-8"
            )
        )

        original_count = len(
            memory_fact_lines(
                original_content
            )
        )

        consolidated_count = len(
            memory_fact_lines(
                consolidated_content
            )
        )

        resolution_count = (
            consolidated_content.count(
                "CONTRADICTION RESOLVED"
            )
        )

        original_normalized = [
            line.strip().casefold()
            for line in memory_fact_lines(
                original_content
            )
        ]

        duplicate_count = (
            len(original_normalized)
            - len(
                set(
                    original_normalized
                )
            )
        )

        passed = (
            original_count == 55
            and consolidated_count < 40
            and duplicate_count >= 3
            and resolution_count >= 3
        )

        details = (
            f"Original={original_count}, "
            f"consolidated={consolidated_count}, "
            f"duplicates={duplicate_count}, "
            f"resolutions={resolution_count}"
        )
    except Exception as error:
        passed = False
        details = (
            f"{type(error).__name__}: {error}"
        )

    record(
        "memory_versions",
        passed,
        details,
    )


def check_file_memory_functions() -> None:
    """Verify file-memory loading and command behavior."""

    try:
        prompt = build_system_prompt(
            "You are a clinical-trial assistant."
        )

        memory_result = handle_command(
            "/memory"
        )

        help_result = handle_command(
            "/help"
        )

        unknown_result = handle_command(
            "/unknown"
        )

        status = consolidation_status()

        passed = (
            "Durable Agent Instructions"
            in prompt
            and "Durable File-Based Memory"
            in prompt
            and memory_result[
                "command"
            ] == "/memory"
            and "/compact" in help_result[
                "content"
            ]
            and "error" in unknown_result
            and status["line_count"] < 40
        )

        details = (
            "Prompt construction, /memory, /help, "
            "unknown-command handling, and consolidated "
            f"line count verified; count={status['line_count']}."
        )
    except Exception as error:
        passed = False
        details = (
            f"{type(error).__name__}: {error}"
        )

    record(
        "file_memory_functions",
        passed,
        details,
    )


def check_agent_function() -> None:
    """Verify the function generated under AGENT.md rules."""

    trials = [
        {
            "id": 1,
            "trial_title": (
                "Sleep Quality Study"
            ),
            "trial_phase": "Phase II",
        },
        {
            "id": 2,
            "trial_title": (
                "Digital Wellness Study"
            ),
            "trial_phase": "Phase I",
        },
    ]

    valid_result = (
        filter_trials_by_phase(
            trials,
            "Phase II",
        )
    )

    invalid_result = (
        filter_trials_by_phase(
            trials,
            "Phase V",
        )
    )

    passed = (
        valid_result["ok"] is True
        and valid_result[
            "data"
        ]["count"] == 1
        and invalid_result[
            "ok"
        ] is False
        and invalid_result[
            "data"
        ] is None
    )

    record(
        "agent_instruction_function",
        passed,
        (
            "Valid phase was filtered and invalid "
            "phase was rejected using a predictable "
            "response structure."
        ),
    )

def check_fastapi_routes() -> None:
    """Verify required Homework 6 API routes."""

    route_paths = {
        route.path
        for route in app.routes
        if hasattr(
            route,
            "path"
        )
    }

    required_exact_paths = {
        "/api/document-trials",
        "/api/chat",
        "/api/memory/{user_id}",
        "/api/aggregate/{user_id}",
        "/health/mongodb",
    }

    missing = sorted(
        required_exact_paths
        - route_paths
    )

    item_route_present = any(
        path.startswith(
            "/api/document-trials/{"
        )
        and path.endswith("}")
        for path in route_paths
    )

    if not item_route_present:
        missing.append(
            "/api/document-trials/{identifier}"
        )

    record(
        "fastapi_routes",
        not missing,
        (
            "All required HW6 routes are registered."
            if not missing
            else (
                "Missing routes: "
                + ", ".join(missing)
            )
        ),
    )

def check_mongodb() -> None:
    """Verify MongoDB connectivity and collections."""

    required_collections = {
        "trial_documents",
        "messages",
        "summaries",
        "episodes",
    }

    database_generator = None

    try:
        database_source = (
            get_mongo_database()
        )

        if hasattr(
            database_source,
            "command",
        ):
            database = database_source
        else:
            database_generator = (
                database_source
            )

            database = next(
                database_generator
            )

        database.command(
            "ping"
        )

        collection_names = set(
            database.list_collection_names()
        )

        missing = sorted(
            required_collections
            - collection_names
        )

        passed = not missing

        details = (
            "MongoDB ping succeeded; "
            f"collections={sorted(collection_names)}; "
            f"missing={missing}"
        )
    except Exception as error:
        passed = False

        details = (
            f"{type(error).__name__}: {error}"
        )
    finally:
        if (
            database_generator
            is not None
        ):
            database_generator.close()

    record(
        "mongodb_collections",
        passed,
        details,
    )

def check_cases() -> None:
    """Verify conversation and probe case files."""

    conversation_path = (
        REPORT_DIRECTORY
        / "cases"
        / "memory_conversation.json"
    )

    probes_path = (
        REPORT_DIRECTORY
        / "cases"
        / "memory_probes.yaml"
    )

    try:
        conversation_data = load_json(
            conversation_path
        )

        probe_data = yaml.safe_load(
            probes_path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            conversation_data,
            dict,
        ):
            conversation_messages = (
                conversation_data.get(
                    "messages",
                    []
                )
            )
        else:
            conversation_messages = (
                conversation_data
            )

        if isinstance(
            probe_data,
            dict,
        ):
            probes = probe_data.get(
                "probes",
                []
            )
        else:
            probes = probe_data

        passed = (
            len(conversation_messages)
            == 30
            and len(probes) == 5
        )

        details = (
            f"Conversation messages="
            f"{len(conversation_messages)}, "
            f"probes={len(probes)}"
        )
    except Exception as error:
        passed = False
        details = (
            f"{type(error).__name__}: {error}"
        )

    record(
        "experiment_cases",
        passed,
        details,
    )


def check_raw_json_files() -> None:
    """Verify required raw JSON files parse successfully."""

    json_files = [
        "part1_crud_results.json",
        "part2_conversation.json",
        "memory_snapshot.json",
        "aggregate_snapshot.json",
        "short_term_sweep_results.json",
        "memory_probe_results.json",
        "compression_results.json",
        "memory_experiment_metrics.json",
    ]

    invalid: list[str] = []

    for filename in json_files:
        path = (
            RAW_DIRECTORY
            / filename
        )

        try:
            load_json(
                path
            )
        except Exception as error:
            invalid.append(
                (
                    f"{filename}: "
                    f"{type(error).__name__}"
                )
            )

    record(
        "raw_json_files",
        not invalid,
        (
            "All required raw JSON files parsed."
            if not invalid
            else (
                "Invalid JSON files: "
                + ", ".join(invalid)
            )
        ),
    )


def find_configurations(
    metrics: Any,
) -> dict[str, Any]:
    """Locate experiment configurations flexibly."""

    if not isinstance(
        metrics,
        dict,
    ):
        return {}

    configurations = metrics.get(
        "configurations"
    )

    if isinstance(
        configurations,
        dict,
    ):
        return configurations

    for value in metrics.values():
        if not isinstance(
            value,
            dict,
        ):
            continue

        nested = value.get(
            "configurations"
        )

        if isinstance(
            nested,
            dict,
        ):
            return nested

    return {}


def check_experiment_outputs() -> None:
    """Verify the four memory experiment settings."""

    metrics_path = (
        RAW_DIRECTORY
        / "memory_experiment_metrics.json"
    )

    try:
        metrics = load_json(
            metrics_path
        )

        serialized = json.dumps(
            metrics
        ).casefold()

        required_labels = [
            "short_term_n=4",
            "short_term_n=12",
            "short_term_n=30",
            "compression_policy",
        ]

        labels_present = all(
            label.casefold()
            in serialized
            for label in required_labels
        )

        expected_values_present = all([
            "11.83" in serialized,
            "4.2" in serialized,
            "1.4" in serialized,
        ])

        passed = (
            labels_present
            and expected_values_present
        )

        details = (
            "Configurations present="
            f"{labels_present}; expected summary "
            f"metrics present={expected_values_present}."
        )
    except Exception as error:
        passed = False
        details = (
            f"{type(error).__name__}: {error}"
        )

    record(
        "memory_experiment_outputs",
        passed,
        details,
    )


def check_run_log() -> None:
    """Verify the reproducibility run log."""

    path = (
        REPORT_DIRECTORY
        / "RUN_LOG.txt"
    )

    try:
        content = path.read_text(
            encoding="utf-8"
        )

        required_text = [
            "HW6",
            "Memory",
            "Consolidation",
            "AGENT.md",
        ]

        missing = [
            text
            for text in required_text
            if text.casefold()
            not in content.casefold()
        ]

        passed = (
            len(content.strip()) > 0
            and not missing
        )

        details = (
            f"Characters={len(content)}; "
            f"missing markers={missing}"
        )
    except Exception as error:
        passed = False
        details = (
            f"{type(error).__name__}: {error}"
        )

    record(
        "run_log",
        passed,
        details,
    )


def main() -> None:
    """Run all Homework 6 verification checks."""

    check_required_files()
    check_python_version()
    check_agent_instructions()
    check_memory_versions()
    check_file_memory_functions()
    check_agent_function()
    check_fastapi_routes()
    check_mongodb()
    check_cases()
    check_raw_json_files()
    check_experiment_outputs()
    check_run_log()

    passed = all(
        check["passed"]
        for check in checks
    )

    result = {
        "assignment": (
            "DATA-260 Homework 6"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "verifySeed": 267801,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": passed,
        "checks": checks,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()