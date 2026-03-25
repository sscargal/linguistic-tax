# Architecture Research: Configurable Models and Dynamic Pricing

**Domain:** Python CLI research toolkit -- extending hardcoded model config to dynamic, user-configurable model selection with live pricing
**Researched:** 2026-03-25
**Confidence:** HIGH (based on direct codebase analysis and SDK introspection)

## System Overview: Current State

```
                         CLI Layer (cli.py)
                              |
            +-----------------+-----------------+
            |                 |                 |
    setup_wizard.py    config_commands.py   run/pilot
            |                 |                 |
            +--------+--------+        +--------+--------+
                     |                 |                  |
              config_manager.py   run_experiment.py   execution_summary.py
                     |                 |                  |
              config.py (constants)    |           PRICE_TABLE (hardcoded)
              - MODELS tuple           |           PREPROC_MODEL_MAP
              - PRICE_TABLE dict       |           RATE_LIMIT_DELAYS
              - PREPROC_MODEL_MAP      |
              - RATE_LIMIT_DELAYS      |
              - ExperimentConfig       |
                                       |
                     +-----------------+--------+
                     |                          |
              api_client.py            prompt_compressor.py
              (prefix-based routing)   (PREPROC_MODEL_MAP lookup)
```

**Key problem:** Six module-level dicts/tuples in `config.py` are hardcoded. Every consumer imports them at module load time. There is no mechanism to override them from user config.

### Component Responsibilities (Current)

| Component | Responsibility | What It Imports from config.py |
|-----------|----------------|-------------------------------|
| `config.py` | Hardcoded constants + ExperimentConfig dataclass | N/A (source of truth) |
| `config_manager.py` | JSON persistence, sparse override merging, validation | `ExperimentConfig`, `PRICE_TABLE` |
| `setup_wizard.py` | Interactive provider/model/key setup | `MODELS`, `OPENROUTER_BASE_URL`, `PREPROC_MODEL_MAP` |
| `config_commands.py` | CLI show/set/reset/diff/list-models | `ExperimentConfig`, `PRICE_TABLE` |
| `api_client.py` | LLM API calls with retry/rate limiting | `OPENROUTER_BASE_URL`, `RATE_LIMIT_DELAYS` |
| `execution_summary.py` | Cost/runtime estimation, confirmation gate | `PRICE_TABLE`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`, `compute_cost` |
| `run_experiment.py` | Experiment execution engine | `ExperimentConfig`, `MAX_TOKENS_BY_BENCHMARK`, `PREPROC_MODEL_MAP`, `compute_cost` |
| `prompt_compressor.py` | Pre-processing interventions | `PREPROC_MODEL_MAP` |
| `pilot.py` | Pilot validation run | `ExperimentConfig`, `MODELS` |
| `scripts/generate_matrix.py` | Experiment matrix generation | `INTERVENTIONS`, `MODELS`, `NOISE_TYPES` |
| `compute_derived.py` | Derived metrics | `INTERVENTIONS`, `MODELS`, `NOISE_TYPES` |

## Recommended Architecture: Target State

### Core Design Decision: ModelConfig Registry

Introduce a `ModelConfig` dataclass and a `ModelRegistry` that replaces all six hardcoded dicts/tuples. The registry is built from config at load time, not at import time.

```
                         CLI Layer (cli.py)
                              |
            +-----------------+-----------------+
            |                 |                 |
    setup_wizard.py    config_commands.py   run/pilot
     (free-text entry)  (list-models live)      |
            |                 |                 |
            +--------+--------+        +--------+--------+
                     |                 |                  |
              config_manager.py   run_experiment.py   execution_summary.py
                     |                 |                  |
              config.py                |           model_registry.get_price()
              - ExperimentConfig       |           model_registry.get_preproc()
              - ModelConfig dataclass   |           model_registry.get_delay()
              - ModelRegistry class    |
              - FALLBACK_* defaults    |
                     |                 |
         +----------+----------+      |
         |                     |      |
   pricing_client.py    env_manager.py |
   (per-provider APIs)  (.env I/O)    |
                                      |
                     +----------------+--------+
                     |                         |
              api_client.py           prompt_compressor.py
              (registry-based routing) (registry.get_preproc())
