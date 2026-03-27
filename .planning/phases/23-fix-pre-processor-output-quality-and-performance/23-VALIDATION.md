---
phase: 23
slug: fix-pre-processor-output-quality-and-performance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `pytest tests/test_prompt_compressor.py tests/test_run_experiment.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_prompt_compressor.py tests/test_run_experiment.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | TODO-preproc-sanitize-accuracy | unit | `pytest tests/test_prompt_compressor.py -x -q` | ✅ | ⬜ pending |
| 23-01-02 | 01 | 1 | TODO-preproc-sanitize-accuracy | unit | `pytest tests/test_run_experiment.py -x -q` | ✅ | ⬜ pending |
| 23-02-01 | 02 | 2 | TODO-preproc-performance-anomaly | unit | `pytest tests/test_prompt_compressor.py -x -q` | ✅ | ⬜ pending |
| 23-02-02 | 02 | 2 | TODO-preproc-performance-anomaly | integration | `pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Test files already exist:
- `tests/test_prompt_compressor.py` — 26+ existing tests
- `tests/test_run_experiment.py` — 17+ existing tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Token-ratio warning in logs | TODO-preproc-performance-anomaly | Requires live API call with reasoning model | Run pilot with gpt-5-nano preproc, check log output for warning |
| Accuracy improvement on type_a | TODO-preproc-sanitize-accuracy | Requires live pilot re-run | Compare pre-fix vs post-fix pilot accuracy on type_a noise |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
