# Phase 17: Registry Consumers - Research

**Researched:** 2026-03-26
**Domain:** Python module refactoring -- migrating hardcoded config imports to centralized registry API
**Confidence:** HIGH

## Summary

Phase 17 is a mechanical refactoring phase: every module that currently imports MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, or compute_cost from `src/config.py` must be migrated to use `src/model_registry.py`'s `get_registry()` singleton directly. Phase 16 already built the ModelRegistry with all necessary methods and added backward-compat shims in config.py so the 541-test suite passes throughout. Phase 17 replaces shim usage module-by-module, then removes the shims as a final cleanup.

There are 12 consumer files to migrate (8 source modules, 4 test files) plus the setup_wizard.py which also imports MODELS and PREPROC_MODEL_MAP. The registry API is already fully functional: `registry.target_models()`, `registry.compute_cost()`, `registry.get_price()`, `registry.get_preproc()`, `registry.get_delay()`. Each migration is a search-and-replace of imports plus minor API adjustments (dict lookup -> method call).

**Primary recommendation:** Migrate in dependency order (leaf modules first, config.py shim removal last), committing each module migration atomically with its test updates, verifying 541 tests pass at every step.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Migrate consumers module-by-module, each testable independently
- After all consumers migrated, remove shims from config.py as a final cleanup step
- Each consumer migration is a separate commit for easy bisection
- Tests for each module updated in the same commit as the module migration
- `scripts/generate_matrix.py` uses `get_registry().target_models()` instead of hardcoded MODELS tuple (EXP-01)
- `src/run_experiment.py` accepts any model the registry knows about; `--model` flag validates against registry not a hardcoded set (EXP-02)
- `src/pilot.py` adapts `_VALID_MODELS` to be `set(get_registry().target_models())` -- runs only configured providers (EXP-03)
- `src/compute_derived.py` iterates over registry target models instead of hardcoded MODELS (EXP-04)
- All four consumers get their model list from the same source: `get_registry().target_models()`
- `src/prompt_compressor.py`: permissive -- warn and use model itself as fallback for unknown preproc mapping
- `src/pilot.py`: permissive -- `_VALID_MODELS` derived from registry
- `src/api_client.py`: permissive -- `get_delay()` returns default 0.5s for unknown models
- `src/execution_summary.py`: permissive -- `compute_cost()` returns $0.00 for unknown models
- Pattern: warn once, don't crash, use sensible defaults
- `generate_matrix.py` uses registry for model list but also accepts `--models` CLI override
- INTERVENTIONS and NOISE_TYPES stay in config.py (not model-related)

### Claude's Discretion
- Order of module migrations (any dependency-safe order is fine)
- Exact import patterns (from src.model_registry import get_registry vs other)
- Test fixture organization for registry-based tests
- Whether to add helper functions in individual modules or call registry directly

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXP-01 | Experiment matrix generation uses configured models (not hardcoded MODELS tuple) | `scripts/generate_matrix.py` line 17 imports MODELS from config; replace with `get_registry().target_models()` + add `--models` CLI override |
| EXP-02 | `--model` flag on `propt run` works with any configured model | `src/run_experiment.py` line 551 has `choices=["claude", "gemini", "all"]` hardcoded; replace with registry-based validation |
| EXP-03 | Pilot run adapts to configured models (runs only configured providers) | `src/pilot.py` line 274 has `_VALID_MODELS = set(MODELS)`; replace with `set(get_registry().target_models())` |
| EXP-04 | Derived metrics computation adapts to configured models | `src/compute_derived.py` line 22 imports MODELS; line 482 iterates `for model in MODELS` |
</phase_requirements>

## Standard Stack

No new libraries required. This phase uses only existing project dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| src/model_registry.py | project-internal | ModelRegistry singleton with get_price/get_preproc/get_delay/compute_cost/target_models | Built in Phase 16, already tested |

### Registry API Reference

| Old Import (config.py) | New Call (model_registry) | Return Type |
|-------------------------|--------------------------|-------------|
| `MODELS` | `get_registry().target_models()` | `list[str]` |
| `PRICE_TABLE[model]` | `get_registry().get_price(model)` | `tuple[float, float]` |
| `PREPROC_MODEL_MAP[model]` | `get_registry().get_preproc(model)` | `str \| None` |
| `RATE_LIMIT_DELAYS[model]` | `get_registry().get_delay(model)` | `float` |
| `compute_cost(model, inp, out)` | `get_registry().compute_cost(model, inp, out)` | `float` |

