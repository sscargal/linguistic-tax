---
phase: 09-add-openrouter-support-with-free-model-defaults-nemotron
plan: 01
subsystem: api
tags: [openrouter, openai-sdk, nemotron, free-models, provider-integration]

# Dependency graph
requires:
  - phase: 07-add-openai-to-supported-model-providers
    provides: OpenAI SDK integration pattern and _call_openai function
provides:
  - _call_openrouter function with OpenAI SDK reuse and base_url override
  - OpenRouter config entries in all config dicts (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS)
  - ExperimentConfig openrouter_model and openrouter_preproc_model fields
  - OPENROUTER_BASE_URL constant with env var override
affects: [09-02-tests, run-experiment, experiment-matrix]

# Tech tracking
tech-stack:
  added: []
  patterns: [openai-sdk-base-url-override, prefix-based-routing]

key-files:
  created: []
  modified:
    - src/config.py
    - src/api_client.py
    - .env.example
    - tests/test_config.py

key-decisions:
  - "Reuse OpenAI SDK with base_url override for OpenRouter (same pattern as direct OpenAI)"
  - "Strip openrouter/ prefix before sending to API but keep full prefix in APIResponse.model for consistency"
  - "0.5s rate limit delay for OpenRouter free models (conservative for free tier)"

patterns-established:
  - "OpenRouter provider via openrouter/ prefix routing in call_model"
  - "Free model pricing at 0.0 in PRICE_TABLE for zero-cost experiment runs"

requirements-completed: [OR-01, OR-02, OR-03, OR-04, OR-05, OR-06, OR-07]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 09 Plan 01: OpenRouter Provider Config and API Client Summary

**OpenRouter provider integration with free Nemotron model config, _call_openrouter via OpenAI SDK base_url override, and call_model routing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T17:12:53Z
- **Completed:** 2026-03-24T17:16:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added OpenRouter config entries across all 5 config structures (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig)
- Implemented _call_openrouter with OpenAI SDK reuse, base_url override, prefix stripping, project headers, and streaming TTFT/TTLT
- Extended call_model routing and API key validation for openrouter/ prefix models

## Task Commits

Each task was committed atomically:

1. **Task 1: Add OpenRouter config entries and ExperimentConfig fields** - `3f62d0f` (feat)
2. **Task 2: Add _call_openrouter and extend call_model routing** - `eb49eb7` (feat)

## Files Created/Modified
- `src/config.py` - OPENROUTER_BASE_URL, ExperimentConfig fields, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS entries
- `src/api_client.py` - _call_openrouter function, call_model routing, _validate_api_keys OpenRouter branch
- `.env.example` - OPENROUTER_API_KEY placeholder
- `tests/test_config.py` - Updated test_models_count from 3 to 4

## Decisions Made
- Reuse OpenAI SDK with base_url override for OpenRouter (follows exact same pattern as _call_openai)
- Keep full openrouter/ prefix in APIResponse.model for consistency with logging and cost computation
- 0.5s rate limit delay for free-tier models (conservative to avoid 429s)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_models_count assertion**
- **Found during:** Task 2 (test verification)
- **Issue:** test_config.py::TestConstants::test_models_count asserted len(MODELS) == 3, but we added a 4th model
- **Fix:** Updated assertion to len(MODELS) == 4
- **Files modified:** tests/test_config.py
- **Verification:** All 53 tests pass
- **Committed in:** eb49eb7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary test update for new model addition. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Users must set OPENROUTER_API_KEY env var before use (documented in .env.example).

## Next Phase Readiness
- OpenRouter provider ready for unit/integration testing in plan 09-02
- Config and API client fully functional for experiment runs with free Nemotron models

---
*Phase: 09-add-openrouter-support-with-free-model-defaults-nemotron*
*Completed: 2026-03-24*
