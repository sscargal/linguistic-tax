---
phase: 17-registry-consumers
plan: 02
subsystem: experiment-pipeline
tags: [model-registry, refactoring, cli, experiment-matrix, pilot, compute-derived]

# Dependency graph
requires:
  - phase: 16-model-registry
    provides: ModelRegistry with target_models(), compute_cost(), get_preproc()
provides:
  - Five pipeline modules using registry directly instead of config shims
  - --models CLI override on generate_matrix.py for subset generation
  - Smart --model validation on run_experiment.py (exact ID or provider prefix)
affects: [17-registry-consumers plan 03, 18-openrouter, 19-env-config]

# Tech tracking
tech-stack:
  added: []
  patterns: [registry.target_models() for model iteration, registry.compute_cost() for pricing, registry.get_preproc() for preprocessor lookup]

key-files:
  created: []
  modified:
    - src/compute_derived.py
    - src/pilot.py
    - src/run_experiment.py
    - scripts/generate_matrix.py
    - src/setup_wizard.py
    - tests/test_pilot.py
    - tests/test_matrix.py
    - tests/test_setup_wizard.py

key-decisions:
  - "setup_wizard PROVIDERS built via _build_providers() function to evaluate registry at import time"
  - "run_experiment --model accepts exact model_id or provider prefix with helpful error on mismatch"
  - "generate_matrix accepts optional models parameter, defaulting to registry.target_models()"

patterns-established:
  - "Registry iteration: use registry.target_models() wherever code iterates over configured models"
  - "Registry cost: use registry.compute_cost() instead of standalone compute_cost()"
  - "Registry preproc: use registry.get_preproc() instead of PREPROC_MODEL_MAP dict lookup"

requirements-completed: [EXP-01, EXP-03, EXP-04]

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 17 Plan 02: Pipeline Consumer Migration Summary

**Five core pipeline modules migrated from config.py shims to direct model_registry usage with --models CLI override on generate_matrix.py**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T00:40:34Z
- **Completed:** 2026-03-26T00:44:51Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Migrated compute_derived.py, pilot.py, run_experiment.py, generate_matrix.py, and setup_wizard.py from hardcoded MODELS/PREPROC_MODEL_MAP/compute_cost imports to direct registry usage
- Added --models CLI flag to generate_matrix.py for subset matrix generation
- Replaced hardcoded choices=["claude", "gemini", "all"] on run_experiment.py --model with smart validation (exact model_id, provider prefix, or "all")
- Updated 3 test files to use registry instead of config imports
- All 541 tests pass after migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate compute_derived.py, pilot.py, and run_experiment.py** - `c504081` (refactor)
2. **Task 2: Migrate generate_matrix.py and setup_wizard.py** - `ba84bce` (refactor)

## Files Created/Modified
- `src/compute_derived.py` - Registry-based model iteration for derived metrics
- `src/pilot.py` - Registry-derived _VALID_MODELS set
- `src/run_experiment.py` - Registry-based cost computation and smart model validation
- `scripts/generate_matrix.py` - Registry-based matrix generation with --models override
- `src/setup_wizard.py` - Registry-based provider/model discovery via _build_providers()
- `tests/test_pilot.py` - Updated model validation assertion to use registry
- `tests/test_matrix.py` - Updated model validation to use registry.target_models()
- `tests/test_setup_wizard.py` - Updated provider and preproc assertions to use registry

## Decisions Made
- setup_wizard PROVIDERS built via _build_providers() function rather than module-level dict comprehension, to properly evaluate registry.target_models() at import time
- run_experiment --model now accepts any string: exact model_id match, provider prefix (startswith), or "all" -- with helpful error listing available models on mismatch
- generate_matrix.py generate_matrix() accepts optional models parameter, defaulting to registry.target_models()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All five pipeline consumer modules now use registry directly
- Config.py shims (MODELS, PREPROC_MODEL_MAP, compute_cost) can be removed in plan 03
- Custom models configured via registry flow through entire pipeline: matrix generation, pilot validation, experiment execution, and derived metrics

---
*Phase: 17-registry-consumers*
*Completed: 2026-03-26*

## Self-Check: PASSED
