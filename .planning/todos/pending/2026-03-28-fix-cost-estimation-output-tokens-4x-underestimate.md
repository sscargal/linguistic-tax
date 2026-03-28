---
created: 2026-03-28T18:08:17.047Z
title: Fix cost estimation output tokens 4x underestimate
area: general
files:
  - src/execution_summary.py
---

## Problem

The pre-execution cost estimate was $1.32 but actual cost was $5.49 (4.2x over). The root cause is output token estimation: estimated 677,980 out vs actual 2,689,267 out (target alone). The estimator assumes far fewer output tokens per call than gpt-5-mini actually generates.

Input tokens were reasonably close (306K estimated vs 394K actual = 1.3x), so the issue is specifically in the output token estimation constants.

## Solution

Review `execution_summary.py`'s `estimate_cost()` function and the per-benchmark output token assumptions. May need to:
- Increase the assumed output tokens per call (especially for code generation benchmarks where models produce verbose output)
- Consider making output token estimates model-aware or benchmark-aware
- Use actual data from this pilot to calibrate the estimates
