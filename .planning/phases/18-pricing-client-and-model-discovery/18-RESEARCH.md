# Phase 18: Pricing Client and Model Discovery - Research

**Researched:** 2026-03-26
**Domain:** Provider SDK model listing APIs, OpenRouter pricing, CLI table output
**Confidence:** HIGH

## Summary

This phase enhances `propt list-models` to query live model availability from all 4 configured providers (Anthropic, Google, OpenAI, OpenRouter) and display model IDs, context windows, and pricing. The SDKs for all 4 providers are already installed and imported in the project. Each provider's `models.list()` returns different metadata -- Anthropic and Google include context window sizes, OpenAI does not, and only OpenRouter exposes pricing via its API. The project already uses `tabulate` for CLI table output and has established patterns for `--format json` flags.

The main implementation work is: (1) a model discovery module with per-provider query functions behind a shared interface, (2) parallel execution via `concurrent.futures.ThreadPoolExecutor`, (3) enhancing `handle_list_models()` in `config_commands.py` to merge live data with registry fallback data, and (4) adding `--json` flag to the `list-models` argparse subcommand.

**Primary recommendation:** Create a new `src/model_discovery.py` module with a `query_provider(provider: str) -> list[DiscoveredModel]` function per provider, a `discover_all_models()` orchestrator using ThreadPoolExecutor, and integrate results into `handle_list_models()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Query all 4 configured providers (Anthropic, Google, OpenAI, OpenRouter) for live model listing
- Use each provider's SDK `models.list()` endpoint where available; HTTP GET for OpenRouter `/api/v1/models`
- Show ALL available models from each provider, with configured models marked/highlighted
- Query providers in parallel (threading or asyncio) for faster CLI response
- Columns: Model ID, Provider, Context Window, Input Price (per 1M tokens), Output Price (per 1M tokens), Status (configured/available)
- Group output by provider with provider headers
- Pricing format: `$X.XX / $Y.YY` per 1M tokens, `free` for zero-cost, `--` for unknown
- Add `--json` flag for programmatic JSON output (consistent with existing `--format json`)
- When provider API unreachable: show fallback pricing from registry with `fallback` indicator, log warning
- 5-second timeout per provider API query
- Missing API keys: warn that provider was skipped, do not crash
- Live pricing is display-only -- does NOT update registry or config
- No caching of live pricing across invocations

### Claude's Discretion
- Internal implementation of provider query abstraction (shared interface vs per-provider functions)
- Threading vs asyncio for parallel queries
- Exact table formatting and column widths
- How to detect and parse context window from each provider's response schema

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSC-01 | `propt list-models` queries live models from each configured provider's API | All 4 provider SDKs verified to have `models.list()` or equivalent endpoint; see Provider API Details section |
| DSC-02 | `propt list-models` displays model ID, context window, and pricing (where available) | Context window available from Anthropic (`max_input_tokens`), Google (`input_token_limit`), OpenRouter (`context_length`); NOT from OpenAI. Pricing only from OpenRouter (`pricing.prompt`, `pricing.completion`) |
| PRC-02 | OpenRouter live pricing is fetched via its `/api/v1/models` endpoint | OpenRouter schema verified: `pricing.prompt` and `pricing.completion` are strings in USD per token; multiply by 1,000,000 for per-1M display |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.84.0 | Anthropic SDK `client.models.list()` | Already in project, provides ModelInfo with context window |
| google-genai | 1.45.0 | Google GenAI SDK `client.models.list()` | Already in project, provides Model with token limits |
| openai | 2.29.0 | OpenAI SDK `client.models.list()` | Already in project, provides model IDs (no context window) |
| requests | 2.33.0 | HTTP GET for OpenRouter `/api/v1/models` | Already available as transitive dep; simpler than using openai SDK with base_url override for listing |
| tabulate | 0.10.0 | CLI table formatting | Already used throughout config_commands.py |
| concurrent.futures | stdlib | ThreadPoolExecutor for parallel queries | Simpler than asyncio for this use case (sync SDK calls) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | asyncio | All provider SDKs have sync clients already initialized; ThreadPoolExecutor is simpler for wrapping sync calls. asyncio would require async clients or run_in_executor anyway. |
| requests for OpenRouter | openai SDK with base_url | Could reuse openai SDK but its `models.list()` response lacks OpenRouter-specific pricing fields. Direct HTTP GET is cleaner. |

**Installation:** No new dependencies needed. All libraries already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  model_discovery.py     # NEW: provider query functions + discover_all_models()
  config_commands.py     # MODIFIED: enhanced handle_list_models()
  cli.py                 # MODIFIED: add --json flag to list-models
  model_registry.py      # READ-ONLY: fallback data source (no changes needed)
```

