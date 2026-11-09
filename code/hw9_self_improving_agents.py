from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REFERENCE_PATH = Path(
    "reference_data.json"
)

LESSONS_PATH = Path(
    "lessons.json"
)


@dataclass
class Evaluation:
    """One evaluator decision."""

    result: str
    explanation: str
    feedback: str
    missing_fields: list[str]


class DomainKnowledge:
    """Ground truth loaded from the reference data."""

    def __init__(
        self,
        path: Path = REFERENCE_PATH,
    ) -> None:
        document = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        self.facts: dict[
            str,
            dict[str, Any],
        ] = document["facts"]

    def identify_trial(
        self,
        question: str,
    ) -> tuple[str, dict[str, Any]]:
        """Identify the referenced trial."""

        normalized = question.lower()

        mappings = [
            (
                (
                    "sleep",
                    "academic performance",
                ),
                "sleep_quality",
            ),
            (
                (
                    "digital",
                    "wellness",
                ),
                "digital_wellness",
            ),
            (
                (
                    "memory",
                    "cognitive",
                ),
                "memory_cognitive",
            ),
            (
                (
                    "remote",
                    "monitoring",
                ),
                "remote_monitoring",
            ),
        ]

        for keywords, trial_key in mappings:
            if any(
                keyword in normalized
                for keyword in keywords
            ):
                return (
                    trial_key,
                    self.facts[trial_key],
                )

        raise ValueError(
            "Question does not identify "
            "a supported clinical trial."
        )

    @staticmethod
    def requested_fields(
        question: str,
    ) -> list[str]:
        """Return facts required by a question."""

        normalized = question.lower()
        fields: list[str] = []

        if "phase" in normalized:
            fields.append("trial_phase")

        enrollment_terms = (
            "enrollment",
            "participant",
            "how many",
            "planned",
        )

        if any(
            term in normalized
            for term in enrollment_terms
        ):
            fields.append(
                "enrollment_target"
            )

        sponsor_terms = (
            "sponsor",
            "organization",
            "funding",
        )

        if any(
            term in normalized
            for term in sponsor_terms
        ):
            fields.append("sponsor_name")

        description_terms = (
            "describe",
            "details",
            "summary",
        )

        if any(
            term in normalized
            for term in description_terms
        ):
            fields = [
                "description",
                "trial_phase",
                "enrollment_target",
                "sponsor_name",
            ]

        if not fields:
            fields = [
                "trial_title",
            ]

        return list(dict.fromkeys(fields))

    def expected_values(
        self,
        question: str,
    ) -> dict[str, str]:
        """Return required ground-truth values."""

        _, facts = self.identify_trial(
            question
        )

        fields = self.requested_fields(
            question
        )

        return {
            field: str(facts[field])
            for field in fields
        }


