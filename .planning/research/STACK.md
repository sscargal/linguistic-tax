# Stack Research: Configurable Models and Dynamic Pricing

**Domain:** Stack additions for dynamic model config, provider pricing APIs, .env management
**Researched:** 2026-03-25
**Confidence:** HIGH (verified against installed SDK source and live API responses)

## Scope

This research covers ONLY the new libraries and integration patterns needed for milestone v2.0. The existing stack (anthropic, google-genai, openai, statsmodels, scipy, etc.) is validated and not re-researched here. See the original STACK.md commit for baseline stack decisions.

## New Dependencies

### Required Addition

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| python-dotenv | >=1.2.0 | Load `.env` files into `os.environ` | De facto standard for `.env` management in Python. Zero dependencies. The wizard needs to write API keys to `.env` and have them available without manual `export`. Latest is 1.2.2. Simple API: `dotenv_values(".env")` for reading, `set_key(".env", key, val)` for writing. |

### NOT Needed (Existing Dependencies Suffice)

| Capability | Why No New Library |
|---|---|
| Anthropic model listing | `anthropic.Anthropic.models.list()` already in SDK v0.86.0. Returns `ModelInfo` with `id`, `display_name`, `max_tokens`. No pricing -- use fallback table. |
| Google model listing | `genai.Client.models.list()` already in SDK v1.68.0. Returns `Model` with `name`, `displayName`, `inputTokenLimit`, `outputTokenLimit`. No pricing -- use fallback table. |
| OpenAI model listing | `openai.OpenAI.models.list()` already in SDK v2.29.0. Returns model IDs. No pricing -- use fallback table. |
| OpenRouter model listing + pricing | `httpx.get("https://openrouter.ai/api/v1/models")` returns pricing per model. `httpx` v0.28.1 is already a transitive dependency of both `anthropic` and `openai` SDKs. No new install needed. |
| HTTP requests for pricing fallback | `httpx` (transitive, already available) covers any HTTP needs. Do NOT add `requests`. |
| Config file management | `json` stdlib + existing `config_manager.py` handles everything. The config structure just needs new fields, not new serialization. |
| Dataclass extensions | `dataclasses` stdlib. The `models` list field uses standard Python types (`list[dict]`). No need for pydantic or attrs. |

## Installation

```bash
# Single new dependency
uv add "python-dotenv>=1.2.0"
```

That is it. One package.

## Provider Pricing API Analysis

**Critical finding:** None of the three major LLM providers expose pricing via their SDK model-listing endpoints. Only OpenRouter does.

### Anthropic (`client.models.list()`)
- **Returns:** `id`, `display_name`, `created_at`, `max_tokens`, `max_input_tokens`, `capabilities`
- **No pricing fields.** Anthropic publishes pricing on their website only.
- **Strategy:** Use hardcoded PRICE_TABLE as primary source. `models.list()` useful for validation ("does this model ID exist?") and for `propt list-models` display.

### Google (`client.models.list()`)
- **Returns:** `name`, `displayName`, `description`, `inputTokenLimit`, `outputTokenLimit`, `supportedActions`
- **No pricing fields.** Google publishes pricing on their website only.
- **Strategy:** Same as Anthropic -- fallback table, use `models.list()` for validation and listing.

### OpenAI (`client.models.list()`)
- **Returns:** model `id` and metadata. No pricing.
- **Strategy:** Same -- fallback table, use for validation.

### OpenRouter (`GET /api/v1/models`)
- **Returns pricing!** Each model has `pricing.prompt` and `pricing.completion` as strings (USD per token, e.g., `"0.0000002"`).
- **Strategy:** Fetch live pricing from this endpoint. Convert per-token to per-1M-token format to match PRICE_TABLE structure. This is the ONLY provider where live pricing retrieval works.
- **Access:** Use `httpx.get()` directly (already available). No API key required for the models endpoint.

### Recommended Pricing Architecture

