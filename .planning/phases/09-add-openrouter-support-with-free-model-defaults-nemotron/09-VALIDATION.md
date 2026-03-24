---
phase: 9
slug: add-openrouter-support-with-free-model-defaults-nemotron
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_api_client.py tests/test_config.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_api_client.py tests/test_config.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | OR-01 | unit | `pytest tests/test_api_client.py::TestCallOpenRouter -x` | No -- Wave 0 | ⬜ pending |
| 09-01-02 | 01 | 1 | OR-02 | unit | `pytest tests/test_api_client.py::TestCallModelRouting -x` | Partially | ⬜ pending |
| 09-01-03 | 01 | 1 | OR-03 | unit | `pytest tests/test_api_client.py::TestAPIKeyValidation -x` | Partially | ⬜ pending |
| 09-01-04 | 01 | 1 | OR-04 | unit | `pytest tests/test_config.py -x` | Partially | ⬜ pending |
| 09-01-05 | 01 | 1 | OR-05 | unit | `pytest tests/test_config.py -x` | No -- Wave 0 | ⬜ pending |
| 09-01-06 | 01 | 1 | OR-06 | unit | `pytest tests/test_api_client.py::TestCallOpenRouter -x` | No -- Wave 0 | ⬜ pending |
| 09-01-07 | 01 | 1 | OR-07 | unit | `pytest tests/test_api_client.py::TestRetryAndRateLimiting -x` | Partially | ⬜ pending |
| 09-01-08 | 01 | 1 | OR-08 | integration | `pytest tests/test_integration.py -x` | Partially | ⬜ pending |
| 09-01-09 | 01 | 1 | OR-09 | manual | `bash scripts/qa_script.sh --section config` | No -- must update | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_client.py::TestCallOpenRouter` — new test class for _call_openrouter streaming, prefix stripping, headers
- [ ] `tests/conftest.py::mock_openrouter_response` — factory fixture (reuse _make_openai_stream_chunks pattern since same SDK)
- [ ] `tests/test_config.py` — assertions for new MODELS entry, PRICE_TABLE entries, PREPROC_MODEL_MAP entry
- [ ] `tests/test_integration.py` — OpenRouter lifecycle test path

*Existing infrastructure covers most needs; Wave 0 adds OpenRouter-specific test stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| QA script validates OpenRouter entries | OR-09 | Shell script validation | Run `bash scripts/qa_script.sh --section config` and verify OpenRouter checks pass |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
