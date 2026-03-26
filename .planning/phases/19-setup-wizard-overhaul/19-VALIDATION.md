---
phase: 19
slug: setup-wizard-overhaul
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -x -q` |
| **Full suite command** | `.venv/bin/python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3 -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | WIZ-01 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "explain" -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | WIZ-02 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "multi_provider" -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | WIZ-03, DSC-03 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "free_text" -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | WIZ-04 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "env_write" -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | WIZ-05 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "budget" -x` | ❌ W0 | ⬜ pending |
| 19-01-06 | 01 | 1 | WIZ-06 | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "validate" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_setup_wizard.py` — expand/rewrite for multi-provider wizard flow (WIZ-01 through WIZ-06, DSC-03)
- [ ] Tests for `_mask_key()`, `_parse_provider_selection()`, `_browse_models()`, `_build_budget_preview()`
- [ ] Tests for Ctrl+C handling at each wizard step
- [ ] Tests for existing config detection (Add/Reconfigure/Start fresh)
- [ ] Tests for `validate_api_key()` with model_id parameter

*Existing 18 tests in test_setup_wizard.py need major rewrite to cover new multi-provider flow.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive wizard UX flow | WIZ-01..06 | Full end-to-end interactive session | Run `python -m src.cli setup`, walk through all steps manually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
