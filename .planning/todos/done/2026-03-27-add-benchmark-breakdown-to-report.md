---
created: 2026-03-27T04:30:00.000Z
title: "Add benchmark breakdown to propt report"
area: general
files:
  - src/execution_summary.py
  - src/cli.py
---

## Problem

The pilot shows a flat ~59.6% pass rate across all conditions, but this aggregates HumanEval, MBPP, and GSM8K. One benchmark may be pulling the average down (e.g., code execution crashes for HumanEval/MBPP vs math extraction for GSM8K). Need per-benchmark breakdown to diagnose.

## Solution

1. **Add `--benchmark` flag to `propt report`** — show pass rate, cost, and timing broken down by benchmark_source (humaneval, mbpp, gsm8k)
2. **Add benchmark x noise cross-tabulation** — the key analysis view: does noise degrade humaneval differently than gsm8k?
3. **Show per-benchmark baseline** (clean + raw) to establish each benchmark's natural pass rate before noise effects
