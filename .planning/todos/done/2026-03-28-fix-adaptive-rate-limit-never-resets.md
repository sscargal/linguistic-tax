---
created: 2026-03-28T19:19:59.224Z
title: "Fix adaptive rate limit — never resets after 429s"
area: general
files:
  - src/api_client.py
---

## Problem

On 429 rate limit errors, `_rate_delays[model]` is doubled (line 433 of api_client.py) but never resets. A few early 429s during a multi-hour run permanently inflate delays to 1.6s, 3.2s, or higher. Over thousands of calls this adds hours of unnecessary sleep.

## Solution

Add a decay mechanism: after N successful consecutive calls (e.g., 50), halve the delay back toward the baseline. Or reset to baseline after a configurable cooldown period.
