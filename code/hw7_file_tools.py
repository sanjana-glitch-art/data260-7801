from __future__ import annotations

import difflib
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SAFE_PREFIXES = (
    "python ",
    "python.exe ",
    "py ",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "echo ",
    "dir",
    "type ",
    "get-location",
    "get-childitem",
)


DESTRUCTIVE_PATTERNS: tuple[
    tuple[re.Pattern[str], str],
    ...,
] = (
    (
        re.compile(
            r"(?:^|\s)"
            r"(?:remove-item|rm|rmdir|rd|del|erase)"
            r"(?:\s|$).*?"
            r"(?:-recurse|/s)"
            r"(?:\s|$)",
            re.IGNORECASE,
        ),
        "recursive deletion",
    ),
    (
        re.compile(
            r"(?:^|\s)"
            r"(?:sudo|runas)"
            r"(?:\s|$)",
            re.IGNORECASE,
        ),
        "privilege escalation",
    ),
    (
        re.compile(
            r"(?:^|\s)"
            r"(?:chmod|chown|icacls|takeown)"
            r"(?:\s|$)",
            re.IGNORECASE,
        ),
        "permission or ownership change",
    ),
    (
        re.compile(
            r"\bdd\b.*?"
            r"\bof\s*=\s*"
            r"(?:/dev/|\\\\\.\\)",
            re.IGNORECASE,
        ),
        "raw-device write",
    ),
    (
        re.compile(
            r"(?:^|\s)"
            r"(?:mkfs(?:\.[a-z0-9]+)?|format)"
            r"(?:\s|$)",
            re.IGNORECASE,
        ),
        "filesystem creation",
    ),
    (
        re.compile(
            r"(?:>|>>|1>|2>)\s*"
            r"(?:"
            r"[a-zA-Z]:[\\/]"
            r"|"
            r"/"
            r")",
            re.IGNORECASE,
        ),
        "root-path redirection",
    ),
)


def utc_timestamp() -> str:
    """Return the current UTC time in ISO format."""

    return datetime.now(
        UTC
    ).isoformat()


