---
phase: 05-statistical-analysis-and-derived-metrics
plan: 01
subsystem: analysis
tags: [consistency-rate, quadrant-classification, cost-rollup, migration-matrix, sqlite, pandas, tabulate]

# Dependency graph
requires:
  - phase: 01-project-foundation
    provides: SQLite schema (experiment_runs, derived_metrics tables), config constants
  - phase: 04-pilot-validation
    provides: Populated experiment_runs data to compute derived metrics from
provides:
  - compute_cr function for pairwise consistency rate
  - classify_quadrant function for stability-correctness classification
  - compute_derived_metrics populates derived_metrics table
  - compute_quadrant_migration builds transition matrices
  - compute_cost_rollups aggregates per-condition costs
  - CLI entry point with JSON/CSV output
affects: [05-02-statistical-analysis, 06-visualization]

# Tech tracking
tech-stack:
  added: [tabulate]
  patterns: [pairwise-consistency-rate, quadrant-classification, transition-matrix]

key-files:
  created:
    - src/compute_derived.py
    - tests/test_compute_derived.py
  modified:
    - tests/conftest.py
    - pyproject.toml

key-decisions:
  - "Pairwise CR via itertools.combinations for exact combinatorial agreement counting"
  - "CREATE TABLE IF NOT EXISTS in compute_derived_metrics for defensive table creation"

patterns-established:
  - "Quadrant classification: robust/confidently_wrong/lucky/broken from CR threshold and majority pass"
  - "Condition string format: {noise_type}_{intervention} as composite key"

requirements-completed: [DERV-01, DERV-02, DERV-03]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 5 Plan 1: Derived Metrics Summary

**Pairwise CR computation, 4-quadrant classification with configurable threshold, cost rollups, and quadrant migration transition matrices via compute_derived.py CLI**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T17:13:57Z
- **Completed:** 2026-03-23T17:19:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Implemented compute_cr using itertools.combinations for exact pairwise agreement (handles K<5 gracefully)
- Built 4-quadrant classifier (robust, confidently_wrong, lucky, broken) with configurable CR threshold
- Quadrant migration transition matrices track prompt movement between conditions
- Cost rollups aggregate per (model, noise_type, intervention) with JSON + CSV output
- 14 tests covering CR edge cases, all quadrant boundaries, custom threshold, DB integration, cost rollups, and migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test fixtures and test scaffold (TDD RED)** - `9f2ca70` (test)
2. **Task 2: Implement compute_derived.py (TDD GREEN)** - `9a37fc1` (feat)

## Files Created/Modified
- `src/compute_derived.py` - CR, quadrant, cost rollup, migration, CLI entry point (8 functions)
- `tests/test_compute_derived.py` - 14 unit/integration tests for derived metrics
- `tests/conftest.py` - Added populated_test_db fixture with 30 synthetic rows
- `pyproject.toml` - Added tabulate>=0.9.0 dependency

## Decisions Made
- Used itertools.combinations for exact pairwise CR rather than a formula shortcut, for clarity and auditability
- Defensive CREATE TABLE IF NOT EXISTS in compute_derived_metrics to handle cases where init_database was not called first

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- System python (3.10) missing pandas; resolved by running tests via venv python (3.13)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- derived_metrics table population ready for Plan 02 (GLMM, bootstrap CIs, McNemar's)
- Quadrant data and migration matrices ready for Phase 6 visualization
- Cost rollup JSON/CSV outputs available for paper tables

---
*Phase: 05-statistical-analysis-and-derived-metrics*
*Completed: 2026-03-23*
