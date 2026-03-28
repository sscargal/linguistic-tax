---
created: 2026-03-28T19:04:22.157Z
title: Self-correct inherently harmful for code benchmarks
area: general
files:
  - src/run_experiment.py
---

## Problem

Self-correct intervention drops HumanEval from 89% to 34% (clean prompts). Even with the code extraction fix, the intervention is inherently harmful because:
- 99% of outputs start with "Corrected prompt:" preamble
- 57% produce multiple function variants
- 35% more output tokens than raw (839 vs 621)
- On clean prompts (no errors to correct), it still drops -24%

However, self-correct HELPS GSM8K (+4.2%) — it seems beneficial for math reasoning.

This is not a bug — it's experimental data showing self-correct hurts code generation. But the self-correct prompt may be suboptimal and worth investigating.

## Solution

This is primarily an analysis finding, not necessarily a code fix. Options:
1. Accept as experimental result — self-correct helps math, hurts code
2. Consider benchmark-specific self-correct prompts (but that changes the experimental design)
3. Document in the paper as a key finding about intervention asymmetry across task types
4. Investigate whether the prompt wording ("First, correct any errors you find, then execute") could be improved to avoid the multi-variant problem