### Pattern 1: Provider Query Abstraction
**What:** A `DiscoveredModel` dataclass returned by all provider query functions, plus per-provider `_query_<provider>()` functions with a shared signature.
**When to use:** Each provider returns different schemas but we need uniform output.
**Example:**
```python
from dataclasses import dataclass

@dataclass
class DiscoveredModel:
    """A model discovered from a provider API."""
    model_id: str
    provider: str
    context_window: int | None  # None if provider doesn't expose it
    input_price_per_1m: float | None  # None if provider doesn't expose pricing
    output_price_per_1m: float | None


def _query_anthropic(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query Anthropic API for available models."""
    import anthropic
    client = anthropic.Anthropic(timeout=timeout)
    models = []
    # Paginate through all models
    page = client.models.list(limit=100)
    for model_info in page.data:
        models.append(DiscoveredModel(
            model_id=model_info.id,
            provider="anthropic",
            context_window=model_info.max_input_tokens,
            input_price_per_1m=None,   # Anthropic doesn't expose pricing via API
            output_price_per_1m=None,
        ))
    # Handle pagination if needed
    while page.has_more:
        page = client.models.list(limit=100, after_id=page.last_id)
        for model_info in page.data:
            models.append(DiscoveredModel(
                model_id=model_info.id,
                provider="anthropic",
                context_window=model_info.max_input_tokens,
                input_price_per_1m=None,
                output_price_per_1m=None,
            ))
    return models
```

### Pattern 2: Parallel Query with ThreadPoolExecutor
**What:** Query all providers concurrently with 5-second timeout, collect results + errors.
**When to use:** Always -- user decision to query in parallel.
**Example:**
```python
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

_PROVIDER_QUERY_MAP = {
    "anthropic": _query_anthropic,
    "google": _query_google,
    "openai": _query_openai,
    "openrouter": _query_openrouter,
}

@dataclass
class DiscoveryResult:
    """Result from querying all providers."""
    models: dict[str, list[DiscoveredModel]]  # provider -> models
    errors: dict[str, str]  # provider -> error message

def discover_all_models(timeout: float = 5.0) -> DiscoveryResult:
    """Query all providers for available models in parallel."""
    from src.model_registry import registry, _PROVIDER_KEY_MAP
    import os

    result = DiscoveryResult(models={}, errors={})
    providers_to_query = []

    for provider, query_fn in _PROVIDER_QUERY_MAP.items():
        key_name = _PROVIDER_KEY_MAP.get(provider, "")
        if not os.environ.get(key_name, ""):
            result.errors[provider] = f"Skipping {provider}: {key_name} not set"
            continue
        providers_to_query.append((provider, query_fn))

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fn, timeout): provider
            for provider, fn in providers_to_query
        }
        for future in as_completed(futures):
            provider = futures[future]
            try:
                result.models[provider] = future.result()
            except Exception as e:
                result.errors[provider] = f"{provider}: {e}"

    return result
```

### Pattern 3: Fallback Merge
**What:** When a provider query fails, show registry-known models for that provider with `fallback` status indicator.
**When to use:** Any provider error or timeout.
**Example:**
```python
def _get_fallback_models(provider: str) -> list[DiscoveredModel]:
    """Get models from registry as fallback for a failed provider query."""
    from src.model_registry import registry
    fallback = []
    for model_id, mc in registry._models.items():
        if mc.provider == provider:
            fallback.append(DiscoveredModel(
                model_id=mc.model_id,
                provider=mc.provider,
                context_window=None,
                input_price_per_1m=mc.input_price_per_1m,
                output_price_per_1m=mc.output_price_per_1m,
            ))
    return fallback
```

### Anti-Patterns to Avoid
- **Modifying registry data:** Live pricing is display-only. Never call `registry.reload()` or update `ModelConfig` instances with live data.
- **Using openai SDK for OpenRouter model listing:** The openai SDK's `Model` type lacks pricing and context_length fields. Use direct HTTP GET for OpenRouter.
- **Blocking on individual provider failures:** Use ThreadPoolExecutor with timeout, not sequential calls. A single slow provider should not block the others.
- **Catching broad exceptions silently:** Catch specific exceptions (httpx.TimeoutException, requests.Timeout, APIError variants) and log meaningful messages.

