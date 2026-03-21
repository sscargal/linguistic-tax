---
phase: 04-pilot-validation
plan: 01
subsystem: experiment
tags: [pilot, stratified-sampling, data-audit, noise-verification, compress-only]

# Dependency graph
requires:
  - phase: 03-execution-engine
    provides: run_experiment.py execution engine, noise_generator, prompt_compressor
provides:
  - Stratified pilot prompt selection (20 prompts: 7 HumanEval + 7 MBPP + 6 GSM8K)
  - Pilot execution orchestrator (run_pilot entry point)
  - Data completeness audit (NULL/zero detection for DB rows)
  - Noise injection rate sanity checker
  - compress_only intervention support in execution engine
  - data/pilot_prompts.json with deterministic seed=42 selection
affects: [04-02-PLAN, phase-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [stratified-sampling-with-seeded-rng, data-completeness-audit-pattern]

key-files:
  created: [src/pilot.py, tests/test_pilot.py, data/pilot_prompts.json]
  modified: [src/run_experiment.py, tests/test_run_experiment.py]

key-decisions:
  - "Used sanitize_and_compress for compress_only since compression instruction handles clean prompts correctly"
  - "Sort prompt ID pools before sampling for cross-platform determinism"

patterns-established:
  - "Stratified sampling: sort pool, then rng.sample() per group for reproducible selection"
  - "Data audit: iterate DB rows checking NULL fields and value constraints, return structured issues list"

requirements-completed: [PILOT-01]

# Metrics
duration: 5min
completed: 2026-03-21
---

# Phase 04 Plan 01: Pilot Core Module Summary

**Stratified 20-prompt pilot selection with compress_only fix, data completeness audit, and noise rate verification**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T00:48:39Z
- **Completed:** 2026-03-21T00:54:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments
- Stratified pilot selection: deterministic seed=42 yields 7 HumanEval + 7 MBPP + 6 GSM8K prompt IDs
- Fixed compress_only intervention in apply_intervention match/case block
- Data completeness audit detects NULL fields, zero token counts, invalid models, and malformed timestamps
- Noise rate verification measures actual vs expected mutation rates with configurable tolerance
- All 246 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `d2b47d5` (test)
2. **Task 1 GREEN: Implementation** - `2c54b27` (feat)

**Plan metadata:** (pending)

_Note: TDD task with RED then GREEN commits_

## Files Created/Modified
- `src/pilot.py` - Pilot module: select_pilot_prompts, filter_pilot_matrix, run_pilot, audit_data_completeness, verify_noise_rates
- `src/run_experiment.py` - Added compress_only case to apply_intervention
- `tests/test_pilot.py` - 12 test functions covering all pilot module functionality
- `tests/test_run_experiment.py` - Added test_apply_intervention_compress_only
- `data/pilot_prompts.json` - 20 selected pilot prompt IDs

## Decisions Made
- Used sanitize_and_compress for compress_only intervention since the compress system prompt already handles clean prompts correctly (no noise to sanitize, just compress)
- Sort prompt ID pools before sampling to ensure cross-platform determinism regardless of JSON load order

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MBPP ID prefix in test assertions**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test used "Mbpp/" prefix but actual MBPP IDs in prompts.json use "mbpp_" prefix
- **Fix:** Changed test assertion from `startswith("Mbpp/")` to `startswith("mbpp_")`
- **Files modified:** tests/test_pilot.py
- **Verification:** All tests pass
- **Committed in:** 2c54b27 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test data mismatch with actual prompt ID format. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pilot prompt selection complete and persisted to data/pilot_prompts.json
- compress_only intervention works in the execution engine
- Data audit and noise verification functions ready for post-pilot analysis
- Plan 04-02 can proceed with actual pilot execution and analysis

---
*Phase: 04-pilot-validation*
*Completed: 2026-03-21*
