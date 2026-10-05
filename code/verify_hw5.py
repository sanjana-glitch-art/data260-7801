from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIRECTORY = ROOT / "reports" / "hw05"
RAW_DIRECTORY = REPORT_DIRECTORY / "raw"
OUTPUT_PATH = REPORT_DIRECTORY / "verification.json"

checks: list[dict[str, Any]] = []


def record(
    name: str,
    passed: bool,
    details: str,
) -> None:
    checks.append({
        "name": name,
        "passed": passed,
        "details": details,
    })


def check_required_files() -> None:
    required = [
        "code/hw5_domain_tools.py",
        "code/hw5_tool_entry.py",
        "code/hw5_agent.py",
        "code/test_hw5_tools.py",
        "code/run_hw5_fault_injection.py",
        "code/run_hw5_agent_scenarios.py",
        "code/mcp_servers/meals_server.py",
        "code/mcp_servers/clinical_trials_server.py",
        "reports/hw05/METRICS.md",
        "reports/hw05/AI_USE.md",
        "reports/hw05/REFLECTION.md",
        "reports/hw05/RUN_LOG.txt",
        "reports/hw05/raw/fault_injection_results.json",
        "reports/hw05/raw/fault_injection_results.csv",
        "reports/hw05/raw/fault_injection_metrics.json",
        "reports/hw05/raw/retry_demonstration.json",
        "reports/hw05/raw/agent_runs.jsonl",
        "reports/hw05/raw/agent_metrics.json",
    ]

    missing = [
        path
        for path in required
        if not (ROOT / path).is_file()
    ]

    record(
        "required_files",
        not missing,
        (
            "All required files exist."
            if not missing
            else f"Missing: {missing}"
        ),
    )


def check_fault_experiment() -> None:
    path = (
        RAW_DIRECTORY
        / "fault_injection_results.json"
    )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        rates = {
            str(item.get(
                "injected_failure_rate",
                item.get(
                    "injectedFailureRate"
                ),
            ))
            for item in data
        }

        passed = len(data) == 150

        record(
            "fault_injection_records",
            passed,
            (
                f"Records={len(data)}, "
                f"rates={sorted(rates)}"
            ),
        )
    except Exception as error:
        record(
            "fault_injection_records",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def check_agent_metrics() -> None:
    path = (
        RAW_DIRECTORY
        / "agent_metrics.json"
    )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        scenarios = data.get(
            "scenarios",
            []
        )

        safety_passed = any(
            scenario.get("stop_reason")
            == "safety_rule_block"
            for scenario in scenarios
        )

        passed = (
            data.get("scenarioCount") == 4
            and len(scenarios) == 4
            and safety_passed
        )

        record(
            "agent_scenarios",
            passed,
            (
                f"Scenarios={len(scenarios)}, "
                f"safety_block={safety_passed}"
            ),
        )
    except Exception as error:
        record(
            "agent_scenarios",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def check_reflection() -> None:
    path = (
        REPORT_DIRECTORY
        / "REFLECTION.md"
    )

    try:
        words = path.read_text(
            encoding="utf-8"
        ).split()

        passed = (
            200 <= len(words) <= 300
        )

        record(
            "reflection_word_count",
            passed,
            f"Words={len(words)}",
        )
    except Exception as error:
        record(
            "reflection_word_count",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def check_offline_tests() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "code.test_hw5_tools",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = (
        completed.stdout
        + completed.stderr
    )

    passed = (
        completed.returncode == 0
        and "9/9 passed" in output
    )

    record(
        "offline_tests",
        passed,
        (
            "9/9 tests passed."
            if passed
            else output[-1000:]
        ),
    )


def check_agent_log() -> None:
    path = (
        RAW_DIRECTORY
        / "agent_runs.jsonl"
    )

    try:
        lines = [
            line
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        valid = all(
            isinstance(
                json.loads(line),
                dict,
            )
            for line in lines
        )

        record(
            "agent_jsonl_log",
            bool(lines) and valid,
            (
                f"Valid JSONL records="
                f"{len(lines)}"
            ),
        )
    except Exception as error:
        record(
            "agent_jsonl_log",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )


def main() -> None:
    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    check_required_files()
    check_fault_experiment()
    check_agent_metrics()
    check_reflection()
    check_offline_tests()
    check_agent_log()

    passed = all(
        check["passed"]
        for check in checks
    )

    result = {
        "assignment": "DATA-260 Homework 5",
        "student": "Sanjana Thummalapalli",
        "sid4": 7801,
        "verifySeed": 267801,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": passed,
        "checks": checks,
    }

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