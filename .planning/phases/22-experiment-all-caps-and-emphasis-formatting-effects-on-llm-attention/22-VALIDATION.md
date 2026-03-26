---
phase: 22
slug: experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_emphasis_converter.py -v --tb=short` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_emphasis_converter.py -v --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | emphasis_converter module | unit | `pytest tests/test_emphasis_converter.py -v` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | intervention registration | unit | `pytest tests/test_emphasis_converter.py -v -k intervention` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | prompt conversion output | unit | `pytest tests/test_emphasis_converter.py -v -k convert` | ❌ W0 | ⬜ pending |
| 22-03-01 | 03 | 2 | experiment execution | integration | `pytest tests/test_emphasis_converter.py -v -k integration` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_emphasis_converter.py` — stubs for emphasis conversion functions, intervention routing, code-block protection
- [ ] Existing `tests/conftest.py` — shared fixtures already exist

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Key-term identification quality | Cluster A prompts | Requires human judgment on which terms are "key" | Review 20-prompt key-term annotations for correctness |
| Experiment result interpretation | Statistical analysis | Requires domain expertise | Review McNemar's/bootstrap results for scientific validity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
