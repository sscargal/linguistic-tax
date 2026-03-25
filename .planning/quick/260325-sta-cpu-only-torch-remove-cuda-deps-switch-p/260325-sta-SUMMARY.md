---
phase: quick-260325-sta
plan: 01
subsystem: infra
tags: [uv, torch, cpu-only, pytorch, dependencies]

# Dependency graph
requires: []
provides:
  - CPU-only PyTorch via uv source override (no CUDA packages)
  - All documentation updated to use uv workflow
affects: [installation, onboarding, disk-usage]

# Tech tracking
tech-stack:
  added: [torch-cpu-only-wheel]
  patterns: [uv-source-override-for-transitive-deps]

key-files:
  created: []
  modified: [pyproject.toml, uv.lock, README.md, docs/getting-started.md, docs/contributing.md]

key-decisions:
  - "Added torch as direct dependency to enable uv source override on transitive dep from bert-score"
  - "Used explicit=true on pytorch-cpu index to avoid affecting other package resolution"

patterns-established:
  - "uv source override pattern: add transitive dep as direct dep + [tool.uv.sources] + [[tool.uv.index]] with explicit=true"

requirements-completed: [QUICK-CPU-TORCH]

# Metrics
duration: 5min
completed: 2026-03-25
---

# Quick Task 260325-sta: CPU-only PyTorch Summary

**CPU-only PyTorch via uv source override eliminates ~6GB CUDA dependencies; all docs updated to uv sync workflow**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-25T20:46:51Z
- **Completed:** 2026-03-25T20:52:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Configured uv source override to pull torch from PyTorch CPU-only wheel index
- Eliminated all NVIDIA/CUDA packages from uv.lock (0 references, down from 51)
- torch 2.11.0+cpu installs and imports successfully
- All 504 existing tests pass with CPU-only torch
- Updated README.md, docs/getting-started.md, docs/contributing.md to use uv sync

## Task Commits

Each task was committed atomically:

1. **Task 1: Add uv torch CPU-only source override to pyproject.toml** - `dc6e93a` (chore)
2. **Task 2: Update all documentation to use uv instead of pip** - `c5f61e2` (docs)

## Files Created/Modified
- `pyproject.toml` - Added torch direct dep, [tool.uv.sources] and [[tool.uv.index]] for CPU-only torch
- `uv.lock` - Regenerated without CUDA/nvidia packages
- `README.md` - Quick Start and Installation sections updated to uv sync, uv added to prerequisites
- `docs/getting-started.md` - Installation and troubleshooting updated to uv sync, uv added to prerequisites
- `docs/contributing.md` - Development setup updated to uv sync

## Decisions Made
- Added torch as a direct dependency in pyproject.toml because uv source overrides only apply to packages in the dependency graph when they are direct dependencies (torch was transitive via bert-score)
- Used explicit=true on the pytorch-cpu index to ensure only torch uses that index, all other packages resolve from PyPI

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added torch as direct dependency for source override to work**
- **Found during:** Task 1
- **Issue:** uv [tool.uv.sources] override was not being applied to torch because it was only a transitive dependency (via bert-score), not a direct dependency
- **Fix:** Added "torch>=2.0.0" to project dependencies so the source override takes effect
- **Files modified:** pyproject.toml
- **Verification:** uv.lock shows torch sourced from download.pytorch.org/whl/cpu, zero nvidia references
- **Committed in:** dc6e93a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for the source override to work. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

---
*Phase: quick-260325-sta*
*Completed: 2026-03-25*