```

### New Components

#### 1. `ModelConfig` dataclass (in `config.py`)

```python
@dataclass
class ModelConfig:
    """Single model configuration entry."""
    provider: str           # "anthropic" | "google" | "openai" | "openrouter"
    model_id: str           # e.g. "claude-sonnet-4-20250514"
    preproc_model_id: str   # e.g. "claude-haiku-4-5-20250514"
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    preproc_input_price_per_1m: float = 0.0
    preproc_output_price_per_1m: float = 0.0
    rate_limit_delay: float = 0.2
    preproc_rate_limit_delay: float = 0.1
```

**Rationale:** Bundles all per-model data (pricing, preproc mapping, rate limits) into one object. Eliminates the need for four parallel dicts that must stay in sync.

#### 2. `ModelRegistry` class (in `config.py`)

```python
class ModelRegistry:
    """Runtime registry of configured models, built from config."""

    def __init__(self, model_configs: list[ModelConfig]) -> None:
        self._models: dict[str, ModelConfig] = {mc.model_id: mc for mc in model_configs}

    @classmethod
    def from_config(cls, config: ExperimentConfig) -> "ModelRegistry":
        """Build registry from an ExperimentConfig's models list."""
        ...

    @classmethod
    def defaults(cls) -> "ModelRegistry":
        """Build registry with current hardcoded defaults (backward compat)."""
        ...

    def get_models(self) -> tuple[str, ...]:
        """Replace MODELS tuple."""
        ...

    def get_price(self, model_id: str) -> dict[str, float]:
        """Replace PRICE_TABLE[model] with fallback to $0.00."""
        ...

    def get_preproc(self, model_id: str) -> str:
        """Replace PREPROC_MODEL_MAP[model] with KeyError -> ValueError."""
        ...

    def get_delay(self, model_id: str) -> float:
        """Replace RATE_LIMIT_DELAYS.get(model, 0.2)."""
        ...

    def compute_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Replace standalone compute_cost() with fallback for unknown models."""
        ...
```

**Rationale:** Single source of truth for all model-related lookups. Consumers receive a registry instance rather than importing module-level dicts. The `from_config` classmethod bridges the ExperimentConfig -> runtime lookup gap.

#### 3. `src/pricing_client.py` (NEW file)

```python
"""Per-provider pricing fetcher with offline fallback."""

def fetch_anthropic_pricing() -> dict[str, dict[str, float]]:
    """Query Anthropic models.list() -- no pricing in API, return empty."""
    # Anthropic ModelInfo has: id, display_name, max_input_tokens, max_tokens
    # NO pricing fields. Return model IDs only for validation.
    ...

def fetch_openai_pricing() -> dict[str, dict[str, float]]:
    """Query OpenAI models.list() -- no pricing in API, return empty."""
    # OpenAI Model has: id, created, object, owned_by
    # NO pricing fields. Return model IDs only for validation.
    ...

def fetch_google_models() -> list[str]:
    """Query google.genai.Client().models.list() for model IDs."""
    # Google models.list() returns model metadata but no pricing.
    ...

def fetch_openrouter_pricing() -> dict[str, dict[str, float]]:
    """Query OpenRouter /api/v1/models -- HAS pricing in response."""
    # OpenRouter is the ONLY provider that returns pricing via API.
    # JSON response includes `pricing.prompt` and `pricing.completion`
    # per-token (not per-1M). Multiply by 1_000_000.
    ...

def fetch_pricing(provider: str, api_key: str) -> dict[str, dict[str, float]]:
    """Unified entry point. Returns {model_id: {input_per_1m, output_per_1m}}."""
    ...

def list_provider_models(provider: str, api_key: str) -> list[str]:
    """List available model IDs from a provider's API."""
    ...
