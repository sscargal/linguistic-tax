---
phase: 3
slug: interventions-and-execution-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | INTV-01 | unit | `pytest tests/test_interventions.py -k router` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | INTV-02 | unit | `pytest tests/test_interventions.py -k self_correct` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | INTV-03 | unit | `pytest tests/test_interventions.py -k sanitize` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | INTV-04 | unit | `pytest tests/test_interventions.py -k compress` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | INTV-05 | unit | `pytest tests/test_interventions.py -k repetition` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | EXEC-01 | unit | `pytest tests/test_api_client.py -k claude` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | EXEC-02 | unit | `pytest tests/test_api_client.py -k gemini` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 1 | EXEC-03 | unit | `pytest tests/test_api_client.py -k instrumentation` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | EXEC-04 | integration | `pytest tests/test_engine.py -k resumability` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | EXEC-05 | integration | `pytest tests/test_engine.py -k rate_limit` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_interventions.py` — stubs for INTV-01 through INTV-05
- [ ] `tests/test_api_client.py` — stubs for EXEC-01 through EXEC-03
- [ ] `tests/test_engine.py` — stubs for EXEC-04, EXEC-05
- [ ] `tests/conftest.py` — shared fixtures (mock API responses, temp DB)

*Existing pytest infrastructure from Phase 1/2 covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live API call succeeds | EXEC-01, EXEC-02 | Requires real API keys and network | Run pilot with 1 prompt per model, verify DB rows |
| Rate limiter prevents 429s | EXEC-05 | Requires sustained API traffic | Run 50+ calls in burst mode, check for 429 errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
