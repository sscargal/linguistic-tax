---
phase: 1
slug: foundation-and-data-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (testpaths = ["tests"]) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-04 | unit | `pytest tests/test_config.py -v` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-03 | unit | `pytest tests/test_db.py -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | NOISE-01, NOISE-02 | unit | `pytest tests/test_noise_generator.py -v` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | NOISE-03 | unit | `pytest tests/test_noise_generator.py -k esl -v` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | NOISE-04 | unit | `pytest tests/test_noise_generator.py -k determinism -v` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | DATA-01 | unit | `pytest tests/test_prompts.py -v` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | DATA-02 | unit | `pytest tests/test_matrix.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config.py` — stubs for DATA-04 (config module)
- [ ] `tests/test_db.py` — stubs for DATA-03 (SQLite schema)
- [ ] `tests/test_noise_generator.py` — stubs for NOISE-01, NOISE-02, NOISE-03, NOISE-04
- [ ] `tests/test_prompts.py` — stubs for DATA-01 (requires curate_prompts.py to be run first to generate data/prompts.json)
- [ ] `tests/test_matrix.py` — stubs for DATA-02 (requires generate_matrix.py to be run first)
- [ ] `tests/conftest.py` — shared fixtures (temp dirs, sample prompts)

*Existing infrastructure: pytest configured in pyproject.toml, tests/ directory exists.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ESL patterns linguistically accurate | NOISE-03 | Requires human judgment on L1 transfer fidelity | Review 5 sample ESL-noised prompts per L1 source language |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
