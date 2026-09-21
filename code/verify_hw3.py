from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROJECT_ROOT_STRING = str(
    PROJECT_ROOT
)

if PROJECT_ROOT_STRING not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT_STRING
    )

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw03"
)

OUTPUT_PATH = (
    REPORT_DIRECTORY
    / "verification.json"
)

QUESTIONS_PATH = (
    REPORT_DIRECTORY
    / "questions.yaml"
)

MANIFEST_PATH = (
    REPORT_DIRECTORY
    / "CORPUS_MANIFEST.json"
)

JSONL_PATH = (
    REPORT_DIRECTORY
    / "raw"
    / "retrieval_results.jsonl"
)

CSV_PATH = (
    REPORT_DIRECTORY
    / "raw"
    / "retrieval_results.csv"
)

METRICS_PATH = (
    REPORT_DIRECTORY
    / "raw"
    / "retrieval_metrics.json"
)

checks: list[dict[str, Any]] = []


def record(
    name: str,
    passed: bool,
    details: str
) -> None:
    """Record one verification result."""

    checks.append({
        "name": name,
        "passed": bool(passed),
        "details": details
    })


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hash of a file."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(65536),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def check_required_files() -> None:
    """Confirm the required HW3 files exist."""

    required_files = [
        "code/main.py",
        "code/auth.py",
        "code/templates/base.html",
        "code/templates/home.html",
        "code/templates/login.html",
        "code/templates/dashboard.html",
        "code/prepare_hw3_corpus.py",
        "code/run_hw3_retrieval.py",
        "code/verify_hw3.py",
        "requirements.txt",
        "reports/hw03/AI_USE.md",
        "reports/hw03/METRICS.md",
        "reports/hw03/RUN_LOG.txt",
        (
            "reports/hw03/"
            "reproducible_run_instructions.md"
        ),
        "reports/hw03/SOURCES.md",
        "reports/hw03/CORPUS_MANIFEST.json",
        "reports/hw03/questions.yaml",
        (
            "reports/hw03/raw/"
            "retrieval_results.jsonl"
        ),
        (
            "reports/hw03/raw/"
            "retrieval_results.csv"
        ),
        (
            "reports/hw03/raw/"
            "retrieval_metrics.json"
        )
    ]

    missing = [
        path
        for path in required_files
        if not (
            PROJECT_ROOT / path
        ).is_file()
    ]

    record(
        "required_files",
        not missing,
        (
            "All required implementation and "
            "evidence files exist."
            if not missing
            else (
                "Missing files: "
                + ", ".join(missing)
            )
        )
    )


def check_python_version() -> None:
    """Check the supported Python version."""

    version = sys.version_info

    passed = (
        version.major == 3
        and version.minor in {
            11,
            12
        }
    )

    record(
        "python_version",
        passed,
        platform.python_version()
    )


def check_dependencies() -> None:
    """Confirm the main runtime modules exist."""

    modules = {
        "fastapi": "FastAPI",
        "starlette": "Starlette",
        "jinja2": "Jinja2",
        "itsdangerous": "itsdangerous",
        "yaml": "PyYAML",
        "llama_index": "LlamaIndex",
        "sentence_transformers": (
            "sentence-transformers"
        ),
        "faiss": "FAISS",
        "numpy": "NumPy",
        "pandas": "pandas"
    }

    missing = [
        package_name
        for module_name, package_name
        in modules.items()
        if importlib.util.find_spec(
            module_name
        ) is None
    ]

    record(
        "dependencies",
        not missing,
        (
            "Required runtime modules are available."
            if not missing
            else (
                "Missing dependencies: "
                + ", ".join(missing)
            )
        )
    )


