---
phase: quick-260326-w5r
plan: 01
subsystem: testing
tags: [pytest, warnings, config]
---

# Quick Task 260326-w5r: Fix pytest warnings

## Changes

1. **Registered `timeout` pytest mark** in `pyproject.toml` — eliminates 3 `PytestUnknownMarkWarning` warnings from `test_grade_results.py`
2. **Filtered `PerfectSeparationWarning`** from statsmodels — expected behavior in GLMM convergence tests, not actionable

## Result

659 passed, 0 warnings (previously 4 warnings).
