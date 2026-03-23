---
phase: 06
slug: publication-figures
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_generate_figures.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_generate_figures.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | FIG-01 | unit | `pytest tests/test_generate_figures.py::TestAccuracyCurves -v` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | FIG-02 | unit | `pytest tests/test_generate_figures.py::TestQuadrantPlots -v` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | FIG-03 | unit | `pytest tests/test_generate_figures.py::TestCostHeatmaps -v` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | FIG-04 | unit | `pytest tests/test_generate_figures.py::TestKendallViz -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_generate_figures.py` — stubs for FIG-01 through FIG-04
- [ ] Test fixtures providing synthetic data in SQLite for figure generation

*Existing test infrastructure (conftest.py, pytest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual quality of figures | FIG-01..04 | Aesthetic judgment | Open generated PDF/PNG files, verify readability, colors, labels |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
