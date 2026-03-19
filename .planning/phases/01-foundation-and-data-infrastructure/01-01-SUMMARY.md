---
phase: 01-foundation-and-data-infrastructure
plan: 01
subsystem: database
tags: [sqlite, dataclass, config, seed-derivation, hashlib]

# Dependency graph
requires: []
provides:
  - "ExperimentConfig frozen dataclass with pinned model versions and experiment parameters"
  - "derive_seed function for deterministic seed derivation via SHA-256"
  - "NOISE_TYPES, INTERVENTIONS, MODELS constants enumerating all experimental conditions"
  - "SQLite schema with experiment_runs and derived_metrics tables matching RDD Section 9.2"
  - "init_database, insert_run, query_runs helper functions"
  - "Shared test fixtures (sample_config, tmp_db_path, sample_prompt_record)"
affects: [noise-generator, prompt-compressor, run-experiment, grade-results, analyze-results, compute-derived]

# Tech tracking
tech-stack:
  added: [sqlite3, hashlib, dataclasses]
  patterns: [frozen-dataclass-config, sha256-seed-derivation, parameterized-sql, wal-journal-mode]

key-files:
  created:
    - src/config.py
    - src/db.py
    - tests/conftest.py
    - tests/test_config.py
    - tests/test_db.py

key-decisions:
  - "Used frozen dataclass for config immutability rather than dict or module constants"
  - "SHA-256 first 8 hex chars for seed derivation (uniform distribution, collision resistant)"
  - "WAL journal mode for SQLite to support concurrent reads during experiment execution"
  - "Dynamic column insertion in insert_run to handle partial row data gracefully"

patterns-established:
  - "Frozen dataclass for immutable configuration"
  - "Isolated seed derivation via hashlib (no global random state)"
  - "Parameterized SQL queries throughout (no string formatting)"
  - "Module-level logger via logging.getLogger(__name__)"

requirements-completed: [DATA-03, DATA-04]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 01 Plan 01: Config and Database Infrastructure Summary

**Frozen dataclass config with pinned models/seeds and SQLite schema matching RDD Section 9.2 with experiment_runs and derived_metrics tables**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T22:32:08Z
- **Completed:** 2026-03-19T22:35:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ExperimentConfig frozen dataclass exposes all pinned model versions, noise parameters, paths, and seed registry
- derive_seed provides deterministic seed derivation using SHA-256 hashing from (base_seed, prompt_id, noise_type, noise_level)
- Full RDD schema with 30-column experiment_runs table and 14-column derived_metrics table
- All 32 tests passing across both modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create config module and shared test fixtures**
   - `b95e0e6` (test) - Failing tests for config module
   - `af5377d` (feat) - Config module implementation, 21 tests passing
2. **Task 2: Create SQLite database module with full RDD schema**
   - `b8162d6` (test) - Failing tests for database module
   - `e51f013` (feat) - Database module implementation, 11 tests passing

## Files Created/Modified
- `src/config.py` - Frozen dataclass config with pinned models, seeds, noise params, paths, and derive_seed function
- `src/db.py` - SQLite schema creation (experiment_runs + derived_metrics), insert_run, query_runs helpers
- `tests/conftest.py` - Shared fixtures: sample_config, tmp_db_path, sample_prompt_record
- `tests/test_config.py` - 21 tests covering config immutability, values, seed derivation, constants
- `tests/test_db.py` - 11 tests covering schema creation, WAL mode, insert/query, idempotency

## Decisions Made
- Used frozen dataclass for config immutability rather than dict or module constants -- provides type checking and IDE support
- SHA-256 first 8 hex chars for seed derivation -- uniform distribution and collision resistance without global random state
- WAL journal mode for SQLite -- better concurrent read performance during experiment runs
- Dynamic column insertion in insert_run -- handles partial row data gracefully (columns not in dict get SQL defaults)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Config module ready for import by all downstream modules (noise_generator, run_experiment, etc.)
- Database schema ready to accept experiment results from Phase 3 execution
- Shared test fixtures available for all future test files

---
*Phase: 01-foundation-and-data-infrastructure*
*Completed: 2026-03-19*
