---
phase: 13-guided-setup-wizard-for-project-configuration
plan: 02
subsystem: cli
tags: [argparse, wizard, api-validation, environment-check, interactive-setup]

# Dependency graph
requires:
  - phase: 13-guided-setup-wizard-for-project-configuration
    provides: config_manager.py with save_config, get_full_config_dict, validate_config
  - phase: 01-foundation
    provides: ExperimentConfig, MODELS, PREPROC_MODEL_MAP, PRICE_TABLE, OPENROUTER_BASE_URL
provides:
  - CLI entry point with argparse subparsers (src/cli.py)
  - Interactive setup wizard with provider/model selection (src/setup_wizard.py)
  - API key validation for all 4 providers
  - Environment check (Python version + packages)
  - Config-missing guard in run_experiment.py and pilot.py
affects: [14-cli-config-subcommands, 15-pre-execution-experiment-summary]

# Tech tracking
tech-stack:
  added: []
  patterns: [input_fn-injection-for-testability, config-missing-guard-pattern]

key-files:
  created: [src/cli.py, src/setup_wizard.py, tests/test_cli.py, tests/test_setup_wizard.py]
  modified: [src/run_experiment.py, src/pilot.py]

key-decisions:
  - "input_fn parameter injection for wizard testability instead of monkeypatching builtins.input"
  - "print() for interactive output (not logging) per CONTEXT.md/RESEARCH.md guidance"
  - "Duplicated _check_config_exists in both entry points rather than shared import for independence"

patterns-established:
  - "input_fn injection: wizard accepts optional input_fn callable for test mocking"
  - "Config guard: entry point scripts check for config file and exit with guidance if missing"

requirements-completed: [SETUP-03, SETUP-04, SETUP-05, SETUP-06, SETUP-07]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 13 Plan 02: CLI Entry Point and Setup Wizard Summary

**Argparse CLI with setup subcommand, interactive wizard for provider/model/API-key configuration, environment checks, and config-missing guards on experiment entry points**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T22:18:13Z
- **Completed:** 2026-03-24T22:22:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- CLI entry point (src/cli.py) with argparse subparsers and --non-interactive flag
- Interactive setup wizard guides through provider selection, model auto-fill from PREPROC_MODEL_MAP, API key validation, environment checks, and config file generation
- API key validation for all 4 providers (Anthropic, Google, OpenAI, OpenRouter) with auth error differentiation
- Config-missing guard in run_experiment.py and pilot.py directs users to run setup wizard
- 22 new tests (5 CLI + 17 wizard) all passing, full suite 422 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI and setup wizard (RED)** - `81d14a1` (test)
2. **Task 1: CLI and setup wizard (GREEN)** - `6c69adc` (feat)
3. **Task 2: Config-missing guard** - `a8b1ef9` (feat)

_TDD task with RED/GREEN commits for Task 1._

## Files Created/Modified
- `src/cli.py` - CLI entry point with argparse subparsers, setup subcommand routing
- `src/setup_wizard.py` - Interactive wizard with PROVIDERS registry, check_environment, validate_api_key, run_setup_wizard
- `tests/test_cli.py` - 5 tests for CLI routing, help, non-interactive flag
- `tests/test_setup_wizard.py` - 17 tests for providers, env checks, API validation, wizard flow
- `src/run_experiment.py` - Added _check_config_exists guard and config_manager import
- `src/pilot.py` - Added _check_config_exists guard and config_manager import

## Decisions Made
- Used input_fn parameter injection for wizard testability rather than monkeypatching builtins.input
- Used print() for interactive wizard output per CONTEXT.md guidance (not logging module)
- Duplicated _check_config_exists function in both run_experiment.py and pilot.py for entry point independence

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI entry point ready for Phase 14 (cli config subcommands) to add more subcommands
- Setup wizard complete, ready for end-to-end user flow
- Config-missing guards ensure users are directed to setup before experiments

---
*Phase: 13-guided-setup-wizard-for-project-configuration*
*Completed: 2026-03-24*
