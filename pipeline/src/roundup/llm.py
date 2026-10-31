"""A small LLM interface with one real provider (Anthropic) and a FakeLLM for offline tests and dev runs.

Model names always come from the environment (LLM_SCREEN_MODEL, LLM_EDITOR_MODEL); nothing here picks a model.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from roundup.config import Settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
JSON_RETRIES = 2  # invalid structured output is retried up to twice

# USD per million tokens (input, output), checked against platform.claude.com/docs/en/about-claude/pricing
# on 2026-10-31. Used only to log estimated costs.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}


class LLMError(Exception):
    pass


@dataclass
class LLMResult(Generic[T]):
    data: T
    model: str
    input_tokens: int
    output_tokens: int


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class LLM:
    """`complete_json` asks for output matching a Pydantic schema and validates it, retrying on invalid output."""

    def complete_json(self, schema: type[T], prompt: str, model: str, *, system: str = "",
                      max_tokens: int = 4000, effort: str = "medium", fallback: bool = False) -> LLMResult[T]:
        input_tokens = output_tokens = 0
        for attempt in range(1 + JSON_RETRIES):
            text, used_model, tokens_in, tokens_out = self._complete(
                prompt, model, system=system, max_tokens=max_tokens, effort=effort, schema=schema, fallback=fallback
            )
            input_tokens += tokens_in
            output_tokens += tokens_out
            try:
                return LLMResult(schema.model_validate_json(text), used_model, input_tokens, output_tokens)
            except ValidationError as e:
                log.warning("Invalid %s output (attempt %d): %s", schema.__name__, attempt + 1, e.errors()[:2])
        raise LLMError(f"{schema.__name__}: invalid output after {1 + JSON_RETRIES} attempts")

    def complete_text(self, prompt: str, model: str, *, system: str = "", max_tokens: int = 4000,
                      effort: str = "medium") -> LLMResult[str]:
        text, used_model, tokens_in, tokens_out = self._complete(
            prompt, model, system=system, max_tokens=max_tokens, effort=effort
        )
        return LLMResult(text, used_model, tokens_in, tokens_out)

    def _complete(self, prompt: str, model: str, *, system: str, max_tokens: int, effort: str,
                  schema: type[BaseModel] | None = None, fallback: bool = False) -> tuple[str, str, int, int]:
        """Return (text, model that answered, input tokens, output tokens)."""
        raise NotImplementedError


class AnthropicLLM(LLM):
    def __init__(self, api_key: str):
        # The SDK already retries 429, 5xx and connection errors with backoff.
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=4)

    def _complete(self, prompt, model, *, system, max_tokens, effort, schema=None, fallback=False):
        output_config: dict = {"effort": effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": anthropic.transform_schema(schema.model_json_schema())}
        extra: dict = {}
        if fallback:
            # If the model declines, the API retries on a substitute model chosen by refusal category.
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        response = self.client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config=output_config,
            **extra,
        )
        if response.stop_reason == "refusal":
            raise LLMError(f"{model} declined the request")
        if response.stop_reason == "max_tokens":
            raise LLMError(f"{model} hit max_tokens={max_tokens} before finishing")
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, response.model, response.usage.input_tokens, response.usage.output_tokens


class FakeLLM(LLM):
    """Offline stand-in: each schema maps to a function that builds a response from the prompt.

    A responder may return a model instance or a raw JSON string (to exercise validation and retries).
    """

    def __init__(self, responders: dict[type[BaseModel], Callable[[str], BaseModel | str]]):
        self.responders = responders
        self.calls: list[tuple[str, str]] = []

    def _complete(self, prompt, model, *, system, max_tokens, effort, schema=None, fallback=False):
        self.calls.append((schema.__name__ if schema else "text", prompt))
        if schema is None:
            return "fake text", "fake", 0, 0
        out = self.responders[schema](prompt)
        text = out if isinstance(out, str) else out.model_dump_json()
        return text, "fake", len(prompt) // 4, len(text) // 4


def get_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "anthropic":
        if not settings.llm_api_key:
            raise LLMError("LLM_API_KEY is not set (see .env.example)")
        return AnthropicLLM(settings.llm_api_key)
    if settings.llm_provider == "fake":
        from roundup.editor import FAKE_RESPONDERS as editor_fakes
        from roundup.screening import FAKE_RESPONDERS as screening_fakes

        return FakeLLM({**screening_fakes, **editor_fakes})
    raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (expected 'anthropic' or 'fake')")
