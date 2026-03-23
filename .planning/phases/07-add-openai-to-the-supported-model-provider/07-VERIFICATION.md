---
phase: 07-add-openai-to-the-supported-model-provider
verified: 2026-03-23T23:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 7: Add OpenAI to the Supported Model Provider — Verification Report

**Phase Goal:** GPT-4o is a fully integrated third target model in the experiment pipeline — API client streams with TTFT/TTLT tracking, config has all pricing/routing entries, pilot and figures handle 3 models, and the full test suite passes.
**Verified:** 2026-03-23
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `call_model('gpt-4o-2024-11-20', ...)` routes to `_call_openai` and returns an `APIResponse` | VERIFIED | `call_model` dispatches via `model.startswith("gpt")` at api_client.py:284; `test_routes_gpt_to_openai` passes |
| 2 | OpenAI streaming captures TTFT, TTLT, and token counts via `stream_options` | VERIFIED | `_call_openai` uses `stream_options={"include_usage": True}`; reads `usage.prompt_tokens`/`usage.completion_tokens` from final chunk; `TestCallOpenAI` confirms |
| 3 | Rate limit errors from OpenAI trigger retry with exponential backoff | VERIFIED | `except openai.RateLimitError` at api_client.py:301 doubles `_rate_delays` and sleeps; `test_retries_on_openai_rate_limit` and `test_openai_429_doubles_rate_delay` pass |
| 4 | Missing `OPENAI_API_KEY` raises `EnvironmentError` before any API call | VERIFIED | `_validate_api_keys` branch at api_client.py:54-56; `test_missing_openai_key_raises` passes |
| 5 | GPT-4o and GPT-4o-mini appear in `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP`, and `RATE_LIMIT_DELAYS` | VERIFIED | All four dicts confirmed in config.py; `TestConstants` assertions for each pass |
| 6 | Pilot validation accepts GPT-4o results without flagging them as unknown model | VERIFIED | `_VALID_MODELS = set(MODELS)` at pilot.py:218; `TestValidModels` class with 4 tests passes |
| 7 | Publication figures render correctly with 3 model panels instead of 2 | VERIFIED | Both `plot_accuracy_curves` and `plot_quadrant_scatter` use `figsize=(3.5 * max(n_models, 2), 3.5)`; no hardcoded `(7, 3.5)` found |
| 8 | Full test suite passes with OpenAI integrated | VERIFIED | `pytest tests/ -q` exits 0: 333 passed, 1 warning |

