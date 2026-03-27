"""Model discovery module for querying live model availability from provider APIs.

Queries Anthropic, Google, OpenAI, and OpenRouter APIs in parallel to discover
available models with context window sizes and pricing (where available).
Falls back to registry data when provider queries fail.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic
import openai
import requests
from google import genai

from src.config import OPENROUTER_BASE_URL
from src.model_registry import _PROVIDER_KEY_MAP, registry

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredModel:
    """A model discovered from a provider API.

    Attributes:
        model_id: Unique model identifier (e.g. "claude-sonnet-4-20250514").
        provider: API provider name ("anthropic", "google", "openai", "openrouter").
        context_window: Maximum input token count. None if provider does not expose it.
        input_price_per_1m: Cost per 1M input tokens in USD. None if not available.
        output_price_per_1m: Cost per 1M output tokens in USD. None if not available.
    """

    model_id: str
    provider: str
    context_window: int | None
    input_price_per_1m: float | None
    output_price_per_1m: float | None


@dataclass
class DiscoveryResult:
    """Result from querying all providers for available models.

    Attributes:
        models: Mapping of provider name to list of discovered models.
        errors: Mapping of provider name to error message string.
    """

    models: dict[str, list[DiscoveredModel]]
    errors: dict[str, str]


def _query_anthropic(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query Anthropic API for available models.

    Paginates through all results using has_more/last_id. Extracts model ID
    and context window (max_input_tokens). Pricing is not available via the
    Anthropic API.

    Args:
        timeout: HTTP timeout in seconds for the API client.

    Returns:
        List of DiscoveredModel instances from Anthropic.
    """
    client = anthropic.Anthropic(timeout=timeout)
    models: list[DiscoveredModel] = []

    page = client.models.list(limit=100)
    for model_info in page.data:
        models.append(
            DiscoveredModel(
                model_id=model_info.id,
                provider="anthropic",
                context_window=model_info.max_input_tokens,
                input_price_per_1m=None,
                output_price_per_1m=None,
            )
        )

    while page.has_more:
        page = client.models.list(limit=100, after_id=page.last_id)
        for model_info in page.data:
            models.append(
                DiscoveredModel(
                    model_id=model_info.id,
                    provider="anthropic",
                    context_window=model_info.max_input_tokens,
                    input_price_per_1m=None,
                    output_price_per_1m=None,
                )
            )

    return models