## Provider API Details

### Anthropic (HIGH confidence -- verified from installed SDK)
- **SDK:** `anthropic.Anthropic(timeout=5.0).models.list(limit=100)`
- **Returns:** `SyncPage[ModelInfo]` with pagination (`has_more`, `last_id`)
- **Fields available:** `id` (str), `display_name` (str), `max_input_tokens` (int|None), `max_tokens` (int|None), `created_at` (datetime), `capabilities` (optional)
- **Context window:** `max_input_tokens` -- this IS the context window
- **Pricing:** NOT available via API (confirmed by REQUIREMENTS.md Out of Scope)
- **Timeout:** Pass `timeout=5.0` to `Anthropic()` constructor

### Google GenAI (HIGH confidence -- verified from installed SDK)
- **SDK:** `genai.Client(api_key=key).models.list()`
- **Returns:** `Pager[Model]` (iterable)
- **Fields available:** `name` (str, format: "models/gemini-1.5-pro"), `display_name`, `input_token_limit` (int|None), `output_token_limit` (int|None), `description`, `version`
- **Context window:** `input_token_limit`
- **Model ID parsing:** `name` field returns "models/gemini-1.5-pro" -- strip "models/" prefix to get usable model ID
- **Pricing:** NOT available via API
- **Timeout:** Use `httpx_client` with timeout or wrap in ThreadPoolExecutor timeout

### OpenAI (HIGH confidence -- verified from installed SDK)
- **SDK:** `openai.OpenAI(api_key=key, timeout=5.0).models.list()`
- **Returns:** `SyncPage[Model]`
- **Fields available:** `id` (str), `created` (int), `owned_by` (str), `object` (literal "model")
- **Context window:** NOT available via models.list API
- **Pricing:** NOT available via API
- **Note:** OpenAI's models.list returns ALL models including embeddings, TTS, DALL-E, etc. May want to show all and let users identify relevant ones, or filter to chat-capable models (models with "gpt" or "o1" or "o3" in ID)

### OpenRouter (HIGH confidence -- verified via official docs)
- **Endpoint:** `GET https://openrouter.ai/api/v1/models`
- **Auth:** `Authorization: Bearer $OPENROUTER_API_KEY`
- **Returns:** JSON `{"data": [...]}`
- **Fields available:** `id` (str), `name` (str), `context_length` (int), `pricing.prompt` (str, USD per token), `pricing.completion` (str, USD per token), `architecture.modality`, `top_provider.max_completion_tokens`
- **Context window:** `context_length` field
- **Pricing:** `pricing.prompt` and `pricing.completion` are STRINGS in USD per-token. Convert: `float(pricing["prompt"]) * 1_000_000` for per-1M display
- **Free models:** pricing values will be "0" (string)
- **No auth required for listing** (but include key if available for rate limits)
- **Timeout:** `requests.get(..., timeout=5.0)`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table formatting | Custom string alignment | `tabulate` library | Already used project-wide; handles column alignment, headers, unicode |
| HTTP requests | urllib/socket code | `requests` library | Already available; handles encoding, timeouts, errors cleanly |
| Parallel execution | Manual threading | `concurrent.futures.ThreadPoolExecutor` | Clean API, handles worker lifecycle, exception propagation |
| SDK pagination | Manual HTTP page-following | SDK built-in pagination (Anthropic `has_more`/`last_id`, Google `Pager`) | SDKs handle auth and pagination automatically |

## Common Pitfalls

### Pitfall 1: OpenRouter pricing is per-token strings, not per-1M floats
**What goes wrong:** Displaying raw OpenRouter pricing values gives nonsensically small numbers.
**Why it happens:** OpenRouter returns pricing as string values in USD per single token (e.g., "0.000003" for $3/1M).
**How to avoid:** Parse as float, multiply by 1,000,000 to convert to per-1M format matching other display values.
**Warning signs:** Prices showing as "$0.00" for models that should cost money.

### Pitfall 2: Google GenAI model name includes "models/" prefix
**What goes wrong:** Model IDs display as "models/gemini-1.5-pro" instead of "gemini-1.5-pro".
**Why it happens:** Google's API returns the full resource path in the `name` field.
**How to avoid:** Strip the "models/" prefix: `model.name.removeprefix("models/")`.
**Warning signs:** Model IDs in output don't match what users would pass to `--model`.

