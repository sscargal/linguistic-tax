---
created: 2026-03-27T04:30:00.000Z
title: "Investigate pre-processor performance anomaly (slow TTFT, high output)"
area: general
files:
  - src/prompt_compressor.py
  - src/api_client.py
---

## Problem

Pilot data shows pre-processor (gpt-5-nano) has:
- TTFT of 3633ms (vs target's 521ms) — 7x slower to first token
- TTLT of 3680ms (almost all time is waiting for first token)
- 869K output tokens from 172K input (5x ratio)

For a nano model doing simple text correction, this is unexpectedly slow and verbose. Possible causes:
- gpt-5-nano may be a reasoning model that generates internal chain-of-thought
- Rate limiting or cold start penalties on the nano tier
- The sanitization prompt is too open-ended, causing the model to overthink
- temperature parameter issue causing retries (each retry adds latency)

## Solution

1. **Time a direct API call** to gpt-5-nano with a simple sanitization prompt — isolate whether the latency is the model or the pipeline
2. **Check if temperature=0.0 is causing retries** for gpt-5-nano (same issue as gpt-5.1)
3. **Compare with gpt-4o-mini** as preproc — is this a gpt-5-nano-specific issue?
4. **Consider using a non-reasoning model** for preproc if gpt-5-nano does chain-of-thought
