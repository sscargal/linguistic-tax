---
phase: 03-interventions-and-execution-engine
verified: 2026-03-20T22:13:53Z
status: passed
score: 23/23 must-haves verified
re_verification: false
---

# Phase 03: Interventions and Execution Engine Verification Report

**Phase Goal:** Researcher can execute any experiment matrix work item end-to-end -- the intervention router dispatches to the correct strategy, the API client calls Claude or Gemini with full instrumentation, and the engine manages resumability and rate limiting
**Verified:** 2026-03-20T22:13:53Z
**Status:** PASSED
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

All truths derived from the three plan `must_haves` blocks (Plans 01, 02, 03).

#### Plan 01 Truths (INTV-01 through INTV-04)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `repeat_prompt()` doubles input text with two-newline separator | VERIFIED | `src/prompt_repeater.py:26` — `return f"{text}\n\n{text}"` |
| 2 | `sanitize()` calls a cheap model and returns corrected text with metadata | VERIFIED | `src/prompt_compressor.py:81-114` — calls `call_fn` with preproc_model, returns `(result, metadata)` with all 5 preproc fields |
| 3 | `sanitize_and_compress()` calls a cheap model and returns optimized text with metadata | VERIFIED | `src/prompt_compressor.py:117-150` — same pattern with compress instruction |
| 4 | Pre-processor falls back to raw prompt if output is empty or >1.5x original length | VERIFIED | `src/prompt_compressor.py:182` — `if not result or len(result) > len(original_text) * 1.5:` sets `preproc_failed=True` |
| 5 | Self-correct prefix text matches RDD Section 6 wording exactly | VERIFIED | `src/prompt_compressor.py:25-29` — "Note: my prompt below may contain spelling or grammar errors. First, correct any errors you find, then execute the corrected version of my request." |
| 6 | Config contains price table for all 4 models with correct USD per 1M token rates | VERIFIED | `src/config.py:95-100` — Sonnet $3.00/$15.00, Haiku $1.00/$5.00, Pro $1.25/$5.00, Flash $0.10/$0.40 |
| 7 | Config contains max_tokens settings for HumanEval/MBPP (2048) and GSM8K (1024) | VERIFIED | `src/config.py:102-106` — humaneval=2048, mbpp=2048, gsm8k=1024 |
| 8 | Config contains vendor-matched pre-processor model mappings | VERIFIED | `src/config.py:108-111` — claude->haiku, gemini->flash |

#### Plan 02 Truths (EXEC-01, EXEC-02, EXEC-05)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 9 | `call_model()` sends requests to Claude Sonnet via Anthropic SDK streaming and returns unified APIResponse | VERIFIED | `src/api_client.py:100` — `with client.messages.stream(**kwargs) as stream:` |
| 10 | `call_model()` sends requests to Gemini Pro via Google GenAI SDK streaming and returns unified APIResponse | VERIFIED | `src/api_client.py:151` — `for chunk in client.models.generate_content_stream(...)` |
| 11 | Every API call measures TTFT and TTLT in milliseconds | VERIFIED | `src/api_client.py:86,103,106,139,157,162` — `time.monotonic()` at start, first chunk, and end |
| 12 | APIResponse contains text, input_tokens, output_tokens, ttft_ms, ttlt_ms, model | VERIFIED | `src/api_client.py:22-31` — `@dataclass(frozen=True)` with all 6 fields |
| 13 | Rate limiting applies a fixed delay between calls with 429-triggered delay doubling | VERIFIED | `src/api_client.py:55-63,224,236` — `_apply_rate_limit()` sleeps; `_rate_delays[model] *= 2` on 429 |
| 14 | pyproject.toml uses google-genai instead of google-generativeai | VERIFIED | `pyproject.toml` contains `"google-genai>=1.0.0"`, no `google-generativeai` |