def _query_google(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query Google GenAI API for available models.

    Strips the "models/" prefix from model names. Skips models with empty
    IDs after prefix removal. Extracts context window from input_token_limit.
    Pricing is not available via the Google API.

    Args:
        timeout: Not directly used (timeout enforced by ThreadPoolExecutor).

    Returns:
        List of DiscoveredModel instances from Google.
    """
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    models: list[DiscoveredModel] = []

    for model in client.models.list():
        model_id = (model.name or "").removeprefix("models/")
        if not model_id:
            continue
        models.append(
            DiscoveredModel(
                model_id=model_id,
                provider="google",
                context_window=model.input_token_limit,
                input_price_per_1m=None,
                output_price_per_1m=None,
            )
        )

    return models


def _query_openai(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query OpenAI API for available models.

    Returns all models from OpenAI's models.list endpoint. Context window
    and pricing are not available via this endpoint.

    Args:
        timeout: HTTP timeout in seconds for the API client.

    Returns:
        List of DiscoveredModel instances from OpenAI.
    """
    client = openai.OpenAI(timeout=timeout)
    models: list[DiscoveredModel] = []

    for model in client.models.list():
        models.append(
            DiscoveredModel(
                model_id=model.id,
                provider="openai",
                context_window=None,
                input_price_per_1m=None,
                output_price_per_1m=None,
            )
        )

    return models


def _query_openrouter(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query OpenRouter API for available models with pricing.

    Uses direct HTTP GET to the OpenRouter /models endpoint. Parses pricing
    from per-token strings to per-1M floats. Handles free models (pricing "0").

    Args:
        timeout: HTTP timeout in seconds for the request.

    Returns:
        List of DiscoveredModel instances from OpenRouter.
    """
    headers: dict[str, str] = {}
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    resp = requests.get(
        f"{OPENROUTER_BASE_URL}/models",
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    models: list[DiscoveredModel] = []
    for item in data.get("data", []):
        pricing = item.get("pricing", {})
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")

        input_per_1m = float(prompt_price) * 1_000_000 if prompt_price is not None else None
        output_per_1m = (
            float(completion_price) * 1_000_000 if completion_price is not None else None
        )

        models.append(
            DiscoveredModel(
                model_id=item["id"],
                provider="openrouter",
                context_window=item.get("context_length"),
                input_price_per_1m=input_per_1m,
                output_price_per_1m=output_per_1m,
            )
        )

    return models


_PROVIDER_QUERY_MAP: dict[str, object] = {
    "anthropic": _query_anthropic,
    "google": _query_google,
    "openai": _query_openai,
    "openrouter": _query_openrouter,
}


def discover_all_models(timeout: float = 5.0) -> DiscoveryResult:
    """Query all configured providers for available models in parallel.

    Checks for API keys before querying each provider. Skips providers with
    missing keys (logs a warning). Uses ThreadPoolExecutor with the specified
    timeout for parallel execution.

    Args:
        timeout: Timeout in seconds for each provider query.

    Returns:
        DiscoveryResult with models and errors per provider.
    """
    result = DiscoveryResult(models={}, errors={})
    providers_to_query: list[tuple[str, object]] = []

    for provider, query_fn in _PROVIDER_QUERY_MAP.items():
        key_name = _PROVIDER_KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")
        if not os.environ.get(key_name, ""):
            msg = f"Skipping {provider}: {key_name} not set"
            result.errors[provider] = msg
            logger.warning(msg)
            continue
        providers_to_query.append((provider, query_fn))

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fn, timeout): provider
            for provider, fn in providers_to_query
        }
        try:
            for future in as_completed(futures, timeout=timeout):
                provider = futures[future]
                try:
                    result.models[provider] = future.result(timeout=0)
                except Exception as exc:
                    msg = f"{provider}: {exc}"
                    result.errors[provider] = msg
                    logger.warning("Provider query failed: %s", msg)
        except TimeoutError:
            # Any futures not yet completed are timed out
            for future, provider in futures.items():
                if not future.done():
                    msg = f"{provider}: query timed out after {timeout}s"
                    result.errors[provider] = msg
                    logger.warning("Provider query timed out: %s", provider)
                    future.cancel()

    return result


def _get_fallback_models(provider: str) -> list[DiscoveredModel]:
    """Get models from registry as fallback for a failed provider query.

    Returns DiscoveredModel instances built from the registry's ModelConfig
    data for the given provider. Context window is None (not stored in registry).

    Args:
        provider: Provider name to get fallback models for.

    Returns:
        List of DiscoveredModel instances from registry data.
    """
    fallback: list[DiscoveredModel] = []
    for model_id, mc in registry._models.items():
        if mc.provider == provider:
            fallback.append(
                DiscoveredModel(
                    model_id=mc.model_id,
                    provider=mc.provider,
                    context_window=None,
                    input_price_per_1m=mc.input_price_per_1m,
                    output_price_per_1m=mc.output_price_per_1m,
                )
            )
    return fallback


@dataclass
class RateLimitInfo:
    """Rate limit status from a provider API."""

    provider: str
    limit: int | None = None
    remaining: int | None = None
    reset_time: datetime | None = None
    error: str | None = None

    @property
    def time_until_reset(self) -> str | None:
        """Human-readable time until reset, or None if unknown."""
        if self.reset_time is None:
            return None
        delta = self.reset_time - datetime.now(timezone.utc)
        if delta.total_seconds() <= 0:
            return "now"
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


def lookup_pricing(
    model_id: str,
    provider: str | None = None,
    timeout: float = 5.0,
) -> tuple[float | None, float | None]:
    """Look up model pricing via OpenRouter's public model list.

    OpenRouter exposes pricing for models from all providers (OpenAI,
    Anthropic, Google, etc.) via its public /models endpoint. This
    provides pricing data for providers whose own APIs don't expose it.

    Args:
        model_id: Model identifier (e.g., "gpt-5.1", "claude-sonnet-4-20250514").
        provider: Optional provider hint for building the OpenRouter model ID.
        timeout: HTTP timeout in seconds.

    Returns:
        Tuple of (input_price_per_1m, output_price_per_1m) in USD,
        or (None, None) if pricing not found.
    """
    # Map provider to OpenRouter prefix
    prefix_map = {
        "openai": "openai/",
        "anthropic": "anthropic/",
        "google": "google/",
    }

    # Build candidate IDs to search for (exact, prefixed, and without date pin)
    candidates = [model_id]
    if provider and provider in prefix_map:
        prefixed = prefix_map[provider] + model_id
        candidates.insert(0, prefixed)

    # Also try without date suffix (e.g., claude-sonnet-4-20250514 -> claude-sonnet-4)
    import re
    base = re.sub(r"-\d{8}$", "", model_id)
    if base != model_id:
        candidates.append(base)
        if provider and provider in prefix_map:
            candidates.append(prefix_map[provider] + base)

    try:
        resp = requests.get(
            f"{OPENROUTER_BASE_URL}/models",
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        models_by_id = {m["id"]: m for m in data.get("data", [])}

        for candidate in candidates:
            if candidate in models_by_id:
                pricing = models_by_id[candidate].get("pricing", {})
                prompt_price = pricing.get("prompt")
                completion_price = pricing.get("completion")
                inp = float(prompt_price) * 1_000_000 if prompt_price else None
                out = float(completion_price) * 1_000_000 if completion_price else None
                return (inp, out)

        # Partial match: find models whose ID starts with a candidate
        for candidate in candidates:
            for or_id, or_model in models_by_id.items():
                if or_id.startswith(candidate):
                    pricing = or_model.get("pricing", {})
                    prompt_price = pricing.get("prompt")
                    completion_price = pricing.get("completion")
                    inp = float(prompt_price) * 1_000_000 if prompt_price else None
                    out = float(completion_price) * 1_000_000 if completion_price else None
                    return (inp, out)

        return (None, None)

    except Exception:
        logger.debug("Pricing lookup failed for %s", model_id)
        return (None, None)


_FREE_TIER_DAILY_LIMIT = 50  # OpenRouter free tier: 50 free-model requests/day


def check_openrouter_limits(timeout: float = 5.0) -> RateLimitInfo:
    """Query OpenRouter rate limit and usage via GET /api/v1/auth/key.

    For free tier users, OpenRouter limits free-model requests to 50/day.
    This endpoint returns usage counts and tier info from the response body.

    Args:
        timeout: HTTP timeout in seconds.

    Returns:
        RateLimitInfo with current limit, remaining, and reset time.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return RateLimitInfo(provider="openrouter", error="OPENROUTER_API_KEY not set")

    try:
        resp = requests.get(
            f"{OPENROUTER_BASE_URL}/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        resp.raise_for_status()

        data = resp.json().get("data", {})
        info = RateLimitInfo(provider="openrouter")

        is_free = data.get("is_free_tier", False)
        usage_daily = data.get("usage_daily", 0)

        # Check explicit limit from API
        api_limit = data.get("limit")
        limit_remaining = data.get("limit_remaining")

        if api_limit is not None:
            info.limit = int(api_limit)
            if limit_remaining is not None:
                info.remaining = int(limit_remaining)
            else:
                info.remaining = int(api_limit) - int(usage_daily)
        elif is_free:
            # Free tier has implicit daily limit for free models
            info.limit = _FREE_TIER_DAILY_LIMIT
            info.remaining = max(0, _FREE_TIER_DAILY_LIMIT - int(usage_daily))

        # Parse reset time if provided
        limit_reset = data.get("limit_reset")
        if limit_reset:
            try:
                info.reset_time = datetime.fromisoformat(limit_reset)
            except (ValueError, TypeError):
                pass

        return info

    except Exception as e:
        return RateLimitInfo(provider="openrouter", error=str(e))
