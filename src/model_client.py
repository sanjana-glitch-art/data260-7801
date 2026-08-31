import re
from dataclasses import dataclass
from typing import Any

from ollama import Client


@dataclass
class CompletionResult:
    """Stable result returned by the model adapter."""

    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    raw_response: Any


class ModelClient:
    """Reusable adapter for local Ollama model calls."""

    def __init__(
        self,
        model: str = "qwen3:4b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        num_ctx: int = 2048,
        num_predict: int = 256
    ) -> None:
        self.model_name = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.num_predict = num_predict

        self.turn_count = 0
        self.cumulative_input_tokens = 0
        self.cumulative_output_tokens = 0

        self._client = Client(
            host=base_url
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[Any] | None = None,
        response_format: dict[str, Any] | str | None = None
    ) -> CompletionResult:
        """
        Send messages through Ollama and return a stable result.

        All project model calls should use this method.
        """
        request: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "think": False,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict
            }
        }

        if tools:
            request["tools"] = tools

        if response_format is not None:
            request["format"] = response_format

        response = self._client.chat(
            **request
        )

        content = response.message.content or ""

        # Defensive cleanup in case a model still emits
        # a visible thinking block.
        content = re.sub(
            r"<think>.*?</think>\s*",
            "",
            content,
            flags=re.DOTALL
        ).strip()

        if "</think>" in content:
            content = content.split(
                "</think>",
                maxsplit=1
            )[1].strip()

        input_tokens = int(
            response.prompt_eval_count or 0
        )

        output_tokens = int(
            response.eval_count or 0
        )

        total_tokens = (
            input_tokens + output_tokens
        )

        self.turn_count += 1
        self.cumulative_input_tokens += input_tokens
        self.cumulative_output_tokens += output_tokens

        return CompletionResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            raw_response=response
        )

    @property
    def cumulative_total_tokens(self) -> int:
        """Return cumulative input and output tokens."""
        return (
            self.cumulative_input_tokens
            + self.cumulative_output_tokens
        )

    def get_stats(self) -> dict[str, int | str]:
        """Return cumulative model-client statistics."""
        return {
            "model": self.model_name,
            "turn_count": self.turn_count,
            "cumulative_input_tokens": (
                self.cumulative_input_tokens
            ),
            "cumulative_output_tokens": (
                self.cumulative_output_tokens
            ),
            "cumulative_total_tokens": (
                self.cumulative_total_tokens
            )
        }