def success_envelope(
    data: Any,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    """Return a successful tool response."""

    result: dict[str, Any] = {
        "success": True,
        "data": data,
        "error": None,
        "ts": utc_timestamp(),
    }

    if source is not None:
        result["source"] = source

    return result


def error_envelope(
    message: str,
) -> dict[str, Any]:
    """Return an unsuccessful tool response."""

    return {
        "success": False,
        "data": None,
        "error": message,
        "ts": utc_timestamp(),
    }


def _sandbox_path(
    sandbox_root: str | Path,
    requested_path: str | Path,
) -> Path:
    """Resolve a path and ensure it remains in the sandbox."""

    root = Path(
        sandbox_root
    ).resolve()

    candidate_path = Path(
        requested_path
    )

    if candidate_path.is_absolute():
        candidate = candidate_path.resolve()
    else:
        candidate = (
            root
            / candidate_path
        ).resolve()

    try:
        candidate.relative_to(
            root
        )
    except ValueError as error:
        raise ValueError(
            "Path escapes the course sandbox."
        ) from error

    return candidate


def read_file(
    sandbox_root: str | Path,
    path: str | Path,
    *,
    max_lines: int = 200,
) -> dict[str, Any]:
    """Read a sandboxed text file with a line limit."""

    if (
        not isinstance(max_lines, int)
        or isinstance(max_lines, bool)
        or max_lines <= 0
    ):
        return error_envelope(
            "max_lines must be a positive integer."
        )

    try:
        target = _sandbox_path(
            sandbox_root,
            path,
        )

        if not target.is_file():
            return error_envelope(
                "File not found."
            )

        lines = target.read_text(
            encoding="utf-8"
        ).splitlines()

        selected_lines = lines[
            :max_lines
        ]

        return success_envelope(
            {
                "path": str(target),
                "content": "\n".join(
                    selected_lines
                ),
                "returned_lines": len(
                    selected_lines
                ),
                "total_lines": len(
                    lines
                ),
                "truncated": (
                    len(lines)
                    > max_lines
                ),
            },
            source=str(target),
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )


def write_file(
    sandbox_root: str | Path,
    path: str | Path,
    content: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a text file inside the sandbox."""

    if not isinstance(content, str):
        return error_envelope(
            "content must be a string."
        )

    try:
        target = _sandbox_path(
            sandbox_root,
            path,
        )

        if (
            target.exists()
            and not overwrite
        ):
            return error_envelope(
                "File already exists; "
                "set overwrite=True to replace it."
            )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            content,
            encoding="utf-8",
        )

        return success_envelope(
            {
                "path": str(target),
                "characters_written": len(
                    content
                ),
            },
            source=str(target),
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )


def edit_file(
    sandbox_root: str | Path,
    path: str | Path,
    old_text: str,
    new_text: str,
) -> dict[str, Any]:
    """Replace one text occurrence and return a short diff."""

    if not isinstance(
        old_text,
        str,
    ) or not isinstance(
        new_text,
        str,
    ):
        return error_envelope(
            "old_text and new_text must be strings."
        )

    if not old_text:
        return error_envelope(
            "old_text must not be empty."
        )

    try:
        target = _sandbox_path(
            sandbox_root,
            path,
        )

        if not target.is_file():
            return error_envelope(
                "File not found."
            )

        original = target.read_text(
            encoding="utf-8"
        )

        occurrence_count = original.count(
            old_text
        )

        if occurrence_count == 0:
            return error_envelope(
                "old_text was not found."
            )

        if occurrence_count > 1:
            return error_envelope(
                "old_text is not unique."
            )

        updated = original.replace(
            old_text,
            new_text,
            1,
        )

        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(),
                updated.splitlines(),
                fromfile=str(target),
                tofile=str(target),
                lineterm="",
            )
        )

        target.write_text(
            updated,
            encoding="utf-8",
        )

        return success_envelope(
            {
                "path": str(target),
                "replacements": 1,
                "diff": "\n".join(
                    diff_lines[:60]
                ),
                "diff_truncated": (
                    len(diff_lines)
                    > 60
                ),
            },
            source=str(target),
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )


def glob_files(
    sandbox_root: str | Path,
    pattern: str,
) -> dict[str, Any]:
    """Return files matching a sandbox-relative pattern."""

    if not isinstance(
        pattern,
        str,
    ) or not pattern.strip():
        return error_envelope(
            "pattern must not be empty."
        )

    try:
        root = Path(
            sandbox_root
        ).resolve()

        matches: list[str] = []

        for candidate in root.glob(
            pattern
        ):
            resolved = candidate.resolve()

            try:
                resolved.relative_to(
                    root
                )
            except ValueError:
                continue

            if resolved.is_file():
                matches.append(
                    str(
                        resolved.relative_to(
                            root
                        )
                    )
                )

        matches.sort()

        return success_envelope(
            {
                "pattern": pattern,
                "count": len(matches),
                "files": matches,
            },
            source=str(root),
        )
    except (
        OSError,
        ValueError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )


def search_in_files(
    sandbox_root: str | Path,
    query: str,
    *,
    file_pattern: str = "**/*",
    case_sensitive: bool = False,
) -> dict[str, Any]:
    """Search matching sandbox files for a text query."""

    if not isinstance(
        query,
        str,
    ) or not query:
        return error_envelope(
            "query must not be empty."
        )

    if not isinstance(
        file_pattern,
        str,
    ) or not file_pattern:
        return error_envelope(
            "file_pattern must not be empty."
        )

    try:
        root = Path(
            sandbox_root
        ).resolve()

        normalized_query = (
            query
            if case_sensitive
            else query.casefold()
        )

        matches: list[
            dict[str, Any]
        ] = []

        for candidate in root.glob(
            file_pattern
        ):
            resolved = candidate.resolve()

            try:
                resolved.relative_to(
                    root
                )
            except ValueError:
                continue

            if not resolved.is_file():
                continue

            try:
                lines = resolved.read_text(
                    encoding="utf-8"
                ).splitlines()
            except (
                OSError,
                UnicodeError,
            ):
                continue

            for line_number, line in enumerate(
                lines,
                start=1,
            ):
                compared_line = (
                    line
                    if case_sensitive
                    else line.casefold()
                )

                if (
                    normalized_query
                    in compared_line
                ):
                    matches.append({
                        "path": str(
                            resolved.relative_to(
                                root
                            )
                        ),
                        "line_number": (
                            line_number
                        ),
                        "line": line,
                    })

        return success_envelope(
            {
                "query": query,
                "file_pattern": (
                    file_pattern
                ),
                "match_count": len(
                    matches
                ),
                "matches": matches,
            },
            source=str(root),
        )
    except (
        OSError,
        ValueError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )


def destructive_reason(
    command: str,
) -> str | None:
    """Return the matched destructive-command category."""

    normalized = " ".join(
        command.strip().casefold().split()
    )

    for pattern, reason in (
        DESTRUCTIVE_PATTERNS
    ):
        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):
            return reason

    return None


def is_destructive(
    command: str,
) -> tuple[bool, str | None]:
    """Classify known destructive shell-command patterns."""

    for pattern, category in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return True, category

    return False, None


def confirm_bash(
    command: str,
    *,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """
    Decide whether a shell command may run.

    Destructive patterns are checked before the safe-prefix
    allowlist so that an allowlisted command such as echo
    cannot redirect output into a protected root path.
    """

    cleaned_command = command.strip()

    if not cleaned_command:
        return {
            "allowed": False,
            "destructive": False,
            "reason": "Command must not be empty.",
        }

    destructive, category = is_destructive(
        cleaned_command
    )

    if destructive:
        if auto_approve:
            return {
                "allowed": True,
                "destructive": True,
                "reason": (
                    "Explicit confirmation supplied for: "
                    f"{category}."
                ),
            }

        return {
            "allowed": False,
            "destructive": True,
            "reason": (
                "Blocked pending explicit confirmation: "
                f"{category}."
            ),
        }

    normalized_command = (
        cleaned_command.casefold()
    )

    if normalized_command.startswith(
        SAFE_PREFIXES
    ):
        return {
            "allowed": True,
            "destructive": False,
            "reason": (
                "Command matches SAFE_PREFIXES."
            ),
        }

    if auto_approve:
        return {
            "allowed": True,
            "destructive": False,
            "reason": (
                "Command was explicitly confirmed."
            ),
        }

    return {
        "allowed": False,
        "destructive": False,
        "reason": (
            "Command is outside SAFE_PREFIXES "
            "and requires confirmation."
        ),
    }


def bash(
    sandbox_root: str | Path,
    command: str,
    *,
    auto_approve: bool = False,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Execute an approved command from the sandbox."""

    decision = confirm_bash(
        command,
        auto_approve=auto_approve,
    )

    if not decision["allowed"]:
        return error_envelope(
            decision["reason"]
        )

    if timeout_seconds <= 0:
        return error_envelope(
            "timeout_seconds must be positive."
        )

    try:
        root = Path(
            sandbox_root
        ).resolve()

        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        completed = subprocess.run(
            command,
            cwd=root,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        return success_envelope(
            {
                "command": command,
                "return_code": (
                    completed.returncode
                ),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "safety_decision": decision,
            },
            source=str(root),
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ) as error:
        return error_envelope(
            f"{type(error).__name__}: {error}"
        )