**Import pattern:** `from src.model_registry import registry` (direct singleton) or define `get_registry()` as a function call. The module already exposes `registry` as a module-level singleton on line 214.

## Architecture Patterns

### Migration Pattern Per Module

For each consumer module:
1. Replace `from src.config import MODELS, PRICE_TABLE, ...` with `from src.model_registry import registry`
2. Replace dict-style lookups with method calls
3. Update corresponding test file imports in the same commit
4. Run full test suite to verify no regression

### Specific Migration Map

```
Module                      | Remove Import                      | Add Import                           | Code Changes
----------------------------|------------------------------------|--------------------------------------|-------------
src/api_client.py           | RATE_LIMIT_DELAYS                  | registry                             | _rate_delays = {m: registry.get_delay(m) for m in registry._models}
src/prompt_compressor.py    | PREPROC_MODEL_MAP                  | registry                             | Replace dict lookup with registry.get_preproc(), add fallback
src/config_commands.py      | PRICE_TABLE                        | registry                             | handle_list_models uses registry.get_price() + registry._models
src/execution_summary.py    | PRICE_TABLE, PREPROC_MODEL_MAP,    | registry                             | estimate_cost/estimate_runtime use registry methods
                            | RATE_LIMIT_DELAYS, compute_cost    |                                      |
src/compute_derived.py      | MODELS                             | registry                             | main() line 482: for model in registry.target_models()
src/run_experiment.py       | PREPROC_MODEL_MAP, compute_cost    | registry                             | _process_item uses registry.compute_cost(), _build_parser removes choices
src/pilot.py                | MODELS                             | registry                             | _VALID_MODELS = set(registry.target_models())
scripts/generate_matrix.py  | MODELS                             | model_registry.registry              | Add --models CLI flag, use registry.target_models() as default
src/setup_wizard.py         | MODELS, PREPROC_MODEL_MAP          | registry                             | PROVIDERS dict uses registry.target_models() filtered by prefix
```

### Test File Migration Map

```
Test File                       | Remove Import                         | Add Import / Change
--------------------------------|---------------------------------------|--------------------
tests/test_matrix.py            | MODELS                                | registry; use registry.target_models()
tests/test_config_commands.py   | PRICE_TABLE                           | registry (or import from model_registry)
tests/test_prompt_repeater.py   | PRICE_TABLE, compute_cost             | registry.get_price(), registry.compute_cost()
tests/test_integration.py       | MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, compute_cost | registry methods
tests/test_execution_summary.py | PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost | registry methods
tests/test_setup_wizard.py      | MODELS, PREPROC_MODEL_MAP             | registry methods
tests/test_pilot.py             | MODELS                                | registry.target_models()
```

### Recommended Migration Order

1. **Leaf modules first** (no downstream consumers depend on their migration):
   - `src/api_client.py` -- only imports RATE_LIMIT_DELAYS
   - `src/prompt_compressor.py` -- only imports PREPROC_MODEL_MAP
   - `src/config_commands.py` -- only imports PRICE_TABLE

2. **Mid-level modules** (consumed by run_experiment but not by each other):
   - `src/execution_summary.py` -- imports PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost
   - `src/compute_derived.py` -- imports MODELS

3. **Top-level pipeline modules**:
   - `src/run_experiment.py` -- imports PREPROC_MODEL_MAP, compute_cost
   - `src/pilot.py` -- imports MODELS
   - `scripts/generate_matrix.py` -- imports MODELS (with --models CLI addition)
   - `src/setup_wizard.py` -- imports MODELS, PREPROC_MODEL_MAP

4. **Shim removal** (final cleanup):
   - Remove from `src/config.py`: `_RegistryBackedDict`, `_LazyModels`, `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`, `compute_cost`, and all `_build_*` helpers
   - Keep: `ExperimentConfig`, `derive_seed`, `NOISE_TYPES`, `INTERVENTIONS`, `MAX_TOKENS_BY_BENCHMARK`, `OPENROUTER_BASE_URL`

