---
phase: 03-interventions-and-execution-engine
plan: 01
subsystem: interventions
tags: [prompt-repeater, prompt-compressor, sanitizer, self-correct, pricing, config]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: ExperimentConfig dataclass, derive_seed, NOISE_TYPES, INTERVENTIONS, MODELS
provides:
  - repeat_prompt() pure function for prompt repetition intervention
  - sanitize() and sanitize_and_compress() with fallback logic for pre-processor interventions
  - build_self_correct_prompt() for self-correct intervention
  - SELF_CORRECT_PREFIX matching RDD Section 6 wording
  - PRICE_TABLE for 4 models (Sonnet, Haiku, Pro, Flash)
  - MAX_TOKENS_BY_BENCHMARK for HumanEval/MBPP/GSM8K
  - PREPROC_MODEL_MAP for vendor-matched pre-processor routing
  - RATE_LIMIT_DELAYS per model
  - compute_cost() function
affects: [03-02 api_client, 03-03 execution engine, 04 pilot execution]

# Tech tracking
tech-stack:
  added: []
  patterns: [callable injection for API mocking, fallback-on-bad-output pattern]

key-files:
  created:
    - src/prompt_repeater.py
    - src/prompt_compressor.py
    - tests/test_prompt_repeater.py
    - tests/test_prompt_compressor.py
  modified:
    - src/config.py

key-decisions:
  - "Callable injection pattern for API calls in prompt_compressor -- accepts call_fn parameter instead of importing api_client, avoiding circular deps and enabling easy mocking"
  - "SELF_CORRECT_PREFIX and build_self_correct_prompt placed in prompt_compressor.py as the intervention module"
  - "Shared _process_response helper for DRY fallback logic between sanitize() and sanitize_and_compress()"

patterns-established:
  - "Callable injection: intervention functions accept call_fn parameter for testability"
  - "Fallback pattern: return raw input + preproc_failed=True metadata when pre-processor output is empty or >1.5x input length"
  - "MockAPIResponse dataclass for test fixtures simulating API responses"

requirements-completed: [INTV-01, INTV-02, INTV-03, INTV-04]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 03 Plan 01: Intervention Functions Summary

**Prompt repeater, sanitizer/compressor with fallback logic, self-correct prefix, and config pricing table for 4 models**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T21:45:50Z
- **Completed:** 2026-03-20T21:51:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Config extended with PRICE_TABLE (4 models), MAX_TOKENS_BY_BENCHMARK, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, and compute_cost()
- prompt_repeater.py with repeat_prompt() pure function implementing Leviathan et al. technique
- prompt_compressor.py with sanitize(), sanitize_and_compress(), build_self_correct_prompt(), and robust fallback logic
- 43 tests total (20 repeater/config + 23 compressor) all passing with mocked API calls

## Task Commits

Each task was committed atomically:

1. **Task 1: Config additions + prompt_repeater.py + tests** - `1b05886` (feat)
2. **Task 2: prompt_compressor.py tests with mocked API** - `22cf610` (test)

_Note: TDD tasks -- prompt_compressor.py implementation was included in Task 1 commit alongside config and repeater._

## Files Created/Modified
- `src/config.py` - Added PRICE_TABLE, MAX_TOKENS_BY_BENCHMARK, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, compute_cost()
- `src/prompt_repeater.py` - Pure repeat_prompt() function with Leviathan et al. docstring
- `src/prompt_compressor.py` - sanitize(), sanitize_and_compress(), build_self_correct_prompt(), SELF_CORRECT_PREFIX, _get_preproc_model()
- `tests/test_prompt_repeater.py` - 20 tests covering repeater, config, self-correct prefix
- `tests/test_prompt_compressor.py` - 23 tests covering sanitize, compress, fallback, model mapping

## Decisions Made
- Used callable injection pattern (call_fn parameter) instead of importing api_client directly -- avoids circular dependencies and makes testing trivial with mock functions
- Placed SELF_CORRECT_PREFIX and build_self_correct_prompt in prompt_compressor.py as the intervention module (not a separate file)
- Created shared _process_response helper to DRY the fallback logic between sanitize() and sanitize_and_compress()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All intervention pure functions importable and tested
- Config has complete pricing/tokens/model mapping for Plan 02 (api_client) and Plan 03 (execution engine)
- prompt_compressor.py ready to receive real call_fn from api_client.call_model once that module exists

---
*Phase: 03-interventions-and-execution-engine*
*Completed: 2026-03-20*
