---
phase: 07-add-openai-to-the-supported-model-provider
plan: 02
subsystem: experiment-pipeline
tags: [openai, pilot, figures, matplotlib, validation]

requires:
  - phase: 07-01
    provides: "OpenAI provider in config.MODELS, PRICE_TABLE, and api_client"
provides:
  - "Pilot validation accepting GPT-4o via dynamic _VALID_MODELS"
  - "Figure layouts scaling dynamically with model count"
affects: [08-write-unit-tests, pilot-execution]

tech-stack:
  added: []
  patterns: ["Dynamic _VALID_MODELS derived from config.MODELS instead of hardcoded set"]

key-files:
  created: []
  modified:
    - src/pilot.py
    - src/generate_figures.py
    - tests/test_pilot.py
    - tests/test_prompt_repeater.py

key-decisions:
  - "Derive _VALID_MODELS as set(MODELS) from config for automatic propagation of new models"

patterns-established:
  - "Config-driven model sets: downstream modules derive valid model lists from config.MODELS rather than maintaining separate hardcoded sets"

requirements-completed: [OAPI-01, OAPI-05]

duration: 4min
completed: 2026-03-23
---

# Phase 7 Plan 2: Downstream Pipeline Integration Summary

**Dynamic _VALID_MODELS from config.MODELS and scaled figure layouts for 3-model panels**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T23:03:28Z
- **Completed:** 2026-03-23T23:07:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Pilot validation now derives _VALID_MODELS from config.MODELS, auto-accepting GPT-4o
- Figure layouts use dynamic width (3.5 inches per model panel) instead of hardcoded 7-inch width
- Full test suite passes (333 tests, 0 failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update pilot _VALID_MODELS to use config.MODELS** - `5cf1f22` (feat)
2. **Task 2: Widen figure layouts for 3 models and run full suite** - `ce9f047` (feat)

## Files Created/Modified
- `src/pilot.py` - _VALID_MODELS now derived from config.MODELS via set(MODELS)
- `src/generate_figures.py` - figsize width uses 3.5 * max(n_models, 2) for both accuracy curves and quadrant scatter
- `tests/test_pilot.py` - Added TestValidModels class with 4 tests for model presence and config sync
- `tests/test_prompt_repeater.py` - Fixed PRICE_TABLE test to expect 6 models including OpenAI

## Decisions Made
- Derive _VALID_MODELS as set(MODELS) from config for automatic propagation of new models

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PRICE_TABLE model count assertion in test_prompt_repeater.py**
- **Found during:** Task 2 (full suite run)
- **Issue:** test_contains_all_four_models expected 4 models but Plan 01 added 2 OpenAI models to PRICE_TABLE (total 6)
- **Fix:** Updated expected set to include gpt-4o-2024-11-20 and gpt-4o-mini-2024-07-18, renamed test to test_contains_all_six_models
- **Files modified:** tests/test_prompt_repeater.py
- **Verification:** pytest tests/ -x -v passes (333 tests)
- **Committed in:** ce9f047 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test fix necessary for correctness -- Plan 01 added OpenAI models but missed updating this assertion. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OpenAI fully integrated across all pipeline stages
- Phase 07 complete: config, API client, pilot validation, and figures all handle 3 models
- Ready for Phase 08 (unit tests) or experiment execution

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 07-add-openai-to-the-supported-model-provider*
*Completed: 2026-03-23*
