---
phase: 5
slug: statistical-analysis-and-derived-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_compute_derived.py tests/test_analyze_results.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_compute_derived.py tests/test_analyze_results.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DERV-01 | unit | `pytest tests/test_compute_derived.py::test_cr_computation -x` | No - W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | DERV-02 | unit | `pytest tests/test_compute_derived.py::test_quadrant_classification -x` | No - W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | DERV-03 | unit | `pytest tests/test_compute_derived.py::test_cost_rollups -x` | No - W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | STAT-01 | unit | `pytest tests/test_analyze_results.py::test_glmm_fit -x` | No - W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | STAT-01 | unit | `pytest tests/test_analyze_results.py::test_glmm_fallback -x` | No - W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | STAT-02 | unit | `pytest tests/test_analyze_results.py::test_bootstrap_ci -x` | No - W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | STAT-03 | unit | `pytest tests/test_analyze_results.py::test_mcnemar -x` | No - W0 | ⬜ pending |
| 05-02-05 | 02 | 2 | STAT-04 | unit | `pytest tests/test_analyze_results.py::test_kendall_tau -x` | No - W0 | ⬜ pending |
| 05-02-06 | 02 | 2 | STAT-05 | unit | `pytest tests/test_analyze_results.py::test_bh_correction -x` | No - W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_compute_derived.py` — stubs for DERV-01, DERV-02, DERV-03
- [ ] `tests/test_analyze_results.py` — stubs for STAT-01 through STAT-05
- [ ] `tests/conftest.py` — add fixtures for synthetic experiment_runs data (5 reps per prompt-condition-model) for deterministic statistical test verification
- [ ] `pip install tabulate` — only new dependency

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GLMM coefficient interpretation | STAT-01 | Statistical judgment | Verify OR and RD values are plausible given experimental design |
| Effect size summary table readability | STAT-02 | Visual inspection | Check CSV output imports cleanly into LaTeX |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
