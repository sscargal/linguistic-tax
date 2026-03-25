---
phase: 16
slug: config-schema-and-defensive-fallbacks
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_model_registry.py tests/test_env_manager.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_model_registry.py tests/test_env_manager.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CFG-01 | unit | `pytest tests/test_model_registry.py -k "test_model_config" -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | CFG-02 | unit | `pytest tests/test_model_registry.py -k "test_registry" -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | PRC-01 | unit | `pytest tests/test_model_registry.py -k "test_default_models" -x` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | CFG-03 | unit | `pytest tests/test_model_registry.py -k "test_compute_cost_unknown" -x` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 1 | PRC-03 | unit | `pytest tests/test_model_registry.py -k "test_unknown_model_warning" -x` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 1 | CFG-04 | unit | `pytest tests/test_config_manager.py -k "test_validate_unknown" -x` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 2 | CFG-05 | unit | `pytest tests/test_config_manager.py -k "test_migrate" -x` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 2 | - | unit | `pytest tests/test_env_manager.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model_registry.py` — stubs for CFG-01, CFG-02, CFG-03, PRC-01, PRC-03
- [ ] `tests/test_env_manager.py` — stubs for env_manager load/write/check
- [ ] Updated `tests/test_config_manager.py` — stubs for CFG-04, CFG-05

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| .env file permissions (chmod 600) | CFG-05/env | OS-dependent, CI may not support | Create .env via env_manager, verify `stat -c %a .env` returns 600 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
