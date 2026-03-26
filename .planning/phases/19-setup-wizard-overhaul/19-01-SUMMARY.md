---
phase: 19-setup-wizard-overhaul
plan: 01
subsystem: cli
tags: [wizard, multi-provider, model-selection, budget-preview, env-manager]

# Dependency graph
requires:
  - phase: 16-model-registry-and-config
    provides: ModelRegistry, ModelConfig, default_models.json, env_manager
  - phase: 18-model-discovery
    provides: Live model query functions, fallback models
provides:
  - Complete multi-provider setup wizard with free-text model entry
  - Live model browser with pagination and search
  - API key collection with .env persistence
  - Model validation pings using actual selected models
  - Budget preview with pilot and full run estimates
affects: [19-02, testing, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-provider wizard flow: providers -> keys -> models -> validate -> confirm"
    - "Free-text model entry with 'list' command for live browsing"
    - "Budget preview via synthetic experiment items and estimate_cost()"

key-files:
  created: []
  modified:
    - src/setup_wizard.py

key-decisions:
  - "All 16 functions in single module (no decomposition into separate files)"
  - "Budget preview builds synthetic items matching real experiment matrix structure"
  - "Global preproc option reuses first provider's preproc for all subsequent providers"

patterns-established:
  - "_browse_models: paginated model browser with /search, n/p navigation, # selection"
  - "_build_budget_preview: synthetic experiment items for cost estimation"

requirements-completed: [WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05, WIZ-06, DSC-03]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 19 Plan 01: Setup Wizard Overhaul Summary

**Multi-provider setup wizard with free-text model entry, live browser, .env key persistence, validation pings, and budget preview**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T03:23:30Z
- **Completed:** 2026-03-26T03:25:42Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Complete rewrite of src/setup_wizard.py with 16+ functions implementing full multi-provider wizard flow
- Free-text model entry with 'list' command for paginated live model browser (20/page, search, nav)
- API keys written to .env immediately via write_env() and loaded into os.environ in same session
- Model validation pings using actual selected target model (not cheap proxy)
- Budget preview showing per-model costs for pilot (20 prompts) and full (200 prompts) runs with unknown pricing handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Wizard infrastructure -- helpers, provider selection, key collection** - `5727aa8` (feat)
2. **Task 2: Verify wizard module integration and fix import issues** - verification-only, no changes needed

## Files Created/Modified
- `src/setup_wizard.py` - Complete rewritten wizard with multi-provider flow (811 lines added, 156 removed)

## Decisions Made
- All 16 functions kept in single module rather than splitting into separate files
- Budget preview builds synthetic experiment items matching real matrix structure (5 interventions x 5 reps x N prompts)
- Global preproc option asks only on first provider, reuses for all subsequent
- Inner helper functions in _build_budget_preview for item generation and per-model cost breakdown

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wizard module fully importable and integration-tested with smoke tests
- Ready for Plan 02 (test suite for the wizard)
- All 7 requirements (WIZ-01 through WIZ-06, DSC-03) addressed in the code

---
*Phase: 19-setup-wizard-overhaul*
*Completed: 2026-03-26*
