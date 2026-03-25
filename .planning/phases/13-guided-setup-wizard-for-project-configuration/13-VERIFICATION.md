---
phase: 13-guided-setup-wizard-for-project-configuration
verified: 2026-03-24T22:45:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 13: Guided Setup Wizard Verification Report

**Phase Goal:** Brainstorm and potentially implement a guided setup wizard that helps new users get started quickly — choose model provider, model(s), working directory, and other essential configuration through a simple Q&A flow instead of manually editing config files (manual config still supported)
**Verified:** 2026-03-24T22:45:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Config file can be saved to and loaded from project directory as JSON | VERIFIED | `src/config_manager.py` save_config/load_config fully implemented; round-trip test passes |
| 2 | Sparse override pattern works: only changed values in file, missing keys use ExperimentConfig defaults | VERIFIED | `load_config` filters to valid field names and merges with `ExperimentConfig()`; `test_load_sparse_override` passes |
| 3 | Validation catches invalid model strings, out-of-range noise rates, negative temperature, zero repetitions | VERIFIED | `validate_config` checks PRICE_TABLE, [0,1] ranges, >=1 repetitions, >=0 temperature; 7 validation tests pass |
| 4 | Tuple fields survive JSON round-trip (saved as lists, loaded back as tuples) | VERIFIED | isinstance detection on defaults; `test_round_trip_produces_equivalent_config` passes |
| 5 | User can run `python src/cli.py setup` to launch the guided wizard | VERIFIED | `src/cli.py` build_cli routes "setup" to run_setup_wizard via set_defaults; confirmed by tests |
| 6 | Wizard validates API key with a minimal test call and reports success or specific failure | VERIFIED | `validate_api_key` implemented for all 4 providers; auth error (401/403/invalid/auth) distinguished from other errors; 7 tests pass |
| 7 | Running experiment without config file prints guidance message and exits | VERIFIED | `_check_config_exists()` in both `src/run_experiment.py` (line 497) and `src/pilot.py` (line 1108), called before argparse in main() |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/config_manager.py` | Config file I/O, validation, merge with ExperimentConfig | VERIFIED | 206 lines; all 6 exports present: CONFIG_FILENAME, find_config_path, load_config, save_config, get_full_config_dict, validate_config |
| `tests/test_config_manager.py` | Unit tests for all config_manager functions | VERIFIED | 197 lines (>100 min); 13 test functions across 5 test classes; 20 test cases passing |
| `src/cli.py` | CLI entry point with argparse subparsers | VERIFIED | 59 lines (>30 min); exports build_cli and main; "setup" subcommand with --non-interactive flag present |
| `src/setup_wizard.py` | Interactive wizard flow, env check, API validation | VERIFIED | 295 lines (>150 min); PROVIDERS, run_setup_wizard, check_environment, validate_api_key all present |
| `tests/test_cli.py` | CLI routing and help tests | VERIFIED | 57 lines (>30 min); 5 test functions |
| `tests/test_setup_wizard.py` | Wizard flow tests with mocked input, env check tests, API validation tests | VERIFIED | 280 lines (>100 min); 17 test functions |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/cli.py` | `src/setup_wizard.py` | `from src.setup_wizard import run_setup_wizard` + `set_defaults(func=run_setup_wizard)` | VERIFIED | Line 11: import; line 35: set_defaults wires subcommand to wizard |
| `src/setup_wizard.py` | `src/config_manager.py` | `from src.config_manager import get_full_config_dict, save_config, validate_config` | VERIFIED | Line 19: all three functions imported and called in run_setup_wizard |
| `src/setup_wizard.py` | `src/config.py` | `from src.config import MODELS, OPENROUTER_BASE_URL, PREPROC_MODEL_MAP` | VERIFIED | Line 18: imports used to build PROVIDERS dict and auto-fill preproc model |
| `src/config_manager.py` | `src/config.py` | `from src.config import ExperimentConfig, PRICE_TABLE` | VERIFIED | Line 13: ExperimentConfig used in load_config, get_full_config_dict; PRICE_TABLE used in validate_config |
| `src/run_experiment.py` | `src/config_manager.py` | `from src.config_manager import find_config_path, CONFIG_FILENAME` | VERIFIED | Line 18; _check_config_exists() uses find_config_path(); called in main() at line 549 |
| `src/pilot.py` | `src/config_manager.py` | `from src.config_manager import find_config_path, CONFIG_FILENAME` | VERIFIED | Line 23; _check_config_exists() uses find_config_path(); called in main() at line 1120 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SETUP-01 | 13-01 | Persist experiment configuration as JSON file with sparse override pattern | SATISFIED | save_config/load_config implemented; sparse override test passes; round-trip verified |
| SETUP-02 | 13-01 | Validate config on load — model strings, noise rates, repetitions, temperature, data paths | SATISFIED | validate_config covers all 5 validation categories; tests confirm error messages returned |
| SETUP-03 | 13-02 | CLI entry point (src/cli.py) with argparse subparsers architecture | SATISFIED | build_cli() creates ArgumentParser with subparsers; extensible for Phase 14 |
| SETUP-04 | 13-02 | Interactive setup wizard guiding provider selection, model auto-fill, path configuration, config file generation | SATISFIED | run_setup_wizard implements full 9-step interactive flow; input_fn injection for testability |
| SETUP-05 | 13-02 | API key validation via minimal test call distinguishing auth errors from network/transient errors | SATISFIED | validate_api_key checks 401/403/invalid/auth keywords; all 4 providers tested |
| SETUP-06 | 13-02 | Environment prerequisite check — Python >= 3.11, required packages installed, API key env vars | SATISFIED | check_environment() checks sys.version_info and importlib.metadata.version for 8 packages |
| SETUP-07 | 13-02 | Config-missing guard in run_experiment.py and pilot.py | SATISFIED | _check_config_exists() present in both files; called before argument parsing in main() |

