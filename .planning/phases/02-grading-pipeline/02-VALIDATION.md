---
phase: 2
slug: grading-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_grade_results.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_grade_results.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_humaneval_pass -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_humaneval_fail -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_mbpp_pass -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_sandbox_timeout -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_sandbox_memory_limit -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_sandbox_fork_bomb -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_code_extraction -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 1 | GRAD-01 | unit | `pytest tests/test_grade_results.py::test_syntax_error -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_integer -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_commas -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_fractions -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_latex -x` | ❌ W0 | ⬜ pending |
| 02-02-05 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_negatives -x` | ❌ W0 | ⬜ pending |
| 02-02-06 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_units -x` | ❌ W0 | ⬜ pending |
| 02-02-07 | 02 | 1 | GRAD-02 | unit | `pytest tests/test_grade_results.py::test_gsm8k_extraction_failed -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | GRAD-03 | integration | `pytest tests/test_grade_results.py::test_db_write_pass_fail -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | GRAD-03 | integration | `pytest tests/test_grade_results.py::test_db_grading_details -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | GRAD-03 | integration | `pytest tests/test_grade_results.py::test_batch_grading -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_grade_results.py` — stubs for GRAD-01, GRAD-02, GRAD-03 (all tests above)
- [ ] Conftest updates: add `sample_run_record` fixture with `raw_output` field for grading test data

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fork bomb protection under real OS load | GRAD-01 | OS-level process limit behavior varies by system | Run `test_sandbox_fork_bomb` and verify host remains responsive |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
