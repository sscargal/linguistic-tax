---
created: 2026-03-28T19:19:59.224Z
title: "Add preproc_failed flag to DB schema"
area: general
files:
  - src/db.py
  - src/run_experiment.py
---

## Problem

When the preprocessor falls back to original text (bloated output, empty output), `metadata["preproc_failed"] = True` is set in prompt_compressor.py. But `preproc_failed` is not a column in the schema, so it's silently dropped by `insert_run()`. Cannot query which runs had preprocessor fallbacks.

## Solution

Add `preproc_failed INTEGER DEFAULT 0` column to `experiment_runs` schema. Populate from `preproc_meta.get("preproc_failed", False)` in `_process_item()`.