#### Plan 03 Truths (INTV-05, EXEC-03, EXEC-04)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 15 | Intervention router dispatches to all 5 strategies | VERIFIED | `src/run_experiment.py:92-104` — `match intervention:` with 5 named cases |
| 16 | Engine loads experiment matrix and skips already-completed run_ids on startup | VERIFIED | `src/run_experiment.py:426,434` — `query_runs(conn, status="completed")` builds skip set |
| 17 | Engine processes all 5 repetitions per condition | VERIFIED | Matrix items contain `repetition_num`; `make_run_id()` includes it; engine iterates all pending |
| 18 | Stopping and restarting resumes from where it left off | VERIFIED | Completed run_ids excluded from pending list; deterministic `make_run_id` matches across restarts |
| 19 | Each completed item written to SQLite with status='completed' | VERIFIED | `src/run_experiment.py:318` — `"status": "completed"` in `run_data` passed to `insert_run()` |
| 20 | Failed items marked status='failed' with fail_reason after 4 attempts | VERIFIED | `src/run_experiment.py:353` — `"status": "failed"` in error handler; api_client re-raises after 4 attempts |
| 21 | Inline grading grades each response immediately after receiving it | VERIFIED | `src/run_experiment.py:286` — `grade_result = grade_run(response.text, prompt_record)` before `insert_run` |
| 22 | `--retry-failed` flag reprocesses failed items | VERIFIED | `src/run_experiment.py:437-450` — clears old failed rows, re-adds items |
| 23 | `--dry-run`, `--model`, `--limit` flags present and functional | VERIFIED | `src/run_experiment.py:493-530` — all four flags in argparse; engine branches on each |

**Score:** 23/23 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/config.py` | PRICE_TABLE, max_tokens, preproc map, rate limits, compute_cost | VERIFIED | All 5 additions present; 4 model keys in PRICE_TABLE |
| `src/prompt_repeater.py` | `repeat_prompt()` pure function | VERIFIED | 27 lines; single function; correct implementation |
| `src/prompt_compressor.py` | `sanitize`, `sanitize_and_compress`, `build_self_correct_prompt`, `SELF_CORRECT_PREFIX` | VERIFIED | All 4 exports present; fallback logic implemented |
| `tests/test_prompt_repeater.py` | Tests for repeater and config constants | VERIFIED | 20 test functions |
| `tests/test_prompt_compressor.py` | Tests for compressor with mocked API | VERIFIED | 23 test functions |
| `src/api_client.py` | Unified `call_model()` with streaming TTFT/TTLT | VERIFIED | Frozen dataclass APIResponse; Anthropic + Google routing; retry logic |
| `tests/test_api_client.py` | Tests with mocked SDK clients | VERIFIED | 19 test functions; all use `mock`/`patch` |
| `pyproject.toml` | `google-genai>=1.0.0` dependency | VERIFIED | Present; old `google-generativeai` removed |
| `src/run_experiment.py` | Router, engine, CLI | VERIFIED | match/case router; full engine; 5-flag CLI |
| `tests/test_run_experiment.py` | Tests for router, resumability, engine | VERIFIED | 29 test functions |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/prompt_compressor.py` | `src/config.py` | `from src.config import PREPROC_MODEL_MAP` | VERIFIED | Line 17 |
| `src/api_client.py` | `anthropic.Anthropic` | `client.messages.stream()` | VERIFIED | Line 100 |
| `src/api_client.py` | `google.genai.Client` | `client.models.generate_content_stream()` | VERIFIED | Line 151 |
| `src/api_client.py` | `src/config.py` | `from src.config import RATE_LIMIT_DELAYS` | VERIFIED | Line 17 |
| `src/run_experiment.py` | `src/api_client.py` | `from src.api_client import call_model` | VERIFIED | Line 16 |
| `src/run_experiment.py` | `src/prompt_compressor.py` | `from src.prompt_compressor import ...` | VERIFIED | Lines 27-31 |
| `src/run_experiment.py` | `src/prompt_repeater.py` | `from src.prompt_repeater import repeat_prompt` | VERIFIED | Line 32 |
| `src/run_experiment.py` | `src/db.py` | `from src.db import init_database, insert_run, query_runs, save_grade_result` | VERIFIED | Line 24 |
| `src/run_experiment.py` | `src/grade_results.py` | `from src.grade_results import grade_run` | VERIFIED | Line 25 |
| `src/run_experiment.py` | `data/experiment_matrix.json` | `json.load` in `run_engine()` | VERIFIED | Line 419 |
| `src/run_experiment.py` | `data/prompts.json` | `json.load` in `run_engine()` | VERIFIED | Line 413 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INTV-01 | 03-01 | Prompt compressor via cheap model | SATISFIED | `sanitize_and_compress()` in `src/prompt_compressor.py` |
| INTV-02 | 03-01 | Prompt repeater `<QUERY><QUERY>` | SATISFIED | `repeat_prompt()` in `src/prompt_repeater.py` |
| INTV-03 | 03-01 | Self-correct prompt prefix | SATISFIED | `SELF_CORRECT_PREFIX` + `build_self_correct_prompt()` |
| INTV-04 | 03-01 | Pre-processor sanitize pipeline | SATISFIED | `sanitize()` with fallback logic |
| INTV-05 | 03-03 | Intervention router (all 5 strategies) | SATISFIED | `apply_intervention()` match/case in `src/run_experiment.py` |
| EXEC-01 | 03-02 | Execute against Claude and Gemini at temperature=0.0 | SATISFIED | `call_model()` routes by model prefix; temperature param defaults to 0.0 |
| EXEC-02 | 03-02 | Log all fields: prompt, response, model, tokens, TTFT, TTLT, cost, timestamp | SATISFIED | `run_data` dict in `_process_item()` captures all fields; `insert_run()` persists |
| EXEC-03 | 03-03 | 5 repetitions per condition | SATISFIED | Matrix contains repetition_num 1-5; engine iterates all pending |
| EXEC-04 | 03-03 | Resumable execution | SATISFIED | `query_runs(conn, status="completed")` skip set on startup |
| EXEC-05 | 03-02 | Proactive rate limiting | SATISFIED | `_apply_rate_limit()` per-model delay; 429-triggered doubling |

