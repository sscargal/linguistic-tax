---
phase: 7
slug: add-openai-to-the-supported-model-provider
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_api_client.py tests/test_config.py -x -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_api_client.py tests/test_config.py -x -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | N/A-01 | unit | `pytest tests/test_api_client.py::TestCallOpenAI -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | N/A-02 | unit | `pytest tests/test_api_client.py::TestCallModelRouting -x` | ✅ extend | ⬜ pending |
| 07-01-03 | 01 | 1 | N/A-03 | unit | `pytest tests/test_api_client.py::TestRetryAndRateLimiting -x` | ✅ extend | ⬜ pending |
| 07-01-04 | 01 | 1 | N/A-04 | unit | `pytest tests/test_api_client.py::TestAPIKeyValidation -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | N/A-05 | unit | `pytest tests/test_config.py -x` | ✅ extend | ⬜ pending |
| 07-01-06 | 01 | 1 | N/A-06 | unit | `pytest tests/test_api_client.py::TestTiming -x` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_client.py::TestCallOpenAI` — new test class for _call_openai streaming
- [ ] `tests/test_api_client.py` — extend TestCallModelRouting with gpt-* routing test
- [ ] `tests/test_api_client.py` — extend TestRetryAndRateLimiting with openai.RateLimitError test
- [ ] `tests/test_api_client.py` — extend TestAPIKeyValidation with OPENAI_API_KEY test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAI streaming TTFT/TTLT accuracy | N/A-06 | Requires real API call to verify timing accuracy | Run pilot with GPT-4o, verify TTFT < TTLT in results.db |
| End-to-end pilot with GPT-4o | N/A-all | Integration requires live API | Run `python -m src.pilot --model gpt-4o` and verify results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
