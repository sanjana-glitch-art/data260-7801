from __future__ import annotations

import multiprocessing
from code.hw10_config import (
    JUDGE_MAX_ATTEMPTS,
    JUDGE_MODEL,
    JUDGE_SCORE_MAXIMUM,
    JUDGE_SCORE_MINIMUM,
    JUDGE_TEMPERATURE,
    JUDGE_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
)
from code.hw10_tracing import trace_span
from dataclasses import asdict, dataclass
from queue import Empty
from time import perf_counter
from typing import Any

from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import (
    LLMTestCase,
    SingleTurnParams,
)
from ollama import AsyncClient, Client
from pydantic import BaseModel


class QwenOllamaJudge(DeepEvalBaseLLM):
    """Schema-aware local judge with thinking disabled."""

    def __init__(
        self,
        *,
        model_name: str = JUDGE_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url

    def load_model(self) -> Client:
        """Return a synchronous Ollama client."""

        return Client(
            host=self.base_url,
        )

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
    ) -> str | BaseModel:
        """Generate text or a requested Pydantic schema."""

        client = self.load_model()

        request_arguments: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": JUDGE_TEMPERATURE,
                "num_predict": 512,
                "num_ctx": 4096,
                "seed": 7801,
            },
        }

        if schema is not None:
            request_arguments["format"] = (
                schema.model_json_schema()
            )

        response = client.chat(
            **request_arguments,
        )

        content = response.message.content

        if not content.strip():
            raise ValueError(
                "Ollama returned an empty response."
            )

        if schema is not None:
            return schema.model_validate_json(
                content
            )

        return content

    async def a_generate(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
    ) -> str | BaseModel:
        """Generate asynchronously with thinking disabled."""

        client = AsyncClient(
            host=self.base_url,
        )

        request_arguments: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": JUDGE_TEMPERATURE,
                "num_predict": 512,
                "num_ctx": 4096,
                "seed": 7801,
            },
        }

        if schema is not None:
            request_arguments["format"] = (
                schema.model_json_schema()
            )

        response = await client.chat(
            **request_arguments,
        )

        content = response.message.content

        if not content.strip():
            raise ValueError(
                "Ollama returned an empty response."
            )

        if schema is not None:
            return schema.model_validate_json(
                content
            )

        return content

    def get_model_name(self) -> str:
        """Return the local judge model name."""

        return (
            f"Ollama {self.model_name} "
            "(thinking disabled)"
        )


@dataclass
class JudgeScore:
    """One bounded GEval score and explanation."""

    criterion: str
    score: int | None
    normalized_score: float | None
    reason: str
    success: bool
    attempt_count: int
    latency_ms: float
    error: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable judge result."""

        return asdict(self)


@dataclass
class PipelineEvaluation:
    """Evaluation of Planner, Writer, and Reviewer output."""

    trace_id: str
    question: str
    plan: list[str]
    writer_draft: str
    final_answer: str
    reference_answer: str
    plan_quality: JudgeScore
    writer_helpfulness: JudgeScore
    final_answer_helpfulness: JudgeScore
    draft_score: int | None
    final_score: int | None
    score_difference: int | None
    improvement_interpretation: str
    success: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable pipeline evaluation."""

        return asdict(self)


PLAN_STEPS = [
    (
        "Check whether the plan identifies the "
        "information required by the input question."
    ),
    (
        "Check whether the plan would retrieve all "
        "facts shown in the expected output."
    ),
    (
        "Penalize plans that omit a requested fact, "
        "contain irrelevant work, or cannot produce "
        "the expected output."
    ),
    (
        "Reward plans that are direct, complete, "
        "ordered, and appropriate for a clinical-trial "
        "research assistant."
    ),
]

HELPFULNESS_STEPS = [
    (
        "Compare the actual output with the input "
        "question and expected output."
    ),
    (
        "Check every clinical-trial fact, including "
        "the title, phase, sponsor, and enrollment "
        "target when requested."
    ),
    (
        "Heavily penalize incorrect facts, unsupported "
        "claims, and answers about the wrong trial."
    ),
    (
        "Penalize missing information that the user "
        "explicitly requested."
    ),
    (
        "Reward answers that are correct, complete, "
        "relevant, concise, and easy to understand."
    ),
]


