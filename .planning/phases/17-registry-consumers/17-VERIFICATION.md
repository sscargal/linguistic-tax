---
phase: 17-registry-consumers
verified: 2026-03-26T01:10:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 17: Registry Consumers Verification Report

**Phase Goal:** Every module that previously imported hardcoded MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, or RATE_LIMIT_DELAYS now reads from the ModelRegistry -- custom models flow through the entire pipeline without hitting allowlist rejections
**Verified:** 2026-03-26T01:10:00Z
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Experiment matrix generation uses configured models, not hardcoded MODELS tuple | VERIFIED | `scripts/generate_matrix.py` line 67: `models = registry.target_models()`; --models CLI override at line 143 |
| 2  | `propt run --model <custom-model>` does not raise "unknown model" errors | VERIFIED | `src/run_experiment.py` line 406: `target_ids = set(registry.target_models())` with smart prefix/exact-ID validation; no `choices=[...]` constraint |
| 3  | Pilot run with subset of providers completes without missing-provider errors | VERIFIED | `src/pilot.py` line 275: `_VALID_MODELS = set(registry.target_models())` -- validation driven by registry not hardcoded set |
| 4  | Derived metrics computation processes exactly the configured models | VERIFIED | `src/compute_derived.py` line 483: `for model in registry.target_models()` |

**Score:** 4/4 ROADMAP success criteria verified

### Plan Must-Have Truths

#### Plan 01 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | api_client.py imports from model_registry, not config shims | VERIFIED | Line 19: `from src.model_registry import registry`; line 38: `registry.get_delay(m) for m in registry._models` |
| 2 | prompt_compressor.py uses registry.get_preproc() with permissive fallback instead of ValueError | VERIFIED | Line 17: `from src.model_registry import registry`; lines 74-80: get_preproc with warn+fallback to model itself |
| 3 | config_commands.py uses registry for model listing instead of PRICE_TABLE | VERIFIED | Line 18: `from src.model_registry import registry`; line 328-329: `registry._models` iteration, `registry.get_price()` |
| 4 | execution_summary.py uses registry methods for all pricing/preproc/delay lookups | VERIFIED | Line 21: `from src.model_registry import registry`; lines 137,141,143,167,245: `registry.compute_cost`, `registry.get_preproc`, `registry.get_delay` |

#### Plan 02 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | compute_derived.py iterates registry.target_models() not hardcoded MODELS | VERIFIED | Line 23: `from src.model_registry import registry`; line 483: `for model in registry.target_models()` |
| 6 | pilot.py derives _VALID_MODELS from registry | VERIFIED | Line 23 import; line 275: `_VALID_MODELS = set(registry.target_models())` |
| 7 | run_experiment.py validates --model against registry not hardcoded choices | VERIFIED | Line 26 import; lines 406-417: registry-based validation with helpful error; no `choices=["claude","gemini","all"]` |
| 8 | generate_matrix.py uses registry with --models override | VERIFIED | Line 18 import; lines 58-67: optional models param defaulting to `registry.target_models()`; line 143: `--models` argparse flag |
| 9 | setup_wizard.py builds PROVIDERS from registry not MODELS import | VERIFIED | Line 19: `from src.model_registry import registry`; lines 29-30: `_build_providers()` using `registry.target_models()` |

#### Plan 03 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 10 | config.py no longer exports MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, or compute_cost | VERIFIED | `grep -cn "_RegistryBackedDict\|_LazyModels\|_build_price_table..."` returns 0; grep for all shim names in config.py returns 0 |
| 11 | Zero shim imports in any src/, tests/, or scripts/ file | VERIFIED | `grep -rn "from src.config import.*MODELS\|PRICE_TABLE\|PREPROC_MODEL_MAP\|RATE_LIMIT_DELAYS\|compute_cost"` across src/ and tests/ returns no matches |

### Required Artifacts

