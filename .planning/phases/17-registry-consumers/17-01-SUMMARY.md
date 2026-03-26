---
phase: 17-registry-consumers
plan: 01
subsystem: config
tags: [model-registry, refactoring, migration]

# Dependency graph
requires:
  - phase: 16-config-schema-and-defensive-fallbacks
    provides: ModelRegistry singleton with get_price/get_preproc/get_delay/compute_cost API
provides:
  - Four leaf consumer modules (api_client, prompt_compressor, config_commands, execution_summary) using registry directly
  - Permissive preproc fallback (warn + self-preprocess) instead of ValueError crash
affects: [17-02, 17-03]

# Tech tracking
tech-stack:
  added: []
  patterns: ["registry.get_delay(model) for rate limit lookups", "registry.get_preproc(model) or fallback for permissive preproc resolution"]

key-files:
  created: []
  modified: [src/api_client.py, src/prompt_compressor.py, src/config_commands.py, src/execution_summary.py, tests/test_prompt_compressor.py, tests/test_execution_summary.py, tests/test_config_commands.py]

key-decisions:
  - "Unknown preproc models warn and return model-itself as fallback instead of raising ValueError"

patterns-established:
  - "Registry consumer pattern: import registry singleton, call registry.get_X() methods instead of config shim constants"

requirements-completed: [EXP-02]

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 17 Plan 01: Leaf Consumer Migration Summary

**Migrated api_client, prompt_compressor, config_commands, and execution_summary from config shim constants to model_registry singleton lookups**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T00:40:31Z
- **Completed:** 2026-03-26T00:44:36Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- All four leaf consumer modules now import from model_registry instead of config shims (RATE_LIMIT_DELAYS, PREPROC_MODEL_MAP, PRICE_TABLE, compute_cost)
- prompt_compressor uses permissive fallback for unknown preproc models (warn + self-preprocess) instead of crashing with ValueError
- Full 541-test suite passes after migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate api_client.py and prompt_compressor.py** - `91ecf21` (refactor)
2. **Task 2: Migrate config_commands.py and execution_summary.py** - `f4f1da5` (refactor)

## Files Created/Modified
- `src/api_client.py` - Registry-based rate limit delay initialization
- `src/prompt_compressor.py` - Permissive preproc lookup via registry with fallback
- `src/config_commands.py` - Registry-based model listing in handle_list_models
- `src/execution_summary.py` - Registry-based cost/preproc/delay lookups throughout
- `tests/test_prompt_compressor.py` - Updated unknown model test from ValueError to fallback assertion
- `tests/test_execution_summary.py` - Replaced config shim imports with registry
- `tests/test_config_commands.py` - Replaced PRICE_TABLE import with registry

## Decisions Made
- Unknown preproc models warn and return the model itself as fallback instead of raising ValueError (aligns with registry's defensive design philosophy from Phase 16)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All leaf consumers migrated; Plan 02 (pipeline consumers) can proceed
- Backward-compat shims in config.py still exist for non-leaf consumers (to be removed in Plan 03)

---
*Phase: 17-registry-consumers*
*Completed: 2026-03-26*