```
PRICE_TABLE resolution order:
1. Live API pricing (OpenRouter only -- other providers don't expose it)
2. User config overrides (from experiment_config.json)
3. Hardcoded fallback defaults (current PRICE_TABLE values)
4. $0.00 with warning (truly unknown model)
```

This means the `PRICE_TABLE` dict is no longer a constant -- it becomes a function that merges sources at config load time. The hardcoded values remain as offline fallback for Anthropic, Google, and OpenAI models.

## python-dotenv Integration Pattern

### How It Fits the Existing Code

Currently, API keys are read via `os.environ.get("ANTHROPIC_API_KEY")` throughout the codebase. python-dotenv loads `.env` values INTO `os.environ`, so **no existing code changes are needed** for key retrieval. The integration point is:

1. **On app startup** (in `cli.py` `main()`): Call `load_dotenv()` before any config or API client initialization.
2. **In setup wizard**: When user provides an API key, call `set_key(".env", "ANTHROPIC_API_KEY", value)` to persist it.

```python
# In cli.py main(), add at top:
from dotenv import load_dotenv
load_dotenv()  # Loads .env into os.environ -- existing os.environ.get() calls just work

# In setup_wizard.py, when user provides a key:
from dotenv import set_key
set_key(".env", env_var, user_provided_key)
```

### .env File Safety

