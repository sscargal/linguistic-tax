---
phase: quick-260327-uz0
plan: 01
subsystem: cli
tags: [setup-wizard, multi-model, interactive-cli]

requires:
  - phase: 19-setup-wizard
    provides: "Single-model wizard with provider selection"
provides:
  - "Multi-model selection (1-4 targets per provider) with add/remove/modify sub-menu"
  - "Descriptive guidance text at each wizard step"
  - "Multi-target existing config detection and display"
affects: [setup-wizard, experiment-config]

tech-stack:
  added: []
  patterns:
    - "Per-provider sub-menu loop for model management"
    - "_select_single_target extracted helper for reuse in add/modify flows"

key-files:
  created: []
  modified:
    - src/setup_wizard.py
    - tests/test_setup_wizard.py

key-decisions:
  - "Flat list return format preserved: multiple targets per provider are multiple entries with same provider key, keeping _build_config_dict, _validate_models, _build_budget_preview, _show_confirmation working unchanged"
  - "_detect_existing_config now returns targets list format instead of single target/preproc dict"
  - "Removing all models from a provider forces re-selection of at least one"

patterns-established:
  - "_select_single_target helper: reusable target+preproc pair selection for add and modify flows"

requirements-completed: [MULTI-MODEL-WIZARD]

duration: 4min
completed: 2026-03-27
---

# Quick Task 260327-uz0: Enhance Setup Wizard with Multi-Model Support Summary

**Multi-model wizard supporting 1-4 targets per provider with add/remove/modify sub-menu and descriptive step guidance**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T22:20:43Z
- **Completed:** 2026-03-27T22:24:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Setup wizard now allows selecting 1-4 target models per provider via add/remove/modify sub-menu
- Descriptive guidance text added to Steps 3 (provider selection), 4 (API keys), and 6 (model selection)
- Existing config detection updated to parse and display multiple targets per provider
- 45 tests pass (7 new tests added, 6 existing tests updated for new sub-menu flow)

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-model selection and descriptive wizard text** - `db7163a` (feat)
2. **Task 2: Update tests for multi-model wizard flow** - `a705ec7` (test)

## Files Created/Modified
- `src/setup_wizard.py` - Added MAX_TARGETS_PER_PROVIDER, multi-target sub-menu, _select_single_target/_show_provider_models helpers, descriptive text, updated _detect_existing_config for targets list format
- `tests/test_setup_wizard.py` - Added TestMultiTargetSelection (5 tests), multi-target existing config test, multi-target _build_config_dict test, updated existing tests for sub-menu exit

## Decisions Made
- Flat list return format preserved: _select_models returns same list-of-dicts format, just with potentially multiple entries per provider. This keeps all downstream functions (_build_config_dict, _validate_models, _build_budget_preview, _show_confirmation) working unchanged.
- _detect_existing_config now returns `{"targets": [{...}, ...]}` per provider instead of `{"target": ..., "preproc": ...}`. Backward compat handled in _handle_existing_config display.
- Removing all models from a provider forces immediate re-selection to prevent empty provider state.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Multi-model wizard complete and tested
- Config output format unchanged, compatible with all existing experiment tooling

---
*Phase: quick-260327-uz0*
*Completed: 2026-03-27*