def _normalized_to_five_point(
    normalized_score: float,
) -> int:
    """Convert DeepEval's zero-to-one score into 1–5."""

    bounded_score = max(
        0.0,
        min(1.0, normalized_score),
    )

    converted = round(
        JUDGE_SCORE_MINIMUM
        + (
            JUDGE_SCORE_MAXIMUM
            - JUDGE_SCORE_MINIMUM
        )
        * bounded_score
    )

    return max(
        JUDGE_SCORE_MINIMUM,
        min(JUDGE_SCORE_MAXIMUM, converted),
    )


def _judge_worker(
    output_queue: Any,
    criterion: str,
    question: str,
    actual_output: str,
    expected_output: str,
) -> None:
    """Run one GEval measurement in a child process."""

    try:
        model = QwenOllamaJudge(
            model_name=JUDGE_MODEL,
            base_url=OLLAMA_BASE_URL,
        )

        if criterion == "plan_quality":
            steps = PLAN_STEPS
            metric_name = "Plan Quality"
        else:
            steps = HELPFULNESS_STEPS
            metric_name = criterion.replace(
                "_",
                " ",
            ).title()

        metric = GEval(
            name=metric_name,
            evaluation_steps=steps,
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.EXPECTED_OUTPUT,
            ],
            model=model,
            threshold=None,
            async_mode=False,
            verbose_mode=False,
        )

        test_case = LLMTestCase(
            input=question,
            actual_output=actual_output,
            expected_output=expected_output,
        )

        metric.measure(test_case)

        raw_score = metric.score

        if raw_score is None:
            raise ValueError(
                "DeepEval returned no score."
            )

        normalized_score = max(
            0.0,
            min(1.0, float(raw_score)),
        )

        reason = metric.reason

        if not isinstance(reason, str):
            reason = str(reason or "")

        output_queue.put(
            {
                "success": True,
                "normalized_score": normalized_score,
                "score": _normalized_to_five_point(
                    normalized_score
                ),
                "reason": reason.strip(),
                "error": None,
                "error_type": None,
            }
        )
    except Exception as error:  # noqa: BLE001
        output_queue.put(
            {
                "success": False,
                "normalized_score": None,
                "score": None,
                "reason": "",
                "error": str(error),
                "error_type": type(error).__name__,
            }
        )


