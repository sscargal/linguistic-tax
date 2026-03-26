---
phase: 17-registry-consumers
plan: 03
subsystem: config
tags: [model-registry, refactoring, shim-removal, backward-compat]

# Dependency graph
requires:
  - phase: 17-registry-consumers (plans 01, 02)
    provides: All consumer modules migrated to registry imports
provides:
  - Clean config.py with no shim code
  - Zero shim imports across entire codebase
  - All test files using model_registry directly
affects: [phase-18-openrouter, phase-19-env-setup]

# Tech tracking
tech-stack:
  added: []
  patterns: [registry-only model access]

key-files:
  created: []
  modified:
    - src/config.py
    - tests/test_integration.py
    - tests/test_prompt_repeater.py
    - scripts/qa_script.sh

key-decisions:
  - "Kept logging import in config.py for standard module logger pattern"

patterns-established:
  - "All model data access goes through src.model_registry.registry singleton"
  - "config.py exports only experiment parameters: ExperimentConfig, derive_seed, INTERVENTIONS, NOISE_TYPES, MAX_TOKENS_BY_BENCHMARK, OPENROUTER_BASE_URL"

requirements-completed: [EXP-01, EXP-02, EXP-03, EXP-04]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 17 Plan 03: Remove Shims Summary

**Removed all backward-compat shims from config.py and migrated remaining test files to model_registry API**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T00:46:40Z
- **Completed:** 2026-03-26T00:50:11Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Migrated test_integration.py and test_prompt_repeater.py from shim imports to registry API
- Deleted 145+ lines of shim infrastructure from config.py (_RegistryBackedDict, _LazyModels, _build_* helpers, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost)
- Updated qa_script.sh smoke tests to use model_registry
- Verified zero shim imports remain across src/, tests/, and scripts/

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate remaining test files to registry imports** - `c603289` (refactor)
2. **Task 2: Remove shims from config.py and update qa_script.sh** - `1a7977a` (refactor)

## Files Created/Modified
- `src/config.py` - Removed all shim classes, functions, and constants (145+ lines deleted)
- `tests/test_integration.py` - OpenRouter lifecycle test uses registry API
- `tests/test_prompt_repeater.py` - TestPriceTable, TestPreprocModelMap, TestComputeCost use registry
- `scripts/qa_script.sh` - Smoke tests updated for registry imports

## Decisions Made
- Kept logging import in config.py for standard module logger pattern (no functional change)
- qa_script.sh ExperimentConfig test updated to check config_version/base_seed instead of removed model fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale ExperimentConfig smoke test in qa_script.sh**
- **Found during:** Task 2
- **Issue:** qa_script.sh referenced c.claude_model, c.gemini_model, c.openai_model which no longer exist on ExperimentConfig
- **Fix:** Updated to check config_version and base_seed; added separate registry target models check
- **Files modified:** scripts/qa_script.sh
- **Verification:** Smoke test Python snippets parse correctly
- **Committed in:** 1a7977a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correction for qa_script.sh to work with current ExperimentConfig schema. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 17 (registry-consumers) is now complete -- all 3 plans executed
- config.py is clean, model_registry is the single source of truth for model data
- Ready for Phase 18 (OpenRouter enhancements) and Phase 19 (env setup)

---
*Phase: 17-registry-consumers*
*Completed: 2026-03-26*
