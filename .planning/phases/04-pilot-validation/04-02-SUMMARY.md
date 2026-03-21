---
phase: 04-pilot-validation
plan: 02
subsystem: testing
tags: [bootstrap, bertscore, scipy, numpy, pilot-validation, cost-projection, latency-profiling]

# Dependency graph
requires:
  - phase: 04-pilot-validation/01
    provides: "Pilot selection, matrix filtering, data audit, noise verification"
  - phase: 03-execution-engine
    provides: "run_experiment.py engine, db.py schema, config.py price table"
provides:
  - "Grading spot-check with ALL GSM8K + 20% code sampling"
  - "Bootstrap cost projection with BCa/percentile CIs and per-condition breakdown"
  - "Budget gate with configurable threshold"
  - "BERTScore pre-processor fidelity checking"
  - "Latency profiling with per-model and per-condition TTFT/TTLT statistics"
  - "Simplified binomial power analysis for N=200 sufficiency"
  - "Structured PASS/FAIL pilot verdict aggregating all sub-checks"
  - "CLI with --budget, --db, --select-only, --analyze-only flags"
affects: [05-analysis, full-experiment-run]

# Tech tracking
tech-stack:
  added: [scipy.stats.bootstrap, numpy, bert-score]
  patterns: [BCa-with-percentile-fallback, lazy-import-for-optional-deps]

key-files:
  created: []
  modified:
    - src/pilot.py
    - tests/test_pilot.py

key-decisions:
  - "BCa bootstrap with automatic fallback to percentile method when data is degenerate (identical costs or single prompt)"
  - "Lazy import pattern for bert_score to allow mocking in tests and graceful degradation when not installed"
  - "Budget gate is informational (warning only), not auto-fail in verdict"
  - "Power analysis uses simplified binomial z-test, not full GLMM (deferred to Phase 5)"

patterns-established:
  - "BCa-with-percentile-fallback: try BCa bootstrap first, catch degenerate-data warnings and fall back to percentile"
  - "Optional dependency pattern: try/except ImportError at module level, return error dict if unavailable"

requirements-completed: [PILOT-02, PILOT-03]

# Metrics
duration: 9min
completed: 2026-03-21
---

# Phase 04 Plan 02: Pilot Analysis and Reporting Summary

**Spot-check, bootstrap cost projection, BERTScore fidelity, latency profiling, power analysis, and structured PASS/FAIL verdict with argparse CLI**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-21T00:54:19Z
- **Completed:** 2026-03-21T01:03:34Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Complete pilot analysis pipeline: spot-check report covering ALL GSM8K + 20% code results
- Bootstrap cost projection with BCa/percentile fallback CIs and per-condition breakdown
- BERTScore fidelity check with graceful ImportError handling for optional dependency
- Latency profiling with per-model/condition stats and 30-second p95 flags
- Structured PASS/FAIL verdict aggregating completion rate, systematic failures, zero variance, and all sub-reports
- CLI with --budget, --db, --select-only, --analyze-only flags matching run_experiment.py pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Spot-check, cost projection, and budget gate** - `6f2e539` (feat)
2. **Task 2: BERTScore fidelity, latency profiling, verdict, power analysis, and CLI** - `5eb4137` (feat)

## Files Created/Modified
- `src/pilot.py` - Complete pilot validation module with 10 public functions and CLI
- `tests/test_pilot.py` - 40 tests covering all pilot functions (275 total suite green)

## Decisions Made
- BCa bootstrap with automatic percentile fallback handles degenerate data (all-same costs, single prompt) without crashing
- bert_score imported lazily at module level; functions return `{"error": ...}` if unavailable
- Budget gate is informational only (logged as warning, not auto-fail in verdict) per CONTEXT.md
- Power analysis uses simplified binomial z-test rather than full GLMM (Phase 5 scope)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BCa bootstrap failure on degenerate/single-observation data**
- **Found during:** Task 1 (cost projection)
- **Issue:** scipy.stats.bootstrap BCa method produces NaN on data with zero variance, and raises ValueError on single-observation arrays
- **Fix:** Added percentile fallback for degenerate data and point-estimate fallback for single observations
- **Files modified:** src/pilot.py
- **Verification:** Tests pass with both varied and uniform cost data
- **Committed in:** 5eb4137 (consolidated in Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness with edge-case pilot data. No scope creep.

## Issues Encountered
None - both TDD tasks completed cleanly after the bootstrap edge case was resolved.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pilot module is complete with all analysis functions ready to run against real pilot data
- Full test suite green (275 tests)
- Phase 5 (analysis) can consume pilot verdict JSON for go/no-go decisions

---
*Phase: 04-pilot-validation*
*Completed: 2026-03-21*
