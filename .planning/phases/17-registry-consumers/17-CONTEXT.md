# Phase 17: Registry Consumers - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate every module that imports hardcoded MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, or RATE_LIMIT_DELAYS to use the ModelRegistry API instead. Remove the backward-compat shims added in Phase 16. Make the experiment pipeline (matrix generation, pilot, derived metrics, run_experiment) work with configured models so custom models flow through the entire pipeline without hitting allowlist rejections.

Requirements: EXP-01, EXP-02, EXP-03, EXP-04.

</domain>

<decisions>
## Implementation Decisions

### Shim removal strategy
- Migrate consumers **module-by-module**, each testable independently
- After all consumers migrated, **remove shims from config.py** as a final cleanup step
- Each consumer migration is a separate commit for easy bisection
- Tests for each module updated in the same commit as the module migration

### Experiment scope adaptation
- `scripts/generate_matrix.py` uses `get_registry().target_models()` instead of hardcoded MODELS tuple (EXP-01)
- `src/run_experiment.py` accepts any model the registry knows about; `--model` flag validates against registry not a hardcoded set (EXP-02)
- `src/pilot.py` adapts `_VALID_MODELS` to be `set(get_registry().target_models())` — runs only configured providers (EXP-03)
- `src/compute_derived.py` iterates over registry target models instead of hardcoded MODELS (EXP-04)
- All four consumers get their model list from the same source: `get_registry().target_models()`

### Model validation strictness
- `src/prompt_compressor.py`: **permissive** — if no preproc mapping exists for a model, warn and use the model itself as fallback (self-preprocessing). No ValueError for unknown models.
- `src/pilot.py`: **permissive** — `_VALID_MODELS` derived from registry, not a hardcoded set. Custom models accepted if they're in the config.
- `src/api_client.py`: **permissive** — `get_delay()` returns default 0.5s for unknown models (already implemented in registry)
- `src/execution_summary.py`: **permissive** — `compute_cost()` returns $0.00 for unknown models (already implemented in registry)
- Pattern: warn once, don't crash, use sensible defaults

### generate_matrix.py handling
- Script uses registry for model list but also accepts `--models` CLI override for flexibility
- Default behavior: generate matrix for all target models in config
- Override: `--models claude-sonnet-4-20250514,gemini-2.0-flash` generates for specific models only

### Claude's Discretion
- Order of module migrations (any dependency-safe order is fine)
- Exact import patterns (from src.model_registry import get_registry vs other)
- Test fixture organization for registry-based tests
- Whether to add helper functions in individual modules or call registry directly

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specification
- `docs/RDD_Linguistic_Tax_v4.md` -- Research Design Document defining experimental parameters and model requirements

### Requirements
- `.planning/REQUIREMENTS.md` -- v2.0 requirements EXP-01 through EXP-04 (all mapped to Phase 17)

### Phase 16 foundation (what was built)
- `src/model_registry.py` -- ModelConfig dataclass, ModelRegistry class, get_registry() singleton, compute_cost(), get_price(), get_preproc(), get_delay(), target_models()
- `data/default_models.json` -- Default model configs for all 8 models
- `src/config.py` -- Current backward-compat shims (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost) that delegate to registry -- these must be removed after migration

### Consumer modules to migrate
- `src/api_client.py` -- Uses RATE_LIMIT_DELAYS for rate limiting
- `src/compute_derived.py` -- Uses MODELS for iteration, INTERVENTIONS, NOISE_TYPES
- `src/config_commands.py` -- Uses PRICE_TABLE for list-models display
- `src/prompt_compressor.py` -- Uses PREPROC_MODEL_MAP with strict validation (ValueError)
- `src/execution_summary.py` -- Uses PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost
- `src/run_experiment.py` -- Uses PREPROC_MODEL_MAP, compute_cost
- `src/pilot.py` -- Uses MODELS for _VALID_MODELS set
- `scripts/generate_matrix.py` -- Uses MODELS for matrix generation
- `tests/test_matrix.py` -- Uses MODELS, INTERVENTIONS, NOISE_TYPES
- `tests/test_config_commands.py` -- Uses PRICE_TABLE
- `tests/test_prompt_repeater.py` -- Uses PRICE_TABLE, compute_cost
- `tests/test_integration.py` -- Uses MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, compute_cost

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_registry()` singleton -- all consumers should use this as the entry point
- `registry.target_models()` -- returns list of target model IDs, replaces MODELS tuple
- `registry.compute_cost()` -- replaces standalone compute_cost() in config.py
- `registry.get_price()` -- replaces PRICE_TABLE dict lookups
- `registry.get_preproc()` -- replaces PREPROC_MODEL_MAP dict lookups
- `registry.get_delay()` -- replaces RATE_LIMIT_DELAYS dict lookups

### Established Patterns
- Phase 16 added backward-compat shims so all 541 tests still pass -- Phase 17 migrates consumers then removes shims
- Registry uses warn-once pattern (_warned_unknown set) for unknown models
- All registry methods return sensible defaults for unknown models (no crashes)

### Integration Points
- `config.py` shim removal is the final step -- only safe after all consumers migrated
- `generate_matrix.py` in scripts/ imports from config without src prefix (uses sys.path manipulation)
- INTERVENTIONS and NOISE_TYPES stay in config.py (not moving to registry -- they're not model-related)

</code_context>

<specifics>
## Specific Ideas

- The migration should preserve the existing 541-test suite passing at every intermediate step
- Each module migration should be a clean atomic commit
- generate_matrix.py's --models flag enables future CI matrix customization

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 17-registry-consumers*
*Context gathered: 2026-03-26*