def check_authentication_source() -> None:
    """Check required authentication implementation."""

    main_source = (
        PROJECT_ROOT
        / "code"
        / "main.py"
    ).read_text(encoding="utf-8")

    auth_source = (
        PROJECT_ROOT
        / "code"
        / "auth.py"
    ).read_text(encoding="utf-8")

    requirements = {
        "SessionMiddleware": (
            "SessionMiddleware"
            in main_source
        ),
        "secure cookie": (
            "https_only=True"
            in main_source
        ),
        "SameSite Lax": (
            'same_site="lax"'
            in main_source
        ),
        "namespaced cookie": (
            'session_cookie=f"{PREFIX}_session"'
            in main_source
        ),
        "idle timeout": (
            "SESSION_IDLE_SECONDS"
            in auth_source
            and "last_activity"
            in auth_source
        ),
        "session clear": (
            "request.session.clear()"
            in auth_source
        ),
        "constant-time comparison": (
            "secrets.compare_digest"
            in auth_source
        ),
        "router": (
            "APIRouter"
            in auth_source
        ),
        "router included": (
            "include_router"
            in main_source
        )
    }

    failed = [
        name
        for name, passed
        in requirements.items()
        if not passed
    ]

    record(
        "authentication_source",
        not failed,
        (
            "Authentication and session requirements "
            "were found."
            if not failed
            else (
                "Missing implementation markers: "
                + ", ".join(failed)
            )
        )
    )