All 10 requirements from all 3 plan frontmatter declarations: SATISFIED.

No orphaned requirements -- REQUIREMENTS.md traceability table lists exactly INTV-01 through INTV-05 and EXEC-01 through EXEC-05 as Phase 3, all covered.

---

## Anti-Patterns Found

None. Scanned all 5 phase-03 source files for TODO/FIXME/placeholder/return null patterns -- zero hits.

---

## Human Verification Required

None required for this phase. All critical behaviors (routing, wiring, fallback logic, retry, resumability) are verifiable from source and confirmed by 234 passing tests.

One item is noted for awareness, not blocking:

**Actual API streaming behavior** -- the timing path for `ttft_ms = 0.0` when a model returns an empty response (no text chunks) is technically possible. The tests mock this correctly and the code handles it gracefully (ttft_ms stays 0.0). No human action needed.

---

## Summary

Phase 03 achieves its goal completely. All three plans delivered their stated outputs:

- **Plan 01:** Intervention pure functions (repeater, compressor/sanitizer, self-correct prefix) and config pricing table are substantive and correct. Fallback logic for bloated/empty pre-processor output is implemented and tested.

- **Plan 02:** Unified `call_model()` wraps both SDKs with real streaming for TTFT/TTLT measurement, exponential backoff (1s/4s/16s), adaptive 429 delay doubling, and API key validation. The `google-generativeai` dependency was replaced with `google-genai`.

- **Plan 03:** The intervention router dispatches all 5 strategies via Python match/case. The execution engine implements the full noise->intervention->API->grade->DB pipeline with resumability via deterministic `make_run_id`, inline grading, and all 4 CLI flags. The import standardization fix (bare `from config` -> `from src.config`) was correctly applied across the project.

Test coverage: 91 phase-03 tests (20 + 23 + 19 + 29), 234 total project tests, all passing.

---

_Verified: 2026-03-20T22:13:53Z_
_Verifier: Claude (gsd-verifier)_
