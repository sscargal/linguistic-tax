---
created: 2026-03-28T19:19:59.224Z
title: "Remove or populate dead schema columns (generation_ms, cot_trace)"
area: general
files:
  - src/db.py
  - src/run_experiment.py
---

## Problem

Two columns are defined in the schema but never populated:
- `generation_ms REAL` — always NULL, could be computed as `ttlt_ms - ttft_ms`
- `cot_trace TEXT` — always NULL, no model returns this data currently

Also `optimized_tokens` is misleadingly named and redundant with `preproc_output_tokens`.

## Solution

- Populate `generation_ms = ttlt_ms - ttft_ms` in `_process_item()`
- Remove `cot_trace` from schema (or populate if models support it)
- Rename or remove `optimized_tokens`
