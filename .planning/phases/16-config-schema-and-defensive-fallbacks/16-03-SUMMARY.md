---
phase: 16-config-schema-and-defensive-fallbacks
plan: 03
subsystem: config
tags: [dataclass, migration, model-registry, env-manager, config-manager]

# Dependency graph
requires:
  - phase: 16-01
    provides: ModelConfig, ModelRegistry, _load_default_models, registry singleton, data/default_models.json
  - phase: 16-02
    provides: load_env(), write_env(), check_keys() in src/env_manager.py
provides:
  - Mutable ExperimentConfig v2 with models list field and config_version
  - Auto-migration from v1 flat-field configs to v2 models list with .bak backup
  - Integrated env loading and registry reload in load_config()
  - Warn-not-reject validation for unknown model IDs
  - Registry-backed backward-compat shims for MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost
affects: [phase-17-consumer-migration, phase-19-wizard]

# Tech tracking
tech-stack:
  added: [shutil]
  patterns: [registry-backed backward-compat shims, v1-to-v2 config migration with backup]

key-files:
  created: []
  modified:
    - src/config.py
    - src/config_manager.py
    - src/config_commands.py
    - tests/test_config.py
    - tests/test_config_manager.py
    - tests/test_config_commands.py
    - tests/test_integration.py
    - tests/test_prompt_repeater.py

key-decisions:
  - "Added registry-backed backward-compat shims for MODELS/PRICE_TABLE/PREPROC_MODEL_MAP/RATE_LIMIT_DELAYS/compute_cost to keep full test suite passing until Phase 17 migrates consumers"
  - "validate_config warns on unknown models/providers via logging.warning instead of returning errors"

patterns-established:
  - "Registry-backed shims: _RegistryBackedDict and _LazyModels delegate to live registry data"
  - "Config migration: detect v1 by missing config_version, backup with .bak, map flat fields to models list"

requirements-completed: [CFG-04, CFG-05]

# Metrics
duration: 6min
completed: 2026-03-26
---

# Phase 16 Plan 03: ExperimentConfig v2, Config Migration, and Pipeline Integration Summary

**Mutable ExperimentConfig with models list, v1-to-v2 auto-migration with backup, load_config integrates env loading and registry reload, validate_config warns instead of rejecting unknown models**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-26T00:07:35Z
- **Completed:** 2026-03-26T00:13:35Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- ExperimentConfig converted from frozen dataclass with flat model fields to mutable dataclass with models list and config_version
- Old hardcoded constants (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost) replaced with registry-backed shims
- Config migration auto-converts v1 flat-field configs to v2 models list format with .bak backup
- load_config() now calls load_env() first and reloads the registry from config models
- validate_config() warns (not rejects) on unknown model IDs and providers
- Full test suite (541 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update ExperimentConfig and remove old constants from config.py** - `68841da` (feat)
2. **Task 2: Add migration logic, env loading, and registry reload to config_manager.py** - `0aa8850` (feat)

## Files Created/Modified
- `src/config.py` - Mutable ExperimentConfig v2 with models list, registry-backed backward-compat shims
- `src/config_manager.py` - Migration logic, env loading, registry reload, updated validation
- `src/config_commands.py` - Updated FIELD_DESCRIPTIONS for new ExperimentConfig fields
- `tests/test_config.py` - New mutability/models tests, removed frozen/old-field tests
- `tests/test_config_manager.py` - Migration tests, updated validation tests, load_env mocking
- `tests/test_config_commands.py` - Updated for new field count and validation behavior
- `tests/test_integration.py` - Replaced config.claude_model with hardcoded model string
- `tests/test_prompt_repeater.py` - Updated test_unknown_model to expect $0.00 instead of KeyError

## Decisions Made
- **Registry-backed backward-compat shims**: The plan specified removing old constants entirely, but 20+ consumer files import them. Rather than breaking the full test suite (which the plan also required to pass), added thin shims that delegate to the live registry. Phase 17 will remove these when consumers migrate. The hardcoded DATA is removed; the NAMES remain as dynamic proxies.
- **validate_config stops validating flat model fields**: Old model_fields validation block (claude_model, gemini_model, etc.) removed entirely. New validation checks the models list and warns on unknown model_ids/providers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added registry-backed backward-compat shims in config.py**
- **Found during:** Task 1
- **Issue:** Removing MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost from config.py would break 20+ consumer modules and their tests (8 source files + 12 test files), causing full test suite failure
- **Fix:** Added _RegistryBackedDict, _LazyModels shims and a compute_cost wrapper that delegate to the live ModelRegistry. Hardcoded data is gone; the names are dynamic proxies.
- **Files modified:** src/config.py
- **Verification:** Full test suite (541 tests) passes
- **Committed in:** 68841da (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test_config_commands.py for new ExperimentConfig shape**
- **Found during:** Task 2
- **Issue:** Tests expected 13 fields, validated against old claude_model field, and used hardcoded field count
- **Fix:** Updated FIELD_DESCRIPTIONS in config_commands.py, changed tests to use dynamic field count and valid validation errors
- **Files modified:** src/config_commands.py, tests/test_config_commands.py
- **Verification:** All config_commands tests pass
- **Committed in:** 0aa8850 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed test_integration.py config.claude_model reference**
- **Found during:** Task 2
- **Issue:** Integration test accessed config.claude_model which no longer exists
- **Fix:** Replaced with hardcoded model string "claude-sonnet-4-20250514"
- **Files modified:** tests/test_integration.py
- **Verification:** Integration test passes
- **Committed in:** 0aa8850 (Task 2 commit)

**4. [Rule 1 - Bug] Fixed test_prompt_repeater.py KeyError expectation**
- **Found during:** Task 2
- **Issue:** Test expected compute_cost to raise KeyError for unknown models; now returns $0.00 per CFG-03
- **Fix:** Changed test to verify $0.00 return value
- **Files modified:** tests/test_prompt_repeater.py
- **Verification:** Test passes
- **Committed in:** 0aa8850 (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 bugs)
**Impact on plan:** All auto-fixes necessary for correctness and test suite stability. The backward-compat shims are the notable addition -- they bridge Phase 16 (registry creation) and Phase 17 (consumer migration) without breaking the codebase.

## Issues Encountered
None beyond the deviation auto-fixes documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 16 is now complete (all 3 plans done)
- Phase 17 (consumer migration) can proceed: swap 20+ consumer imports from old constants to registry methods, then remove backward-compat shims from config.py
- Phase 18 (OpenRouter live pricing) can proceed in parallel
- Phase 19 (wizard updates) can proceed after Phase 17

---
*Phase: 16-config-schema-and-defensive-fallbacks*
*Completed: 2026-03-26*