| Artifact | Status | Key Evidence |
|----------|--------|--------------|
| `src/api_client.py` | VERIFIED | `from src.model_registry import registry`; `registry.get_delay(m) for m in registry._models` |
| `src/prompt_compressor.py` | VERIFIED | `registry.get_preproc`; fallback returns `main_model` with warning |
| `src/config_commands.py` | VERIFIED | `registry.get_price`; iterates `sorted(registry._models)` |
| `src/execution_summary.py` | VERIFIED | `registry.compute_cost`; `registry.get_preproc`; `registry.get_delay` |
| `src/compute_derived.py` | VERIFIED | `registry.target_models()` in main loop |
| `src/pilot.py` | VERIFIED | `set(registry.target_models())` for `_VALID_MODELS` |
| `src/run_experiment.py` | VERIFIED | `registry.target_models()` for model validation; `registry.compute_cost` for cost tracking |
| `scripts/generate_matrix.py` | VERIFIED | `registry.target_models()` default; `--models` CLI flag; `args.models.split(",")` override |
| `src/setup_wizard.py` | VERIFIED | `registry.target_models()` via `_build_providers()` |
| `src/config.py` | VERIFIED | Contains only: `ExperimentConfig`, `derive_seed`, `INTERVENTIONS`, `NOISE_TYPES`, `MAX_TOKENS_BY_BENCHMARK`, `OPENROUTER_BASE_URL` |
| `tests/test_integration.py` | VERIFIED | `from src.model_registry import registry` at line 167; `registry.compute_cost` usage |
| `tests/test_prompt_repeater.py` | VERIFIED | Multiple inline `from src.model_registry import registry` imports; no config shim imports |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `src/api_client.py` | `src/model_registry.py` | `registry.get_delay()` | WIRED | Line 38: `registry.get_delay(m) for m in registry._models` |
| `src/prompt_compressor.py` | `src/model_registry.py` | `registry.get_preproc()` with fallback | WIRED | Line 74: `preproc = registry.get_preproc(main_model)` |
| `src/execution_summary.py` | `src/model_registry.py` | `registry.compute_cost/get_price/get_preproc/get_delay` | WIRED | Lines 137, 141, 143, 167, 245 |
| `scripts/generate_matrix.py` | `src/model_registry.py` | `registry.target_models()` | WIRED | Line 67 in `generate_matrix()` function body |
| `src/pilot.py` | `src/model_registry.py` | `set(registry.target_models())` | WIRED | Line 275 |
| `src/compute_derived.py` | `src/model_registry.py` | `registry.target_models()` | WIRED | Line 483 |
| `src/run_experiment.py` | `src/model_registry.py` | `registry.(compute_cost\|target_models)` | WIRED | Lines 285, 286, 290, 406 |

### Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| EXP-01 | 17-02, 17-03 | Experiment matrix generation uses configured models (not hardcoded MODELS tuple) | SATISFIED | `generate_matrix.py` uses `registry.target_models()` as default; `--models` override supported |
| EXP-02 | 17-01, 17-02, 17-03 | `--model` flag on `propt run` works with any configured model | SATISFIED | `run_experiment.py` validates against `registry.target_models()`; no hardcoded choices list |
| EXP-03 | 17-02, 17-03 | Pilot run adapts to configured models | SATISFIED | `pilot.py` `_VALID_MODELS = set(registry.target_models())` |
| EXP-04 | 17-02, 17-03 | Derived metrics computation adapts to configured models | SATISFIED | `compute_derived.py` iterates `registry.target_models()` |

All 4 requirements declared across the 3 plans are accounted for. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/pilot.py` | 295, 298 | `placeholders` variable in SQL string building | Info | Not a stub -- this is a legitimate SQL parameterization pattern; no functional concern |

No TODO/FIXME/PLACEHOLDER markers found in any migrated file. No empty implementations. No stubs detected.

### Human Verification Required

None. All observable truths are verifiable programmatically:
- Import chains are grep-verifiable
- Registry method calls are grep-verifiable
- Shim absence is grep-verifiable
- 541-test suite passed with `pytest tests/ -x -q`

### Test Suite Verification

The full test suite was executed and confirmed passing:

```
541 passed, 4 warnings in 36.05s
```

The 4 warnings are pre-existing pytest mark and statsmodels convergence warnings, unrelated to Phase 17 changes.

### Git Commit Verification

All 6 task commits from the summaries were confirmed to exist in git history:
- `91ecf21` -- refactor(17): migrate api_client and prompt_compressor to model_registry
- `f4f1da5` -- refactor(17): migrate config_commands and execution_summary to model_registry
- `c504081` -- refactor(17-02): migrate compute_derived, pilot, run_experiment to model_registry
- `ba84bce` -- refactor(17-02): migrate generate_matrix and setup_wizard to model_registry
- `c603289` -- refactor(17-03): migrate remaining test files to model_registry
- `1a7977a` -- refactor(17-03): remove backward-compat shims from config.py

### Gaps Summary

No gaps. All must-haves verified. Phase goal fully achieved.

---

_Verified: 2026-03-26T01:10:00Z_
_Verifier: Claude (gsd-verifier)_
