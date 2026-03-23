---
phase: 07-add-openai-to-the-supported-model-provider
plan: 01
subsystem: api
tags: [openai, gpt-4o, streaming, api-client]

# Dependency graph
requires:
  - phase: 03-api-client-and-prompt-processing
    provides: api_client.py with call_model, _call_anthropic, _call_google patterns
provides:
  - _call_openai function with streaming TTFT/TTLT measurement
  - GPT-4o and GPT-4o-mini config entries in all dicts
  - OpenAI rate limit handling with exponential backoff
  - openai SDK dependency
affects: [08-write-unit-tests, 09-add-openrouter-support]

# Tech tracking
tech-stack:
  added: [openai>=2.0.0]
  patterns: [openai streaming with stream_options include_usage, gpt prefix routing]

key-files:
  created: [.env.example]
  modified: [src/config.py, src/api_client.py, pyproject.toml, tests/test_api_client.py, tests/test_config.py]

key-decisions:
  - "Used openai SDK stream_options={'include_usage': True} for token count extraction from final usage chunk"
  - "Routing via model.startswith('gpt') consistent with existing claude/gemini prefix patterns"

patterns-established:
  - "OpenAI streaming: iterate chunks, check chunk.usage for final usage data, check chunk.choices for content"
  - "Three-provider routing: claude -> anthropic, gemini -> google, gpt -> openai"

requirements-completed: [OAPI-01, OAPI-02, OAPI-03, OAPI-04, OAPI-05, OAPI-06]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 7 Plan 1: Add OpenAI Config and API Client Summary

**OpenAI GPT-4o integrated as third model provider with streaming, rate limiting, and comprehensive tests via TDD**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T22:56:43Z
- **Completed:** 2026-03-23T23:01:13Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments
- GPT-4o-2024-11-20 added to MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS
- _call_openai function with streaming, TTFT/TTLT measurement, and usage extraction
- call_model routes gpt-* models to _call_openai with key validation and retry logic
- 53 tests pass including 13 new OpenAI-specific tests

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for OpenAI integration** - `cd9d03f` (test)
2. **Task 1 GREEN: Implement OpenAI provider** - `9213027` (feat)

_TDD task with RED/GREEN commits._

## Files Created/Modified
- `src/config.py` - Added GPT-4o entries to all config dicts and ExperimentConfig.openai_model
- `src/api_client.py` - Added _call_openai with streaming, GPT routing, OpenAI rate limit handler
- `pyproject.toml` - Added openai>=2.0.0 dependency
- `.env.example` - Added OPENAI_API_KEY placeholder
- `tests/test_api_client.py` - Added TestCallOpenAI class, GPT routing/retry/key validation tests
- `tests/test_config.py` - Added OpenAI config entry assertions, updated MODELS count to 3

## Decisions Made
- Used openai SDK stream_options={"include_usage": True} for token counts from final chunk
- Routing via model.startswith("gpt") consistent with existing prefix-based patterns
- Rate limit default 0.2s for GPT-4o, 0.1s for GPT-4o-mini (matching Anthropic tier structure)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- openai package needed to be installed into project venv specifically (not system Python) - resolved immediately

## User Setup Required

Users must set `OPENAI_API_KEY` environment variable to use GPT-4o models. See `.env.example`.

## Next Phase Readiness
- OpenAI fully integrated, ready for experiment matrix inclusion
- Plan 07-02 can proceed with experiment_matrix.json updates if needed

---
*Phase: 07-add-openai-to-the-supported-model-provider*
*Completed: 2026-03-23*