```

**Critical finding from SDK introspection:**
- **Anthropic SDK** (`anthropic==0.86.0`): `client.models.list()` returns `ModelInfo` with `id`, `display_name`, `max_input_tokens`, `max_tokens`, `capabilities`. **No pricing fields.**
- **OpenAI SDK** (`openai==2.29.0`): `client.models.list()` returns `Model` with `id`, `created`, `object`, `owned_by`. **No pricing fields.**
- **Google GenAI SDK**: `client.models.list()` returns model metadata. **No pricing fields.**
- **OpenRouter**: Uses OpenAI SDK with base_url override. The standard SDK `Model` type lacks pricing, but the raw `/api/v1/models` JSON response includes `pricing.prompt` and `pricing.completion`. Must use `httpx`/`requests` or parse raw response.

**Implication:** Live pricing is only available from OpenRouter. For the other three providers, the PRICE_TABLE fallback defaults are the primary pricing source. The `propt list-models` command can show model availability (via API) but pricing must come from hardcoded fallbacks for Anthropic, Google, and OpenAI.

#### 4. `src/env_manager.py` (NEW file)

```python
"""Manages .env file creation and API key storage."""

from pathlib import Path

def load_dotenv(env_path: Path | None = None) -> None:
    """Load .env file into os.environ. No-op if file missing."""
    ...

def set_env_var(key: str, value: str, env_path: Path | None = None) -> None:
    """Write or update a key=value pair in the .env file."""
    ...

def get_env_path() -> Path:
    """Return project root .env path."""
    ...
```

**Dependency decision:** Use `python-dotenv` (add to dependencies). It is the standard library for this and avoids reimplementing .env parsing. Current project does NOT have it installed.

**Alternative considered:** Manual file I/O. Rejected because .env files have edge cases (quoting, multiline, comments, export prefixes) that python-dotenv handles correctly.

### Modified Components

#### 5. `ExperimentConfig` (MODIFIED in `config.py`)

Add a `models` field:

```python
@dataclass(frozen=True)
class ExperimentConfig:
    # ... existing fields unchanged for backward compat ...
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-1.5-pro"
    openai_model: str = "gpt-4o-2024-11-20"
    openrouter_model: str = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_preproc_model: str = "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"

    # NEW: structured model configurations (source of truth when present)
    models: tuple[dict, ...] = ()  # Serialized ModelConfig entries
```

**Backward compatibility strategy:** When `models` is empty (default), the old flat fields are used to build the registry. When `models` is populated, it is the source of truth and flat fields are ignored. This means existing config files continue to work.

#### 6. `config_manager.py` (MODIFIED)

- **`validate_config()`**: Change model validation from "must be in PRICE_TABLE" (hard error) to "warn if not in fallback defaults" (warning only). This is the single most critical change for supporting free-text model entry.
- **`load_config()`**: Handle new `models` list field (list of dicts -> tuple of dicts for frozen dataclass).
- **`save_config()`**: Serialize `models` field properly.

#### 7. `setup_wizard.py` (MODIFIED -- heaviest changes)

- **Provider selection**: Keep pick-one-first flow, then offer "Add another provider?"
- **Model entry**: Show defaults but accept free-text. Validate by pinging API.
- **Preproc model**: Explain what it is ("A cheap/fast model used for sanitize/compress pre-processing. It cleans up prompts before sending to the target model.").
- **API key handling**: If env var not set, prompt for key, write to `.env` via `env_manager.py`.
- **Budget display**: After model selection, show estimated experiment cost using pricing data.
- **Build `models` list**: Construct the structured model config entries.

#### 8. `config_commands.py` (MODIFIED)

- **`handle_list_models()`**: Query live provider APIs for available models + pricing. Show both configured models and available-but-not-configured models.

#### 9. `api_client.py` (MODIFIED)

- **`_apply_rate_limit()`**: Use registry instead of `RATE_LIMIT_DELAYS` dict.
- **`call_model()` routing**: The current prefix-based routing (`model.startswith("claude")`) works for known providers. For unknown models from free-text entry, need a provider field or a smarter routing strategy. **Recommendation:** Add an optional `provider` parameter to `call_model()` OR use the ModelRegistry to look up provider from model_id.

#### 10. `prompt_compressor.py` (MODIFIED)

- **`_get_preproc_model()`**: Use registry instead of `PREPROC_MODEL_MAP` dict. Change error from ValueError to fallback with warning for unknown models.

#### 11. `execution_summary.py` (MODIFIED)

- **`estimate_cost()`**: Use `registry.compute_cost()` instead of `compute_cost()`.
- **`estimate_runtime()`**: Use `registry.get_delay()` instead of `RATE_LIMIT_DELAYS`.

#### 12. `scripts/generate_matrix.py` (MODIFIED)

- **`generate_matrix()`**: Use `registry.get_models()` instead of `MODELS` tuple. This makes the matrix adapt to configured models.

#### 13. `pilot.py` and `compute_derived.py` (MODIFIED)

- Replace `MODELS` imports with registry-derived model lists.

#### 14. `cli.py` (MODIFIED)

- **`--model` choices**: Remove hardcoded `choices=["claude", "gemini", "gpt", "openrouter", "all"]`. Derive from configured providers or accept any string.
- Add `.env` loading at startup via `env_manager.load_dotenv()`.

## Data Flow: Config -> Registry -> Consumers

### Setup Flow (New)

```
User runs `propt setup`
    |
    v
