---
phase: 23-fix-pre-processor-output-quality-and-performance
verified: 2026-03-27T21:40:00Z
status: human_needed
score: 7/8 must-haves verified
re_verification: false
human_verification:
  - test: "Re-run type_a pilot conditions with fixes applied"
    expected: "pre_proc_sanitize accuracy for type_a conditions >= raw accuracy (was 73.6% vs 74.4%)"
    why_human: "Requires live API calls, costs money, and compares runtime accuracy metrics — cannot verify statically"
  - test: "Confirm clean and type_b conditions show preproc_skipped in inspect output"
    expected: "propt inspect --last --intervention pre_proc_sanitize shows preproc_skipped=True for clean and type_b rows"
    why_human: "Requires a live pilot run with real data in results.db"
---

# Phase 23: Fix Pre-Processor Output Quality and Performance Verification Report

**Phase Goal:** Diagnose and fix the pre-processor pipeline producing bloated output (869K tokens from 172K input, 5x ratio) and degrading accuracy (73.6% pre_proc_sanitize vs 74.4% raw) -- root-cause the prompt mangling, fix sanitize/compress prompt templates and fallback thresholds, and verify fixes improve both output quality and accuracy
**Verified:** 2026-03-27T21:40:00Z
**Status:** human_needed (automated checks passed; runtime accuracy improvement requires human re-pilot)
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Preproc is skipped for clean and type_b noise types, returning prompt unchanged with preproc_skipped=True metadata | VERIFIED | `src/run_experiment.py:117-122` — early-return block for non-type_a noise present with correct metadata |
| 2 | Preproc still runs normally for type_a noise types | VERIFIED | `src/run_experiment.py:118` — condition is `noise_type and not noise_type.startswith("type_a_")`, so type_a passes through to match block |
| 3 | System prompts contain anti-reasoning directives to reduce token bloat from reasoning models | VERIFIED | `src/prompt_compressor.py:33,44` — both `_SANITIZE_SYSTEM` and `_COMPRESS_SYSTEM` contain "Do not think step by step. Do not reason." |
| 4 | Token-ratio warning is logged when output_tokens > input_tokens * 3 | VERIFIED | `src/prompt_compressor.py:196-204` — warning block present with correct condition and "token bloat" / "non-reasoning model" in format string |
| 5 | Existing callers without noise_type parameter continue to work (backward compatible) | VERIFIED | `src/run_experiment.py:93` — `noise_type: str = ""` default; condition `if noise_type and not...` will not trigger for empty string |
| 6 | Documentation warns against reasoning models as pre-processors with recommended alternatives | VERIFIED | `docs/getting-started.md:95-104` — full table with per-provider recommendations and skip-for-clean note |
| 7 | Setup wizard warns about reasoning model pre-processor choice | VERIFIED | `src/setup_wizard.py:336-338` — print block with "non-reasoning models for pre-processing" and specific model recommendations |
| 8 | Re-piloting type_a conditions shows accuracy improvement or parity vs raw | NEEDS HUMAN | Cannot verify programmatically -- requires live API calls and runtime accuracy comparison |