def check_fastapi_routes() -> None:
    """Import the app and check required routes."""

    try:
        from code.main import app

        route_methods: set[
            tuple[str, str]
        ] = set()

        for route in app.routes:
            path = getattr(
                route,
                "path",
                ""
            )

            methods = getattr(
                route,
                "methods",
                set()
            ) or set()

            for method in methods:
                route_methods.add(
                    (
                        method.upper(),
                        path
                    )
                )

        required_routes = {
            ("GET", "/"),
            ("GET", "/login"),
            ("POST", "/login"),
            ("GET", "/dashboard"),
            ("GET", "/logout"),
            ("GET", "/trials"),
            ("GET", "/api/trials"),
            ("POST", "/api/trials"),
            (
                "GET",
                "/api/trials/{trial_id}"
            ),
            (
                "PUT",
                "/api/trials/{trial_id}"
            ),
            (
                "DELETE",
                "/api/trials/{trial_id}"
            )
        }

        missing = sorted(
            required_routes
            - route_methods
        )

        record(
            "fastapi_routes",
            not missing,
            (
                "All required FastAPI routes "
                "are registered."
                if not missing
                else (
                    "Missing routes: "
                    + ", ".join(
                        f"{method} {path}"
                        for method, path
                        in missing
                    )
                )
            )
        )

    except Exception as error:
        record(
            "fastapi_routes",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_demo_credentials() -> None:
    """Verify valid and invalid credentials."""

    try:
        from code.auth import (
            DEMO_PASSWORD,
            DEMO_USERNAME,
            credentials_are_valid
        )

        valid_passes = (
            credentials_are_valid(
                DEMO_USERNAME,
                DEMO_PASSWORD
            )
        )

        invalid_rejected = not (
            credentials_are_valid(
                DEMO_USERNAME,
                "incorrect-password"
            )
        )

        passed = (
            valid_passes
            and invalid_rejected
        )

        record(
            "credential_validation",
            passed,
            (
                "Valid credentials were accepted and "
                "invalid credentials were rejected."
                if passed
                else (
                    "Credential validation did not "
                    "behave as expected."
                )
            )
        )

    except Exception as error:
        record(
            "credential_validation",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_bootstrap_templates() -> None:
    """Check templates and Bootstrap usage."""

    template_directory = (
        PROJECT_ROOT
        / "code"
        / "templates"
    )

    template_names = [
        "base.html",
        "home.html",
        "login.html",
        "dashboard.html"
    ]

    templates = {}

    for name in template_names:
        path = (
            template_directory / name
        )

        templates[name] = (
            path.read_text(
                encoding="utf-8"
            )
            if path.is_file()
            else ""
        )

    requirements = {
        "Bootstrap CSS": (
            "bootstrap"
            in templates["base.html"].lower()
        ),
        "navbar": (
            "navbar"
            in templates["base.html"]
        ),
        "login form": (
            'action="/login"'
            in templates["login.html"]
            and 'name="username"'
            in templates["login.html"]
            and 'name="password"'
            in templates["login.html"]
        ),
        "Bootstrap alert": (
            "alert"
            in templates["login.html"]
        ),
        "dashboard user": (
            "user.display_name"
            in templates["dashboard.html"]
        ),
        "logout link": (
            'href="/logout"'
            in templates["dashboard.html"]
        )
    }

    failed = [
        name
        for name, passed
        in requirements.items()
        if not passed
    ]

    record(
        "bootstrap_templates",
        not failed,
        (
            "Bootstrap authentication templates passed."
            if not failed
            else (
                "Template checks failed: "
                + ", ".join(failed)
            )
        )
    )


def check_corpus_manifest() -> None:
    """Validate corpus size, files, sizes, and hashes."""

    try:
        manifest = json.loads(
            MANIFEST_PATH.read_text(
                encoding="utf-8"
            )
        )

        files = manifest.get(
            "files",
            []
        )

        problems: list[str] = []
        actual_total = 0

        for file_data in files:
            relative_path = Path(
                file_data["relativePath"]
            )

            path = (
                PROJECT_ROOT
                / relative_path
            )

            if not path.is_file():
                problems.append(
                    f"Missing corpus file: "
                    f"{relative_path}"
                )
                continue

            actual_size = (
                path.stat().st_size
            )

            actual_total += actual_size

            expected_size = int(
                file_data["byteSize"]
            )

            if actual_size != expected_size:
                problems.append(
                    f"Size mismatch: "
                    f"{relative_path}"
                )

            actual_hash = sha256_file(
                path
            )

            expected_hash = str(
                file_data["sha256"]
            )

            if actual_hash != expected_hash:
                problems.append(
                    f"Hash mismatch: "
                    f"{relative_path}"
                )

        manifest_total = int(
            manifest.get(
                "totalTextBytes",
                0
            )
        )

        if manifest_total != actual_total:
            problems.append(
                "Manifest total does not match "
                "the actual total."
            )

        if actual_total < 200000:
            problems.append(
                "Corpus is below 200,000 bytes."
            )

        if len(files) < 2:
            problems.append(
                "Corpus must contain multiple files."
            )

        record(
            "corpus_manifest",
            not problems,
            (
                f"Files={len(files)}, "
                f"total bytes={actual_total}, "
                "hashes and sizes valid."
                if not problems
                else "; ".join(problems)
            )
        )

    except Exception as error:
        record(
            "corpus_manifest",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def load_questions() -> list[
    dict[str, Any]
]:
    """Load questions for shared checks."""

    data = yaml.safe_load(
        QUESTIONS_PATH.read_text(
            encoding="utf-8"
        )
    )

    return data.get(
        "questions",
        []
    )


def check_questions() -> None:
    """Validate the domain questions."""

    try:
        questions = load_questions()

        required_fields = {
            "id",
            "question",
            "expected_answer",
            "expected_source_file"
        }

        invalid_questions = [
            question.get(
                "id",
                "unknown"
            )
            for question in questions
            if not required_fields.issubset(
                question
            )
        ]

        source_counts: dict[
            str,
            int
        ] = {}

        for question in questions:
            source = str(
                question.get(
                    "expected_source_file",
                    ""
                )
            )

            source_counts[source] = (
                source_counts.get(
                    source,
                    0
                )
                + 1
            )

        passed = (
            len(questions) >= 5
            and not invalid_questions
            and len(source_counts) >= 2
        )

        record(
            "questions",
            passed,
            (
                f"Questions={len(questions)}, "
                f"expected sources={len(source_counts)}, "
                f"invalid={invalid_questions}"
            )
        )

    except Exception as error:
        record(
            "questions",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_question_preregistration() -> None:
    """Check that questions were added before raw results."""

    try:
        question_command = [
            "git",
            "log",
            "--diff-filter=A",
            "--format=%ct",
            "-1",
            "--",
            "reports/hw03/questions.yaml"
        ]

        results_command = [
            "git",
            "log",
            "--diff-filter=A",
            "--format=%ct",
            "-1",
            "--",
            (
                "reports/hw03/raw/"
                "retrieval_results.jsonl"
            )
        ]

        question_result = subprocess.run(
            question_command,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True
        )

        retrieval_result = subprocess.run(
            results_command,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True
        )

        question_text = (
            question_result.stdout.strip()
        )

        retrieval_text = (
            retrieval_result.stdout.strip()
        )

        if not question_text:
            raise ValueError(
                "Could not find the Git commit that "
                "added questions.yaml."
            )

        if not retrieval_text:
            raise ValueError(
                "Could not find the Git commit that "
                "added the retrieval results."
            )

        question_time = int(
            question_text
        )

        retrieval_time = int(
            retrieval_text
        )

        passed = (
            question_time <= retrieval_time
        )

        record(
            "question_preregistration",
            passed,
            (
                "questions.yaml was committed before "
                "the retrieval results."
                if passed
                else (
                    "The retrieval results appear to "
                    "precede questions.yaml."
                )
            )
        )

    except Exception as error:
        record(
            "question_preregistration",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_retrieval_results() -> None:
    """Validate JSONL and CSV retrieval data."""

    try:
        questions = load_questions()

        with JSONL_PATH.open(
            encoding="utf-8"
        ) as file:
            runs = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

        with CSV_PATH.open(
            encoding="utf-8",
            newline=""
        ) as file:
            csv_rows = list(
                csv.DictReader(file)
            )

        expected_runs = (
            len(questions) * 3
        )

        expected_rows = (
            expected_runs * 5
        )

        techniques = {
            run.get("technique")
            for run in runs
        }

        required_techniques = {
            "token",
            "semantic",
            "sentence_window"
        }

        run_fields_valid = all(
            run.get(
                "query_embedding_dimension",
                0
            ) > 0
            and len(
                run.get(
                    "query_embedding_first_8",
                    []
                )
            ) == 8
            and len(
                run.get(
                    "results",
                    []
                )
            ) == 5
            for run in runs
        )

        row_fields_valid = all(
            row.get("store_score", "") != ""
            and float(
                row.get(
                    "cosine_similarity",
                    0
                )
            ) != 0
            and int(
                row.get(
                    "chunk_length",
                    0
                )
            ) > 0
            and float(
                row.get(
                    "retrieval_latency_ms",
                    0
                )
            ) > 0
            for row in csv_rows
        )

        passed = (
            len(runs) == expected_runs
            and len(csv_rows) == expected_rows
            and techniques
            == required_techniques
            and run_fields_valid
            and row_fields_valid
        )

        record(
            "retrieval_results",
            passed,
            (
                f"Runs={len(runs)}/"
                f"{expected_runs}, "
                f"rows={len(csv_rows)}/"
                f"{expected_rows}, "
                f"techniques={sorted(techniques)}, "
                f"run fields valid="
                f"{run_fields_valid}, "
                f"row fields valid="
                f"{row_fields_valid}"
            )
        )

    except Exception as error:
        record(
            "retrieval_results",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_retrieval_metrics() -> None:
    """Validate the summary metrics."""

    try:
        metrics = json.loads(
            METRICS_PATH.read_text(
                encoding="utf-8"
            )
        )

        technique_data = metrics.get(
            "techniques",
            {}
        )

        expected_techniques = {
            "token",
            "semantic",
            "sentence_window"
        }

        required_metric_fields = {
            "chunk_count",
            "average_chunk_length",
            "mean_top_1_cosine",
            "mean_at_k_cosine",
            "recall_at_k",
            "recall_at_k_percent",
            "mean_retrieval_latency_ms"
        }

        fields_valid = all(
            required_metric_fields.issubset(
                technique_data.get(
                    technique,
                    {}
                )
            )
            for technique
            in expected_techniques
        )

        values_valid = all(
            technique_data[
                technique
            ]["chunk_count"] > 0
            and technique_data[
                technique
            ][
                "average_chunk_length"
            ] > 0
            and technique_data[
                technique
            ][
                "mean_retrieval_latency_ms"
            ] > 0
            for technique
            in expected_techniques
            if technique
            in technique_data
        )

        passed = (
            set(technique_data)
            == expected_techniques
            and fields_valid
            and values_valid
        )

        record(
            "retrieval_metrics",
            passed,
            (
                "All three techniques contain the "
                "required metrics."
                if passed
                else (
                    "Metrics are missing techniques, "
                    "fields, or positive values."
                )
            )
        )

    except Exception as error:
        record(
            "retrieval_metrics",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_false_positive() -> None:
    """Confirm at least one source mismatch exists."""

    try:
        with CSV_PATH.open(
            encoding="utf-8",
            newline=""
        ) as file:
            rows = list(
                csv.DictReader(file)
            )

        mismatches = [
            row
            for row in rows
            if row.get(
                "source_match",
                ""
            ).lower() == "false"
        ]

        highest_score = max(
            (
                float(
                    row[
                        "cosine_similarity"
                    ]
                )
                for row in mismatches
            ),
            default=0.0
        )

        passed = (
            len(mismatches) >= 1
            and highest_score > 0
        )

        record(
            "false_positive_candidate",
            passed,
            (
                f"Source mismatches="
                f"{len(mismatches)}, "
                f"highest cosine="
                f"{highest_score:.4f}"
            )
        )

    except Exception as error:
        record(
            "false_positive_candidate",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_run_log() -> None:
    """Check that the real run log has evidence."""

    path = (
        REPORT_DIRECTORY
        / "RUN_LOG.txt"
    )

    try:
        raw_content = path.read_bytes()

        if raw_content.startswith(
            (
                b"\xff\xfe",
                b"\xfe\xff"
            )
        ):
            content = raw_content.decode(
        "       utf-16",
                errors="replace"
            )
        else:
            content = raw_content.decode(
                "utf-8-sig",
                errors="replace"
            )

        requirements = [
            (
                "HW3 Part 1 "
                "Authentication Verification"
            ),
            (
                "HW3 Part 2 "
                "Retrieval Experiment"
            ),
            "TECHNIQUE:",
            "FINAL RETRIEVAL METRICS"
        ]

        missing = [
            requirement
            for requirement in requirements
            if requirement not in content
        ]

        record(
            "run_log",
            not missing,
            (
                "RUN_LOG.txt contains authentication "
                "and retrieval evidence."
                if not missing
                else (
                    "Missing log markers: "
                    + ", ".join(missing)
                )
            )
        )

    except Exception as error:
        record(
            "run_log",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def main() -> None:
    """Run all HW3 self-checks."""

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    check_required_files()
    check_python_version()
    check_dependencies()
    check_authentication_source()
    check_fastapi_routes()
    check_demo_credentials()
    check_bootstrap_templates()
    check_corpus_manifest()
    check_questions()
    check_question_preregistration()
    check_retrieval_results()
    check_retrieval_metrics()
    check_false_positive()
    check_run_log()

    passed = all(
        check["passed"]
        for check in checks
    )

    result = {
        "assignment": "DATA-260 Homework 3",
        "student": "Sanjana Thummalapalli",
        "sid4": 7801,
        "portBase": 8601,
        "prefix": "s7801",
        "seed": 7801,
        "verifySeed": 267801,
        "domainId": 1,
        "domain": "Clinical Trial Listings",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": passed,
        "checks": checks
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()