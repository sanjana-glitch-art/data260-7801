from __future__ import annotations

import json
import tempfile
from code.hw7_file_tools import (
    confirm_bash,
    edit_file,
    glob_files,
    read_file,
    search_in_files,
    write_file,
)
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

RAW_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw07"
    / "raw"
)

RESULT_PATH = (
    RAW_DIRECTORY
    / "file_tool_test_results.json"
)


def require_success(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Assert that a tool response succeeded."""

    assert result["success"] is True, result
    assert result["error"] is None

    data = result["data"]

    assert isinstance(
        data,
        dict,
    )

    return data


def run_integration_test(
    sandbox: Path,
) -> dict[str, Any]:
    """Run glob, search, and read over three files."""

    files = {
        "alpha.py": (
            'MESSAGE = "ordinary value"\n'
        ),
        "beta.py": (
            'LOG_LEVEL = "DEBUG"\n'
            'MESSAGE = "target file"\n'
        ),
        "gamma.py": (
            'MESSAGE = "another value"\n'
        ),
    }

    write_results: list[
        dict[str, Any]
    ] = []

    for filename, content in files.items():
        result = write_file(
            sandbox,
            filename,
            content,
        )

        require_success(
            result
        )

        write_results.append(
            result
        )

    glob_result = glob_files(
        sandbox,
        "*.py",
    )

    glob_data = require_success(
        glob_result
    )

    assert glob_data["count"] == 3

    search_result = search_in_files(
        sandbox,
        "DEBUG",
        file_pattern="*.py",
    )

    search_data = require_success(
        search_result
    )

    assert (
        search_data["match_count"]
        == 1
    )

    match = search_data[
        "matches"
    ][0]

    assert (
        match["path"]
        == "beta.py"
    )

    read_result = read_file(
        sandbox,
        match["path"],
        max_lines=20,
    )

    read_data = require_success(
        read_result
    )

    assert (
        "DEBUG"
        in read_data["content"]
    )

    edit_result = edit_file(
        sandbox,
        "beta.py",
        'MESSAGE = "target file"',
        'MESSAGE = "verified target file"',
    )

    edit_data = require_success(
        edit_result
    )

    assert (
        "verified target file"
        in edit_data["diff"]
    )

    return {
        "passed": True,
        "created_files": (
            glob_data["files"]
        ),
        "search_query": "DEBUG",
        "matched_file": (
            match["path"]
        ),
        "matched_line": (
            match["line"]
        ),
        "read_content": (
            read_data["content"]
        ),
        "edit_diff": (
            edit_data["diff"]
        ),
        "tool_sequence": [
            "write_file",
            "glob_files",
            "search_in_files",
            "read_file",
            "edit_file",
        ],
    }


def run_safety_tests() -> dict[str, Any]:
    """Run five allowed and five blocked tests."""

    allowed_commands = [
        "python --version",
        "git status --short",
        "echo hello",
        "dir",
        "Get-Location",
    ]

    blocked_commands = [
        "Remove-Item C:\\ -Recurse -Force",
        "sudo chmod 777 important.txt",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda1",
        "echo malicious > C:\\system.txt",
    ]

    results: list[
        dict[str, Any]
    ] = []

    false_allows: list[str] = []
    false_blocks: list[str] = []

    for command in allowed_commands:
        decision = confirm_bash(
            command,
            auto_approve=False,
        )

        passed = (
            decision["allowed"] is True
            and decision["destructive"]
            is False
        )

        if not passed:
            false_blocks.append(
                command
            )

        results.append({
            "expected": "allow",
            "command": command,
            "passed": passed,
            **decision,
        })

    for command in blocked_commands:
        decision = confirm_bash(
            command,
            auto_approve=False,
        )

        passed = (
            decision["allowed"] is False
            and decision["destructive"]
            is True
        )

        if not passed:
            false_allows.append(
                command
            )

        results.append({
            "expected": "block",
            "command": command,
            "passed": passed,
            **decision,
        })

    confirmed_destructive = confirm_bash(
        "sudo chmod 777 important.txt",
        auto_approve=True,
    )

    assert (
        confirmed_destructive[
            "allowed"
        ]
        is True
    )

    assert (
        confirmed_destructive[
            "destructive"
        ]
        is True
    )

    return {
        "passed": (
            not false_allows
            and not false_blocks
        ),
        "allowed_expected": 5,
        "allowed_passed": sum(
            result["passed"]
            for result in results
            if (
                result["expected"]
                == "allow"
            )
        ),
        "blocked_expected": 5,
        "blocked_passed": sum(
            result["passed"]
            for result in results
            if (
                result["expected"]
                == "block"
            )
        ),
        "false_allows": false_allows,
        "false_blocks": false_blocks,
        "results": results,
        "explicit_confirmation_test": (
            confirmed_destructive
        ),
    }


def main() -> None:
    """Run the Homework 7 Part 6 tests."""

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="s7801_hw7_"
    ) as temporary_directory:
        sandbox = Path(
            temporary_directory
        ).resolve()

        integration = (
            run_integration_test(
                sandbox
            )
        )

        safety = run_safety_tests()

    overall_passed = (
        integration["passed"]
        and safety["passed"]
    )

    output = {
        "assignment": (
            "DATA-260 Homework 7 Part 6"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": 7801,
        "overall_passed": (
            overall_passed
        ),
        "integration_test": (
            integration
        ),
        "safety_gate_test": (
            safety
        ),
    }

    RESULT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "DATA-260 Homework 7 Part 6"
    )
    print(
        "File Tools and Safety Gate"
    )
    print()

    print(
        "Integration test:",
        (
            "PASS"
            if integration["passed"]
            else "FAIL"
        ),
    )

    print(
        "Tool sequence:",
        " -> ".join(
            integration[
                "tool_sequence"
            ]
        ),
    )

    print(
        "DEBUG found in:",
        integration["matched_file"],
    )

    print(
        "File content:"
    )

    print(
        integration["read_content"]
    )

    print()

    print(
        "Safety gate:",
        (
            "PASS"
            if safety["passed"]
            else "FAIL"
        ),
    )

    print(
        "Allowed:",
        (
            f"{safety['allowed_passed']}"
            "/5"
        ),
    )

    print(
        "Blocked:",
        (
            f"{safety['blocked_passed']}"
            "/5"
        ),
    )

    print()

    for result in safety[
        "results"
    ]:
        outcome = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"{outcome} | "
            f"expected={result['expected']} | "
            f"allowed={result['allowed']} | "
            f"destructive="
            f"{result['destructive']} | "
            f"{result['command']} | "
            f"{result['reason']}"
        )

    print()

    print(
        "Overall:",
        (
            "PASS"
            if overall_passed
            else "FAIL"
        ),
    )

    print(
        "Results:",
        RESULT_PATH,
    )

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()