setup_wizard.py: interactive Q&A
    |
    +-- Select provider(s)
    +-- Enter target model (free-text, default shown)
    +-- Enter preproc model (free-text, default auto-filled)
    +-- Enter/confirm API key -> env_manager.set_env_var() -> .env file
    +-- [Optional] pricing_client.fetch_pricing() for cost preview
    +-- Show estimated experiment cost
    +-- Offer "Add another provider?"
    +-- Build models list
    |
    v
config_manager.save_config({...models: [...]...})
    |
    v
experiment_config.json (with models field)
```

### Runtime Flow (Modified)

```
Any command (run, pilot, list-models, etc.)
    |
    v
cli.py main():
    env_manager.load_dotenv()          # NEW: load .env
    config = config_manager.load_config()
    registry = ModelRegistry.from_config(config)  # NEW: build registry
    |
    v
Pass `registry` to consumers:
    - run_experiment.py: registry.compute_cost(), registry.get_preproc()
    - execution_summary.py: registry.compute_cost(), registry.get_delay()
    - prompt_compressor.py: registry.get_preproc()
    - api_client.py: registry.get_delay(), provider lookup
    - generate_matrix.py: registry.get_models()
```

### Pricing Flow (New)

```
propt list-models (or setup wizard)
    |
    v
pricing_client.list_provider_models(provider, api_key)
    |
    +-- Anthropic: client.models.list() -> model IDs only
    +-- OpenAI: client.models.list() -> model IDs only
    +-- Google: client.models.list() -> model IDs only
    +-- OpenRouter: httpx.get("/api/v1/models") -> model IDs + pricing
    |
    v
Merge with FALLBACK_PRICE_TABLE for display
    |
    v
For OpenRouter: live pricing overrides fallback
For others: fallback pricing only (with "fallback" indicator)
```

## Architectural Patterns

### Pattern 1: Registry with Fallback Defaults

**What:** A runtime-constructed registry that merges user config with hardcoded fallback values. Unknown models get $0.00 pricing with a warning.

**When to use:** When the set of valid values is open-ended (any model string) but you need lookup tables for associated data.

**Trade-offs:**
- Pro: Supports arbitrary models without code changes
- Pro: Existing hardcoded values serve as sensible defaults
- Con: Unknown model pricing is $0.00 which underestimates costs
- Mitigation: Warning at setup time + budget gate at run time

**Example:**
```python
class ModelRegistry:
    _FALLBACK_PRICE = {"input_per_1m": 0.0, "output_per_1m": 0.0}

    def get_price(self, model_id: str) -> dict[str, float]:
        if model_id in self._models:
            mc = self._models[model_id]
            return {"input_per_1m": mc.input_price_per_1m,
                    "output_per_1m": mc.output_price_per_1m}
        logger.warning("No pricing for %s, using $0.00 fallback", model_id)
        return dict(self._FALLBACK_PRICE)