### Anti-Patterns to Avoid
- **Importing registry and shim simultaneously:** Never have both `from src.config import PRICE_TABLE` and `from src.model_registry import registry` in the same file. Complete the migration for each file.
- **Accessing registry._models directly:** Prefer public methods (get_price, get_preproc, etc.). Exception: `handle_list_models` needs to iterate all models, which requires `registry._models.keys()` or adding a public `all_models()` method.
- **Changing registry API in this phase:** The registry is frozen from Phase 16. If something is missing, add a thin wrapper in the consumer, not a registry change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model list lookup | Custom filtering of config dicts | `registry.target_models()` | Already implemented, tested |
| Cost computation | Inline math with price tables | `registry.compute_cost()` | Handles unknown models, warns once |
| Preproc model mapping | Dict with ValueError on miss | `registry.get_preproc()` + fallback | Returns None for unknown, no crash |
| Rate limit delays | Hardcoded delay dicts | `registry.get_delay()` | Returns 0.5s default for unknown |

## Common Pitfalls

### Pitfall 1: generate_matrix.py Import Path
**What goes wrong:** `generate_matrix.py` uses `sys.path.insert(0, ...)` to import from `src/` without the `src.` prefix. It imports `from config import MODELS` not `from src.config import MODELS`.
**Why it happens:** Scripts in `scripts/` are outside the `src/` package.
**How to avoid:** When migrating, import from `model_registry` using the same sys.path trick: `from model_registry import registry`. Or change to absolute import with package prefix.
**Warning signs:** ImportError when running `python scripts/generate_matrix.py` directly.

### Pitfall 2: prompt_compressor ValueError Removal
**What goes wrong:** Current `_get_preproc_model()` raises `ValueError` for unknown models. Changing to permissive mode requires updating all tests that expect ValueError.
**Why it happens:** Tests explicitly assert `pytest.raises(ValueError)` for unknown model lookups.
**How to avoid:** Update the function to warn and return the model itself as fallback. Update test expectations simultaneously.
**Warning signs:** Test failures in `test_prompt_compressor.py`.

### Pitfall 3: run_experiment --model Choices
**What goes wrong:** `_build_parser()` line 551 has `choices=["claude", "gemini", "all"]`. This hard-limits which model prefixes are accepted.
**Why it happens:** Original design only supported two providers.
**How to avoid:** Remove the `choices` constraint. Use registry to validate model exists, or accept any string (the engine already validates per-call). Consider accepting full model IDs or provider prefixes.
**Warning signs:** `argparse` rejects valid model names at CLI level.

### Pitfall 4: _rate_delays Initialization in api_client.py
**What goes wrong:** Line 36 in api_client.py: `_rate_delays: dict[str, float] = dict(RATE_LIMIT_DELAYS)`. This is a module-level snapshot. If registry changes after import, _rate_delays is stale.
**Why it happens:** Module-level evaluation happens at import time.
**How to avoid:** Initialize from registry at module level: `_rate_delays = {m: registry.get_delay(m) for m in registry._models}`. This is the same behavior (snapshot at import time) but pulls from registry. The adaptive backoff logic already modifies _rate_delays in-place during execution, so a snapshot is correct.
**Warning signs:** None -- this is actually fine as-is since the adaptive logic updates it.

### Pitfall 5: setup_wizard.py Module-Level PROVIDERS Dict
**What goes wrong:** `PROVIDERS` dict is built at import time using list comprehensions over `MODELS`. After migration, it must use `registry.target_models()` at import time.
**Why it happens:** Module-level code executes during import.
**How to avoid:** Build PROVIDERS dict using registry at module level (same timing). Or make it a function that builds dynamically on first access. Module-level is fine since registry is initialized at import time from default_models.json.

### Pitfall 6: Test Files That Import Shims for Assertion
**What goes wrong:** `tests/test_prompt_repeater.py` imports `PRICE_TABLE` and `compute_cost` to test config module features. After shim removal, these imports break.
**Why it happens:** Tests were written against config.py API.
**How to avoid:** Migrate test imports to use `from src.model_registry import registry` and call `registry.get_price()` / `registry.compute_cost()`.
**Warning signs:** ImportError in test collection after shim removal.

## Code Examples

### Pattern: Migrating a Simple Dict Lookup

```python
# BEFORE (e.g., api_client.py)
from src.config import RATE_LIMIT_DELAYS

_rate_delays: dict[str, float] = dict(RATE_LIMIT_DELAYS)

# AFTER
from src.model_registry import registry

_rate_delays: dict[str, float] = {
    m: registry.get_delay(m) for m in registry._models
}
```

### Pattern: Migrating compute_cost

```python
# BEFORE (e.g., run_experiment.py)
from src.config import compute_cost

main_input_cost = compute_cost(item["model"], response.input_tokens, 0)

# AFTER
from src.model_registry import registry

main_input_cost = registry.compute_cost(item["model"], response.input_tokens, 0)
```

