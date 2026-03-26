---
phase: 20-update-skills-and-agents
plan: 01
subsystem: skills
tags: [skill-files, model-registry, config-manager, env-manager]

# Dependency graph
requires:
  - phase: 16-model-registry-and-config
    provides: model_registry.py, config_manager.py, env_manager.py modules
  - phase: 17-integration
    provides: Removed backward-compat shims; registry is sole source of truth
  - phase: 18-model-discovery
    provides: model_discovery.py and setup_wizard.py
provides:
  - All 7 SKILL.md files updated with v2.0 module references
  - db-context.md updated with registry-backed pricing note
  - New validation dimension (Configuration management) in validate-rdd skill
affects: [20-02-PLAN (trigger re-optimization), documentation updates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Skills reference model_registry APIs instead of config.py constants
    - Skills acknowledge dynamic model configuration via propt setup

key-files:
  created: []
  modified:
    - .claude/skills/validate-rdd/SKILL.md
    - .claude/skills/run-experiment/SKILL.md
    - .claude/skills/run-pilot/SKILL.md
    - .claude/skills/check-results/SKILL.md
    - .claude/skills/check-results/references/db-context.md
    - .claude/skills/analyze/SKILL.md
    - .claude/skills/generate-figures/SKILL.md
    - .claude/skills/write-section/SKILL.md

key-decisions:
  - "Workspace evaluation output files (validate-rdd-workspace/) left untouched — they are historical artifacts, not active skill guidance"

patterns-established:
  - "Skill files reference model_registry.target_models(), get_price(), get_delay(), compute_cost() instead of config.py constants"
  - "Skills mentioning setup reference propt setup and env_manager.check_keys()"

requirements-completed: [SKL-01, SKL-02, SKL-03, SKL-04, SKL-05, SKL-06, SKL-07]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 20 Plan 01: Update Skills Summary

**All 7 SKILL.md files and db-context.md updated to replace stale config.py constant references with v2.0 model_registry, config_manager, and env_manager APIs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T03:49:11Z
- **Completed:** 2026-03-26T03:51:30Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Replaced all stale config.py:MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, and compute_cost references in 4 HIGH-impact skills
- Added new "Configuration management" validation dimension to validate-rdd skill covering config_manager, model_registry, env_manager, setup_wizard, and model_discovery
- Updated db-context.md with registry-backed pricing note and propt list-models command
- Updated 3 LOW-impact skills (analyze, generate-figures, write-section) with dynamic model acknowledgments

## Task Commits

Each task was committed atomically:

1. **Task 1: Update HIGH-impact skills** - `e6dc78f` (feat)
2. **Task 2: Update LOW-impact skills** - `8f30f1b` (feat)

## Files Created/Modified
- `.claude/skills/validate-rdd/SKILL.md` - Replaced model config table entries, cost tracking ref, added section 8
- `.claude/skills/run-experiment/SKILL.md` - Updated rate limit ref, added env_manager and registry notes
- `.claude/skills/run-pilot/SKILL.md` - Added env_manager.check_keys(), config_manager, registry delay ref
- `.claude/skills/check-results/SKILL.md` - Added registry pricing comment, propt list-models mention
- `.claude/skills/check-results/references/db-context.md` - Added pricing NOTE, dynamic models line, list-models command
- `.claude/skills/analyze/SKILL.md` - Added model registry pipeline note and variable model counts note
- `.claude/skills/generate-figures/SKILL.md` - Updated completeness check, added model set note
- `.claude/skills/write-section/SKILL.md` - Updated methodology guidance, added configurable models note

## Decisions Made
- Workspace evaluation output files (validate-rdd-workspace/) left untouched — they are historical artifacts, not active skill guidance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 skills now reflect v2.0 module architecture
- Ready for Plan 02 (trigger description re-optimization and evaluation re-runs)

## Self-Check: PASSED

All 8 modified files verified present. Both task commits (e6dc78f, 8f30f1b) verified in git log.

---
*Phase: 20-update-skills-and-agents*
*Completed: 2026-03-26*
