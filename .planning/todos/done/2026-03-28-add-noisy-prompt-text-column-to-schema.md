---
created: 2026-03-28T19:19:59.224Z
title: "Add noisy_prompt_text column to DB schema"
area: general
files:
  - src/db.py
  - src/run_experiment.py
---

## Problem

The noisy prompt text (after noise injection, before preprocessing) is overwritten by the intervention result and never stored. For preprocessing interventions, `prompt_text` stores the CLEANED version, making it impossible to:
- Verify noise injection worked correctly
- Diff what the preprocessor received vs produced
- Debug cases where preprocessing made things worse

The pipeline has 3 distinct prompt states: clean → noisy → processed. Only the last is stored.

## Solution

1. Add `noisy_prompt_text TEXT` column to `experiment_runs` schema in db.py
2. In `_process_item()`, capture the noisy text before calling `apply_intervention()` and store it
3. Also rename `prompt_text` to `model_input_text` (or add a comment clarifying it stores post-intervention text)
