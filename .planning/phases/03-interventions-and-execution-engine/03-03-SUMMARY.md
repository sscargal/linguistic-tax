---
phase: 03-interventions-and-execution-engine
plan: 03
subsystem: execution-engine
tags: [intervention-router, execution-engine, resumability, inline-grading, cli, match-case]

# Dependency graph
requires:
  - phase: 03-interventions-and-execution-engine plan 01
    provides: repeat_prompt, sanitize, sanitize_and_compress, build_self_correct_prompt, config pricing/tokens
  - phase: 03-interventions-and-execution-engine plan 02
    provides: call_model, APIResponse, _validate_api_keys
  - phase: 01-foundation
    provides: ExperimentConfig, derive_seed, init_database, insert_run, query_runs, save_grade_result
  - phase: 02-grading-pipeline
    provides: grade_run, GradeResult
provides:
  - "apply_intervention() dispatching all 5 strategies via match/case"
  - "make_run_id() for deterministic run IDs from matrix items"
  - "run_engine() with full resumability via completed/failed tracking"
  - "_process_item() pipeline: noise->intervention->API->grade->DB"
  - "CLI with --model, --limit, --retry-failed, --dry-run, --db flags"
  - "Inline grading immediately after each API response"
  - "_order_by_model() for provider-grouped deterministic execution order"
affects: [04 pilot execution, 05 analysis]

# Tech tracking
tech-stack:
  added: []
  patterns: [match-case intervention router, provider-grouped execution order, inline-grading pipeline]

key-files:
  created:
    - src/run_experiment.py
    - tests/test_run_experiment.py
  modified:
    - src/noise_generator.py
    - src/prompt_compressor.py
    - tests/test_noise_generator.py
    - tests/test_prompt_compressor.py
    - tests/test_prompt_repeater.py
    - tests/test_matrix.py

key-decisions:
  - "Standardized all imports to src. prefix across the entire project for consistency with api_client.py pattern"
  - "Noise applied at runtime from clean prompts using derive_seed, not stored as separate noisy text in matrix"
  - "Failed items excluded from pending list and only re-added when --retry-failed is active, preventing duplicates"

patterns-established:
  - "Intervention router: match/case dispatching to pure functions for each of 5 strategies"
  - "Resumability: query completed run_ids on startup, skip those, process remaining"
  - "Inline grading: grade_run called immediately after API response, results persisted with save_grade_result"

requirements-completed: [INTV-05, EXEC-03, EXEC-04]

# Metrics
duration: 11min
completed: 2026-03-20
---

# Phase 03 Plan 03: Execution Engine Summary

**Intervention router dispatching 5 strategies via match/case, execution engine with DB resumability and inline grading, and full CLI with --model/--limit/--retry-failed/--dry-run**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-20T21:57:01Z
- **Completed:** 2026-03-20T22:08:01Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Intervention router dispatches raw, self_correct, prompt_repetition, pre_proc_sanitize, pre_proc_sanitize_compress via Python match/case
- Execution engine loads experiment matrix, skips completed runs, processes pending items through noise->intervention->API->grade->DB pipeline
- Full CLI with --model (claude/gemini/all), --limit N, --retry-failed, --dry-run, --db override
- 29 tests covering router dispatch, run_id generation, model ordering, engine resumability, retry-failed, limit, dry-run, model filter, progress logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Intervention router and deterministic run_id** - `5150e1b` (test RED) + `20b47cb` (feat GREEN)
2. **Task 2: Execution engine with resumability, inline grading, CLI** - `9aac8dc` (feat)

## Files Created/Modified
- `src/run_experiment.py` - Intervention router, execution engine, CLI entry point
- `tests/test_run_experiment.py` - 29 tests for router, engine, resumability, CLI
- `src/noise_generator.py` - Fixed import to use src. prefix
- `src/prompt_compressor.py` - Fixed import to use src. prefix
- `tests/test_noise_generator.py` - Updated imports to src. prefix, CLI test to use -m flag
- `tests/test_prompt_compressor.py` - Updated imports to src. prefix
- `tests/test_prompt_repeater.py` - Updated imports to src. prefix
- `tests/test_matrix.py` - Updated imports to src. prefix

## Decisions Made
- Standardized all imports project-wide to use `from src.` prefix, matching the pattern established by api_client.py. This ensures consistent import resolution regardless of how modules are invoked.
- Noise is applied at runtime from clean prompt text using `derive_seed()` for deterministic noise generation, rather than storing pre-noised text in the matrix.
- Failed items are excluded from the initial pending list and only re-added when `--retry-failed` is explicitly used, preventing duplicate processing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Standardized bare imports to src. prefix across project**
- **Found during:** Task 1 (import chain from run_experiment -> noise_generator -> config)
- **Issue:** noise_generator.py and prompt_compressor.py used bare imports (`from config import`), causing ModuleNotFoundError when imported via `from src.noise_generator import`
- **Fix:** Changed all bare imports to `from src.` prefix in source and test files
- **Files modified:** src/noise_generator.py, src/prompt_compressor.py, tests/test_noise_generator.py, tests/test_prompt_compressor.py, tests/test_prompt_repeater.py, tests/test_matrix.py
- **Verification:** Full test suite (234 tests) passes
- **Committed in:** 20b47cb (Task 1 commit)

**2. [Rule 1 - Bug] Fixed retry-failed duplicate processing**
- **Found during:** Task 2 (engine tests)
- **Issue:** Failed items appeared in both the initial pending list (not in completed_runs) and the retry-failed additions, causing duplicate processing and IntegrityError
- **Fix:** Exclude failed run_ids from initial pending list, only re-add when --retry-failed is active
- **Verification:** test_engine_retry_failed passes
- **Committed in:** 9aac8dc (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct operation. Import standardization improves project consistency. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full execution pipeline ready: matrix -> noise -> intervention -> API -> grade -> DB
- CLI ready for pilot execution (Phase 4) with --limit flag for controlled runs
- All 234 tests pass across the full project

---
*Phase: 03-interventions-and-execution-engine*
*Completed: 2026-03-20*