class LessonStore:
    """Persistent reusable lesson memory."""

    def __init__(
        self,
        path: Path = LESSONS_PATH,
    ) -> None:
        self.path = path
        self.lessons = self._load()

    def _load(self) -> list[dict[str, Any]]:
        """Load lessons from disk."""

        if not self.path.exists():
            return []

        document = json.loads(
            self.path.read_text(
                encoding="utf-8-sig"
            )
        )

        if not isinstance(document, list):
            raise TypeError(
                "lessons.json must contain "
                "a JSON list."
            )

        return document

    def save(self) -> None:
        """Persist lessons."""

        self.path.write_text(
            json.dumps(
                self.lessons,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Remove all lessons."""

        self.lessons = []
        self.save()

    def add_enrollment_lesson(
        self,
    ) -> dict[str, Any]:
        """Create or return the enrollment lesson."""

        for lesson in self.lessons:
            if (
                lesson["failure_pattern"]
                == (
                    "The answer omits the "
                    "requested enrollment target."
                )
            ):
                return lesson

        lesson = {
            "lesson_id": "lesson_001",
            "failure_pattern": (
                "The answer omits the requested "
                "enrollment target."
            ),
            "correction": (
                "When a question requests both "
                "phase and enrollment, or asks "
                "for trial details, include the "
                "numeric enrollment target."
            ),
            "created_at": (
                datetime.now(UTC)
                .date()
                .isoformat()
            ),
            "use_count": 0,
        }

        self.lessons.append(lesson)
        self.save()

        return lesson

    def relevant_lessons(
        self,
        question: str,
        *,
        update_use_count: bool,
    ) -> list[dict[str, Any]]:
        """Return lessons relevant to a question."""

        normalized = question.lower()

        needs_enrollment = any(
            term in normalized
            for term in (
                "enrollment",
                "participant",
                "how many",
                "planned",
                "describe",
                "details",
                "summary",
            )
        )

        relevant = [
            lesson
            for lesson in self.lessons
            if (
                needs_enrollment
                and "enrollment"
                in lesson[
                    "failure_pattern"
                ].lower()
            )
        ]

        if relevant and update_use_count:
            for lesson in relevant:
                lesson["use_count"] += 1

            self.save()

        return relevant


class AnsweringAgent:
    """Generate answers from domain facts."""

    def __init__(
        self,
        knowledge: DomainKnowledge,
        lessons: LessonStore,
    ) -> None:
        self.knowledge = knowledge
        self.lessons = lessons

    def answer(
        self,
        question: str,
        *,
        attempt: int,
        feedback: str = "",
        use_lessons: bool,
        update_lesson_count: bool = True,
    ) -> dict[str, Any]:
        """Generate one answer attempt."""

        started_at = time.perf_counter()

        _, facts = (
            self.knowledge.identify_trial(
                question
            )
        )

        requested_fields = (
            self.knowledge.requested_fields(
                question
            )
        )

        loaded_lessons = (
            self.lessons.relevant_lessons(
                question,
                update_use_count=(
                    update_lesson_count
                    and use_lessons
                ),
            )
            if use_lessons
            else []
        )

        should_omit_enrollment = (
            attempt == 1
            and not feedback
            and not loaded_lessons
            and "enrollment_target"
            in requested_fields
            and (
                "trial_phase"
                in requested_fields
                or "description"
                in requested_fields
            )
        )

        included_fields = [
            field
            for field in requested_fields
            if not (
                should_omit_enrollment
                and field
                == "enrollment_target"
            )
        ]

        parts = [
            str(facts["trial_title"])
            + ":"
        ]

        if "description" in included_fields:
            parts.append(
                str(facts["description"])
            )

        if "trial_phase" in included_fields:
            parts.append(
                "Phase: "
                + str(facts["trial_phase"])
                + "."
            )

        if (
            "enrollment_target"
            in included_fields
        ):
            parts.append(
                "Enrollment target: "
                + str(
                    facts[
                        "enrollment_target"
                    ]
                )
                + "."
            )

        if "sponsor_name" in included_fields:
            parts.append(
                "Sponsor: "
                + str(facts["sponsor_name"])
                + "."
            )

        if "trial_title" in included_fields:
            parts.append(
                "The trial title is "
                + str(facts["trial_title"])
                + "."
            )

        answer = " ".join(parts)

        latency_ms = (
            time.perf_counter()
            - started_at
        ) * 1000

        return {
            "answer": answer,
            "loaded_lesson_ids": [
                lesson["lesson_id"]
                for lesson in loaded_lessons
            ],
            "included_fields": (
                included_fields
            ),
            "latency_ms": round(
                latency_ms,
                3,
            ),
        }


class EvaluatorAgent:
    """Evaluate answers against reference facts."""

    def __init__(
        self,
        knowledge: DomainKnowledge,
    ) -> None:
        self.knowledge = knowledge

    def evaluate(
        self,
        question: str,
        answer: str,
    ) -> Evaluation:
        """Return PASS or REVISE."""

        expected = (
            self.knowledge.expected_values(
                question
            )
        )

        normalized_answer = answer.lower()

        missing_fields = [
            field
            for field, value in expected.items()
            if value.lower()
            not in normalized_answer
        ]

        if not missing_fields:
            return Evaluation(
                result="PASS",
                explanation=(
                    "The answer contains all "
                    "facts required by the "
                    "reference dataset."
                ),
                feedback="",
                missing_fields=[],
            )

        missing_descriptions = [
            (
                field
                + "="
                + expected[field]
            )
            for field in missing_fields
        ]

        feedback = (
            "Add the following missing "
            "ground-truth facts: "
            + ", ".join(
                missing_descriptions
            )
            + "."
        )

        return Evaluation(
            result="REVISE",
            explanation=(
                "The answer is incomplete "
                "relative to the reference "
                "dataset."
            ),
            feedback=feedback,
            missing_fields=missing_fields,
        )


class SelfImprovingSystem:
    """Two-agent repair and lesson workflow."""

    def __init__(self) -> None:
        self.knowledge = DomainKnowledge()
        self.lessons = LessonStore()
        self.answering_agent = AnsweringAgent(
            self.knowledge,
            self.lessons,
        )
        self.evaluator_agent = EvaluatorAgent(
            self.knowledge
        )

    def run(
        self,
        question: str,
        *,
        evaluator_enabled: bool,
        lessons_enabled: bool,
        update_lesson_count: bool = True,
    ) -> dict[str, Any]:
        """Run with a maximum of two attempts."""

        started_at = time.perf_counter()
        attempts: list[dict[str, Any]] = []
        feedback = ""
        maximum_attempts = (
            2
            if evaluator_enabled
            else 1
        )

        for attempt_number in range(
            1,
            maximum_attempts + 1,
        ):
            response = (
                self.answering_agent.answer(
                    question,
                    attempt=attempt_number,
                    feedback=feedback,
                    use_lessons=(
                        lessons_enabled
                    ),
                    update_lesson_count=(
                        update_lesson_count
                    ),
                )
            )

            evaluation = (
                self.evaluator_agent.evaluate(
                    question,
                    response["answer"],
                )
            )

            attempt_record = {
                "attempt": attempt_number,
                "answer": response[
                    "answer"
                ],
                "loaded_lesson_ids": (
                    response[
                        "loaded_lesson_ids"
                    ]
                ),
                "evaluation_result": (
                    evaluation.result
                ),
                "evaluation_explanation": (
                    evaluation.explanation
                ),
                "feedback": (
                    evaluation.feedback
                ),
                "missing_fields": (
                    evaluation.missing_fields
                ),
            }

            attempts.append(
                attempt_record
            )

            if evaluation.result == "PASS":
                break

            feedback = evaluation.feedback

        final_attempt = attempts[-1]

        total_latency_ms = (
            time.perf_counter()
            - started_at
        ) * 1000

        return {
            "question": question,
            "attempts": attempts,
            "attempt_count": len(attempts),
            "final_answer": (
                final_attempt["answer"]
            ),
            "final_evaluation": (
                final_attempt[
                    "evaluation_result"
                ]
            ),
            "success": (
                final_attempt[
                    "evaluation_result"
                ]
                == "PASS"
            ),
            "latency_ms": round(
                total_latency_ms,
                3,
            ),
            "stop_reason": (
                "passed"
                if final_attempt[
                    "evaluation_result"
                ]
                == "PASS"
                else "maximum_attempts_reached"
            ),
        }
