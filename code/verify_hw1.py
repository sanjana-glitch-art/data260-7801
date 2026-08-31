import json
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "hw01"
    / "verification.json"
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
        "passed": passed,
        "details": details
    })


def check_required_files() -> None:
    """Verify all required deliverables exist."""
    required_files = [
        "AGENT.md",
        "DOMAIN_SCHEMA.md",
        "README.md",
        "requirements.txt",
        "code/Dockerfile",
        "code/agents_demo.py",
        "code/hw1_client.py",
        "code/run_nondeterminism.py",
        "code/verify_hw1.py",
        "code/web_application/index.html",
        "code/web_application/script.js",
        "src/__init__.py",
        "src/model_client.py",
        "reports/hw01/AI_USE.md",
        "reports/hw01/METRICS.md",
        "reports/hw01/RUN_LOG.txt",
        "reports/hw01/report.pdf",
        "reports/hw01/verification.json",
        "reports/hw01/reproducible_run_instructions.md",
        "reports/hw01/cases/nondeterminism_input.json",
        "reports/hw01/raw/nondeterminism_results.json",
        "reports/hw01/raw/nondeterminism_results.csv",
        "reports/hw01/raw/nondeterminism_metrics.json",
        "reports/hw01/raw/client_token_counts.json"
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
            "All required files exist."
            if not missing
            else f"Missing files: {missing}"
        )
    )


def check_python_version() -> None:
    """Verify that Python 3.11 or 3.12 is active."""
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


def check_python_sources() -> None:
    """Verify that all Python source files compile."""
    source_paths = [
        (
            PROJECT_ROOT
            / "code"
            / "agents_demo.py"
        ),
        (
            PROJECT_ROOT
            / "code"
            / "run_nondeterminism.py"
        ),
        (
            PROJECT_ROOT
            / "code"
            / "hw1_client.py"
        ),
        (
            PROJECT_ROOT
            / "src"
            / "model_client.py"
        )
    ]

    failures: list[str] = []

    for path in source_paths:
        try:
            source = path.read_text(
                encoding="utf-8"
            )

            compile(
                source,
                str(path),
                "exec"
            )
        except Exception as error:
            failures.append(
                f"{path.name}: {error}"
            )

    record(
        "python_source_compilation",
        not failures,
        (
            "All Python source files compile."
            if not failures
            else f"Compilation failures: {failures}"
        )
    )


def check_html() -> None:
    """Verify the required HTML form elements."""
    html_path = (
        PROJECT_ROOT
        / "code"
        / "web_application"
        / "index.html"
    )

    html = html_path.read_text(
        encoding="utf-8"
    )

    requirements = {
        "correct title": (
            "<title>HW1-Sanjana Thummalapalli</title>"
            in html
        ),
        "largest heading": (
            "<h1>Clinical Trial Listing</h1>"
            in html
        ),
        "primary field": (
            'id="trialTitle"' in html
        ),
        "primary field autofocus": (
            "autofocus" in html
        ),
        "secondary field": (
            'id="sponsorName"' in html
        ),
        "email field": (
            'type="email"' in html
        ),
        "description field": (
            'id="trialDescription"' in html
        ),
        "category field": (
            'id="trialPhase"' in html
        ),
        "terms checkbox": (
            'id="termsAccepted"' in html
        ),
        "JavaScript link": (
            '<script src="script.js"></script>'
            in html
        )
    }

    failed = [
        name
        for name, passed
        in requirements.items()
        if not passed
    ]

    option_count = len(
        re.findall(
            r'<option value="Phase (?:I|II|III|IV)">',
            html
        )
    )

    if option_count != 4:
        failed.append(
            "expected 4 phase options, "
            f"found {option_count}"
        )

    record(
        "html_requirements",
        not failed,
        (
            "HTML requirements passed."
            if not failed
            else f"Failed: {failed}"
        )
    )


