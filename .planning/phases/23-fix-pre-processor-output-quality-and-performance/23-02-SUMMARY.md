---
phase: 23-fix-pre-processor-output-quality-and-performance
plan: 02
subsystem: docs
tags: [documentation, setup-wizard, pre-processor, model-guidance]

requires:
  - phase: 23-01
    provides: "Code fixes for preproc skip logic and anti-reasoning directives"
provides:
  - "Pre-processor model guidance in getting-started.md"
  - "Wizard warning about reasoning model bloat"
affects: [setup-wizard, getting-started-docs]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - docs/getting-started.md
    - src/setup_wizard.py

key-decisions:
  - "Guidance placed after model table in getting-started.md for natural reading flow"
  - "Wizard warning inserted between pre-processor explanation and scope question"

patterns-established: []

requirements-completed: [TODO-preproc-performance-anomaly]

duration: 1min
completed: 2026-03-27
---

# Phase 23 Plan 02: Pre-processor Model Guidance Summary

**Documentation and wizard warnings against reasoning models as pre-processors, with recommended non-reasoning alternatives per provider**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-27T21:20:53Z
- **Completed:** 2026-03-27T21:22:15Z
- **Tasks:** 2 (1 auto + 1 auto-approved checkpoint)
- **Files modified:** 2

## Accomplishments
- Added pre-processor model recommendation table to getting-started.md with per-provider guidance
- Added reasoning model warning to setup wizard's model roles explanation
- Documented that toolkit skips preproc for clean/ESL conditions automatically

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pre-processor model guidance to docs and wizard** - `6e01bda` (docs)
2. **Task 2: Verify pre-processor fix via re-piloting** - auto-approved checkpoint (no commit)

## Files Created/Modified
- `docs/getting-started.md` - Added non-reasoning model recommendation table and preproc skip note
- `src/setup_wizard.py` - Added warning about reasoning model bloat in _explain_model_roles()

## Decisions Made
- Guidance placed immediately after the default models table in getting-started.md for natural reading flow
- Wizard warning inserted between pre-processor explanation and scope question for visibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 23 complete: both code fixes (Plan 01) and documentation (Plan 02) shipped
- Users can re-pilot type_a conditions to verify accuracy improvement at their convenience

---
*Phase: 23-fix-pre-processor-output-quality-and-performance*
*Completed: 2026-03-27*
