---
phase: quick-260329-3au
plan: 01
subsystem: experiment-engine
tags: [matrix-generation, refactoring, in-memory]

requires: []
provides:
  - "src/matrix_generator.py module with generate_matrix() and extract_noise_level()"
  - "In-memory matrix generation in pilot.py and run_experiment.py"
  - "Removal of _remap_matrix_models and static JSON matrix loading"
affects: [pilot, run-experiment, scripts]

tech-stack:
  added: []
  patterns: ["In-memory matrix generation from configured models at runtime"]

key-files:
  created:
    - src/matrix_generator.py
    - tests/test_matrix_generator.py
  modified:
    - scripts/generate_matrix.py
    - src/pilot.py
    - src/run_experiment.py
    - tests/test_pilot.py
    - tests/test_run_experiment.py

key-decisions:
  - "Added matrix parameter to run_engine() to allow pilot to pass filtered matrix directly, eliminating tempfile dance"

requirements-completed: [QUICK-260329-3AU]

duration: 6min
completed: 2026-03-29
---

# Quick Task 260329-3au: Auto-generate Experiment Matrix from Config

**Moved generate_matrix() to src/matrix_generator.py; pilot.py and run_experiment.py now generate matrices in-memory from configured models, eliminating static JSON + model remap workflow**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-29T02:25:09Z
- **Completed:** 2026-03-29T02:30:48Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created src/matrix_generator.py with generate_matrix() and extract_noise_level() extracted from scripts/
- Rewrote scripts/generate_matrix.py as a thin CLI wrapper importing from src/
- Removed _remap_matrix_models() entirely from pilot.py
- Rewrote filter_pilot_matrix() to generate matrix in-memory instead of loading from JSON
- Added matrix parameter to run_engine() for direct in-memory matrix passing
- Eliminated tempfile dance in run_pilot() -- filtered matrix passed directly to engine
- All 740 tests pass

## Task Commits

1. **Task 1: Create src/matrix_generator.py and update scripts/generate_matrix.py** - `d57f9af` (feat)
2. **Task 2: Wire pilot.py and run_experiment.py to use generate_matrix()** - `eba58c6` (feat)

## Files Created/Modified
- `src/matrix_generator.py` - New module with generate_matrix() and extract_noise_level()
- `scripts/generate_matrix.py` - Thin CLI wrapper (was full implementation)
- `tests/test_matrix_generator.py` - 12 tests for the new module
- `src/pilot.py` - Removed _remap_matrix_models, rewrote filter_pilot_matrix
- `src/run_experiment.py` - Added matrix parameter to run_engine, replaced JSON loading
- `tests/test_pilot.py` - Removed TestRemapMatrixModels class
- `tests/test_run_experiment.py` - Updated run_engine calls to pass matrix parameter

## Decisions Made
- Added `matrix` parameter to `run_engine()` so pilot can pass the filtered matrix directly, avoiding the tempfile workaround

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated run_engine test calls to pass matrix parameter**
- **Found during:** Task 2
- **Issue:** 4 tests in test_run_experiment.py failed because they relied on run_engine loading matrix from JSON file, but run_engine now generates in-memory
- **Fix:** Added `matrix=...` parameter to all run_engine test calls so tests use the explicit test matrix items instead of generating a full matrix
- **Files modified:** tests/test_run_experiment.py
- **Verification:** All 740 tests pass
- **Committed in:** eba58c6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary fix for test compatibility with the new in-memory matrix generation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Matrix generation is now fully in-memory from configured models
- Static experiment_matrix.json is no longer required for normal operation
- scripts/generate_matrix.py remains available for optional JSON export

---
*Quick task: 260329-3au*
*Completed: 2026-03-29*