**No orphaned requirements found.** All 7 SETUP-* IDs from REQUIREMENTS.md (lines 83-88, 171-177) are claimed by plans and verified.

---

### Anti-Patterns Found

No anti-patterns detected in any phase 13 files.

Files scanned: `src/config_manager.py`, `src/cli.py`, `src/setup_wizard.py`, `tests/test_config_manager.py`, `tests/test_cli.py`, `tests/test_setup_wizard.py`

No TODOs, FIXMEs, placeholder returns, or stub implementations found.

---

### Test Results

- **Phase 13 tests:** 42/42 passed (test_config_manager.py: 20, test_cli.py: 5, test_setup_wizard.py: 17)
- **Full suite regression:** 422/422 passed, 0 failures, 1 benign statsmodels warning

---

### Human Verification Required

#### 1. Interactive Wizard End-to-End Flow

**Test:** Run `python src/cli.py setup` (without --non-interactive) in a terminal with a real API key set.
**Expected:** Wizard prints numbered provider list, accepts keyboard input for selection, auto-fills preproc model, offers API key validation, asks about file paths, writes experiment_config.json, and prints "Setup complete! Run experiments with: python src/run_experiment.py"
**Why human:** Interactive terminal I/O flow cannot be fully exercised by automated tests — the test suite mocks input_fn and save_config.

#### 2. Config-Missing Guard Exit Behavior

**Test:** Delete or rename experiment_config.json, then run `python src/run_experiment.py --help` or `python src/pilot.py`.
**Expected:** Process exits with an error message referencing `python src/cli.py setup` before printing help.
**Why human:** The guard depends on the working directory's filesystem state at runtime; automated tests patch find_config_path.

---

### Summary

Phase 13 fully achieves its goal. The guided setup wizard is implemented end-to-end:

- **Foundation (Plan 01):** `src/config_manager.py` provides JSON persistence with sparse override merge, tuple round-trip, and comprehensive field validation against ExperimentConfig defaults and PRICE_TABLE. 20 unit tests verify all behaviors.

- **Wizard + CLI (Plan 02):** `src/cli.py` provides an argparse entry point routing to the wizard. `src/setup_wizard.py` implements the full interactive Q&A flow: environment check, provider selection, model auto-fill from PREPROC_MODEL_MAP, API key validation (with auth-vs-other error differentiation), path configuration, and config file generation. Non-interactive mode (`--non-interactive`) writes defaults without prompting. 22 tests cover all wizard behaviors.

- **Config guards:** Both `src/run_experiment.py` and `src/pilot.py` now call `_check_config_exists()` before argument parsing, directing users to the wizard if no config file is found.

- **No regressions:** Full 422-test suite passes after all phase 13 changes.

All 7 requirement IDs (SETUP-01 through SETUP-07) are satisfied with evidence. No stubs, orphans, or anti-patterns found.

---

_Verified: 2026-03-24T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
