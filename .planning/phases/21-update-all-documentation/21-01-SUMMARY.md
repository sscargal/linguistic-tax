---
phase: 21-update-all-documentation
plan: 01
subsystem: documentation
tags: [markdown, readme, claude-md, v2.0-migration]

# Dependency graph
requires:
  - phase: 20-update-skills-agents-evaluations
    provides: v2.0 codebase with ModelRegistry, env_manager, model_discovery modules
provides:
  - Updated README.md reflecting v2.0 architecture
  - Updated CLAUDE.md reflecting v2.0 modules and providers
affects: [21-02, 21-03, 21-04]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - README.md
    - CLAUDE.md

key-decisions:
  - "Used ExperimentConfig field names for set-config examples (base_seed, repetitions, temperature) based on config_commands.py source"
  - "Presented work item count as formula with calculated default example (~80K with 4 models)"
  - "Kept config.py description as 'ExperimentConfig, noise types, intervention constants' to distinguish from model_registry.py"

patterns-established:
  - "Default models labeled configurable: 'Default models (configurable via propt setup)'"
  - "ModelRegistry as canonical reference for model/pricing data in documentation"

requirements-completed: [DOC-01, DOC-02, DOC-07]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 21 Plan 01: README.md and CLAUDE.md Summary

**Updated root README.md and CLAUDE.md to reflect v2.0 architecture: configurable models via ModelRegistry, .env-first API keys, simplified Quick Start, 21 modules, 4 providers, and all stale v1.0 references removed**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T18:14:32Z
- **Completed:** 2026-03-26T18:17:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- README.md fully updated: simplified Quick Start (clone/sync/setup), .env-first API keys, v2.0 wizard description, updated CLI reference with --json flag, formula-based work item count, 21 modules/25 tests in project structure, ModelRegistry glossary references, bibtex with author placeholder
- CLAUDE.md fully updated: all 21 modules listed alphabetically in architecture tree, 4 providers in Tech Stack, default_models.json in data section, configurable pre-processor reference
- Zero stale v1.0 references remaining (PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, Python 3.11, 18 modules, 19 tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update README.md for v2.0** - `aa7d706` (docs)
2. **Task 2: Update CLAUDE.md for v2.0** - `eb97886` (docs)

## Files Created/Modified
- `README.md` - Root readme with v2.0 Quick Start, .env API keys, updated CLI reference, configurable models table, formula work items, 21-module project structure, ModelRegistry glossary, bibtex with author
- `CLAUDE.md` - Project instructions with all 21 modules in architecture tree, 4 providers in Tech Stack, configurable pre-processor reference

## Decisions Made
- Used ExperimentConfig field names (base_seed, repetitions, temperature) for set-config examples, verified against config_commands.py handle_set_config() which validates against ExperimentConfig dataclass fields
- Presented work item count as formula (`prompts x noise_types x interventions x models x repetitions`) with default example (200 x 8 x 5 x 4 x 5 = ~80,000)
- Labeled config.py description as "ExperimentConfig, noise types, intervention constants" to clearly distinguish it from model_registry.py's role

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- README.md and CLAUDE.md are consistent and ready for cross-referencing by subsequent plans
- Plans 02-04 can proceed with docs/getting-started.md, docs/architecture.md, docs/contributing.md, and the final sweep

---
*Phase: 21-update-all-documentation*
*Completed: 2026-03-26*
