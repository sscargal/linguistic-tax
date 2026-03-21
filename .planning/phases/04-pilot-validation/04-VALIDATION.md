---
phase: 4
slug: pilot-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_pilot.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds (unit tests only, no API calls) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pilot.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | PILOT-01 | unit | `pytest tests/test_pilot.py::test_select_pilot_prompts -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | PILOT-01 | unit | `pytest tests/test_pilot.py::test_filter_pilot_matrix -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | PILOT-01 | unit | `pytest tests/test_pilot.py::test_data_completeness_audit -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | PILOT-01 | unit | `pytest tests/test_pilot.py::test_noise_sanity_check -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | PILOT-02 | unit | `pytest tests/test_pilot.py::test_spot_check_sampling -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | PILOT-02 | unit | `pytest tests/test_pilot.py::test_spot_check_report_format -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 1 | PILOT-03 | unit | `pytest tests/test_pilot.py::test_cost_projection -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | 01 | 1 | PILOT-03 | unit | `pytest tests/test_pilot.py::test_budget_gate -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pilot.py` — stubs for PILOT-01, PILOT-02, PILOT-03
- [ ] No new framework install needed — pytest already configured in pyproject.toml

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grading spot-check human review | PILOT-02 | Requires human judgment on edge cases | Review `results/pilot_spot_check.json`, check flagged items for systematic patterns |
| BERTScore flagged outliers | PILOT-01 | Semantic fidelity requires human assessment | Review pairs below 0.85 threshold for meaning drift |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