def score_with_geval(
    *,
    criterion: str,
    question: str,
    actual_output: str,
    expected_output: str,
    timeout_seconds: float = JUDGE_TIMEOUT_SECONDS,
    maximum_attempts: int = JUDGE_MAX_ATTEMPTS,
) -> JudgeScore:
    """Run GEval with bounded attempts and timeout."""

    if not question.strip():
        raise ValueError(
            "question must be a non-empty string."
        )

    if not actual_output.strip():
        raise ValueError(
            "actual_output must be a non-empty string."
        )

    if not expected_output.strip():
        raise ValueError(
            "expected_output must be a non-empty string."
        )

    if maximum_attempts < 1:
        raise ValueError(
            "maximum_attempts must be positive."
        )

    if timeout_seconds <= 0:
        raise ValueError(
            "timeout_seconds must be positive."
        )

    started = perf_counter()
    last_error: str | None = None
    last_error_type: str | None = None

    for attempt in range(
        1,
        maximum_attempts + 1,
    ):
        context = multiprocessing.get_context(
            "spawn"
        )
        output_queue = context.Queue()

        process = context.Process(
            target=_judge_worker,
            args=(
                output_queue,
                criterion,
                question,
                actual_output,
                expected_output,
            ),
        )

        process.start()
        process.join(timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join(timeout=5.0)

            last_error = (
                "Judge exceeded the configured timeout "
                f"of {timeout_seconds} seconds."
            )
            last_error_type = "JudgeTimeoutError"
            output_queue.close()
            output_queue.join_thread()
            continue

        try:
            result = output_queue.get(
                timeout=2.0,
            )
        except Empty:
            last_error = (
                "Judge process ended without returning "
                "a result."
            )
            last_error_type = "MissingJudgeResultError"
            output_queue.close()
            output_queue.join_thread()
            continue

        output_queue.close()
        output_queue.join_thread()

        if result.get("success"):
            latency_ms = round(
                (
                    perf_counter()
                    - started
                )
                * 1000,
                3,
            )

            return JudgeScore(
                criterion=criterion,
                score=result.get("score"),
                normalized_score=result.get(
                    "normalized_score"
                ),
                reason=str(
                    result.get("reason", "")
                ),
                success=True,
                attempt_count=attempt,
                latency_ms=latency_ms,
            )

        last_error = str(
            result.get(
                "error",
                "Unknown judge error.",
            )
        )
        last_error_type = str(
            result.get(
                "error_type",
                "JudgeError",
            )
        )

    latency_ms = round(
        (
            perf_counter()
            - started
        )
        * 1000,
        3,
    )

    return JudgeScore(
        criterion=criterion,
        score=None,
        normalized_score=None,
        reason="",
        success=False,
        attempt_count=maximum_attempts,
        latency_ms=latency_ms,
        error=last_error,
        error_type=last_error_type,
    )


def interpret_improvement(
    draft_score: int | None,
    final_score: int | None,
) -> tuple[int | None, str]:
    """Explain the final-versus-draft score change."""

    if (
        draft_score is None
        or final_score is None
    ):
        return (
            None,
            (
                "Improvement could not be calculated "
                "because one or both judge scores failed."
            ),
        )

    difference = final_score - draft_score

    if difference > 0:
        interpretation = (
            "The Reviewer improved the Writer draft "
            f"by {difference} point(s)."
        )
    elif difference < 0:
        interpretation = (
            "The final answer scored "
            f"{abs(difference)} point(s) below the "
            "Writer draft."
        )
    else:
        interpretation = (
            "The Reviewer did not change the measured "
            "helpfulness score."
        )

    return difference, interpretation


def evaluate_writer_draft(
    *,
    question: str,
    writer_draft: str,
    reference_answer: str,
) -> JudgeScore:
    """Evaluate one Writer draft for helpfulness."""

    return score_with_geval(
        criterion="writer_helpfulness",
        question=question,
        actual_output=writer_draft,
        expected_output=reference_answer,
    )


def evaluate_pipeline(
    *,
    trace_id: str,
    question: str,
    plan: list[str],
    writer_draft: str,
    final_answer: str,
    reference_answer: str,
) -> PipelineEvaluation:
    """Evaluate Planner, Writer, and Reviewer output."""

    if not trace_id.strip():
        raise ValueError(
            "trace_id must be a non-empty string."
        )

    if not plan:
        raise ValueError(
            "plan must contain at least one step."
        )

    plan_text = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(
            plan,
            start=1,
        )
    )

    with trace_span(
        trace_id,
        "evaluation",
        metadata={
            "judge_model": JUDGE_MODEL,
            "evaluation_framework": "DeepEval GEval",
        },
    ) as evaluation_span:
        plan_quality = score_with_geval(
            criterion="plan_quality",
            question=question,
            actual_output=plan_text,
            expected_output=reference_answer,
        )

        writer_helpfulness = score_with_geval(
            criterion="writer_helpfulness",
            question=question,
            actual_output=writer_draft,
            expected_output=reference_answer,
        )

        final_helpfulness = score_with_geval(
            criterion="final_answer_helpfulness",
            question=question,
            actual_output=final_answer,
            expected_output=reference_answer,
        )

        difference, interpretation = (
            interpret_improvement(
                writer_helpfulness.score,
                final_helpfulness.score,
            )
        )

        success = all(
            result.success
            for result in (
                plan_quality,
                writer_helpfulness,
                final_helpfulness,
            )
        )

        evaluation_span.add_metadata(
            plan_score=plan_quality.score,
            writer_score=writer_helpfulness.score,
            final_score=final_helpfulness.score,
            score_difference=difference,
            judge_success=success,
        )

    return PipelineEvaluation(
        trace_id=trace_id,
        question=question,
        plan=plan,
        writer_draft=writer_draft,
        final_answer=final_answer,
        reference_answer=reference_answer,
        plan_quality=plan_quality,
        writer_helpfulness=writer_helpfulness,
        final_answer_helpfulness=final_helpfulness,
        draft_score=writer_helpfulness.score,
        final_score=final_helpfulness.score,
        score_difference=difference,
        improvement_interpretation=interpretation,
        success=success,
    )