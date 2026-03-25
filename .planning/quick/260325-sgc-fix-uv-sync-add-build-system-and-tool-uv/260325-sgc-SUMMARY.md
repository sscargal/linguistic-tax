---
phase: quick
plan: 260325-sgc
subsystem: infra
tags: [uv, hatchling, build-system, pyproject]

requires:
  - phase: none
    provides: n/a
provides:
  - "Working build-system configuration enabling uv entry point installation"
  - "propt CLI command available after uv sync"
affects: [all-phases]

tech-stack:
  added: [hatchling]
  patterns: [hatchling-build-backend-with-src-layout]

key-files:
  created: []
  modified: [pyproject.toml, uv.lock]

key-decisions:
  - "Added [tool.hatch.build.targets.wheel] packages=['src'] because hatchling cannot auto-discover src/ when project name differs"

patterns-established:
  - "Hatchling build backend with explicit src/ package declaration for uv compatibility"

requirements-completed: [fix-uv-sync-entry-points]

duration: 2min
completed: 2026-03-25
---

# Quick Task 260325-sgc: Fix uv sync Entry Points Summary

**Added hatchling build-system and tool.uv package flag to enable propt CLI entry point installation via uv sync**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T20:30:36Z
- **Completed:** 2026-03-25T20:32:44Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added [build-system] section with hatchling backend to pyproject.toml
- Added [tool.hatch.build.targets.wheel] for explicit src/ package discovery
- Added [tool.uv] package=true to enable entry point installation
- `uv sync` now installs propt entry point without warnings
- `propt --help` confirms CLI is functional

## Task Commits

Each task was committed atomically:

1. **Task 1: Add build-system and package flag to pyproject.toml** - `5d6da72` (fix)
2. **Lockfile update** - `1cf9d83` (chore)

## Files Created/Modified
- `pyproject.toml` - Added [build-system], [tool.hatch.build.targets.wheel], and [tool.uv] sections
- `uv.lock` - Updated lockfile reflecting build-system addition

## Decisions Made
- Added `[tool.hatch.build.targets.wheel] packages = ["src"]` because hatchling cannot auto-discover the `src/` directory when the project name (`linguistic-tax`) does not match the package directory name (`src`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added hatch build targets wheel configuration**
- **Found during:** Task 1 (build-system addition)
- **Issue:** Hatchling could not auto-discover src/ directory because project name (linguistic-tax) does not match package directory (src)
- **Fix:** Added `[tool.hatch.build.targets.wheel] packages = ["src"]`
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` succeeds, `propt --help` works
- **Committed in:** 5d6da72 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was necessary for hatchling to find the package. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Build system fully configured
- Entry points working correctly
- No blockers

---
*Quick task: 260325-sgc*
*Completed: 2026-03-25*