def check_javascript() -> None:
    """Verify the required JavaScript concepts."""
    script_path = (
        PROJECT_ROOT
        / "code"
        / "web_application"
        / "script.js"
    )

    script = script_path.read_text(
        encoding="utf-8"
    )

    requirements = {
        "arrow validation": (
            "const validateForm = () =>"
            in script
        ),
        "description length": (
            "trialDescription.length <= 25"
            in script
        ),
        "checkbox validation": (
            "termsAccepted" in script
            and ".checked" in script
        ),
        "JSON stringify": (
            "JSON.stringify" in script
        ),
        "JSON parse": (
            "JSON.parse" in script
        ),
        "destructuring": (
            "const { trialTitle, submitterEmail }"
            in script
        ),
        "spread operator": (
            "...parsedObject" in script
        ),
        "submission date": (
            "submissionDate" in script
        ),
        "closure": (
            "createSubmissionCounter"
            in script
        )
    }

    failed = [
        name
        for name, passed
        in requirements.items()
        if not passed
    ]

    record(
        "javascript_requirements",
        not failed,
        (
            "JavaScript requirements passed."
            if not failed
            else f"Failed: {failed}"
        )
    )


def check_model_adapter() -> None:
    """Verify all model calls use ModelClient."""
    agents_path = (
        PROJECT_ROOT
        / "code"
        / "agents_demo.py"
    )

    experiment_path = (
        PROJECT_ROOT
        / "code"
        / "run_nondeterminism.py"
    )

    client_path = (
        PROJECT_ROOT
        / "code"
        / "hw1_client.py"
    )

    agents_source = agents_path.read_text(
        encoding="utf-8"
    )

    experiment_source = (
        experiment_path.read_text(
            encoding="utf-8"
        )
    )

    client_source = client_path.read_text(
        encoding="utf-8"
    )

    sources = [
        agents_source,
        experiment_source,
        client_source
    ]

    passed = (
        all(
            "from src.model_client import ModelClient"
            in source
            for source in sources
        )
        and all(
            "ChatOllama" not in source
            for source in sources
        )
    )

    record(
        "model_adapter_usage",
        passed,
        (
            "All application model calls use ModelClient."
            if passed
            else "A direct model call may remain."
        )
    )


def check_nondeterminism_results() -> None:
    """Verify all 40 experiment results."""
    path = (
        PROJECT_ROOT
        / "reports"
        / "hw01"
        / "raw"
        / "nondeterminism_results.json"
    )

    results = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    counts = Counter(
        result["temperature"]
        for result in results
    )

    schemas_valid = all(
        isinstance(
            result.get("tags"),
            list
        )
        and len(result["tags"]) == 3
        and len(
            result.get(
                "summary",
                ""
            ).split()
        ) <= 25
        and bool(
            result.get(
                "summary",
                ""
            ).strip()
        )
        for result in results
    )

    passed = (
        len(results) == 40
        and counts[0.7] == 20
        and counts[0.0] == 20
        and schemas_valid
    )

    record(
        "nondeterminism_results",
        passed,
        (
            f"Total={len(results)}, "
            f"temp0.7={counts[0.7]}, "
            f"temp0.0={counts[0.0]}, "
            f"schemas_valid={schemas_valid}"
        )
    )


def check_token_results() -> None:
    """Verify the saved five-turn token log."""
    path = (
        PROJECT_ROOT
        / "reports"
        / "hw01"
        / "raw"
        / "client_token_counts.json"
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    turns = data.get(
        "turns",
        []
    )

    bullet_checks_passed = all(
        turn.get(
            "bullet_only_passed"
        )
        for turn in turns
    )

    token_counts_present = all(
        turn.get(
            "input_tokens",
            0
        ) > 0
        and turn.get(
            "output_tokens",
            0
        ) > 0
        and turn.get(
            "total_tokens",
            0
        ) > 0
        for turn in turns
    )

    passed = (
        len(turns) == 5
        and bullet_checks_passed
        and token_counts_present
    )

    record(
        "token_accounting",
        passed,
        (
            f"Turns={len(turns)}, "
            "all bullet checks passed="
            f"{bullet_checks_passed}, "
            "token counts present="
            f"{token_counts_present}"
        )
    )


def main() -> None:
    """Run all Homework 1 verification checks."""
    checks.clear()

    check_required_files()
    check_python_version()
    check_python_sources()
    check_html()
    check_javascript()
    check_model_adapter()
    check_nondeterminism_results()
    check_token_results()

    passed = all(
        check["passed"]
        for check in checks
    )

    result = {
        "assignment": (
            "DATA-260 Homework 1"
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
        "checks": checks
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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