---
created: 2026-03-28T18:08:17.047Z
title: Investigate compress_only 100 calls vs 800 for other interventions
area: general
files:
  - src/run_experiment.py
  - data/experiment_matrix.json
---

## Problem

The `compress_only` intervention only had 100 API calls in the pilot while all other interventions had 800. Its 83% pass rate isn't directly comparable to others. It appears `compress_only` only runs on clean prompts, which means it's testing compression-without-noise rather than compression-as-noise-mitigation.

If this is by design (compress_only is only meaningful on clean text), the report should note the limited comparability. If it's a bug in the matrix generation, compress_only should run across all noise conditions like the other interventions.

## Solution

1. Check `experiment_matrix.json` generation to understand why compress_only is limited to clean prompts
2. Verify against the RDD whether compress_only should run across noise conditions
3. Either fix the matrix generation or add a note in the report about limited comparability