### Pattern: Migrating MODELS Iteration

```python
# BEFORE (e.g., compute_derived.py)
from src.config import MODELS

for model in MODELS:
    ...

# AFTER
from src.model_registry import registry

for model in registry.target_models():
    ...
```

### Pattern: Permissive Preproc Lookup

```python
# BEFORE (prompt_compressor.py)
from src.config import PREPROC_MODEL_MAP

def _get_preproc_model(main_model: str) -> str:
    if main_model not in PREPROC_MODEL_MAP:
        raise ValueError(...)
    return PREPROC_MODEL_MAP[main_model]

# AFTER
from src.model_registry import registry

def _get_preproc_model(main_model: str) -> str:
    preproc = registry.get_preproc(main_model)
    if preproc is None:
        logger.warning(
            "No pre-processor mapping for '%s'; using model itself as fallback",
            main_model,
        )
        return main_model
    return preproc
```

### Pattern: generate_matrix.py with --models Override

```python
# AFTER (scripts/generate_matrix.py)
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from model_registry import registry

def generate_matrix(prompts_path, config=None, models=None):
    if models is None:
        models = registry.target_models()
    # ... use models in loops ...

# CLI
parser.add_argument(
    "--models",
    type=str,
    default=None,
    help="Comma-separated model IDs (default: all configured target models)",
)
args = parser.parse_args()
models = args.models.split(",") if args.models else None
matrix = generate_matrix(args.prompts, models=models)
```

### Pattern: PRICE_TABLE Dict -> Registry in handle_list_models

```python
# BEFORE (config_commands.py)
from src.config import PRICE_TABLE

def handle_list_models(args):
    for model, prices in sorted(PRICE_TABLE.items()):
        inp = prices["input_per_1m"]
        out = prices["output_per_1m"]
        ...

# AFTER
from src.model_registry import registry

def handle_list_models(args):
    for model_id in sorted(registry._models):
        inp, out = registry.get_price(model_id)
        ...
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml / pytest.ini (project root) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 | Matrix generation uses configured models | unit | `pytest tests/test_matrix.py -x` | Exists (needs update) |
| EXP-02 | --model flag works with any configured model | unit | `pytest tests/test_run_experiment.py -x` | Exists (needs update) |
| EXP-03 | Pilot adapts to configured models | unit | `pytest tests/test_pilot.py -x` | Exists (needs update) |
| EXP-04 | Derived metrics uses configured models | unit | `pytest tests/test_compute_derived.py -x` | Exists (needs update) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (full suite, fail-fast)
- **Per wave merge:** `pytest tests/ -v` (full suite, verbose)
- **Phase gate:** Full 541-test suite green before verification

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. Tests need import updates, not new test files.

## Open Questions

1. **registry._models Access Pattern**
   - What we know: `handle_list_models` and `api_client._rate_delays` need to iterate all model IDs. Currently requires accessing `registry._models` (private).
   - What's unclear: Whether to add a public `all_model_ids()` method or accept `_models` access.
   - Recommendation: Accept `_models` access for now. It's a simple project-internal module, not a published library. A public accessor could be added later if needed.

2. **run_experiment --model Flag Semantics**
   - What we know: Currently accepts "claude", "gemini", or "all" as provider-prefix filters. Must now accept any configured model or provider prefix.
   - What's unclear: Whether to accept full model IDs (e.g., `--model claude-sonnet-4-20250514`) or keep provider-prefix style (e.g., `--model claude`), or both.
   - Recommendation: Accept any string. If it matches a full model ID, filter to that exact model. If it matches a provider prefix, filter by prefix. "all" runs everything. Remove argparse `choices=` constraint.

## Sources

### Primary (HIGH confidence)
- `src/model_registry.py` -- read in full, all registry methods verified
- `src/config.py` -- read in full, shim implementation verified
- All 9 consumer source files -- read in full, all import statements catalogued
- All 7 consumer test files -- imports verified via grep
- 541 tests confirmed passing via `pytest tests/ --co -q`

### Secondary (MEDIUM confidence)
- `.planning/phases/17-registry-consumers/17-CONTEXT.md` -- user decisions locked

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all methods already implemented in Phase 16
- Architecture: HIGH -- mechanical refactoring with clear before/after patterns for every module
- Pitfalls: HIGH -- every consumer file read in full, all import sites catalogued via grep

**Research date:** 2026-03-26
**Valid until:** No expiry (internal refactoring, no external dependency changes)
