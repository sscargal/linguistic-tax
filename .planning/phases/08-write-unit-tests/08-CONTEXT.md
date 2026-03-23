# Phase 8: Write Unit Tests - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand test coverage for the research toolkit to 80% line coverage and create a comprehensive QA bash script (`scripts/qa_script.sh`) for CLI smoke testing, data pipeline validation, config checks, and optional live API tests. The project already has 333 passing tests across 14 files — this phase fills gaps and adds a unified QA entry point.

</domain>

<decisions>
## Implementation Decisions

### Coverage scope
- Run `pytest --cov` to measure current coverage and identify gaps
- Fill gaps proportionally — focus on modules with lowest coverage percentage, even if they already have large test files
- Two separate efforts: pytest unit/integration tests AND `scripts/qa_script.sh` bash QA script

### Test quality bar
- Target: 80% line coverage across all modules
- Add negative/error path tests where missing (invalid inputs, missing files, corrupt DB)
- Tests must be meaningful — no filler tests just to hit numbers

### Test categories
- Both unit tests AND integration tests (multi-module flows like noise→intervention→grading)
- `qa_script.sh` covers CLI-level E2E smoke testing separately
- Mark slow tests with `@pytest.mark.slow` for `pytest -m 'not slow'` fast runs

### QA script (`scripts/qa_script.sh`)
- **Sections (grouped):** 1) Environment checks, 2) Unit tests (pytest run), 3) CLI smoke tests, 4) Data pipeline checks, 5) Config validation, 6) Live API tests (if `--live`)
- **Flags:** `--live` enables real API calls (default: offline only), `--section <name>` runs a specific section, `--log` writes results to log file
- **Status codes:** PASS, FAIL, WARN, INFO per check
- **Summary format:** Detailed table with check number, status, time, description, then counts + overall VERDICT
- **Exit code:** Non-zero on any FAIL (CI-compatible), but primary focus is local use
- **Pytest included:** The qa_script runs pytest as one of its checks — single QA entry point

### Test isolation
- Temp file SQLite databases per test (via pytest `tmp_path` fixture) — not in-memory
- Matches existing conftest.py pattern

### Conftest and fixtures
- Extend existing conftest.py as needed — don't refactor what works
- Create shared mock factories for API responses (mock_anthropic_response, mock_google_response, mock_openai_response) in conftest to DRY up test_api_client and test_run_experiment

### Test naming conventions
- Follow existing pattern: `TestClassName` classes with `test_descriptive_snake_case` methods
- Consistent with all 14 existing test files

### Claude's Discretion
- Exact integration test scenarios to add
- Which coverage gaps to prioritize within the 80% target
- Internal structure of helper functions within qa_script.sh
- pytest marker registration in pyproject.toml

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Testing infrastructure
- `tests/conftest.py` — Existing shared fixtures (7 fixtures including temp DB, sample records, analysis DB)
- `pyproject.toml` — pytest configuration, dependencies

### Source modules under test
- `src/config.py` — Configuration module with pinned settings
- `src/noise_generator.py` — Type A/B noise with seed determinism
- `src/prompt_compressor.py` — Compress/sanitize via cheap model
- `src/prompt_repeater.py` — Query repetition intervention
- `src/run_experiment.py` — Execution engine with resumability
- `src/grade_results.py` — Sandboxed code grader + regex math grader
- `src/analyze_results.py` — GLMM, bootstrap, McNemar's, Kendall's tau
- `src/compute_derived.py` — CR, quadrants, cost rollups
- `src/api_client.py` — Multi-provider API client with streaming
- `src/db.py` — SQLite schema and operations
- `src/pilot.py` — Pilot validation tooling
- `src/generate_figures.py` — Publication figure generation

### Research spec
- `docs/RDD_Linguistic_Tax_v4.md` — Research Design Document (authoritative spec for experimental parameters)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py`: 7 shared fixtures — sample_config, tmp_db_path, sample_prompt_record, sample_run_record, populated_test_db, analysis_test_db, degenerate_test_db
- 333 existing tests across 14 test files (~5,000 lines total) — all passing in ~33s
- Every `src/` module already has a corresponding `tests/test_*.py` file

### Established Patterns
- Test classes: `TestClassName` with `test_descriptive_method_name`
- API mocking: inline mocks per test file (to be centralized in conftest)
- DB testing: temp file DBs via `tmp_path` fixture with deterministic data patterns
- Determinism tests: noise generators verified for same-seed reproducibility

### Integration Points
- All CLI entry points use argparse — qa_script.sh can invoke `python -m src.module --help` or with basic args
- pytest already configured in pyproject.toml
- API keys via environment variables (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY)

</code_context>

<specifics>
## Specific Ideas

- The QA script should feel like a pre-release checklist — "run this before users see it"
- Detailed table output format with numbered checks, status, time, and description
- Each test section (environment, pytest, CLI, data, config, live API) is independently runnable via `--section`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-write-unit-tests*
*Context gathered: 2026-03-23*
