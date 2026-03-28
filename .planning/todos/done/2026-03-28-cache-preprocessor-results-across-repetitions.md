---
created: 2026-03-28T19:19:59.224Z
title: "Cache preprocessor results across repetitions"
area: general
files:
  - src/run_experiment.py
  - src/prompt_compressor.py
---

## Problem

The same prompt with the same noise is preprocessed identically across all 5 repetitions and across interventions sharing the same preproc step. Of ~41,000 preproc calls at full scale, only ~8,200 are unique — meaning ~32,800 redundant API calls (~55 hours wasted at 6s/call).

Preprocessing is deterministic (same input → same output from the cheap model at temp=0), so caching is safe.

## Solution

Add an in-memory cache keyed by `(prompt_id, noise_type, preproc_model, intervention)` in the execution loop. On first occurrence, call the preprocessor and cache the result (processed_text + metadata). On subsequent hits, reuse the cached result.

Could also be implemented as a disk cache (SQLite table) for cross-session reuse, but in-memory is simpler and sufficient for a single run.

Estimated savings: ~32,800 API calls eliminated → ~55 hours saved on full run.