### Pitfall 3: OpenAI models.list returns non-chat models
**What goes wrong:** Output is cluttered with embedding models, TTS, DALL-E, whisper, etc.
**Why it happens:** OpenAI's models endpoint returns ALL model types.
**How to avoid:** Either show all (aids discovery per user decision) or optionally filter. Since the user decided "show ALL available models," include all but consider adding the `owned_by` field to help users distinguish.
**Warning signs:** Hundreds of irrelevant models in output.

### Pitfall 4: Anthropic pagination
**What goes wrong:** Only first page of models shown.
**Why it happens:** `models.list()` returns a paginated `SyncPage`. Must check `has_more` and use `after_id` to get subsequent pages.
**How to avoid:** Loop while `page.has_more`, passing `after_id=page.last_id`.
**Warning signs:** Missing models that are known to exist.

### Pitfall 5: Thread timeout vs SDK timeout
**What goes wrong:** Thread hangs past 5 seconds despite setting SDK timeout.
**Why it happens:** Not all SDKs handle timeout the same way. Google GenAI may not have a simple timeout parameter.
**How to avoid:** Use ThreadPoolExecutor with `future.result(timeout=5.0)` as the outer timeout guarantee, AND set SDK-level timeouts where supported.
**Warning signs:** CLI hangs when a provider is slow.

### Pitfall 6: Missing API key causes SDK initialization error
**What goes wrong:** Creating an SDK client without a valid API key throws immediately.
**Why it happens:** SDKs validate key presence at client construction time.
**How to avoid:** Check `registry.check_provider(provider)` BEFORE constructing the SDK client. Skip providers with missing keys.
**Warning signs:** Unhandled exception on client construction.

## Code Examples

### OpenRouter HTTP query
```python
import requests
import os
import logging

logger = logging.getLogger(__name__)

def _query_openrouter(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query OpenRouter API for available models with pricing."""
    from src.config import OPENROUTER_BASE_URL

    headers = {}
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

    models = []
    for item in data.get("data", []):
        pricing = item.get("pricing", {})
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")

        input_per_1m = float(prompt_price) * 1_000_000 if prompt_price else None
        output_per_1m = float(completion_price) * 1_000_000 if completion_price else None

        models.append(DiscoveredModel(
            model_id=item["id"],
            provider="openrouter",
            context_window=item.get("context_length"),
            input_price_per_1m=input_per_1m,
            output_price_per_1m=output_per_1m,
        ))
    return models
```

### Google GenAI query with name prefix stripping
```python
def _query_google(timeout: float = 5.0) -> list[DiscoveredModel]:
    """Query Google GenAI API for available models."""
    from google import genai
    import os

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    models = []
    for model in client.models.list():
        model_id = (model.name or "").removeprefix("models/")
        if not model_id:
            continue
        models.append(DiscoveredModel(
            model_id=model_id,
            provider="google",
            context_window=model.input_token_limit,
            input_price_per_1m=None,
            output_price_per_1m=None,
        ))
    return models
```

### Enhanced handle_list_models with fallback merge
```python
def handle_list_models(args: Any) -> None:
    """List available models from live provider APIs with fallback to registry."""
    from src.model_discovery import discover_all_models, _get_fallback_models

    result = discover_all_models(timeout=5.0)

    # Log errors/warnings
    for provider, error_msg in result.errors.items():
        logger.warning(error_msg)

    # Build rows grouped by provider
    configured_ids = set(registry._models.keys())
    provider_order = ["anthropic", "google", "openai", "openrouter"]

    all_rows = {}
    for provider in provider_order:
        if provider in result.models:
            rows = _build_rows(result.models[provider], configured_ids, source="live")
        elif provider in result.errors:
            fallback = _get_fallback_models(provider)
            rows = _build_rows(fallback, configured_ids, source="fallback")
        else:
            continue
        all_rows[provider] = rows

    if hasattr(args, "json") and args.json:
        # JSON output
        print(json.dumps(all_rows, indent=2))
    else:
        # Table output grouped by provider
        for provider, rows in all_rows.items():
            print(f"\n{provider.upper()}")
            print(tabulate(rows, headers=[...], tablefmt="simple"))
```

