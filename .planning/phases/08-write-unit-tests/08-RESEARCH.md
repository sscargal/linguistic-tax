# Phase 8: Write Unit Tests - Research

**Researched:** 2026-03-24
**Domain:** Python testing, pytest, coverage analysis, bash QA scripting
**Confidence:** HIGH

## Summary

Phase 8 expands test coverage from 78% to 80%+ and creates a comprehensive QA bash script. The project already has 333 passing tests across 14 files with solid infrastructure (conftest fixtures, tmp_path DB pattern, deterministic mocking). The measured coverage gap is small (2 percentage points) but concentrated: `analyze_results.py` at 62% and `compute_derived.py` at 64% are the primary targets. Both have large untested CLI `main()` functions and several helper functions with missing branches. The QA script (`scripts/qa_script.sh`) is a new artifact providing a unified pre-release checklist.

**Primary recommendation:** Focus pytest effort on the two lowest-coverage modules (analyze_results, compute_derived), add shared mock factories to conftest, then build the qa_script.sh as a standalone deliverable with section-based execution.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Run `pytest --cov` to measure current coverage and identify gaps
- Fill gaps proportionally -- focus on modules with lowest coverage percentage
- Two separate efforts: pytest unit/integration tests AND `scripts/qa_script.sh` bash QA script
- Target: 80% line coverage across all modules
- Add negative/error path tests where missing (invalid inputs, missing files, corrupt DB)
- Tests must be meaningful -- no filler tests just to hit numbers
- Both unit tests AND integration tests (multi-module flows like noise->intervention->grading)
- `qa_script.sh` covers CLI-level E2E smoke testing separately
- Mark slow tests with `@pytest.mark.slow` for `pytest -m 'not slow'` fast runs
- QA script sections: 1) Environment checks, 2) Unit tests (pytest run), 3) CLI smoke tests, 4) Data pipeline checks, 5) Config validation, 6) Live API tests (if `--live`)
- QA script flags: `--live`, `--section <name>`, `--log`
- Status codes: PASS, FAIL, WARN, INFO per check
- Summary format: Detailed table with check number, status, time, description, then counts + overall VERDICT
- Exit code: Non-zero on any FAIL (CI-compatible)
- Temp file SQLite databases per test (via pytest `tmp_path` fixture)
- Extend existing conftest.py -- don't refactor what works
- Create shared mock factories for API responses (mock_anthropic_response, mock_google_response, mock_openai_response) in conftest
- Follow existing pattern: `TestClassName` classes with `test_descriptive_snake_case` methods

### Claude's Discretion
- Exact integration test scenarios to add
- Which coverage gaps to prioritize within the 80% target
- Internal structure of helper functions within qa_script.sh
- pytest marker registration in pyproject.toml

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x (already installed) | Test framework | Already used, 333 tests passing |
| pytest-cov | 7.1.0 (just installed) | Coverage reporting | Standard pytest coverage plugin |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | stdlib | Mocking API calls, subprocess | Already used extensively across test files |
| tmp_path | pytest builtin | Temp directories for DB files | Already the standard pattern in conftest |

### No New Dependencies Needed
The existing stack (pytest + unittest.mock + stdlib) handles all test needs. pytest-cov was installed during research and should be added to dev dependencies.

**pyproject.toml update needed:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

## Architecture Patterns

### Current Coverage Baseline (measured 2026-03-24)

| Module | Stmts | Miss | Cover | Gap Nature |
|--------|-------|------|-------|------------|
| analyze_results.py | 421 | 159 | 62% | CLI main(), helper fns, sensitivity CLI |
| compute_derived.py | 165 | 59 | 64% | CLI main(), quadrant migration in main |
| generate_figures.py | 211 | 47 | 78% | Some branch paths in plot functions |
| noise_generator.py | 168 | 35 | 79% | CLI main() entry point (lines 511-581) |
| grade_results.py | 246 | 49 | 80% | Error paths, edge cases |
| pilot.py | 400 | 64 | 84% | Some CLI paths, edge cases |
| run_experiment.py | 168 | 21 | 88% | Error handling paths |
| api_client.py | 124 | 8 | 94% | OpenAI streaming edge case |
| config.py | 30 | 0 | 100% | -- |
| db.py | 43 | 0 | 100% | -- |
| prompt_compressor.py | 34 | 0 | 100% | -- |
| prompt_repeater.py | 2 | 0 | 100% | -- |
| **TOTAL** | **2012** | **442** | **78%** | Need ~40 more stmts covered |

### Priority Order for Coverage Gaps

1. **analyze_results.py** (62% -> target 80%): 75 lines to cover. Main gaps:
   - Lines 935-1033: `main()` CLI entry point (untested)
   - Lines 1043-1069, 1087-1114, 1126-1154, 1171-1197, 1214-1224: CLI helper functions (`_run_glmm_analysis`, `_run_mcnemar_analysis_cli`, etc.)
   - Lines 183-199, 215-228: Branch paths in core analysis functions

