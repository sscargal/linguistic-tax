"""Unified API client for the Linguistic Tax research toolkit.

Wraps Anthropic and Google GenAI SDKs with streaming for TTFT/TTLT
measurement. Single call_model() entry point for all LLM calls.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import anthropic
import openai
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from src.config import OPENROUTER_BASE_URL
from src.model_registry import registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class APIResponse:
    """Unified response from any model API call."""

    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float
    ttlt_ms: float
    model: str


# Mutable state for adaptive rate limiting
_rate_delays: dict[str, float] = {
    m: registry.get_delay(m) for m in registry._models
}
_rate_baselines: dict[str, float] = dict(_rate_delays)
_rate_successes: dict[str, int] = {}

_RATE_DECAY_AFTER: int = 50  # halve delay after N consecutive successes


def _rate_limit_success(model: str) -> None:
    """Record a successful API call and decay inflated rate limits."""
    _rate_successes[model] = _rate_successes.get(model, 0) + 1
    if _rate_successes[model] >= _RATE_DECAY_AFTER:
        baseline = _rate_baselines.get(model, registry.get_delay(model))
        current = _rate_delays.get(model, baseline)
        if current > baseline:
            _rate_delays[model] = max(baseline, current / 2)
        _rate_successes[model] = 0


def _rate_limit_backoff(model: str) -> None:
    """Double the rate limit delay after a 429 error."""
    _rate_delays[model] = _rate_delays.get(model, 0.2) * 2
    _rate_successes[model] = 0


def _validate_api_keys(model: str) -> None:
    """Validate required API key exists in environment.

    Args:
        model: Model identifier used to determine which key is needed.

    Raises:
        EnvironmentError: If the required API key is not set.
    """
    if model.startswith("claude"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
    elif model.startswith("gemini"):
        if not os.environ.get("GOOGLE_API_KEY"):
            raise EnvironmentError("GOOGLE_API_KEY not set")
    elif model.startswith(("gpt", "o1", "o3", "o4")):
        if not os.environ.get("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY not set")
    elif model.startswith("openrouter/"):
        if not os.environ.get("OPENROUTER_API_KEY"):
            raise EnvironmentError("OPENROUTER_API_KEY not set")


_QUOTA_KEYWORDS = (
    "per-day", "per-month", "per-week", "daily", "monthly", "weekly",
    "quota", "credits", "limit exceeded",
)


class QuotaExceededError(Exception):
    """Raised when a provider's usage quota is exhausted (not a transient rate limit)."""

    def __init__(self, model: str, message: str):
        self.model = model
        super().__init__(f"Quota exceeded for {model}: {message}")


def _is_quota_error(error: Exception) -> bool:
    """Check if a rate limit error is actually a quota/daily limit exhaustion.

    Quota errors are not transient — retrying won't help until the quota
    resets (typically next day/month).

    Args:
        error: The rate limit exception to inspect.

    Returns:
        True if this is a quota exhaustion, not a transient rate limit.
    """
    msg = str(error).lower()
    return any(kw in msg for kw in _QUOTA_KEYWORDS)


def _apply_rate_limit(model: str) -> None:
    """Sleep for the configured rate limit delay for this model.

    Args:
        model: Model identifier used to look up the delay.
    """
    delay = _rate_delays.get(model, 0.2)
    if delay > 0:
        time.sleep(delay)


def _call_anthropic(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    """Call Anthropic API with streaming for TTFT/TTLT measurement.

    Args:
        model: Anthropic model identifier.
        system: Optional system prompt.
        user_message: The user message to send.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature.

    Returns:
        Unified APIResponse with text, token counts, and timing.
    """
    client = anthropic.Anthropic()
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages = [{"role": "user", "content": user_message}]
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        temperature=temperature,
    )
    if system is not None:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if not chunks:
                ttft_ms = (time.monotonic() - start) * 1000
            chunks.append(text)

    ttlt_ms = (time.monotonic() - start) * 1000
    final = stream.get_final_message()

    return APIResponse(
        text="".join(chunks),
        input_tokens=final.usage.input_tokens,
        output_tokens=final.usage.output_tokens,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )


def _call_google(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    """Call Google GenAI API with streaming for TTFT/TTLT measurement.

    Args:
        model: Google model identifier.
        system: Optional system instruction.
        user_message: The user message to send.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature.

    Returns:
        Unified APIResponse with text, token counts, and timing.
    """
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []
    last_chunk = None

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    if system is not None:
        config.system_instruction = system

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=user_message,
        config=config,
    ):
        if chunk.text and not chunks:
            ttft_ms = (time.monotonic() - start) * 1000
        if chunk.text:
            chunks.append(chunk.text)
        last_chunk = chunk

    ttlt_ms = (time.monotonic() - start) * 1000

    usage = last_chunk.usage_metadata if last_chunk else None
    return APIResponse(
        text="".join(chunks),
        input_tokens=usage.prompt_token_count if usage else 0,
        output_tokens=usage.candidates_token_count if usage else 0,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )


def _call_openai(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    """Call OpenAI API with streaming for TTFT/TTLT measurement.

    Args:
        model: OpenAI model identifier.
        system: Optional system prompt.
        user_message: The user message to send.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature.

    Returns:
        Unified APIResponse with text, token counts, and timing.
    """
    client = openai.OpenAI()
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages: list[dict] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    # Build params — some models reject certain parameters
    params: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        params["temperature"] = temperature

    try:
        stream = client.chat.completions.create(**params)
    except openai.BadRequestError as e:
        err_msg = str(e)
        # Retry with adjusted params based on error
        if "max_completion_tokens" in err_msg:
            params.pop("max_completion_tokens")
            params["max_tokens"] = max_tokens
        if "temperature" in err_msg:
            params.pop("temperature", None)
        stream = client.chat.completions.create(**params)

    usage = None
    for chunk in stream:
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta.content is not None:
            if not chunks:
                ttft_ms = (time.monotonic() - start) * 1000
            chunks.append(chunk.choices[0].delta.content)

    ttlt_ms = (time.monotonic() - start) * 1000

    return APIResponse(
        text="".join(chunks),
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )


def _call_openrouter(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    """Call OpenRouter API with streaming for TTFT/TTLT measurement.

    Uses the OpenAI SDK with base_url override pointing to OpenRouter.
    Strips the 'openrouter/' prefix from the model ID before sending
    to the API. Adds project-identifying HTTP headers.

    Args:
        model: Full model identifier with openrouter/ prefix.
        system: Optional system prompt.
        user_message: The user message to send.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature.

    Returns:
        Unified APIResponse with text, token counts, and timing.
    """
    api_model = model.removeprefix("openrouter/")

    client = openai.OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "https://github.com/linguistic-tax",
            "X-Title": "Linguistic Tax Research",
        },
    )
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages: list[dict] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    params: dict[str, Any] = {
        "model": api_model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        params["temperature"] = temperature

    try:
        stream = client.chat.completions.create(**params)
    except openai.BadRequestError as e:
        err_msg = str(e)
        if "max_completion_tokens" in err_msg:
            params.pop("max_completion_tokens")
            params["max_tokens"] = max_tokens
        if "temperature" in err_msg:
            params.pop("temperature", None)
        stream = client.chat.completions.create(**params)

    usage = None
    for chunk in stream:
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta.content is not None:
            if not chunks:
                ttft_ms = (time.monotonic() - start) * 1000
            chunks.append(chunk.choices[0].delta.content)

    ttlt_ms = (time.monotonic() - start) * 1000

    return APIResponse(
        text="".join(chunks),
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )


def call_model(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float = 0.0,
) -> APIResponse:
    """Call an LLM via streaming, measure timing, return unified response.

    Includes retry with exponential backoff (1s, 4s, 16s) on rate limit
    errors. After 4 total attempts, re-raises the exception.
    On 429, doubles the rate limit delay for this model.

    Args:
        model: Model identifier (e.g., "claude-sonnet-4-20250514", "gemini-1.5-pro").
        system: Optional system prompt / system instruction.
        user_message: The user message to send.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (default 0.0).

    Returns:
        Unified APIResponse with text, token counts, and timing.

    Raises:
        ValueError: If model name is not recognized.
        EnvironmentError: If required API key is missing.
        anthropic.RateLimitError: If rate limited after 4 attempts.
        openai.RateLimitError: If rate limited after 4 attempts (OpenAI or OpenRouter).
        genai_errors.ClientError: If rate limited after 4 attempts (Google).
    """
    _validate_api_keys(model)

    retry_delays = [1, 4, 16]  # seconds between retries
    last_error: Exception | None = None

    for attempt in range(4):  # 1 initial + 3 retries
        try:
            _apply_rate_limit(model)
            if model.startswith("claude"):
                result = _call_anthropic(
                    model, system, user_message, max_tokens, temperature
                )
            elif model.startswith("gemini"):
                result = _call_google(
                    model, system, user_message, max_tokens, temperature
                )
            elif model.startswith(("gpt", "o1", "o3", "o4")):
                result = _call_openai(
                    model, system, user_message, max_tokens, temperature
                )
            elif model.startswith("openrouter/"):
                result = _call_openrouter(
                    model, system, user_message, max_tokens, temperature
                )
            else:
                raise ValueError(f"Unknown model: {model}")
            _rate_limit_success(model)
            return result
        except anthropic.RateLimitError as e:
            if _is_quota_error(e):
                raise
            last_error = e
            _rate_limit_backoff(model)
            logger.warning(
                "Rate limited on %s (attempt %d/4), delay now %.1fs",
                model, attempt + 1, _rate_delays.get(model, 0.2),
            )
            if attempt < 3:
                time.sleep(retry_delays[attempt])
        except openai.RateLimitError as e:
            if _is_quota_error(e):
                raise
            last_error = e
            _rate_limit_backoff(model)
            logger.warning(
                "Rate limited on %s (attempt %d/4), delay now %.1fs",
                model, attempt + 1, _rate_delays.get(model, 0.2),
            )
            if attempt < 3:
                time.sleep(retry_delays[attempt])
        except genai_errors.ClientError as e:
            if e.code == 429:
                if _is_quota_error(e):
                    raise
                last_error = e
                _rate_limit_backoff(model)
                logger.warning(
                    "Rate limited on %s (attempt %d/4), delay now %.1fs",
                    model, attempt + 1, _rate_delays.get(model, 0.2),
                )
                if attempt < 3:
                    time.sleep(retry_delays[attempt])
            else:
                raise

    raise last_error  # type: ignore[misc]
