---
phase: 21-update-all-documentation
plan: 03
subsystem: documentation
tags: [markdown, mermaid, architecture, contributing, model-registry]

# Dependency graph
requires:
  - phase: 16-model-registry-and-configuration
    provides: ModelRegistry, default_models.json, env_manager, model_discovery modules
provides:
  - Updated architecture.md with v2.0 module reference, diagrams, and Design Decisions
  - Updated contributing.md with v2.0 model addition workflow
affects: [21-04-final-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - docs/architecture.md
    - docs/contributing.md

key-decisions:
  - "Design Decisions section uses historical 'formerly known as' references to old constants for clarity"
  - "New Environment and Discovery Layer section in module reference (separate from Configuration Layer)"
  - "ModelRegistry config flow documented as text description per CONTEXT.md (no new diagram)"

patterns-established:
  - "v2.0 module reference: model_registry, env_manager, model_discovery in separate layer"

requirements-completed: [DOC-04, DOC-05]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 21 Plan 03: Architecture and Contributing Docs Summary

**Architecture doc updated with 3 new modules, v2.0 ExperimentConfig, Design Decisions section, and ModelRegistry config flow; contributing guide rewritten for default_models.json-based model addition workflow**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T18:14:30Z
- **Completed:** 2026-03-26T18:19:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Architecture doc now has complete v2.0 module reference with model_registry, env_manager, and model_discovery in a new Environment and Discovery Layer
- CLI command map and pipeline architecture Mermaid diagrams updated with new module nodes and configurable providers note
- Design Decisions section added documenting registry pattern, .env management, and live model discovery
- Contributing guide's "Adding a New Model Provider" section rewritten from 9-step v1.0 workflow (MODELS tuple, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) to 8-step v2.0 workflow (default_models.json, model_discovery, env_manager)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update docs/architecture.md for v2.0** - `b114ef9` (docs)
2. **Task 2: Update docs/contributing.md for v2.0** - `6911e0d` (docs)

## Files Created/Modified
- `docs/architecture.md` - v2.0 module reference, updated diagrams, Design Decisions, ModelRegistry config flow, ExperimentConfig v2
- `docs/contributing.md` - v2.0 model addition guide, updated project structure, stale reference cleanup

## Decisions Made
- Created a separate "Environment and Discovery Layer" in the module reference rather than adding env_manager and model_discovery to the Configuration Layer -- they serve a distinct purpose
- Design Decisions section mentions old constant names (PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) in historical context for clarity about what was replaced
- ModelRegistry config flow documented as numbered text per CONTEXT.md decision (no new Mermaid diagram)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Architecture and contributing docs are v2.0-current
- Ready for Plan 04 final sweep to verify cross-document consistency

## Self-Check: PASSED

- FOUND: docs/architecture.md
- FOUND: docs/contributing.md
- FOUND: 21-03-SUMMARY.md
- FOUND: b114ef9 (Task 1 commit)
- FOUND: 6911e0d (Task 2 commit)

---
*Phase: 21-update-all-documentation*
*Completed: 2026-03-26*