2. **compute_derived.py** (64% -> target 80%): 26 lines to cover. Main gaps:
   - Lines 397-514: `main()` CLI entry point (untested)
   - Lines 191-195: Edge case in cost rollups
   - Lines 151-152: Edge case in derived metrics

3. **noise_generator.py** (79% -> target 80%): Just 2 lines to cover.
   - Lines 511-538, 543-581: CLI `main()` entry point

4. **generate_figures.py** (78% -> target 80%): 5 lines to cover.
   - Various branch paths in plotting functions

### Recommended Test File Structure
```
tests/
├── conftest.py              # Extended with mock factories
├── test_analyze_results.py  # Add CLI + helper function tests
├── test_compute_derived.py  # Add CLI + main() tests
├── test_noise_generator.py  # Add CLI entry point test
├── test_generate_figures.py # Add branch coverage tests
├── test_integration.py      # NEW: multi-module integration flows
scripts/
├── qa_script.sh             # NEW: comprehensive QA runner
```

### Pattern: Shared Mock Factories in conftest.py

```python
@pytest.fixture
def mock_anthropic_response():
    """Factory for mock Anthropic API responses."""
    def _make(content="test response", input_tokens=100, output_tokens=50,
              model="claude-sonnet-4-20250514", ttft=0.05):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.content = [MagicMock(text=content)]
        response.model = model
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        return response
    return _make

@pytest.fixture
def mock_google_response():
    """Factory for mock Google Gemini API responses."""
    def _make(text="test response", input_tokens=100, output_tokens=50):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.text = text
        response.usage_metadata.prompt_token_count = input_tokens
        response.usage_metadata.candidates_token_count = output_tokens
        return response
    return _make

@pytest.fixture
def mock_openai_response():
    """Factory for mock OpenAI API responses."""
    def _make(content="test response", input_tokens=100, output_tokens=50,
              model="gpt-4o-2024-11-20"):
        from unittest.mock import MagicMock
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = content
        chunk.usage = MagicMock()
        chunk.usage.prompt_tokens = input_tokens
        chunk.usage.completion_tokens = output_tokens
        return chunk
    return _make
```

### Pattern: CLI Main Function Testing

```python
class TestCLI:
    """Test CLI entry point for analyze_results."""

    def test_main_glmm_subcommand(self, analysis_test_db, tmp_path):
        """Test main() with glmm subcommand."""
        output_dir = str(tmp_path / "output")
        with patch("sys.argv", [
            "analyze_results", "--db", analysis_test_db,
            "--output-dir", output_dir, "glmm"
        ]):
            from src.analyze_results import main
            main()
        # Verify output files created
        assert (tmp_path / "output").exists()
```

### Pattern: Integration Tests (Multi-Module Flow)

```python
class TestNoiseToGradingPipeline:
    """Integration test: noise generation -> intervention -> grading."""

    def test_noise_then_grade_humaneval(self, tmp_path):
        """Generate noisy prompt, apply intervention, verify gradeable."""
        from src.noise_generator import apply_type_a_noise
        from src.grade_results import grade_humaneval_output

        clean_prompt = "def add(a, b):\n    return a + b"
        noisy = apply_type_a_noise(clean_prompt, error_rate=0.1, seed=42)
        # Verify noisy prompt is different but still processable
        assert noisy != clean_prompt
```

### Anti-Patterns to Avoid
- **Filler tests:** Tests that only assert `True` or test trivial getters to inflate coverage
- **Over-mocking:** Mocking so many internals that tests don't verify real behavior
- **Fragile string matching:** Asserting exact log messages or output strings that break on formatting changes
- **Testing third-party code:** Don't test that sqlite3 works or that argparse parses correctly

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage measurement | Manual line counting | `pytest-cov` | Accurate, integrates with pytest |
| Temp file cleanup | Manual try/finally cleanup | pytest `tmp_path` fixture | Automatic cleanup, isolation |
| API response mocking | Real API calls in tests | `unittest.mock.patch` | Deterministic, free, fast |
| Test markers | Custom skip decorators | `@pytest.mark.slow` | Standard pytest convention |

## Common Pitfalls

### Pitfall 1: Testing CLI main() without isolating sys.argv
**What goes wrong:** Tests modify sys.argv globally, causing side effects
**How to avoid:** Always use `unittest.mock.patch("sys.argv", [...])` context manager
**Warning signs:** Tests pass individually but fail when run together

### Pitfall 2: Database tests sharing state
**What goes wrong:** Tests write to same DB, order-dependent failures
**How to avoid:** Use `tmp_path` fixture for every DB test (already the pattern)
**Warning signs:** `pytest -x` passes but `pytest` fails on specific test

### Pitfall 3: Coverage-chasing with meaningless tests
**What goes wrong:** Tests cover lines but don't verify behavior
**How to avoid:** Every test must assert something meaningful about output or side effects
**Warning signs:** Tests with no assertions or only `assert True`

