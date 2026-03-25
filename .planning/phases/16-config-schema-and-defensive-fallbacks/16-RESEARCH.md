# Phase 16: Config Schema and Defensive Fallbacks - Research

**Researched:** 2026-03-25
**Domain:** Python dataclass config management, JSON schema migration, python-dotenv
**Confidence:** HIGH

## Summary

Phase 16 replaces hardcoded model constants (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) with a config-driven ModelRegistry backed by ModelConfig dataclasses. The work is well-scoped: a new `model_registry.py` module, a `data/default_models.json` defaults file, migration logic in `config_manager.py`, a new `env_manager.py` module wrapping python-dotenv, and defensive fallbacks for unknown models. All user decisions are locked and specific.

The project uses Python 3.13 with a uv-managed venv, pytest for testing, and standard dataclasses (not pydantic) for config. python-dotenv is NOT yet installed in the project venv and must be added as a dependency. The existing codebase has 8+ files importing the old constants -- but consumer migration is Phase 17 scope. This phase builds the registry and makes it importable; Phase 17 swaps the imports.

**Primary recommendation:** Build ModelConfig as a plain `@dataclass` (mutable), ModelRegistry as a class with dict-based lookup, and default_models.json as the single source of truth for curated model data. Migration detects v1 format by absence of `config_version` field and converts in-place with `.bak` backup.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Models represented as a **list of self-contained model objects** in the config JSON
- Each model entry carries: model_id, provider, role, preproc_model_id (if target), input_price_per_1m, output_price_per_1m, rate_limit_delay
- Preproc models are **separate entries** in the models list (role: "preproc"), not nested inside target models
- All 8 models (4 targets + 4 preproc) listed explicitly in the default config
- Provider field is **explicit** (provider: "anthropic" | "google" | "openai" | "openrouter") -- no string inference from model_id
- Provider is a free string (no enum enforcement) -- validation warns on unknown providers but accepts them
- Add **config_version: 2** field for programmatic format detection
- Default config **ships with the project** pre-populated with all 8 models
- Unknown property values use **null in JSON / None in Python** -- explicit distinction between "free" (0.0) and "unknown" (null). Code applies sensible defaults (0.0 for pricing, 0.5s for delay) when None
- New **ModelConfig dataclass** (mutable, not frozen) with fields matching the JSON model object
- New **ModelRegistry class** in a dedicated `src/model_registry.py` file -- provides get_price(), get_preproc(), get_delay(), target_models(), compute_cost() methods
- Registry is a **module-level singleton** created at import time from loaded config
- compute_cost() moves to a **method on ModelRegistry** (not standalone function)
- **ExperimentConfig becomes mutable** (remove frozen=True) -- wizard can build and modify incrementally
- Old flat fields (claude_model, gemini_model, openai_model, openrouter_model, openrouter_preproc_model) **stripped entirely** from ExperimentConfig
- Old module-level constants (PRICE_TABLE, MODELS, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) **removed entirely** -- no backward-compat aliases
- Tests use **new API only** (get_price, get_preproc, etc.) -- no dict-style access properties on registry
- **data/default_models.json** -- a separate JSON file with complete model entries (all 8 models, full pricing, delays, preproc mappings, roles, providers)
- **Auto-migrate on load**: load_config() detects old v1.0 format and converts to new format
- Creates **.bak backup** of old config before rewriting
- Populates **pricing/delays from defaults** (data/default_models.json)
- **config_version field** for format detection: no version = v1, version 2 = current
- **Config diff on migration**: log a clear diff showing what changed
- compute_cost() returns **$0.00 with warning** for unknown models (no crash)
- Warning logged **once per unknown model** -- subsequent calls silent
- validate_config() **warns but accepts** unknown model IDs (CFG-04)
- Unknown models **allowed to run experiments**
- Missing preproc model (referenced but not in config): **auto-add with defaults** ($0.00 pricing, 0.5s delay)
- New module: `src/env_manager.py` with three capabilities: load_env(), write_env(), check_keys()
- .env file at **project root only** -- not configurable
- **Auto-load during load_config()** -- load_env() called first so API keys are always available
- Set **chmod 600** on .env file when creating or writing (owner-only read/write)
- No .env.example template
- Provider-to-API-key mapping **hardcoded** in env_manager: {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
- **registry.reload()** method for wizard config change support
- **Provider health check**: registry.check_provider(provider) verifies API key exists

### Claude's Discretion
- Internal implementation details of ModelRegistry (data structures, caching)
- Exact warning message wording
- Test organization and test helper utilities
- Order of migration steps within load_config()

### Deferred Ideas (OUT OF SCOPE)
- **Wizard config file handling** (Phase 19): When config exists, wizard should ask: delete and start over, backup and create new, update existing, or cancel
- **Consumer migration** (Phase 17): Swap all hardcoded imports to registry lookups across 8+ consumer modules
- **Live pricing from OpenRouter API** (Phase 18): Fetch real pricing via /api/v1/models endpoint

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | User can configure target and pre-processor models per provider via a `models` list in ExperimentConfig | ModelConfig dataclass + ModelRegistry class + default_models.json provide the config-driven model list |
| CFG-02 | PRICE_TABLE, PREPROC_MODEL_MAP, and RATE_LIMIT_DELAYS are derived from config at load time, not hardcoded | ModelRegistry builds internal dicts from loaded config's models list; get_price/get_preproc/get_delay methods replace direct dict access |
| CFG-03 | `compute_cost()` falls back to $0.00 with a warning for models not in the price table (no crash) | ModelRegistry.compute_cost() catches missing model, returns 0.0, logs warning once per unknown model_id |
| CFG-04 | `validate_config()` warns instead of rejecting unknown model IDs | validate_config() updated to log warning for unknown models but return no errors for them |
| CFG-05 | Old flat-field configs auto-migrate to new models list format on load | load_config() detects missing config_version, maps old flat fields to model entries using default_models.json pricing, creates .bak backup |
| PRC-01 | Curated fallback price table provides pricing for known models when no API pricing is available | data/default_models.json contains all 8 models with current pricing -- serves as the curated fallback |
| PRC-03 | Unknown models default to $0.00 pricing with a user-visible warning | Same as CFG-03 -- compute_cost returns $0.00 + warning for unknown models |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses (stdlib) | Python 3.13 built-in | ModelConfig dataclass | Already used for ExperimentConfig; no new dependency needed |
| python-dotenv | 1.1.1+ (latest 1.2.2) | .env file load/write | De facto standard for Python .env management; already a transitive dependency of google-adk |
| json (stdlib) | Python 3.13 built-in | Config file I/O, default_models.json | Already used throughout project |
| logging (stdlib) | Python 3.13 built-in | Warning output for unknown models | Project convention: all output uses logging module |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | Python 3.13 built-in | File path manipulation | Config file paths, .env path |
| shutil (stdlib) | Python 3.13 built-in | Config backup (.bak) creation | Migration creates .bak before rewriting |
| os (stdlib) | Python 3.13 built-in | chmod for .env file permissions | Set 0o600 on .env after write |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain dataclass for ModelConfig | Pydantic BaseModel | Pydantic is installed but overkill; project convention uses dataclasses; adding pydantic would be inconsistent |
| Manual JSON validation | jsonschema | Over-engineering; validation rules are simple enough for Python code |
| python-dotenv set_key() | Manual file writing | set_key handles quoting, comments preservation, atomic writes via tempfile |

**Installation:**
```bash
uv add python-dotenv
```

**Version verification:** python-dotenv 1.2.2 is latest on PyPI (released 2026-03-01). The project should pin `>=1.0.0` since the API is stable. The `set_key()` and `load_dotenv()` functions have been stable since 0.19+.

## Architecture Patterns

### Recommended Project Structure
```
src/
    config.py            # ExperimentConfig (modified: mutable, no flat model fields)
                         # NOISE_TYPES, INTERVENTIONS, derive_seed() (unchanged)
                         # compute_cost() REMOVED (moved to registry)
                         # MODELS, PRICE_TABLE, etc. REMOVED
    model_registry.py    # NEW: ModelConfig, ModelRegistry, module-level singleton
    config_manager.py    # MODIFIED: migration logic, env loading in load_config()
    env_manager.py       # NEW: load_env(), write_env(), check_keys()

data/
    default_models.json  # NEW: curated defaults for all 8 models
```

### Pattern 1: ModelConfig Dataclass
**What:** Mutable dataclass representing a single model's configuration
**When to use:** Every model entry in the config's models list becomes a ModelConfig instance
**Example:**
```python
@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""
    model_id: str
    provider: str                          # "anthropic", "google", "openai", "openrouter"
    role: str                              # "target" or "preproc"
    preproc_model_id: str | None = None    # only for role="target"
    input_price_per_1m: float | None = None   # None = unknown, 0.0 = free
    output_price_per_1m: float | None = None  # None = unknown, 0.0 = free
    rate_limit_delay: float | None = None     # None = unknown, default 0.5s
```

### Pattern 2: ModelRegistry Singleton
**What:** Central registry providing dict-like access to model data, built from config
**When to use:** Any code that previously accessed PRICE_TABLE, PREPROC_MODEL_MAP, etc.
**Example:**
```python
class ModelRegistry:
    """Registry of configured models with pricing, preproc mapping, and delays."""

    def __init__(self, models: list[ModelConfig]) -> None:
        self._models: dict[str, ModelConfig] = {m.model_id: m for m in models}
        self._warned_unknown: set[str] = set()  # for once-per-model warnings

    def get_price(self, model_id: str) -> tuple[float, float]:
        """Return (input_per_1m, output_per_1m). Defaults to (0.0, 0.0) for unknown."""
        ...

    def get_preproc(self, model_id: str) -> str | None:
        """Return preproc model_id for a target model, or None."""
        ...

    def get_delay(self, model_id: str) -> float:
        """Return rate limit delay. Defaults to 0.5 for unknown."""
        ...

    def target_models(self) -> list[str]:
        """Return list of model_ids with role='target'."""
        ...

    def compute_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Compute cost in USD. Returns 0.0 with warning for unknown models."""
        ...

    def reload(self, models: list[ModelConfig]) -> None:
        """Reload registry with new model list (for wizard updates)."""
        ...

    def check_provider(self, provider: str) -> dict[str, bool]:
        """Check if API key exists for provider. Returns {"key_name": ..., "exists": bool}."""
        ...

# Module-level singleton
registry: ModelRegistry = _build_registry()
```

### Pattern 3: Config Migration (v1 to v2)
**What:** Auto-detect old flat-field config format and convert to models list
**When to use:** In load_config() before constructing ExperimentConfig
**Example:**
```python
def _migrate_v1_to_v2(raw: dict, config_path: Path) -> dict:
    """Convert v1 flat-field config to v2 models list format."""
    # 1. Create .bak backup
    backup_path = config_path.with_suffix(".json.bak")
    shutil.copy2(config_path, backup_path)
    logger.info("Config backup saved to %s", backup_path)

    # 2. Map old flat fields to model entries using defaults
    defaults = _load_default_models()
    models = []
    field_to_model = {
        "claude_model": raw.get("claude_model"),
        "gemini_model": raw.get("gemini_model"),
        "openai_model": raw.get("openai_model"),
        "openrouter_model": raw.get("openrouter_model"),
    }
    # ... build model entries from defaults, using flat field values as model_ids

    # 3. Remove old flat fields, add models list and config_version
    for old_field in ["claude_model", "gemini_model", "openai_model",
                       "openrouter_model", "openrouter_preproc_model"]:
        raw.pop(old_field, None)
    raw["models"] = [asdict(m) for m in models]
    raw["config_version"] = 2

    # 4. Log diff
    logger.info("Migrated config from v1 to v2: ...")

    # 5. Write migrated config
    save_config(raw, config_path)
    return raw
```

### Pattern 4: Once-per-model Warning
**What:** Log a warning the first time an unknown model is encountered, suppress subsequent warnings
**When to use:** compute_cost() and get_price() for unknown model IDs
**Example:**
```python
def compute_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
    if model_id not in self._models:
        if model_id not in self._warned_unknown:
            logger.warning(
                "Unknown model '%s': using $0.00 pricing. "
                "Run `propt list-models` to see configured models.",
                model_id,
            )
            self._warned_unknown.add(model_id)
        return 0.0
    inp, out = self.get_price(model_id)
    return input_tokens * inp / 1_000_000 + output_tokens * out / 1_000_000
```

### Anti-Patterns to Avoid
- **Module-level singleton that calls load_config() at import time**: This creates circular imports if config_manager imports from model_registry or vice versa. Use a lazy initialization pattern or explicit `_build_registry()` called after imports resolve.
- **Storing None in JSON and treating 0 as falsy**: The user decision explicitly distinguishes None (unknown) from 0.0 (free). Never use `if not price:` -- always use `if price is None:`.
- **Enum for provider field**: User decision says provider is a free string. Do not add an enum.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env file parsing/writing | Custom regex parser for .env | python-dotenv load_dotenv() + set_key() | Handles quoting, comments, interpolation, atomic writes |
| File permission setting | Manual stat/chmod logic | os.chmod(path, 0o600) | One-liner, no edge cases |
| Config backup | Custom versioned backup system | shutil.copy2() with .bak suffix | Simple, preserves metadata |
| JSON pretty-printing | Manual indentation | json.dump(indent=2) | Already used in save_config() |

**Key insight:** The project already has config persistence in config_manager.py (save_config, load_config). Migration and env loading hook into the existing flow -- don't create a parallel config loading path.

## Common Pitfalls

### Pitfall 1: Circular Import Between model_registry.py and config_manager.py
**What goes wrong:** ModelRegistry singleton tries to call load_config() at module level, but config_manager.py might import from model_registry.py.
**Why it happens:** Module-level singleton initialization runs at import time.
**How to avoid:** Keep the dependency one-directional: config_manager.py builds and sets the registry, model_registry.py only defines classes and a `registry` variable initially set to None or built from default_models.json. Alternative: use a lazy initialization pattern where registry is built on first access.
**Warning signs:** `ImportError` or `AttributeError: None` at import time.

### Pitfall 2: set_key() File Creation Behavior
**What goes wrong:** python-dotenv set_key() docstring says "fails instead of risking creating an orphan .env" but the actual implementation calls `pathlib.Path(path).touch()` which CREATES the file if missing.
**Why it happens:** Docstring is outdated/misleading vs actual behavior (verified in source code of v1.1.1).
**How to avoid:** This is actually desired behavior for our env_manager.write_env() -- the file gets created if it doesn't exist. Just be aware and set chmod 600 after writing.
**Warning signs:** N/A -- this pitfall is informational.

### Pitfall 3: None vs 0.0 in JSON Round-Trip
**What goes wrong:** JSON `null` becomes Python `None`, but code that does `price or 0.0` treats `0.0` (free model) the same as `None` (unknown).
**Why it happens:** Python's falsy evaluation: `0.0` is falsy.
**How to avoid:** Always use explicit `is None` checks: `price if price is not None else 0.0`. Never use `price or default`.
**Warning signs:** Free models (like OpenRouter :free) getting logged as "unknown pricing."

### Pitfall 4: ExperimentConfig Frozen Removal Breaking Tests
**What goes wrong:** Removing `frozen=True` from ExperimentConfig breaks test_config.py's `test_config_is_frozen` test.
**Why it happens:** That test explicitly asserts FrozenInstanceError is raised.
**How to avoid:** Update test_config.py to remove the frozen assertion test. Also update conftest.py's `sample_config` fixture if needed. Replace old model-field-specific tests with new models-list-based tests.
**Warning signs:** pytest failures in test_config.py.

### Pitfall 5: Migration Handling Missing Flat Fields
**What goes wrong:** User's v1 config might only have some flat fields (e.g., only `claude_model` and `gemini_model`), not all 5.
**Why it happens:** v1 load_config() used sparse overrides -- config files could have any subset of fields.
**How to avoid:** Migration should use `.get()` with ExperimentConfig defaults as fallback. If a flat field is absent, use the default model ID from ExperimentConfig and look up its pricing from default_models.json.
**Warning signs:** KeyError during migration of a sparse config.

### Pitfall 6: data/ Directory Git Tracking
**What goes wrong:** data/default_models.json might not be committed if data/ is gitignored.
**Why it happens:** Some projects gitignore data directories for large datasets.
**How to avoid:** Verify data/ is tracked (it is -- data/prompts.json is already committed). default_models.json should be committed alongside it.
**Warning signs:** File not found errors when loading defaults.

## Code Examples

### default_models.json Structure
```json
{
  "models": [
    {
      "model_id": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "role": "target",
      "preproc_model_id": "claude-haiku-4-5-20250514",
      "input_price_per_1m": 3.00,
      "output_price_per_1m": 15.00,
      "rate_limit_delay": 0.2
    },
    {
      "model_id": "claude-haiku-4-5-20250514",
      "provider": "anthropic",
      "role": "preproc",
      "preproc_model_id": null,
      "input_price_per_1m": 1.00,
      "output_price_per_1m": 5.00,
      "rate_limit_delay": 0.1
    },
    {
      "model_id": "gemini-1.5-pro",
      "provider": "google",
      "role": "target",
      "preproc_model_id": "gemini-2.0-flash",
      "input_price_per_1m": 1.25,
      "output_price_per_1m": 5.00,
      "rate_limit_delay": 0.1
    },
    {
      "model_id": "gemini-2.0-flash",
      "provider": "google",
      "role": "preproc",
      "preproc_model_id": null,
      "input_price_per_1m": 0.10,
      "output_price_per_1m": 0.40,
      "rate_limit_delay": 0.05
    },
    {
      "model_id": "gpt-4o-2024-11-20",
      "provider": "openai",
      "role": "target",
      "preproc_model_id": "gpt-4o-mini-2024-07-18",
      "input_price_per_1m": 2.50,
      "output_price_per_1m": 10.00,
      "rate_limit_delay": 0.2
    },
    {
      "model_id": "gpt-4o-mini-2024-07-18",
      "provider": "openai",
      "role": "preproc",
      "preproc_model_id": null,
      "input_price_per_1m": 0.15,
      "output_price_per_1m": 0.60,
      "rate_limit_delay": 0.1
    },
    {
      "model_id": "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
      "provider": "openrouter",
      "role": "target",
      "preproc_model_id": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
      "input_price_per_1m": 0.0,
      "output_price_per_1m": 0.0,
      "rate_limit_delay": 0.5
    },
    {
      "model_id": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
      "provider": "openrouter",
      "role": "preproc",
      "preproc_model_id": null,
      "input_price_per_1m": 0.0,
      "output_price_per_1m": 0.0,
      "rate_limit_delay": 0.5
    }
  ]
}
```

### env_manager.py Core Functions
```python
# Source: python-dotenv API (verified from source code)
from dotenv import load_dotenv, set_key, dotenv_values
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Hardcoded provider-to-key mapping (per user decision)
PROVIDER_KEY_MAP: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_ENV_PATH = Path(".env")

def load_env() -> bool:
    """Load .env file from project root into os.environ."""
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH, override=False)
        return True
    return False

def write_env(key: str, value: str) -> None:
    """Write a key-value pair to .env file. Creates file if needed."""
    # set_key creates the file via pathlib.Path.touch() if missing
    set_key(str(_ENV_PATH), key, value)
    os.chmod(_ENV_PATH, 0o600)

def check_keys(providers: list[str]) -> dict[str, bool]:
    """Check which providers have API keys set in environment."""
    return {
        provider: os.environ.get(PROVIDER_KEY_MAP.get(provider, ""), "") != ""
        for provider in providers
    }
```

### ExperimentConfig v2 Shape (after migration)
```python
@dataclass
class ExperimentConfig:
    """Experiment configuration with config-driven model list."""

    # Model list (replaces flat model fields)
    models: list[dict] | None = None  # Populated from config JSON; None = use defaults

    # Config version
    config_version: int = 2

    # Seeds
    base_seed: int = 42

    # Noise parameters
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    type_a_weights: tuple[float, ...] = (0.40, 0.25, 0.20, 0.15)

    # Experiment parameters
    repetitions: int = 5
    temperature: float = 0.0

    # Paths
    prompts_path: str = "data/prompts.json"
    matrix_path: str = "data/experiment_matrix.json"
    results_db_path: str = "results/results.db"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded PRICE_TABLE dict | Config-driven ModelRegistry | This phase | All pricing lookups go through registry |
| Frozen ExperimentConfig | Mutable ExperimentConfig | This phase | Wizard can build config incrementally |
| Flat model fields (claude_model, etc.) | models list of model objects | This phase | Supports arbitrary models, not just 4 providers |
| compute_cost() crashes on unknown model | Returns $0.00 with warning | This phase | Unknown models don't break experiment runs |
| No .env support | python-dotenv auto-loading | This phase | API keys managed in .env file |

**Deprecated/outdated:**
- `compute_cost()` standalone function in config.py: replaced by ModelRegistry.compute_cost() method
- `PRICE_TABLE`, `MODELS`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS` module constants: removed entirely
- `ExperimentConfig.claude_model`, `.gemini_model`, `.openai_model`, `.openrouter_model`, `.openrouter_preproc_model`: removed entirely

## Open Questions

1. **Module-level singleton initialization timing**
   - What we know: Registry should be available at import time for consumers
   - What's unclear: Whether to initialize from default_models.json and let load_config() reload, or use lazy init
   - Recommendation: Initialize from default_models.json at module level. load_config() calls registry.reload() after loading config. This avoids None checks throughout consumer code.

2. **ExperimentConfig.models field type**
   - What we know: JSON models list needs to be stored in ExperimentConfig for persistence
   - What's unclear: Whether to store as `list[dict]` or `list[ModelConfig]` in ExperimentConfig
   - Recommendation: Store as `list[dict]` in ExperimentConfig (for JSON serialization simplicity). ModelRegistry converts to ModelConfig instances internally.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_model_registry.py tests/test_env_manager.py tests/test_config.py tests/test_config_manager.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | Custom model in config loads without error | unit | `pytest tests/test_model_registry.py::TestModelRegistry::test_custom_model_loads -x` | No -- Wave 0 |
| CFG-02 | Registry provides price/preproc/delay from config | unit | `pytest tests/test_model_registry.py::TestModelRegistry::test_derived_from_config -x` | No -- Wave 0 |
| CFG-03 | compute_cost returns $0.00 for unknown model | unit | `pytest tests/test_model_registry.py::TestModelRegistry::test_unknown_model_returns_zero -x` | No -- Wave 0 |
| CFG-04 | validate_config warns but does not reject unknown model | unit | `pytest tests/test_config_manager.py::TestValidateConfig::test_unknown_model_warns_not_rejects -x` | No -- Wave 0 |
| CFG-05 | v1 flat-field config auto-migrates to v2 | unit | `pytest tests/test_config_manager.py::TestMigration::test_v1_to_v2_migration -x` | No -- Wave 0 |
| PRC-01 | default_models.json loads and provides pricing | unit | `pytest tests/test_model_registry.py::TestDefaultModels::test_defaults_load -x` | No -- Wave 0 |
| PRC-03 | Unknown model gets $0.00 pricing with warning | unit | `pytest tests/test_model_registry.py::TestModelRegistry::test_unknown_model_returns_zero -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_model_registry.py tests/test_env_manager.py tests/test_config.py tests/test_config_manager.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_model_registry.py` -- covers CFG-01, CFG-02, CFG-03, PRC-01, PRC-03
- [ ] `tests/test_env_manager.py` -- covers env_manager load/write/check functionality
- [ ] `tests/test_config.py` -- needs updates: remove frozen test, remove old flat field tests, add models list tests
- [ ] `tests/test_config_manager.py` -- needs updates: add migration tests (CFG-05), update validation tests (CFG-04)
- [ ] `tests/conftest.py` -- needs update: sample_config fixture must return updated ExperimentConfig
- [ ] Framework install: `uv add python-dotenv` -- python-dotenv not in project venv

## Sources

### Primary (HIGH confidence)
- `/home/steve/linguistic-tax/src/config.py` -- current hardcoded constants, ExperimentConfig, compute_cost()
- `/home/steve/linguistic-tax/src/config_manager.py` -- current load_config, validate_config, save_config
- `/home/steve/.local/lib/python3.10/site-packages/dotenv/main.py` -- python-dotenv source code (v1.1.1): verified load_dotenv(), set_key(), rewrite() behavior
- `.planning/phases/16-config-schema-and-defensive-fallbacks/16-CONTEXT.md` -- all user decisions

### Secondary (MEDIUM confidence)
- [python-dotenv PyPI](https://pypi.org/project/python-dotenv/) -- latest version 1.2.2 (2026-03-01)
- [python-dotenv GitHub](https://github.com/theskumar/python-dotenv) -- API reference

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib dataclasses + python-dotenv, both verified
- Architecture: HIGH -- patterns directly from user decisions in CONTEXT.md, code examples verified against current codebase
- Pitfalls: HIGH -- identified from reading actual source code (circular imports, None vs 0.0, set_key behavior)

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain, no fast-moving dependencies)
