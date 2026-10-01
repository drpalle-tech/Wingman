"""Model-agnostic LLM client with per-task settings (Azure OpenAI chat completions)."""

import logging
import os
from dataclasses import dataclass
from typing import AsyncIterator, Literal, Optional, Union

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

Task = Literal["chat", "review", "generate"]

# Reasoning models reject custom temperature and count hidden reasoning tokens
# against max_completion_tokens, so they get a larger budget.
REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")
JSON_MODE_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4")
NON_REASONING_OUTPUT_CAP = 4096


@dataclass(frozen=True)
class TaskSettings:
    max_output_tokens: int
    temperature: float
    reasoning_effort: str
    json_output: bool = False


TASK_SETTINGS: dict[str, TaskSettings] = {
    "chat": TaskSettings(max_output_tokens=8000, temperature=0.3, reasoning_effort="low"),
    "review": TaskSettings(max_output_tokens=16000, temperature=0.1, reasoning_effort="medium", json_output=True),
    "generate": TaskSettings(max_output_tokens=16000, temperature=0.2, reasoning_effort="medium"),
}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class Completion:
    text: str
    usage: Usage
    finish_reason: Optional[str]


@dataclass
class StreamEnd:
    usage: Usage
    finish_reason: Optional[str]


class LLMClient:
    def __init__(self) -> None:
        self.deployment = os.getenv("DEPLOYMENT_NAME", "gpt-5-mini")
        self.model = os.getenv("LLM_MODEL") or self.deployment
        name = self.model.lower()

        reasoning_override = os.getenv("LLM_REASONING")
        self.reasoning = (
            reasoning_override.strip().lower() == "true"
            if reasoning_override
            else name.startswith(REASONING_MODEL_PREFIXES)
        )
        self.json_mode = name.startswith(JSON_MODE_MODEL_PREFIXES)
        self.reasoning_effort_override = os.getenv("LLM_REASONING_EFFORT")

        self._client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION", "2025-04-01-preview"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        )
        logger.info("LLM client ready: deployment=%s model=%s reasoning=%s", self.deployment, self.model, self.reasoning)

    def _request_kwargs(self, task: Task) -> dict:
        settings = TASK_SETTINGS[task]
        kwargs: dict = {"model": self.deployment}
        if self.reasoning:
            kwargs["max_completion_tokens"] = settings.max_output_tokens
            kwargs["reasoning_effort"] = self.reasoning_effort_override or settings.reasoning_effort
        else:
            kwargs["max_tokens"] = min(settings.max_output_tokens, NON_REASONING_OUTPUT_CAP)
            kwargs["temperature"] = settings.temperature
        if settings.json_output and self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    async def complete(self, messages: list[dict], task: Task) -> Completion:
        response = await self._client.chat.completions.create(messages=messages, **self._request_kwargs(task))
        choice = response.choices[0]
        usage = Usage()
        if response.usage:
            usage = Usage(response.usage.prompt_tokens, response.usage.completion_tokens)
        if choice.finish_reason == "length":
            logger.warning("Model hit the output token limit for task=%s", task)
        return Completion(text=choice.message.content or "", usage=usage, finish_reason=choice.finish_reason)

    async def stream(self, messages: list[dict], task: Task) -> AsyncIterator[Union[str, StreamEnd]]:
        """Yields text deltas, then a single StreamEnd with usage."""
        response = await self._client.chat.completions.create(
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **self._request_kwargs(task),
        )
        usage = Usage()
        finish_reason: Optional[str] = None
        async for chunk in response:
            if chunk.usage:
                usage = Usage(chunk.usage.prompt_tokens, chunk.usage.completion_tokens)
            for choice in chunk.choices:
                if choice.delta and choice.delta.content:
                    yield choice.delta.content
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        yield StreamEnd(usage=usage, finish_reason=finish_reason)
