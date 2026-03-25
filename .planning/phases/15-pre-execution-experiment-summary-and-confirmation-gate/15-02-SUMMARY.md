---
phase: 15-pre-execution-experiment-summary-and-confirmation-gate
plan: 02
subsystem: cli
tags: [argparse, tqdm, confirmation-gate, progress-bar, cli]

# Dependency graph
requires:
  - phase: 15-01
    provides: execution_summary module with estimate_cost, confirm_execution, format_summary, save_execution_plan
provides:
  - propt run and propt pilot CLI subcommands with full flag parity
  - Confirmation gate wired into run_engine and run_pilot before execution
  - tqdm progress bar with cost-so-far tracking during experiment execution
  - --dry-run summary display via format_summary
affects: [experiment-execution, pilot-validation]

# Tech tracking
tech-stack:
  added: [tqdm>=4.66.0]
  patterns: [confirmation-gate-before-execution, tqdm-progress-with-cost-tracking]

key-files:
  created: []
  modified:
    - src/cli.py
    - src/run_experiment.py
    - src/pilot.py
    - pyproject.toml

key-decisions:
  - "print() for config-not-found in CLI handler (consistent with Phase 14 CLI output convention)"
  - "getattr for yes/budget flags in run_engine for backward compatibility with direct script invocation"

patterns-established:
  - "Confirmation gate pattern: estimate -> format -> confirm -> save plan -> execute"
  - "tqdm postfix for live cost tracking during experiment loops"

requirements-completed: [GATE-CLI-RUN, GATE-CLI-PILOT, GATE-DRYRUN, GATE-PROGRESS, GATE-WIRE, GATE-TQDM]

# Metrics
duration: 4min
completed: 2026-03-25
---

# Phase 15 Plan 02: CLI Wiring and Confirmation Gate Integration Summary

**propt run/pilot subcommands with confirmation gate, tqdm progress bar, and --dry-run/--yes/--budget flags wired into execution engine**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-25T02:38:51Z
- **Completed:** 2026-03-25T02:42:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Registered `propt run` and `propt pilot` as CLI subcommands with full flag sets (--model, --limit, --retry-failed, --db, --yes, --budget, --dry-run, --intervention for run; --yes, --budget, --dry-run, --db for pilot)
- Wired confirmation gate into both run_engine() and run_pilot() with three-way Y/N/M flow, budget gate, and auto-accept support
- Replaced old _show_dry_run() with format_summary from execution_summary module for rich tabulated output
- Added tqdm progress bar with live cost-so-far postfix to experiment processing loop
- Added tqdm>=4.66.0 to pyproject.toml dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Register propt run and pilot subcommands in cli.py** - `d36ed94` (feat)
2. **Task 2: Wire confirmation gate, tqdm progress bar, add tqdm dep** - `3c54262` (feat)

## Files Created/Modified
- `src/cli.py` - Added handle_run, handle_pilot handlers and run/pilot subparser registration with INTERVENTIONS choices
- `src/run_experiment.py` - Added confirmation gate, tqdm progress bar, removed _show_dry_run, added --yes/--budget/--intervention to _build_parser
- `src/pilot.py` - Updated run_pilot signature with yes/dry_run params, added confirmation gate, updated _build_parser and main()
- `pyproject.toml` - Added tqdm>=4.66.0 dependency

## Decisions Made
- Used print() for config-not-found message in CLI handlers (consistent with Phase 14 convention of print() for user-facing CLI output)
- Used getattr() for yes/budget flags in run_engine to maintain backward compatibility when called directly from scripts without those args

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Confirmation gate fully wired into both execution paths
- Ready for Plan 03 (tests for confirmation gate integration)

---
*Phase: 15-pre-execution-experiment-summary-and-confirmation-gate*
*Completed: 2026-03-25*
