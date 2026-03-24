---
phase: 8
slug: write-unit-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --cov=src --cov-report=term-missing` |
| **Estimated runtime** | ~34 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --cov=src --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 34 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | Coverage infra | unit | `pytest tests/ -x -q` | ✅ | ⬜ pending |
| 08-01-02 | 01 | 1 | Mock factories | unit | `pytest tests/ -x -q` | ✅ conftest.py | ⬜ pending |
| 08-02-01 | 02 | 1 | analyze_results coverage | unit | `pytest tests/test_analyze_results.py -x` | ✅ | ⬜ pending |
| 08-02-02 | 02 | 1 | compute_derived coverage | unit | `pytest tests/test_compute_derived.py -x` | ✅ | ⬜ pending |
| 08-03-01 | 03 | 2 | Integration tests | integration | `pytest tests/test_integration.py -x` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | qa_script.sh | smoke | `bash scripts/qa_script.sh --section env` | ❌ W0 | ⬜ pending |
| 08-05-01 | 05 | 3 | Coverage >= 80% | coverage | `pytest --cov=src --cov-fail-under=80` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest-cov` added to dev dependencies in pyproject.toml
- [ ] `markers` registered in pyproject.toml (`slow`)
- [ ] `tests/test_integration.py` — stub file for multi-module flows
- [ ] `scripts/qa_script.sh` — new QA runner script

*Existing infrastructure covers most phase requirements. Wave 0 items are additions.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| qa_script.sh output formatting | QA readability | Visual check of table alignment | Run `bash scripts/qa_script.sh` and verify table columns align |
| --live API tests work | Live API validation | Requires real API keys | Run `bash scripts/qa_script.sh --live` with valid keys set |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 34s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
