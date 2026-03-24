---
phase: 13
slug: guided-setup-wizard-for-project-configuration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_cli.py tests/test_setup_wizard.py tests/test_config_manager.py -x -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cli.py tests/test_setup_wizard.py tests/test_config_manager.py -x -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | P13-01 | unit | `pytest tests/test_cli.py -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | P13-02 | unit | `pytest tests/test_setup_wizard.py -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | P13-03 | unit | `pytest tests/test_config_manager.py -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | P13-04 | unit | `pytest tests/test_config_manager.py -x` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 1 | P13-05 | unit | `pytest tests/test_setup_wizard.py -x` | ❌ W0 | ⬜ pending |
| 13-01-06 | 01 | 1 | P13-06 | unit (mocked) | `pytest tests/test_setup_wizard.py -x` | ❌ W0 | ⬜ pending |
| 13-01-07 | 01 | 1 | P13-07 | unit | `pytest tests/test_run_experiment.py -x` | ⬜ partial | ⬜ pending |
| 13-01-08 | 01 | 1 | P13-08 | unit | `pytest tests/test_config_manager.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` — CLI entry point, subparser routing, help output
- [ ] `tests/test_setup_wizard.py` — wizard flow with mocked input, env checks, API validation
- [ ] `tests/test_config_manager.py` — config save/load, sparse override merge, validation rules
- [ ] Mock `input()` strategy: use `unittest.mock.patch("builtins.input")` with side_effect lists

*Existing infrastructure covers partial requirements (test_run_experiment.py already exists).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive wizard UX flow | P13-02 | Terminal interaction quality | Run `python src/cli.py setup`, complete wizard, verify prompts are clear |
| API key validation with real key | P13-06 | Requires live API credentials | Set valid API key, run wizard, confirm validation passes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