- Add `.env` to `.gitignore` (verify it's already there or add it)
- The wizard should create `.env` only when the user provides keys interactively
- Never overwrite existing `.env` values without confirmation

## Config Structure Changes (No New Dependencies)

The `ExperimentConfig` frozen dataclass needs a new `models` field. This uses only stdlib types:

```python
@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single model provider."""
    provider: str           # "anthropic", "google", "openai", "openrouter"
    target_model: str       # e.g., "claude-sonnet-4-20250514"
    preproc_model: str      # e.g., "claude-haiku-4-5-20250514"
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    preproc_input_price_per_1m: float = 0.0
    preproc_output_price_per_1m: float = 0.0
    rate_limit_delay: float = 0.2

@dataclass(frozen=True)
class ExperimentConfig:
    # ... existing fields ...
    models: tuple[ModelConfig, ...] = ()  # New: list of configured models
```

Using a nested frozen dataclass keeps immutability guarantees. Serialization to/from JSON is handled by `dataclasses.asdict()` (already used in config_manager.py) and manual reconstruction.

**JSON representation:**
```json
{
  "models": [
    {
      "provider": "anthropic",
      "target_model": "claude-sonnet-4-20250514",
      "preproc_model": "claude-haiku-4-5-20250514",
      "input_price_per_1m": 3.00,
      "output_price_per_1m": 15.00,
      "preproc_input_price_per_1m": 1.00,
      "preproc_output_price_per_1m": 5.00,
      "rate_limit_delay": 0.2
    }
  ]
}
```

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| python-dotenv | environs | Heavier (wraps marshmallow), adds validation layer we don't need. python-dotenv is dependency-free and does exactly one thing. |
| python-dotenv | Manual `.env` parsing | Fragile. python-dotenv handles quoting, multiline values, comments, export prefixes. Not worth reimplementing. |
| Hardcoded pricing fallback | Scraping provider pricing pages | Fragile, breaks on HTML changes, violates ToS. The three providers that don't expose API pricing update prices rarely -- manual fallback table is fine. |
| httpx for OpenRouter pricing | `requests` | httpx is already installed (transitive dep). Adding `requests` means two HTTP libraries for no benefit. |
| Nested dataclass for ModelConfig | Plain dict | Dataclass gives type safety, IDE autocomplete, and `asdict()` serialization. Worth the small added structure. |
| Nested dataclass for ModelConfig | pydantic BaseModel | Adds a heavy dependency for a simple config object. stdlib dataclasses are sufficient. Project already uses dataclasses throughout. |
| `tuple[ModelConfig, ...]` field | `list[ModelConfig]` | ExperimentConfig is frozen. Tuples are immutable, lists are not. Using tuple maintains the frozen contract. |

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| `litellm` | Unified LLM API wrapper. Adds ~50 transitive dependencies, abstracts away provider-specific behavior we need to measure. | Keep direct SDK calls per provider. |
| `pydantic` | Config validation library. Overkill for this project's simple config. Adds large dependency tree. | Use stdlib dataclasses + manual validation in `validate_config()`. |
| `requests` | HTTP library. `httpx` is already available as transitive dependency. | Use `httpx` for the one HTTP call needed (OpenRouter pricing). |
| `dynaconf` / `omegaconf` | Config management libraries. Add complexity for a project that stores config in one JSON file. | Keep existing `config_manager.py` pattern with JSON + dataclass. |
| `keyring` | System keychain integration for secrets. Over-engineered for a single-researcher CLI tool. | `.env` file via python-dotenv. |
| Any caching library | For pricing data. Pricing changes rarely and is fetched once at setup/list-models time. | Simple dict in memory during the session. No persistence needed beyond the config file. |

## Integration Points

### Where New Code Touches Existing Code

| Existing File | Change Type | What Changes |
|---|---|---|
| `src/config.py` | **Extend** | Add `ModelConfig` dataclass. Add `models` field to `ExperimentConfig`. Keep flat fields for backward compat. Add `build_price_table()` function that derives PRICE_TABLE from config. |
| `src/config_manager.py` | **Extend** | `load_config()` needs to deserialize `models` list into `ModelConfig` tuples. `validate_config()` changes model validation from "reject unknown" to "warn unknown". |
| `src/setup_wizard.py` | **Major rewrite** | Multi-provider flow, free-text model entry, API key collection with `.env` writing, budget estimation display. |
| `src/cli.py` | **Minor** | Add `load_dotenv()` call at startup. Enhance `list-models` subcommand to query live APIs. |
| `src/run_experiment.py` | **Minor** | Derive MODELS tuple from config instead of importing constant. |
| `pyproject.toml` | **Add dependency** | Add `python-dotenv>=1.2.0`. |
| `.gitignore` | **Verify/add** | Ensure `.env` is listed. |

### What Does NOT Change

- API client code (anthropic, google-genai, openai SDKs) -- same call patterns
- Grading modules -- model-agnostic
- Analysis modules -- model-agnostic
- Noise generation -- model-agnostic
- Database schema -- already stores model name as string

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| python-dotenv 1.2.2 | Python >=3.9 | Zero dependencies. No conflicts possible. |
| anthropic 0.86.0 `models.list()` | Any anthropic >=0.40.0 | Models API has been stable since early SDK versions. |
| google-genai 1.68.0 `models.list()` | Any google-genai >=1.0.0 | Core SDK feature, stable. |
| openai 2.29.0 `models.list()` | Any openai >=1.0.0 | Stable since v1 rewrite. |
| httpx 0.28.1 | Already installed | Transitive dep of anthropic + openai. Do NOT pin explicitly -- let SDK manage it. |

## Sources

- Anthropic SDK v0.86.0 `ModelInfo` schema: verified via `anthropic.types.ModelInfo.model_json_schema()` -- fields: id, display_name, created_at, max_tokens, max_input_tokens, capabilities. **No pricing.**
- Google genai SDK v1.68.0 `Model` schema: verified via `types.Model.model_json_schema()` -- fields: name, displayName, inputTokenLimit, outputTokenLimit, etc. **No pricing.**
- OpenAI SDK v2.29.0 `models.list()`: verified via `dir(client.models)` -- standard list/retrieve. **No pricing.**
- OpenRouter `/api/v1/models` endpoint: verified via live HTTP call -- returns `pricing.prompt` and `pricing.completion` per model as USD-per-token strings.
- python-dotenv: latest version 1.2.2 confirmed via `uv pip install --dry-run python-dotenv`.
- httpx 0.28.1: confirmed installed as transitive dependency via `uv pip show httpx`.

---
*Stack research for: Configurable Models and Dynamic Pricing milestone*
*Researched: 2026-03-25*
