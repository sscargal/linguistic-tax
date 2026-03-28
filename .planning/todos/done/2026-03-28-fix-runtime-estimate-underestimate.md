---
created: 2026-03-28T18:08:17.047Z
title: Fix runtime estimate underestimate
area: general
files:
  - src/execution_summary.py
---

## Problem

Runtime estimate was 7h 15m but actual was 9h 43m (1.34x over). The estimator uses a fixed per-call time assumption that doesn't account for actual model latency. Pilot data shows average target TTLT of 7718ms and average of 8.53s/item.

## Solution

Review the per-call time constant in `execution_summary.py`. May need to:
- Increase the base time-per-call estimate
- Factor in model-specific latency characteristics
- Use TTLT data from pilot runs to improve the estimate
