---
phase: quick-260327-3tc
plan: 01
subsystem: execution
tags: [openrouter, rate-limits, dry-run, ux]
---

# Quick Task 260327-3tc: Add OpenRouter rate limit check to pre-execution summary

## Changes

1. **Added `check_openrouter_limits()`** to `src/model_discovery.py` — queries `/api/v1/auth/key` for usage stats and tier info
2. **Added `RateLimitInfo` dataclass** with limit, remaining, reset time, and human-readable time-until-reset
3. **Integrated into `format_summary()`** — checks OpenRouter limits when OpenRouter models are configured, warns if quota insufficient

## How it works

- Free tier: 50 free-model requests/day (detected via `is_free_tier` + `usage_daily`)
- Paid tier: uses explicit `limit` and `limit_remaining` from API
- Compares remaining quota against total API calls (target + preproc)
- Shows WARNING with options when run won't complete, or "sufficient" confirmation when OK

## Result

660 tests pass. Live tested against OpenRouter API — correctly detects 50/day limit and warns when 5,800 calls required.