```

### Pattern 2: Backward-Compatible Config Evolution

**What:** Add new structured fields alongside existing flat fields. Use new fields when present, fall back to flat fields for old configs.

**When to use:** When existing config files must continue to work after schema changes.

**Trade-offs:**
- Pro: Zero-disruption upgrade path
- Pro: Old tests continue to pass without modification
- Con: Two code paths to maintain during transition
- Mitigation: Deprecation warnings on flat-field-only configs

**Example:**
```python
@classmethod
def from_config(cls, config: ExperimentConfig) -> "ModelRegistry":
    if config.models:
        return cls([ModelConfig(**m) for m in config.models])
    # Backward compat: build from flat fields
    return cls._from_flat_fields(config)
```

### Pattern 3: Provider Abstraction for API Discovery

**What:** Each provider has a uniform `list_models()` / `fetch_pricing()` interface, but the implementations differ based on what each API actually exposes.

**When to use:** When integrating multiple external APIs with different capabilities.

**Trade-offs:**
- Pro: Uniform interface for consumers
- Con: Some providers return less data (no pricing)
- Mitigation: Explicit "source" field on pricing data (live vs fallback)

## Anti-Patterns

### Anti-Pattern 1: Making All Dicts Dynamic at Import Time

**What people do:** Replace `PRICE_TABLE = {...}` with `PRICE_TABLE = load_from_config()` at module level.

**Why it's wrong:** Module-level execution happens at import time, before any config file is loaded or CLI is parsed. Circular imports. Test isolation breaks. Config file must exist for any import to succeed.

**Do this instead:** Keep static fallback defaults at module level. Build the ModelRegistry at runtime (in CLI entry points) and pass it explicitly to functions that need it.

### Anti-Pattern 2: Adding Provider-Specific Pricing Scrapers

**What people do:** Scrape pricing pages or maintain a mapping of model names to prices from documentation.

**Why it's wrong:** Pricing pages change without notice, scraping is fragile, and hardcoded mappings go stale. Three of the four providers have no pricing API.

**Do this instead:** Use hardcoded fallback prices that are updated manually when models change. For OpenRouter (which has a pricing API), fetch live data. For others, the FALLBACK_PRICE_TABLE is authoritative.

### Anti-Pattern 3: Modifying Frozen Dataclass Fields via Object Replacement

**What people do:** Create a new ExperimentConfig with `models` field by replacing the entire object after load.

**Why it's wrong:** The `frozen=True` constraint is intentional for reproducibility. Building new instances is fine, but consumers must not mutate config during a run.

**Do this instead:** Build the ModelRegistry once from config, then use the registry. Never modify config after load.

## Integration Points

### External Services

| Service | Integration Pattern | Pricing Available? | Notes |
|---------|--------------------|--------------------|-------|
| Anthropic API | `client.models.list()` -> model IDs | NO | Returns `ModelInfo` with id, display_name, max_tokens only |
| OpenAI API | `client.models.list()` -> model IDs | NO | Returns `Model` with id, created, owned_by only |
| Google GenAI | `client.models.list()` -> model IDs | NO | Returns model metadata, no pricing |
| OpenRouter API | `httpx.get("/api/v1/models")` -> IDs + pricing | YES | Raw JSON has `pricing.prompt`, `pricing.completion` per-token |

### Internal Boundaries (Changes Required)

| Boundary | Current Communication | New Communication | Migration Effort |
|----------|----------------------|-------------------|-----------------|
| config.py -> all consumers | Module-level dict imports | Registry instance passed at runtime | MEDIUM -- every consumer gains a `registry` parameter |
| config_manager.py -> config.py | Imports PRICE_TABLE for validation | Imports FALLBACK_PRICE_TABLE for warnings | LOW -- change error to warning |
| setup_wizard.py -> config.py | Imports MODELS, PREPROC_MODEL_MAP | Uses registry defaults + free-text | MEDIUM -- wizard rewrite |
| cli.py -> env | os.environ only | env_manager.load_dotenv() at startup | LOW -- one line addition |
| prompt_compressor.py -> config.py | Direct PREPROC_MODEL_MAP import | Registry.get_preproc() | LOW -- one function change |

## Suggested Build Order

The dependencies between components dictate this build order:

### Phase 1: Foundation (no existing behavior changes)

1. **Add `python-dotenv` dependency** -- add to pyproject.toml
2. **Create `src/env_manager.py`** -- .env load/write utilities
3. **Create `ModelConfig` dataclass** -- in config.py, alongside existing constants
4. **Create `ModelRegistry` class** -- in config.py, with `defaults()` classmethod that wraps current hardcoded values
5. **Add `models` field to `ExperimentConfig`** -- default empty tuple, backward compat

**Test gate:** All existing tests pass. Registry.defaults() returns same data as current dicts.

### Phase 2: Registry Consumers (swap imports to registry)

6. **Update `compute_cost()`** -- make it a registry method AND keep standalone function with deprecation
7. **Update `prompt_compressor.py`** -- accept registry parameter for preproc lookup
8. **Update `execution_summary.py`** -- accept registry parameter for pricing/delays
9. **Update `api_client.py`** -- accept registry parameter for rate limit delays
10. **Update `run_experiment.py`** -- build registry from config, pass to all consumers

**Test gate:** All existing tests pass. Behavior identical to before.

### Phase 3: Pricing Client (new capability)

11. **Create `src/pricing_client.py`** -- per-provider model listing and OpenRouter pricing
12. **Update `config_commands.py` `handle_list_models()`** -- query live APIs + merge with fallbacks

**Test gate:** `propt list-models` shows live model availability.

### Phase 4: Setup Wizard Overhaul (user-facing changes)

13. **Update `config_manager.py` `validate_config()`** -- warn-only for unknown models
14. **Update `setup_wizard.py`** -- free-text entry, multi-provider, .env writing, budget preview
15. **Update `cli.py`** -- load .env at startup, dynamic --model choices

**Test gate:** Full wizard flow works with free-text models. .env created.

### Phase 5: Matrix Adaptation (experiment scope)

16. **Update `scripts/generate_matrix.py`** -- use registry.get_models()
17. **Update `pilot.py`** -- use registry-derived model list
18. **Update `compute_derived.py`** -- use registry-derived model list
19. **Update `cli.py --model flag`** -- accept configured provider names dynamically

**Test gate:** Matrix generation adapts to configured models. Pilot runs with subset of providers.

### Phase ordering rationale

- Phases 1-2 are zero-risk: they add new code paths without changing existing behavior
- Phase 3 is independent of 2 but benefits from having the registry in place
- Phase 4 depends on 1 (env_manager), 2 (registry), and 3 (pricing for budget preview)
- Phase 5 depends on 2 (registry) and 4 (wizard populates models config)

## Sources

- Direct codebase analysis of all files listed in the component table above
- SDK introspection: `anthropic==0.86.0` ModelInfo fields, `openai==2.29.0` Model fields, `google-genai` Client.models.list() methods
- Anthropic SDK: `client.models.list()` returns `SyncPage[ModelInfo]` with fields: `id`, `display_name`, `created_at`, `max_input_tokens`, `max_tokens`, `capabilities`, `type` -- confirmed no pricing
- OpenAI SDK: `client.models.list()` returns `Model` with fields: `id`, `created`, `object`, `owned_by` -- confirmed no pricing
- OpenRouter REST API documentation (training data): `/api/v1/models` returns `pricing.prompt` and `pricing.completion` per-token -- MEDIUM confidence (not verified live)
- `python-dotenv` is the standard .env management library for Python projects -- HIGH confidence

---
*Architecture research for: Configurable Models and Dynamic Pricing integration with existing Linguistic Tax toolkit*
*Researched: 2026-03-25*
