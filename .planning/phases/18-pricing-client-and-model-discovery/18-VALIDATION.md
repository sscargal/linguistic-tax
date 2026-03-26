---
phase: 18
slug: pricing-client-and-model-discovery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_model_discovery.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_model_discovery.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | DSC-01 | unit | `pytest tests/test_model_discovery.py -k "test_list_models"` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | DSC-02 | unit | `pytest tests/test_model_discovery.py -k "test_context_window_and_pricing"` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | PRC-02 | unit | `pytest tests/test_model_discovery.py -k "test_openrouter_pricing"` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | DSC-01,DSC-02 | integration | `pytest tests/test_config_commands.py -k "test_list_models"` | ✅ | ⬜ pending |
| 18-02-02 | 02 | 2 | DSC-01 | unit | `pytest tests/test_model_discovery.py -k "test_fallback"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model_discovery.py` — stubs for DSC-01, DSC-02, PRC-02
- [ ] Test fixtures for mocked provider API responses

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live provider API queries return real data | DSC-01 | Requires valid API keys and network | Run `propt list-models` with valid API keys set in .env |
| OpenRouter live pricing matches current rates | PRC-02 | Pricing changes over time | Compare `propt list-models` OpenRouter pricing with https://openrouter.ai/models |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
