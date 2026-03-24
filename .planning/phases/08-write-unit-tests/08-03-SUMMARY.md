---
phase: 08-write-unit-tests
plan: 03
subsystem: testing
tags: [bash, qa, ci, smoke-test, validation]

# Dependency graph
requires:
  - phase: 01-project-config
    provides: ExperimentConfig, derive_seed, data files
  - phase: 02-grading-pipeline
    provides: grade_results CLI module
  - phase: 03-api-and-preprocessing
    provides: noise_generator, prompt_compressor, api_client modules
  - phase: 04-pilot-validation
    provides: pilot CLI module
  - phase: 05-analysis-pipeline
    provides: analyze_results, compute_derived CLI modules
  - phase: 06-figure-generation
    provides: generate_figures CLI module
provides:
  - Unified QA runner script (scripts/qa_script.sh)
  - Pre-release validation checklist covering 6 areas
  - CI-compatible exit codes (non-zero on failure)
affects: [ci-cd, release-process]

# Tech tracking
tech-stack:
  added: []
  patterns: [section-based-qa-runner, venv-auto-activation, ansi-color-logging]

key-files:
  created: [scripts/qa_script.sh]
  modified: []

key-decisions:
  - "Auto-activate project venv if VIRTUAL_ENV not set and .venv/bin/activate exists"
  - "Use inject_type_a_noise Python function directly instead of CLI for functional smoke test (CLI requires --input file)"
  - "Adapted derive_seed test to use correct 4-arg signature (base_seed, prompt_id, noise_type, noise_level)"

patterns-established:
  - "Section-based QA: each validation area is an independent function callable via --section flag"
  - "Three-tier check status: PASS (green, counted), FAIL (red, counted, triggers non-zero exit), WARN (yellow, counted, non-fatal)"

requirements-completed: [TEST-06]

# Metrics
duration: 8min
completed: 2026-03-24
---

# Phase 08 Plan 03: QA Script Summary

**Comprehensive bash QA runner with 6 validation sections (env, pytest, cli, data, config, api), color-coded output, and PASS/FAIL VERDICT**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-24T00:19:47Z
- **Completed:** 2026-03-24T00:27:29Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created 493-line QA script covering all project validation needs
- 6 sections: environment checks (Python, packages, dirs), pytest runner, CLI smoke tests for 7 modules, data pipeline validation, config validation, live API tests
- Supports --live, --section, and --log flags for flexible execution
- Full offline run completes with 33 PASS, 0 FAIL, 2 INFO

## Task Commits

Each task was committed atomically:

1. **Task 1: Create scripts/qa_script.sh with all 6 sections** - `dcca865` (feat)

_Note: Script was committed as part of the 08-01 plan execution batch. Content verified correct and all acceptance criteria pass._

## Files Created/Modified
- `scripts/qa_script.sh` - Unified QA runner with section-based execution, color output, ANSI log stripping, and CI-compatible exit codes

## Decisions Made
- Auto-activate project venv on script start to ensure packages are available without manual activation
- Used Python function call (inject_type_a_noise) for noise generator functional test since CLI requires --input file path, not inline text
- Fixed derive_seed invocation to use correct 4-argument signature matching config.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed noise generator functional test parameter name**
- **Found during:** Task 1 (CLI section implementation)
- **Issue:** Plan specified `rate=0.05` but inject_type_a_noise uses `error_rate` parameter
- **Fix:** Changed to `error_rate=0.05` in the functional smoke test
- **Files modified:** scripts/qa_script.sh
- **Verification:** CLI section passes all 8 checks

**2. [Rule 3 - Blocking] Added venv auto-activation**
- **Found during:** Task 1 (initial env section testing)
- **Issue:** Running script without activated venv caused all package import checks to fail
- **Fix:** Added automatic venv detection and activation at script start
- **Files modified:** scripts/qa_script.sh
- **Verification:** Env section passes all 17 checks without manual venv activation

**3. [Rule 1 - Bug] Adapted derive_seed test call signature**
- **Found during:** Task 1 (config section implementation)
- **Issue:** Plan used `derive_seed('test','a')` but function requires 4 args: base_seed, prompt_id, noise_type, noise_level
- **Fix:** Changed to `derive_seed(42, 'test', 'type_a', '5')`
- **Files modified:** scripts/qa_script.sh
- **Verification:** Config section passes all 3 checks

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full QA runner available for pre-release validation
- All offline checks pass; live API tests available with --live flag
- Script is CI-compatible (non-zero exit on any FAIL)

---
*Phase: 08-write-unit-tests*
*Completed: 2026-03-24*
