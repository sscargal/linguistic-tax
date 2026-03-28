---
created: 2026-03-28T19:19:59.224Z
title: "Add provider-level parallelism for multi-model runs"
area: general
files:
  - src/run_experiment.py
---

## Problem

The execution loop is fully sequential. When multiple models from different providers are configured, all capacity from idle providers is wasted while one model's items run. With 2 providers, this halves throughput.

## Solution

Use `concurrent.futures.ThreadPoolExecutor` with one worker per model/provider. Partition `pending` items by model, run each partition in its own thread. SQLite WAL mode supports concurrent writes. Each thread maintains its own rate limiter.

Estimated speedup: proportional to number of providers (2 providers → ~2x).
