from __future__ import annotations

from typing import Any


ALLOWED_PHASES = {
    "Phase I",
    "Phase II",
    "Phase III",
    "Phase IV",
}


def filter_trials_by_phase(
    trials: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    """
    Return clinical trials matching one validated phase.

    The function follows AGENT.md by using type hints,
    descriptive names, input validation, a docstring, and
    a predictable dictionary response.
    """

    cleaned_phase = phase.strip()

    if cleaned_phase not in ALLOWED_PHASES:
        return {
            "ok": False,
            "data": None,
            "error": (
                "Trial phase must be Phase I, Phase II, "
                "Phase III, or Phase IV."
            ),
        }

    matching_trials = [
        trial
        for trial in trials
        if trial.get(
            "trial_phase"
        ) == cleaned_phase
    ]

    return {
        "ok": True,
        "data": {
            "phase": cleaned_phase,
            "count": len(
                matching_trials
            ),
            "trials": matching_trials,
        },
        "error": None,
    }