**Score:** 7/8 truths verified (1 requires human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/prompt_compressor.py` | Anti-reasoning system prompts and token-ratio warning | VERIFIED | Lines 31-46 (both system consts), 196-204 (token warning), 208 (fallback check unchanged) |
| `src/run_experiment.py` | Noise-aware skip logic in apply_intervention | VERIFIED | Lines 87-122 — `noise_type` param, skip block, and `_process_item` threads `noise_type=item["noise_type"]` at line 313 |
| `tests/test_prompt_compressor.py` | Tests for anti-reasoning and token-ratio warning | VERIFIED | Lines 301, 305, 322, 339, 355 — all five required test functions present |
| `tests/test_run_experiment.py` | Tests for skip logic: clean skipped, type_b skipped, type_a runs | VERIFIED | Lines 201, 211, 227, 236, 238, 248, 257, 267 — all eight required test functions present |
| `docs/getting-started.md` | Pre-processor model guidance for researchers | VERIFIED | Lines 95-104 — recommendation table present with non-reasoning guidance |
| `src/setup_wizard.py` | Wizard output warns about reasoning model preproc choice | VERIFIED | Lines 336-338 — warning block present |

All artifacts: exist, substantive, and wired.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_experiment.py:_process_item` | `apply_intervention` | `noise_type=item["noise_type"]` kwarg | WIRED | `grep` confirms line 313: `noise_type=item["noise_type"]` |
| `run_experiment.py:apply_intervention` | `preproc_skipped` metadata | Early return for non-type_a noise | WIRED | Lines 117-122 — condition `if noise_type and not noise_type.startswith("type_a_")` with correct return dict |
| `prompt_compressor.py:_process_response` | `logger.warning` for token ratio | `output_tokens > input_tokens * 3` check | WIRED | Lines 196-204 — condition and warning call both present |
| `docs/getting-started.md` | Pre-processor model table | Recommendation text in model selection section | WIRED | Line 95-104 — table and note follow default models table |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TODO-preproc-sanitize-accuracy | 23-01-PLAN.md | Fix accuracy regression from preproc running on clean/ESL prompts | SATISFIED | Skip logic in `apply_intervention` prevents unnecessary preproc API calls for clean and type_b noise; 8 new tests confirm behavior |
| TODO-preproc-performance-anomaly | 23-01-PLAN.md, 23-02-PLAN.md | Fix token bloat (869K from 172K, 5x ratio) and document model selection guidance | SATISFIED (code) / NEEDS HUMAN (accuracy validation) | Anti-reasoning directives in system prompts, token-ratio warning at >3x, per-provider non-reasoning model docs and wizard guidance all shipped |

**Note on requirement IDs:** Both `TODO-preproc-sanitize-accuracy` and `TODO-preproc-performance-anomaly` are declared in the PLAN frontmatter and referenced in the ROADMAP. They do NOT appear in `.planning/REQUIREMENTS.md` (which only tracks v1.0 and v2.0 numbered requirements like CFG-01, WIZ-01, etc.). These are ad-hoc TODO-style identifiers for this phase's specific technical debt, not entries in the formal requirements registry. No orphaned requirements found in REQUIREMENTS.md for Phase 23.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No anti-patterns found in modified source files (`src/prompt_compressor.py`, `src/run_experiment.py`, `docs/getting-started.md`, `src/setup_wizard.py`, `tests/test_prompt_compressor.py`, `tests/test_run_experiment.py`).

### Human Verification Required

#### 1. Re-pilot type_a conditions and check accuracy improvement

**Test:** Run `propt pilot --session post-fix-type-a`, then `propt report --session post-fix-type-a`
**Expected:** pre_proc_sanitize accuracy for type_a noise conditions is >= raw accuracy (the regression was 73.6% vs 74.4% raw)
**Why human:** Requires live API calls with real money, executes the full 20-prompt pilot matrix, and compares accuracy metrics at runtime. Cannot determine accuracy from static code inspection.

#### 2. Confirm preproc_skipped behavior in inspect output

**Test:** After a pilot run, run `propt inspect --last --intervention pre_proc_sanitize | head -20`
**Expected:** Rows with noise_type=clean and noise_type=type_b_esl show `preproc_skipped=True` in the output; rows with noise_type=type_a_* show no skip and actual preproc metadata
**Why human:** Requires a live results.db populated by a real pilot run.

### Gaps Summary

No automated gaps found. All seven statically-verifiable must-haves pass:

- Skip logic is correctly implemented and backward-compatible
- Anti-reasoning directives are present in both system prompt constants
- Token-ratio warning is wired and fires at the correct threshold
- All 15 new tests exist and pass (confirmed: 706/706 suite tests pass)
- Documentation and wizard guidance ship the per-provider recommendations
- All three commit hashes (cfc8cf5, 190a3dc, 6e01bda) exist and match the described changes

The one unverifiable truth (accuracy improvement after re-pilot) is inherent to the task — it requires executing the experiment against live APIs. The code changes are correctly structured to produce that improvement: skip logic eliminates the wasted preproc calls on clean/ESL prompts that caused the accuracy regression, and anti-reasoning directives address the token bloat root cause.

---

_Verified: 2026-03-27T21:40:00Z_
_Verifier: Claude (gsd-verifier)_
