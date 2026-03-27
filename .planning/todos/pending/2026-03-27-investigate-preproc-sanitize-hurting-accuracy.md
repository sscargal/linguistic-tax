---
created: 2026-03-27T06:00:00.000Z
title: "Investigate why pre_proc_sanitize hurts accuracy vs raw"
area: general
files:
  - src/prompt_compressor.py
  - results/results.db
---

## Problem

Pilot data shows pre_proc_sanitize (73.6%) performing worse than raw (74.4%). The pre-processor should help, not hurt. Combined with the pre-processor output anomaly (869K output from 172K input, 5x ratio), the pre-processor may be:

1. Mangling prompts instead of cleaning them (adding explanations, changing meaning)
2. Triggering the fallback path (output > 1.5x input) and silently using the noisy original
3. Stripping important context while "cleaning"

Related to existing todos:
- "Inspect pre-processor output and fix chatty responses"
- "Investigate pre-processor performance anomaly"

## Solution

1. Query runs where intervention=pre_proc_sanitize AND pass_fail=0, compare the prompt_text against the original clean prompt to see what changed
2. Count how many runs hit the fallback path (preproc_failed=True in metadata — though this may not be stored)
3. Compare pre_proc_sanitize pass rate by benchmark — is it hurting all benchmarks equally or just MBPP?
4. Inspect a few cases where raw=PASS but pre_proc_sanitize=FAIL for the same prompt+noise combo
