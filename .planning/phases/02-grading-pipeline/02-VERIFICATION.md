---
phase: 02-grading-pipeline
verified: 2026-03-19T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 2: Grading Pipeline Verification Report

**Phase Goal:** Researcher can automatically grade any LLM output — HumanEval/MBPP code is executed in a secure sandbox with pass/fail, GSM8K answers are extracted and compared via regex, and all grades are recorded in SQLite
**Verified:** 2026-03-19
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                            | Status     | Evidence                                                                                |
|-----|--------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------|
| 1   | HumanEval code outputs are executed in a subprocess sandbox with 10s timeout and 512MB memory limit | VERIFIED | `_run_sandbox` uses Popen + `_set_limits` (RLIMIT_AS=512MB, RLIMIT_CPU=15s). `grade_code` calls `_run_sandbox` with 10s default timeout |
| 2   | MBPP code outputs are executed with direct assert test harness (not HumanEval check/candidate pattern) | VERIFIED | `_build_mbpp_harness` produces `f"{llm_code}\n\n{test_code}\n"` (raw asserts). `_build_humaneval_harness` adds `check({entry_point})`. Distinct paths confirmed |
| 3   | Infinite loops, fork bombs, and memory bombs do not hang or crash the host process              | VERIFIED | `test_sandbox_timeout`, `test_sandbox_fork_bomb`, `test_sandbox_memory_limit` all pass (57/57 in 15.23s). Process group kill via `os.killpg` on timeout |
| 4   | Markdown fences are stripped from LLM responses before code execution                          | VERIFIED | `extract_code` uses `re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)`, returns `blocks[-1].strip()` or full stripped text. `test_strips_python_fences`, `test_multiple_blocks_returns_last` pass |
| 5   | All grading results (pass/fail + metadata) are written to SQLite                               | VERIFIED | `save_grade_result` in `src/db.py` UPDATEs `experiment_runs.pass_fail` and INSERTs into `grading_details`. `batch_grade` calls it for every run. `test_save_grade_result` and `test_batch_grading` pass |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                          | Expected                                              | Status      | Details                                                                                     |
|-----------------------------------|-------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------|
| `src/grade_results.py`            | Code grading with sandbox execution                   | VERIFIED    | 679 lines, non-stub. Exports GradeResult, grade_code, extract_code, _run_sandbox, _set_limits, _build_humaneval_harness, _build_mbpp_harness, _extract_entry_point, ExtractionResult, _extract_number, _normalize_number, grade_math, grade_run, batch_grade, _build_parser, main |
| `src/db.py`                       | Extended schema with grading_details table            | VERIFIED    | Contains `CREATE TABLE IF NOT EXISTS grading_details` with all 7 required columns (run_id, fail_reason, extraction_method, stdout, stderr, execution_time_ms, graded_at). Contains `def save_grade_result(` |
| `tests/test_grade_results.py`     | Adversarial sandbox tests and code grading tests      | VERIFIED    | 679 lines, 57 tests. Contains test_sandbox_timeout, test_sandbox_memory_limit, test_sandbox_fork_bomb, test_humaneval_pass, test_mbpp_pass, test_code_extraction-equivalent tests, and 16 GSM8K format variant tests |
| `tests/conftest.py`               | sample_run_record fixture                             | VERIFIED    | Contains `def sample_run_record` fixture returning dict with all required fields |

### Key Link Verification

| From                    | To               | Via                                          | Status      | Details                                                                             |
|-------------------------|------------------|----------------------------------------------|-------------|-------------------------------------------------------------------------------------|
| `src/grade_results.py`  | `src/db.py`      | insert grading_details and update pass_fail  | WIRED       | `batch_grade` imports `from src.db import init_database, query_runs, save_grade_result` and calls `save_grade_result(conn, ...)` for each run |
| `src/grade_results.py`  | `data/prompts.json` | reads test_code and entry_point from prompt records | WIRED | `batch_grade` opens `prompts_path` and builds `prompts_by_id` dict keyed on `problem_id`. `grade_code` reads `prompt_record["test_code"]` and `prompt_record["prompt_text"]` |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                              | Status    | Evidence                                                                                                     |
|-------------|-------------|----------------------------------------------------------------------------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------|
| GRAD-01     | 02-01-PLAN  | Auto-grade HumanEval/MBPP outputs via sandboxed subprocess code execution with timeout and resource limits | SATISFIED | `grade_code` + `_run_sandbox` with RLIMIT_AS/NPROC/CPU. test_humaneval_pass, test_mbpp_pass, all sandbox adversarial tests pass |
| GRAD-02     | 02-01-PLAN  | Auto-grade GSM8K outputs via regex extraction of final numerical answer with format-variant handling      | SATISFIED | `grade_math` + `_extract_number` with 6 pattern families + LaTeX boxed + overlap dedup. 16 GSM8K format variant tests pass |
| GRAD-03     | 02-01-PLAN  | Record pass/fail result for every experimental run in SQLite                                             | SATISFIED | `save_grade_result` writes to both `experiment_runs.pass_fail` and `grading_details` table. `test_save_grade_result` and `test_batch_grading` verify DB writes |

No orphaned requirements. REQUIREMENTS.md maps GRAD-01, GRAD-02, GRAD-03 to Phase 2, all claimed and satisfied by plan 02-01.

### Anti-Patterns Found

None. Scanned `src/grade_results.py`, `src/db.py`, `tests/test_grade_results.py` for TODO, FIXME, XXX, HACK, placeholder comments, empty returns, and stub implementations. All clear.

### Human Verification Required

None. All goal truths are verifiable programmatically. The sandbox security model (resource limits, process group kill) was confirmed by adversarial tests executing in CI.

### Gaps Summary

No gaps. All 5 must-have truths verified, all 4 artifacts substantive and wired, both key links confirmed, all 3 requirements satisfied. The full test suite (143 tests) passes with no regressions.

---

## Supporting Evidence

**Test run:** `python -m pytest tests/test_grade_results.py -x --timeout=60 -q` — 57 passed in 15.23s

**Full suite:** `python -m pytest tests/ --timeout=60 -q` — 143 passed in 15.75s

**Import check:** `from src.grade_results import grade_code, grade_math, grade_run, batch_grade, GradeResult, ExtractionResult` — OK

**DB import:** `from src.db import save_grade_result` — OK

**CLI:** `python -m src.grade_results --help` — displays all required options (--db, --run-id, --force, --format, --prompts)

**Commits verified:**
- `280299c` — feat(02-01): add code grading pipeline with subprocess sandbox
- `1666d58` — feat(02-01): add GSM8K math grading, batch mode, and CLI

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