**Score:** 8/8 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/config.py` | OpenAI model entries in all config dicts | VERIFIED | `gpt-4o-2024-11-20` in MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS; `openai_model` in ExperimentConfig |
| `src/api_client.py` | `_call_openai` function with streaming | VERIFIED | Full implementation at lines 179-235; `import openai` at line 13 |
| `pyproject.toml` | openai dependency | VERIFIED | `"openai>=2.0.0"` present at line 9 |
| `.env.example` | `OPENAI_API_KEY` placeholder | VERIFIED | `OPENAI_API_KEY=sk-xxxxx` present |
| `tests/test_api_client.py` | OpenAI routing, streaming, retry, and key validation tests | VERIFIED | `TestCallOpenAI` class (5 tests), `test_routes_gpt_to_openai`, `test_missing_openai_key_raises`, `test_retries_on_openai_rate_limit`, `test_openai_429_doubles_rate_delay` all present and passing |
| `tests/test_config.py` | Tests verifying 3 models in MODELS tuple | VERIFIED | `test_models_count` asserts `len(MODELS) == 3`; `test_models_contents` asserts all three model IDs |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/pilot.py` | Updated `_VALID_MODELS` including GPT-4o | VERIFIED | `_VALID_MODELS = set(MODELS)` at line 218; no hardcoded set |
| `src/generate_figures.py` | Wider figure layout for 3 models | VERIFIED | `figsize=(3.5 * max(n_models, 2), 3.5)` in both `plot_accuracy_curves` (line 167) and `plot_quadrant_scatter` (line 265) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/api_client.py` | openai SDK | `import openai; openai.OpenAI()` | VERIFIED | `import openai` at line 13; `client = openai.OpenAI()` at line 198; `client.chat.completions.create(stream=True)` at line 208 |
| `src/api_client.py call_model()` | `src/api_client.py _call_openai()` | `model.startswith('gpt')` routing | VERIFIED | `elif model.startswith("gpt"):` at line 284 dispatches to `_call_openai` |
| `src/config.py PREPROC_MODEL_MAP` | `gpt-4o-mini-2024-07-18` | dict lookup | VERIFIED | `"gpt-4o-2024-11-20": "gpt-4o-mini-2024-07-18"` at config.py:115 |
| `src/pilot.py _VALID_MODELS` | `src/config.py MODELS` | `set(MODELS)` derivation | VERIFIED | `_VALID_MODELS = set(MODELS)` — dynamic, no hardcoded set |

---

## Requirements Coverage

The PLAN frontmatter declares requirement IDs OAPI-01 through OAPI-06. These IDs are **not present in `.planning/REQUIREMENTS.md`** — the REQUIREMENTS.md traceability table ends at FIG-04 (Phase 6) and Phase 7 is entirely absent. The IDs were created by the planner for this phase but were never registered in the requirements document.

This is a documentation gap in REQUIREMENTS.md, not an implementation gap. The implementation satisfies all behaviors the OAPI-* IDs were intended to represent:

| Requirement ID | Declared in PLAN | Present in REQUIREMENTS.md | Implementation Evidence |
|----------------|-----------------|---------------------------|------------------------|
| OAPI-01 | 07-01, 07-02 | MISSING from REQUIREMENTS.md | GPT-4o in config, API client, pilot, and figures — all verified |
| OAPI-02 | 07-01 | MISSING from REQUIREMENTS.md | `_call_openai` streaming with TTFT/TTLT tracking — verified |
| OAPI-03 | 07-01 | MISSING from REQUIREMENTS.md | `openai.RateLimitError` retry logic — verified |
| OAPI-04 | 07-01 | MISSING from REQUIREMENTS.md | `OPENAI_API_KEY` validation — verified |
| OAPI-05 | 07-01, 07-02 | MISSING from REQUIREMENTS.md | All config dicts updated + downstream modules — verified |
| OAPI-06 | 07-01 | MISSING from REQUIREMENTS.md | Full test suite passes — verified |

**Note:** REQUIREMENTS.md traceability table should be updated to include Phase 7 and OAPI-01 through OAPI-06, but this does not affect the correctness of the implementation.

---

## Anti-Patterns Found

No anti-patterns detected in phase 7 files.

| File | Pattern | Severity | Finding |
|------|---------|----------|---------|
| `src/api_client.py` | TODO/placeholder | — | None found |
| `src/config.py` | TODO/placeholder | — | None found |
| `src/pilot.py` | hardcoded model set | — | None — uses `set(MODELS)` |
| `src/generate_figures.py` | hardcoded figsize | — | None — uses `3.5 * max(n_models, 2)` |

---

## Human Verification Required

None. All behavioral claims are fully covered by the unit test suite. The streaming TTFT/TTLT logic uses mocked `time.monotonic()` in `TestTiming` to assert exact timing values. No real API calls are needed for verification.

---

## Commit Verification

All commits documented in SUMMARY.md are confirmed to exist in git history:

| Commit | Message | Plan |
|--------|---------|------|
| `cd9d03f` | test(07-01): add failing tests for OpenAI integration | 07-01 RED |
| `9213027` | feat(07-01): implement OpenAI GPT-4o as third model provider | 07-01 GREEN |
| `5cf1f22` | feat(07-02): derive _VALID_MODELS from config.MODELS for auto-propagation | 07-02 Task 1 |
| `ce9f047` | feat(07-02): widen figure layouts for dynamic model count | 07-02 Task 2 |

---

## Summary

Phase 7 goal is fully achieved. GPT-4o is a complete, tested, third target model:

- The API client routes `gpt-*` models to `_call_openai`, which streams with TTFT/TTLT capture and token counting via `stream_options={"include_usage": True}`.
- All six config structures (ExperimentConfig, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, and the implicit test expectations) contain GPT-4o and GPT-4o-mini entries.
- Rate limiting and retry logic handles `openai.RateLimitError` with the same exponential backoff pattern used for Anthropic and Google.
- Pilot validation derives `_VALID_MODELS` dynamically from `config.MODELS`, so GPT-4o is automatically accepted.
- Figure layouts scale to `3.5 * max(n_models, 2)` inches wide, accommodating any number of models.
- 333 tests pass across the full suite with zero failures.

The only documentation gap found is that OAPI-01 through OAPI-06 are not registered in `.planning/REQUIREMENTS.md`. The implementation is correct; the requirements document needs updating.

---

_Verified: 2026-03-23_
_Verifier: Claude (gsd-verifier)_