### Pitfall 4: QA script not being portable
**What goes wrong:** Script uses bash-isms or hardcoded paths that fail on other machines
**How to avoid:** Use `#!/usr/bin/env bash`, set -euo pipefail, detect python/venv dynamically
**Warning signs:** Works on developer machine only

### Pitfall 5: Forgetting to register pytest markers
**What goes wrong:** `@pytest.mark.slow` triggers warnings about unknown markers
**How to avoid:** Register in pyproject.toml `[tool.pytest.ini_options]` markers list
**Warning signs:** pytest warnings about unknown markers

## Code Examples

### QA Script Structure

```bash
#!/usr/bin/env bash
set -euo pipefail

# Color codes
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

PASS_COUNT=0; FAIL_COUNT=0; WARN_COUNT=0; CHECK_NUM=0
LIVE=false; LOG_FILE=""; SECTION=""

usage() {
    echo "Usage: $0 [--live] [--section NAME] [--log]"
    echo "Sections: env, pytest, cli, data, config, api"
}

run_check() {
    local description="$1"; shift
    CHECK_NUM=$((CHECK_NUM + 1))
    local start_time=$(date +%s%N)
    if "$@" > /dev/null 2>&1; then
        local elapsed=$(( ($(date +%s%N) - start_time) / 1000000 ))
        printf "| %3d | ${GREEN}PASS${NC} | %5dms | %s\n" "$CHECK_NUM" "$elapsed" "$description"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        local elapsed=$(( ($(date +%s%N) - start_time) / 1000000 ))
        printf "| %3d | ${RED}FAIL${NC} | %5dms | %s\n" "$CHECK_NUM" "$elapsed" "$description"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# Section functions: check_env, check_pytest, check_cli, check_data, check_config, check_api
```

### Negative/Error Path Test Examples

```python
class TestErrorPaths:
    def test_grade_with_corrupt_db(self, tmp_path):
        """Grading should handle corrupt database gracefully."""
        db_path = str(tmp_path / "corrupt.db")
        with open(db_path, "w") as f:
            f.write("not a database")
        with pytest.raises(Exception):
            from src.db import init_database
            # This should fail on corrupt file
            init_database(db_path)

    def test_analyze_empty_dataframe(self):
        """Analysis functions should handle empty input."""
        import pandas as pd
        from src.analyze_results import compute_bootstrap_cis
        df = pd.DataFrame()
        result = compute_bootstrap_cis(df, n_iterations=100, seed=42)
        # Should return empty/default result, not crash
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --cov=src --cov-report=term-missing` |

### Phase Requirements -> Test Map

This phase has no formal requirement IDs. The implicit requirements are:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Coverage >= 80% | coverage | `pytest --cov=src --cov-fail-under=80` | N/A (metric) |
| analyze_results CLI works | unit | `pytest tests/test_analyze_results.py -x` | Exists, needs expansion |
| compute_derived CLI works | unit | `pytest tests/test_compute_derived.py -x` | Exists, needs expansion |
| Mock factories in conftest | unit | `pytest tests/ -x` | Needs addition to conftest.py |
| Integration flows work | integration | `pytest tests/test_integration.py -x` | Needs creation |
| qa_script.sh runs | smoke | `bash scripts/qa_script.sh --section env` | Needs creation |
| Slow marker works | unit | `pytest tests/ -m 'not slow' -x` | Needs pyproject.toml update |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green + coverage >= 80%

### Wave 0 Gaps
- [ ] `pytest-cov` in dev dependencies (pyproject.toml)
- [ ] `markers` registered in pyproject.toml
- [ ] `tests/test_integration.py` -- new file for multi-module flows
- [ ] `scripts/qa_script.sh` -- new QA runner script

## Open Questions

1. **Exact coverage improvement needed is modest**
   - What we know: Currently at 78%, need 80%. That is roughly 40 additional statements to cover.
   - What is clear: The two lowest modules (analyze_results at 62%, compute_derived at 64%) have the most room for improvement.
   - Recommendation: Start with analyze_results CLI helpers -- they provide the most coverage gain per test.

2. **Integration test scope**
   - What we know: User wants multi-module flows (noise->intervention->grading).
   - What is unclear: How many integration tests are enough vs diminishing returns.
   - Recommendation: 3-5 integration tests covering the main pipeline paths (clean flow, noisy flow with intervention, error flow).

## Sources

### Primary (HIGH confidence)
- Direct `pytest --cov` run on the codebase (2026-03-24) -- measured actual coverage numbers
- Existing test files and conftest.py -- read directly from codebase
- pyproject.toml -- current configuration

### Secondary (MEDIUM confidence)
- pytest and pytest-cov documentation (well-known, stable APIs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - already established, no new dependencies needed
- Architecture: HIGH - directly measured coverage gaps, read all source files
- Pitfalls: HIGH - common pytest patterns, well-documented
- QA script design: HIGH - user specified exact requirements in CONTEXT.md

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain, no fast-moving dependencies)
