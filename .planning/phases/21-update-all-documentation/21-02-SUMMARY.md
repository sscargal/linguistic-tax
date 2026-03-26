---
phase: 21-update-all-documentation
plan: 02
subsystem: docs
tags: [getting-started, wizard, setup, env, api-keys, onboarding]

# Dependency graph
requires:
  - phase: 19-rewrite-wizard
    provides: v2.0 multi-provider wizard flow in setup_wizard.py
provides:
  - Updated getting-started.md reflecting v2.0 wizard flow and .env-first key management
affects: [21-04-final-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns: [wizard-first configuration approach, .env as primary key method]

key-files:
  created: []
  modified: [docs/getting-started.md]

key-decisions:
  - "Restructured config section to lead with propt setup wizard before manual set-config"
  - "Added preproc model column to provider defaults table"
  - "Updated sample pilot output to include Noise Conditions section from v2.0 format_summary()"
  - "Changed show-config example from claude_model to temperature (valid v2.0 property)"

patterns-established:
  - "Wizard-first: propt setup is primary config path, manual set-config is secondary"
  - ".env-first: .env file is recommended key method, shell export is alternative"

requirements-completed: [DOC-03]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 21 Plan 02: Getting Started Guide Summary

**Rewrote getting-started.md for v2.0: wizard-first multi-provider flow with .env key management, validation pings, budget preview, and configurable model defaults**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T18:14:32Z
- **Completed:** 2026-03-26T18:17:21Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Rewrote wizard walkthrough section describing full v2.0 multi-provider flow (9 steps: env check, existing config detection, provider selection, API key collection, model roles, model selection with browser, validation pings, budget preview, confirmation)
- Restructured API key section to present .env as primary method with shell export as alternative
- Updated all Python version references from 3.11 to 3.12+
- Eliminated all stale references to v1.0 constants (PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) and config fields (claude_model, gemini_model)
- Updated set-config examples to use v2.0 properties (temperature, results_db_path, repetitions)
- Labeled provider/model table as "Default models (configurable via propt setup)" with preproc model column added

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite getting-started.md for v2.0** - `904db7b` (docs)

**Plan metadata:** [pending final commit]

## Files Created/Modified
- `docs/getting-started.md` - Complete rewrite of wizard section, API keys section, manual config section, and troubleshooting for v2.0

## Decisions Made
- Restructured Configuration section to lead with "Run the Setup Wizard" before "API Keys" and "Manual Configuration" (wizard-first approach per CONTEXT.md)
- Added preproc model column to the provider defaults table for completeness
- Updated sample pilot output to include Noise Conditions section (matches v2.0 format_summary() output)
- Changed show-config single property example from `claude_model` to `temperature` (valid v2.0 field)
- Added note about .env chmod 600 security in API Keys section (from env_manager.py source)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures (pandas/matplotlib import errors, some pilot test failures) unrelated to documentation changes -- 483 tests pass, 48 fail with same results before and after changes

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Getting-started.md is v2.0 compliant
- Plan 03 (architecture.md + contributing.md) can proceed
- Plan 04 final sweep should re-check getting-started.md for cross-document consistency

---
*Phase: 21-update-all-documentation*
*Completed: 2026-03-26*
