# Phase 23: Fix Pre-processor Output Quality and Performance - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Diagnose and fix the pre-processor pipeline that is producing bloated output (avg 510 tokens from 101 input, 5x ratio via gpt-5-nano) and degrading accuracy on clean/ESL prompts. The fix involves noise-aware preprocessing (skip clean/ESL), prompt hardening against reasoning models, token-ratio warnings, and verification via re-piloting type_a conditions.

This phase does NOT add new intervention types, change the experiment matrix structure, or modify the grading pipeline.

</domain>

<decisions>
## Implementation Decisions

### Noise-aware preprocessing
- Skip preproc entirely when `noise_type='clean'` -- zero risk of degradation, saves cost
- Skip preproc entirely for all `type_b_*` (ESL) noise -- target models handle ESL at 94-100% natively; sanitizing ESL risks meaning changes, especially on math prompts (GSM8K drops 3-7%)
- Only run preproc for `type_a_*` (typo) noise, where it demonstrably helps (+3-4% on type_a_10pct and type_a_20pct)
- The skip logic lives in `apply_intervention()` in `run_experiment.py` -- when intervention is `pre_proc_sanitize` or `pre_proc_sanitize_compress` and noise_type is not `type_a_*`, return the prompt unchanged with metadata noting `preproc_skipped=True`

### Anti-reasoning system prompt
- Add "Do not think step by step. Do not reason. Just output the corrected text verbatim." to both `_SANITIZE_SYSTEM` and `_COMPRESS_SYSTEM` in `prompt_compressor.py`
- This targets reasoning models (gpt-5-nano, o-series) that generate hidden chain-of-thought, inflating output tokens and cost

### Token-ratio warning
- After each preproc call, if `output_tokens > input_tokens * 3`, log a WARNING suggesting the user switch to a non-reasoning preproc model
- Keep the existing character-based fallback (`len(result) > len(original_text) * 1.5`) unchanged -- it correctly catches text bloat
- The token warning is informational only, not a fallback trigger

### Model guidance documentation
- Document in wizard output and docs that reasoning models (gpt-5-nano, o-series) are poor preproc choices due to token bloat (5x ratio) and latency (3.6s TTFT)
- Recommend non-reasoning models: gpt-4o-mini, claude-haiku, gemini-2.0-flash
- This is guidance only -- no code enforcement of model choice

### Verification approach
- Re-run pilot subset: 20 prompts x type_a noise levels x preproc interventions (~200 API calls)
- Compare before/after accuracy on the same prompts to verify the fix helps
- Tag old runs as "pre-fix baseline" via session metadata; new runs get "post-fix" tag
- Keep all data in the same results.db for direct comparison

### Claude's Discretion
- Exact implementation of the noise_type check (string match, enum check, etc.)
- Whether to add the skip logic in `apply_intervention` or in `sanitize`/`sanitize_and_compress` directly
- Token-ratio warning message wording
- How to tag sessions (column, JSON metadata field, session name convention)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pre-processor pipeline
- `src/prompt_compressor.py` -- Sanitize/compress functions, system prompts, fallback logic
- `src/run_experiment.py` lines 110-125 -- `apply_intervention()` routing for preproc interventions

### Prior fix context
- `.planning/quick/260327-r3e-inspect-pre-processor-output-and-fix-cha/260327-r3e-SUMMARY.md` -- Previous quick task that tightened prompts, added preproc_raw_output storage, max_tokens cap

### Research design
- `docs/RDD_Linguistic_Tax_v4.md` -- Section 6 (intervention definitions), Section 4 (noise types)

### Data context
- Pilot data in `results/results.db`: 1600 preproc runs (all gpt-5-nano), 800 raw runs
- All preproc_raw_output is NULL (pre-migration data)
- Key finding: sanitize helps type_a (+3-4%) but hurts clean (-3.3% GSM8K) and ESL (-3 to -7% GSM8K)

### TODO files being addressed
- `.planning/todos/pending/2026-03-27-investigate-preproc-sanitize-hurting-accuracy.md`
- `.planning/todos/pending/2026-03-27-investigate-preproc-performance-anomaly.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prompt_compressor.py:_process_response()` -- Central fallback logic, already stores `preproc_raw_output` metadata
- `prompt_compressor.py:_get_preproc_model()` -- Model lookup with fallback
- `run_experiment.py:apply_intervention()` -- Intervention routing switch, already has access to `noise_type` via the item dict
- `propt inspect` CLI command -- Can verify preproc output quality post-fix
- `execution_summary.py` -- Already reports fallback rates

### Established Patterns
- Metadata dict pattern: preproc functions return `(text, metadata_dict)` -- extend with `preproc_skipped` key
- Fallback pattern: `_process_response()` sets `preproc_failed=True` in metadata on fallback
- Logging: all modules use `logging.getLogger(__name__)`

### Integration Points
- `apply_intervention()` in `run_experiment.py` is the routing point -- noise_type available from the experiment item
- `prompt_compressor.sanitize()` and `sanitize_and_compress()` signatures don't currently receive noise_type
- Session tagging via session_id field in experiment_runs table

</code_context>

<specifics>
## Specific Ideas

- The noise_type check should be early and cheap -- avoid making an API call just to skip it
- The skip should still return proper metadata so downstream reporting knows preprocessing was skipped (not missing)
- Anti-reasoning prompt wording should be model-agnostic -- works whether the model actually reasons or not

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 23-fix-pre-processor-output-quality-and-performance*
*Context gathered: 2026-03-27*