### Pricing format helper
```python
def _format_price(input_per_1m: float | None, output_per_1m: float | None) -> str:
    """Format pricing for display."""
    if input_per_1m is None and output_per_1m is None:
        return "--"
    inp = input_per_1m or 0.0
    out = output_per_1m or 0.0
    if inp == 0.0 and out == 0.0:
        return "free"
    return f"${inp:.2f} / ${out:.2f}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static model list from registry | Live API queries + registry fallback | Phase 18 | Users discover all available models, not just curated defaults |
| No context window display | Context window from 3 of 4 providers | Phase 18 | Users can see model capacity before selecting |
| No live pricing | OpenRouter pricing via API | Phase 18 | Accurate OpenRouter pricing without manual curation |

**Provider pricing availability (confirmed):**
- Anthropic: NO pricing API (only model listing with capabilities)
- Google: NO pricing API (only model listing with token limits)
- OpenAI: NO pricing API (minimal model listing -- id and owned_by only)
- OpenRouter: YES -- full pricing via `/api/v1/models`

## Open Questions

1. **OpenAI model filtering**
   - What we know: OpenAI returns ALL model types (chat, embedding, TTS, image, etc.)
   - What's unclear: Whether to show ALL or filter to chat-relevant models
   - Recommendation: Show all per user's "show ALL available models" decision. Users can visually identify relevant ones. The `--json` flag enables programmatic filtering.

2. **Google GenAI timeout handling**
   - What we know: `genai.Client` doesn't have a simple timeout parameter on `models.list()`
   - What's unclear: Best way to enforce 5-second timeout on the Pager iteration
   - Recommendation: Rely on ThreadPoolExecutor's `future.result(timeout=5.0)` as the outer enforcement. This is reliable regardless of SDK internals.

3. **OpenRouter response size**
   - What we know: OpenRouter has 400+ models. Response could be large.
   - What's unclear: Exact response size and whether it fits within 5-second timeout on slow connections
   - Recommendation: 5-second timeout is generous for a single HTTP GET. If it times out, fallback kicks in gracefully.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_model_discovery.py tests/test_config_commands.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DSC-01 | list-models queries each provider API | unit (mocked) | `pytest tests/test_model_discovery.py::test_query_each_provider -x` | No -- Wave 0 |
| DSC-02 | Output includes model ID, context window, pricing columns | unit | `pytest tests/test_config_commands.py::test_list_models_columns -x` | No -- Wave 0 |
| PRC-02 | OpenRouter pricing fetched and parsed correctly | unit | `pytest tests/test_model_discovery.py::test_openrouter_pricing_parse -x` | No -- Wave 0 |

### Additional test scenarios
| Scenario | Test Type | Command |
|----------|-----------|---------|
| Provider timeout produces fallback | unit (mocked) | `pytest tests/test_model_discovery.py::test_provider_timeout_fallback -x` |
| Missing API key skips provider | unit | `pytest tests/test_model_discovery.py::test_missing_api_key_skip -x` |
| --json flag produces valid JSON | unit | `pytest tests/test_config_commands.py::test_list_models_json -x` |
| Google model name prefix stripped | unit | `pytest tests/test_model_discovery.py::test_google_name_prefix -x` |
| OpenRouter per-token to per-1M conversion | unit | `pytest tests/test_model_discovery.py::test_openrouter_price_conversion -x` |

### Sampling Rate
- **Per task commit:** `pytest tests/test_model_discovery.py tests/test_config_commands.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_model_discovery.py` -- NEW file covering DSC-01, DSC-02, PRC-02, all provider query functions
- [ ] Mock fixtures for provider SDK responses (anthropic ModelInfo, google Model, openai Model, openrouter JSON)

## Sources

### Primary (HIGH confidence)
- Anthropic SDK v0.84.0 -- `ModelInfo` fields verified from installed package: id, max_input_tokens, max_tokens, display_name, capabilities
- Google GenAI SDK v1.45.0 -- `Model` fields verified from installed package: name, input_token_limit, output_token_limit
- OpenAI SDK v2.29.0 -- `Model` fields verified from installed package: id, created, owned_by (NO context window or pricing)
- OpenRouter API docs (https://openrouter.ai/docs/api/api-reference/models/get-models) -- response schema with pricing.prompt, pricing.completion as strings per-token, context_length as int

### Secondary (MEDIUM confidence)
- OpenRouter pricing field format (strings vs floats) -- verified via official docs page

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified
- Architecture: HIGH -- SDK APIs inspected directly from installed packages
- Provider APIs: HIGH for Anthropic/Google/OpenAI (SDK introspection), HIGH for OpenRouter (official docs)
- Pitfalls: HIGH -- derived from verified SDK field inspection

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (SDKs are stable; provider APIs rarely change listing endpoints)
