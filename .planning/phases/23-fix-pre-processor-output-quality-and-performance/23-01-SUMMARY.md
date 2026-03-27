---
phase: 23-fix-pre-processor-output-quality-and-performance
plan: 01
subsystem: experiment-engine
tags: [prompt-compressor, preprocessing, token-optimization, noise-aware]

# Dependency graph
requires:
  - phase: 22-experiment-all-caps-emphasis-formatting
    provides: apply_intervention with prompt_id parameter
provides:
  - Noise-aware preproc skip logic (clean and type_b skip preproc API calls)
  - Anti-reasoning system prompt directives for preproc models
  - Token-ratio warning logging for output bloat detection
affects: [run-experiment, pilot, prompt-compressor]

# Tech tracking
tech-stack:
  added: []
  patterns: [noise-aware intervention routing, preproc_skipped metadata]

key-files:
  created: []
  modified:
    - src/prompt_compressor.py
    - src/run_experiment.py
    - tests/test_prompt_compressor.py
    - tests/test_run_experiment.py

key-decisions:
  - "noise_type parameter backward-compatible: empty string default preserves old caller behavior"
  - "Token-ratio warning is informational only, does not trigger fallback"
  - "Anti-reasoning directives added to system prompts, not user messages"

patterns-established:
  - "preproc_skipped metadata pattern: early return with {preproc_skipped: True, preproc_skip_reason: ...}"

requirements-completed: [TODO-preproc-sanitize-accuracy, TODO-preproc-performance-anomaly]

# Metrics
duration: 3min
completed: 2026-03-27
---

# Phase 23 Plan 01: Fix Pre-processor Output Quality and Performance Summary

**Noise-aware preproc skip for clean/ESL prompts, anti-reasoning system prompt hardening, and token-ratio warning logging**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T21:15:54Z
- **Completed:** 2026-03-27T21:18:54Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Preproc interventions now skip API calls for clean and type_b noise types, eliminating accuracy regression from unnecessary preprocessing
- System prompts hardened with "Do not think step by step. Do not reason." to suppress chain-of-thought in reasoning models
- Token-ratio WARNING logged when preproc output exceeds 3x input tokens for observability
- Full backward compatibility preserved -- callers without noise_type parameter work identically to before
- 15 new tests added (7 for prompt_compressor, 8 for run_experiment), all 706 suite tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden system prompts and add token-ratio warning** - `cfc8cf5` (feat)
2. **Task 2: Add noise-aware skip logic in apply_intervention** - `190a3dc` (feat)

_Both tasks followed TDD: RED (failing tests) -> GREEN (implementation) -> verified_

## Files Created/Modified
- `src/prompt_compressor.py` - Anti-reasoning directives in system prompts, token-ratio warning in _process_response
- `src/run_experiment.py` - noise_type parameter on apply_intervention, skip logic for non-type_a noise, threaded from _process_item
- `tests/test_prompt_compressor.py` - 7 new tests for anti-reasoning and token-ratio warning
- `tests/test_run_experiment.py` - 8 new tests for skip logic, no-skip, and backward compatibility

## Decisions Made
- noise_type parameter uses empty string default ("") so existing callers without it continue to run preproc as before
- Token-ratio warning is purely informational -- it does NOT trigger fallback to original text
- Anti-reasoning directives placed in system prompts (not user messages) to keep user message clean
- Updated existing system prompt tests to use constant references instead of hardcoded strings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing system prompt assertion tests**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Existing tests did exact string match on old system prompt values ("You are a text corrector." / "You are a prompt optimizer.")
- **Fix:** Changed assertions to compare against the _SANITIZE_SYSTEM / _COMPRESS_SYSTEM constants
- **Files modified:** tests/test_prompt_compressor.py
- **Verification:** All tests pass
- **Committed in:** cfc8cf5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for test correctness after system prompt changes. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Skip logic and hardened prompts ready for pilot re-run to verify accuracy improvement
- Plan 23-02 can proceed to validate results

---
*Phase: 23-fix-pre-processor-output-quality-and-performance*
*Completed: 2026-03-27*
