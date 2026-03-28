---
created: 2026-03-28T19:19:59.224Z
title: "Fix null rate_limit_delay defaulting to 0.5s"
area: general
files:
  - src/model_registry.py
  - experiment_config.json
---

## Problem

When `rate_limit_delay` is null in experiment_config.json, `get_delay()` returns 0.5s as the default. For gpt-5-mini and gpt-4o-mini, this means 0.5s sleep before EVERY API call. OpenAI rate limits for paid tiers are generous (500-10,000 RPM). At 123,000 calls for a full run, this wastes ~15 hours in pure sleep.

For a preproc item, there's 1.0s of pure sleep (0.5s preproc + 0.5s target) before any network I/O.

## Solution

1. Lower the default in `get_delay()` from 0.5s to 0.1s for unknown models
2. Set explicit `rate_limit_delay` values in experiment_config.json (0.1s for gpt-5-mini, 0.05s for gpt-4o-mini)
3. Consider making the default proportional to the model's known rate limit tier
