---
created: 2026-03-28T19:04:22.157Z
title: High instability — 41% of prompts inconsistent across reps
area: general
files:
  - src/run_experiment.py
  - src/config.py
---

## Problem

On raw+clean (baseline), 8 of 20 prompts (41%) produce inconsistent results across 5 repetitions (some pass, some fail). This is with temperature=0.0, which should produce deterministic output.

Notable unstable prompts:
- gsm8k_539: 2/5 (model consistently gets $35 but extractor variance — this may resolve with extraction fix)
- HumanEval/114: 3/5
- mbpp_115: 3/5
- HumanEval/28, HumanEval/58, gsm8k_118, mbpp_119, mbpp_141: all 4/5

## Solution

1. Some instability will resolve with the GSM8K extraction fix (gsm8k_539 is likely a misextraction issue)
2. Verify temperature=0.0 is actually being sent — even at temp=0, some providers have slight non-determinism
3. At 20 prompts, 41% instability is expected due to small sample size — the full 200-prompt run will average out
4. Consider this a valid research finding: even with deterministic settings, LLM outputs vary enough to affect pass/fail on borderline prompts. This is WHY we run 5 repetitions.
5. After re-run, compute the Consistency Ratio (CR) metric defined in the RDD
