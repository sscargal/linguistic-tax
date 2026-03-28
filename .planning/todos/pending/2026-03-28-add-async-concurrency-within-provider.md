---
created: 2026-03-28T19:19:59.224Z
title: "Add async concurrency within a single provider"
area: general
files:
  - src/run_experiment.py
  - src/api_client.py
---

## Problem

Even within a single provider, the pipeline makes one API call at a time. OpenAI tier 3+ allows 500+ RPM. At 6s per call, you could overlap 5-10 concurrent requests while staying within limits. This is the highest-impact single optimization but the most complex.

## Solution

Use `asyncio` with async client variants (Anthropic, OpenAI, and Google all offer async SDKs). Implement a semaphore-based concurrency limiter per provider. Requires refactoring `_process_item()` to be async and updating the main loop to use `asyncio.gather()` with bounded concurrency.

Estimated speedup: 3-5x within a single provider.
