---
phase: quick-260326-w5r
plan: 01
subsystem: testing
tags: [pytest, warnings, config, mocking]
---

# Quick Task 260326-w5r: Fix pytest warnings and test failures

## Changes

1. **Registered `timeout` pytest mark** in `pyproject.toml` — eliminates 3 `PytestUnknownMarkWarning` warnings from `test_grade_results.py`
2. **Filtered `PerfectSeparationWarning`** from statsmodels — expected behavior in GLMM convergence tests, not actionable
3. **Mocked `discover_all_models` in list-models tests** — `test_list_models_all_entries` and `test_list_models_free_indicator` were calling live APIs, which fails when `OPENROUTER_API_KEY` is set but live model IDs don't match registry IDs. Now uses deterministic fallback.

## Result

659 passed, 0 failures, 0 warnings.
