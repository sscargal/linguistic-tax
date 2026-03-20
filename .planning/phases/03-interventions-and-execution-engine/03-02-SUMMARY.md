---
phase: 03-interventions-and-execution-engine
plan: 02
subsystem: api
tags: [anthropic, google-genai, streaming, ttft, ttlt, rate-limiting, retry]

# Dependency graph
requires:
  - phase: 03-interventions-and-execution-engine plan 01
    provides: RATE_LIMIT_DELAYS, PRICE_TABLE, PREPROC_MODEL_MAP in config.py
provides:
  - "Unified call_model() function routing to Anthropic/Google SDKs"
  - "APIResponse frozen dataclass with text, tokens, timing, model"
  - "Streaming TTFT/TTLT measurement via time.monotonic()"
  - "Exponential backoff retry (1s, 4s, 16s) on rate limit errors"
  - "Adaptive rate limiting with 429-triggered delay doubling"
  - "API key validation with clear EnvironmentError messages"
affects: [prompt_compressor, run_experiment, pilot-execution]

# Tech tracking
tech-stack:
  added: [google-genai]
  patterns: [unified-api-wrapper, streaming-timing, adaptive-rate-limiting]

key-files:
  created: [src/api_client.py]
  modified: [pyproject.toml]

key-decisions:
  - "Used google.genai.errors.ClientError with code==429 for Google rate limit detection"
  - "Separate exception handlers for Anthropic RateLimitError and Google ClientError to avoid broad catch"

patterns-established:
  - "Unified API wrapper: all LLM calls go through call_model() returning APIResponse"
  - "Streaming-first: never use non-streaming API calls, always measure TTFT/TTLT"
  - "Adaptive rate limiting: _rate_delays mutable dict doubles on 429, shared across calls"

requirements-completed: [EXEC-01, EXEC-02, EXEC-05]

# Metrics
duration: 7min
completed: 2026-03-20
---

# Phase 3 Plan 2: API Client Summary

**Unified call_model() wrapping Anthropic and Google GenAI SDKs with streaming TTFT/TTLT, exponential backoff retry, and adaptive rate limiting**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-20T21:45:49Z
- **Completed:** 2026-03-20T21:52:49Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Unified API client dispatching to Anthropic or Google based on model name prefix
- Streaming TTFT/TTLT measurement using time.monotonic() for both providers
- Retry with exponential backoff (1s, 4s, 16s) and adaptive rate delay doubling on 429
- pyproject.toml updated from deprecated google-generativeai to google-genai
- 19 tests all passing with fully mocked SDK clients

## Task Commits

Each task was committed atomically:

1. **Task 1: api_client.py with streaming, timing, rate limiting, retry + tests** - `9a019fc` (feat)

_Note: TDD RED commit was skipped because tests were already committed in plan 03-01._

## Files Created/Modified
- `src/api_client.py` - Unified API client with call_model(), _call_anthropic(), _call_google(), retry, rate limiting
- `pyproject.toml` - Replaced google-generativeai with google-genai dependency
- `tests/test_api_client.py` - 19 tests covering all behaviors with mocked SDKs (pre-existing from plan 03-01)

## Decisions Made
- Used `google.genai.errors.ClientError` with `code == 429` check for Google rate limit detection, keeping exception handling specific rather than using broad catch
- Separate try/except blocks for Anthropic and Google errors to avoid accidentally catching non-rate-limit errors

## Deviations from Plan

None - plan executed exactly as written. RATE_LIMIT_DELAYS and other config constants were already present from plan 03-01.

## Issues Encountered
- google-genai package was not installed in the project venv (only in system Python 3.10). Installed it in the .venv before implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- api_client.py ready for use by prompt_compressor.py (pre-processor calls) and run_experiment.py (main experiment calls)
- All downstream modules can import call_model and APIResponse from src.api_client

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 03-interventions-and-execution-engine*
*Completed: 2026-03-20*
