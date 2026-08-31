import json
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

OUTPUT_PATH = (
    ROOT / "reports" / "hw01" / "verification.json"
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
    required_files = [
        "AGENT.md",
        "DOMAIN_SCHEMA.md",
        "Dockerfile",
        "README.md",
        "agents_demo.py",
        "hw1_client.py",
        "index.html",
        "script.js",
        "src/model_client.py",
        "reports/hw01/AI_USE.md",
        "reports/hw01/METRICS.md",
        "reports/hw01/RUN_LOG.txt",
        "reports/hw01/cases/nondeterminism_input.json",
        "reports/hw01/raw/nondeterminism_results.json",
        "reports/hw01/raw/nondeterminism_results.csv",
        "reports/hw01/raw/nondeterminism_metrics.json",
        "reports/hw01/raw/client_token_counts.json"
    ]

    missing = [
        path
        for path in required_files
        if not (ROOT / path).is_file()
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
    version = sys.version_info
    passed = (
        version.major == 3
        and version.minor in {11, 12}
    )

    record(
        "python_version",
        passed,
        platform.python_version()
    )


def check_html() -> None:
    html = (
        ROOT / "index.html"
    ).read_text(encoding="utf-8")

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
        "autofocus": (
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
        for name, passed in requirements.items()
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
            f"expected 4 phase options, found {option_count}"
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
    script = (
        ROOT / "script.js"
    ).read_text(encoding="utf-8")

    requirements = {
        "arrow validation": (
            "const validateForm = () =>" in script
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
        for name, passed in requirements.items()
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
    agents_source = (
        ROOT / "agents_demo.py"
    ).read_text(encoding="utf-8")

    experiment_source = (
        ROOT / "run_nondeterminism.py"
    ).read_text(encoding="utf-8")

    passed = (
        "from src.model_client import ModelClient"
        in agents_source
        and "from src.model_client import ModelClient"
        in experiment_source
        and "ChatOllama" not in agents_source
        and "ChatOllama" not in experiment_source
    )

    record(
        "model_adapter_usage",
        passed,
        (
            "Agent and experiment calls use ModelClient."
            if passed
            else "A direct model call may remain."
        )
    )


def check_nondeterminism_results() -> None:
    path = (
        ROOT
        / "reports"
        / "hw01"
        / "raw"
        / "nondeterminism_results.json"
    )

    results = json.loads(
        path.read_text(encoding="utf-8")
    )

    counts = Counter(
        result["temperature"]
        for result in results
    )

    schemas_valid = all(
        len(result["tags"]) == 3
        and len(result["summary"].split()) <= 25
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
    path = (
        ROOT
        / "reports"
        / "hw01"
        / "raw"
        / "client_token_counts.json"
    )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    turns = data.get("turns", [])

    passed = (
        len(turns) == 5
        and all(
            turn.get("bullet_only_passed")
            for turn in turns
        )
        and all(
            turn.get("input_tokens", 0) > 0
            and turn.get("output_tokens", 0) > 0
            for turn in turns
        )
    )

    record(
        "token_accounting",
        passed,
        (
            f"Turns={len(turns)}, "
            "all bullet checks passed="
            f"{all(turn.get('bullet_only_passed') for turn in turns)}"
        )
    )


def main() -> None:
    check_required_files()
    check_python_version()
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
        "assignment": "DATA-260 Homework 1",
        "student": "Sanjana Thummalapalli",
        "sid4": 7801,
        "verifySeed": 267801,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": passed,
        "checks": checks
    }

    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(result, indent=2))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()