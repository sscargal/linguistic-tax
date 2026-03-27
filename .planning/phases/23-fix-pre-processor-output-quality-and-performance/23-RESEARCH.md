# Phase 23: Fix Pre-processor Output Quality and Performance - Research

**Researched:** 2026-03-27
**Domain:** Pre-processor pipeline optimization (prompt_compressor.py, run_experiment.py)
**Confidence:** HIGH

## Summary

This phase fixes two interrelated problems in the pre-processor pipeline: (1) the pre-processor hurts accuracy on clean and ESL prompts (73.6% vs 74.4% raw), and (2) reasoning models like gpt-5-nano produce bloated output (5x token ratio) with high latency (3.6s TTFT). The root causes are well understood from pilot data analysis: preprocessing clean/ESL prompts is net-harmful because models already handle these natively, and reasoning models generate hidden chain-of-thought that inflates output tokens.

The fix is primarily routing logic (skip preproc for non-type_a noise) plus prompt hardening (anti-reasoning directives in system prompts) plus observability (token-ratio warnings). All decisions are locked in CONTEXT.md with clear implementation targets. The codebase is well-structured for these changes -- `apply_intervention()` already receives noise_type context, and the metadata dict pattern supports new keys like `preproc_skipped`.

**Primary recommendation:** Implement noise-aware skip logic in `apply_intervention()`, harden system prompts against reasoning models, add token-ratio warning logging, and verify via re-piloting type_a conditions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Skip preproc entirely when `noise_type='clean'` -- zero risk of degradation, saves cost
- Skip preproc entirely for all `type_b_*` (ESL) noise -- target models handle ESL at 94-100% natively; sanitizing ESL risks meaning changes, especially on math prompts (GSM8K drops 3-7%)
- Only run preproc for `type_a_*` (typo) noise, where it demonstrably helps (+3-4% on type_a_10pct and type_a_20pct)
- The skip logic lives in `apply_intervention()` in `run_experiment.py` -- when intervention is `pre_proc_sanitize` or `pre_proc_sanitize_compress` and noise_type is not `type_a_*`, return the prompt unchanged with metadata noting `preproc_skipped=True`
- Add "Do not think step by step. Do not reason. Just output the corrected text verbatim." to both `_SANITIZE_SYSTEM` and `_COMPRESS_SYSTEM` in `prompt_compressor.py`
- After each preproc call, if `output_tokens > input_tokens * 3`, log a WARNING suggesting the user switch to a non-reasoning preproc model
- Keep the existing character-based fallback (`len(result) > len(original_text) * 1.5`) unchanged
- The token warning is informational only, not a fallback trigger
- Document in wizard output and docs that reasoning models are poor preproc choices
- Recommend non-reasoning models: gpt-4o-mini, claude-haiku, gemini-2.0-flash
- Re-run pilot subset: 20 prompts x type_a noise levels x preproc interventions (~200 API calls)
- Tag old runs as "pre-fix baseline" via session metadata; new runs get "post-fix" tag
- Keep all data in the same results.db for direct comparison

### Claude's Discretion
- Exact implementation of the noise_type check (string match, enum check, etc.)
- Whether to add the skip logic in `apply_intervention` or in `sanitize`/`sanitize_and_compress` directly
- Token-ratio warning message wording
- How to tag sessions (column, JSON metadata field, session name convention)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TODO-preproc-sanitize-accuracy | Pre_proc_sanitize hurts accuracy vs raw (73.6% vs 74.4%) -- diagnose and fix | Noise-aware skip logic prevents preproc from degrading clean/ESL accuracy; anti-reasoning prompts reduce output mangling; verified by re-pilot comparison |
| TODO-preproc-performance-anomaly | Pre-processor produces bloated output (5x token ratio) with slow TTFT (3.6s) | Anti-reasoning system prompt directives reduce chain-of-thought inflation; token-ratio warning alerts users to switch models; model guidance documents non-reasoning alternatives |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Project standard |
| pytest | 9.0.2 | Testing | Already in use |
| logging | stdlib | Observability | Project convention (no print for non-CLI) |

### Supporting
No new libraries needed. All changes are to existing modules using existing patterns.

## Architecture Patterns

### Recommended Change Structure
```
src/
  prompt_compressor.py   # Modify: anti-reasoning system prompts, token-ratio warning
  run_experiment.py      # Modify: noise-aware skip logic in apply_intervention()
```

### Pattern 1: Noise-Aware Skip in apply_intervention()
**What:** Early return for preproc interventions when noise_type is not type_a_*
**When to use:** Every preproc intervention call
**Example:**
```python
# In apply_intervention(), before the match statement or within preproc cases:
def apply_intervention(
    prompt_text: str,
    intervention: str,
    model: str,
    call_fn: Callable[..., Any],
    prompt_id: str = "",
    noise_type: str = "",  # NEW parameter
) -> tuple[str, dict[str, Any]]:
    # Skip preproc for non-type_a noise
    if intervention in ("pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only"):
        if not noise_type.startswith("type_a_"):
            return (prompt_text, {"preproc_skipped": True, "preproc_skip_reason": f"noise_type={noise_type}"})
    # ... existing match statement
```

**Why in apply_intervention, not sanitize():** The CONTEXT.md specifies this location. It keeps the skip logic centralized at the routing layer, avoiding changes to `sanitize()` and `sanitize_and_compress()` signatures (which are also used by tests). The noise_type is already available in `_process_item()` via `item["noise_type"]`.

### Pattern 2: Anti-Reasoning System Prompts
**What:** Append anti-reasoning directives to system prompt constants
**When to use:** Both _SANITIZE_SYSTEM and _COMPRESS_SYSTEM
**Example:**
```python
_SANITIZE_SYSTEM: str = (
    "You are a text corrector. "
    "Do not think step by step. Do not reason. "
    "Just output the corrected text verbatim."
)

_COMPRESS_SYSTEM: str = (
    "You are a prompt optimizer. "
    "Do not think step by step. Do not reason. "
    "Just output the optimized text verbatim."
)
```

### Pattern 3: Token-Ratio Warning in _process_response()
**What:** Log WARNING when output_tokens > input_tokens * 3
**When to use:** After every preproc API call, before fallback check
**Example:**
```python
def _process_response(response, original_text, preproc_model):
    result = response.text.strip()
    metadata = { ... }

    # Token ratio warning (informational only)
    if response.output_tokens > response.input_tokens * 3:
        logger.warning(
            "Pre-processor token bloat: %s produced %d output tokens from %d input tokens (%.1fx ratio). "
            "Consider switching to a non-reasoning model (gpt-4o-mini, claude-haiku, gemini-2.0-flash).",
            preproc_model, response.output_tokens, response.input_tokens,
            response.output_tokens / max(response.input_tokens, 1),
        )

    # Existing fallback logic unchanged
    if not result or len(result) > len(original_text) * 1.5:
        ...
```

### Pattern 4: Passing noise_type Through the Call Chain
**What:** Thread noise_type from _process_item to apply_intervention
**Current state:** `apply_intervention()` signature has `prompt_id` but not `noise_type`. `_process_item()` has access to `item["noise_type"]`.
**Change required:**
```python
# In _process_item():
processed_text, preproc_meta = apply_intervention(
    prompt_text, item["intervention"], item["model"], call_model,
    prompt_id=item["prompt_id"],
    noise_type=item["noise_type"],  # NEW
)
```
**Backward compatibility:** Use default `noise_type=""` so existing callers (tests, other call sites) continue to work. Empty string does not start with "type_a_" so preproc runs as before if noise_type is not provided.

### Anti-Patterns to Avoid
- **Modifying sanitize()/sanitize_and_compress() signatures:** The skip belongs in the router, not the preproc functions. Adding noise_type to those functions leaks routing concerns into the processing layer.
- **Enforcing model choice in code:** The token-ratio warning is guidance only. Do NOT reject or override the user's preproc model choice.
- **Breaking the fallback path:** The existing `len(result) > len(original_text) * 1.5` fallback MUST remain unchanged. It catches text bloat at the character level.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Noise type classification | Custom noise parser | Simple `str.startswith("type_a_")` | Noise types follow a strict naming convention in _NOISE_TYPE_MAP |
| Session tagging | Custom metadata table | Session name convention (e.g., "pilot-prefix-postfix") | Session system already exists from quick task 260327-rhk |
| Preproc quality metrics | Custom analysis pipeline | Existing `propt report` and `propt inspect` commands | Already built in prior quick tasks |

## Common Pitfalls

### Pitfall 1: Backward-Incompatible Signature Change
**What goes wrong:** Adding required parameters to `apply_intervention()` breaks all existing callers and tests.
**Why it happens:** Forgetting that tests call `apply_intervention()` directly without noise_type.
**How to avoid:** Use `noise_type: str = ""` as a keyword argument with default. Empty string correctly triggers no-skip behavior.
**Warning signs:** Test failures in `test_run_experiment.py::TestApplyIntervention`.

### Pitfall 2: Skip Logic Too Broad
**What goes wrong:** Skipping preproc for compress_only intervention when it should only skip for sanitize variants.
**Why it happens:** compress_only shares the same code path as sanitize_and_compress.
**How to avoid:** The CONTEXT.md says skip for `pre_proc_sanitize` and `pre_proc_sanitize_compress`. Include `compress_only` too since it uses the same underlying function and has the same problem.
**Warning signs:** compress_only still making API calls on clean prompts.

### Pitfall 3: Token Warning Logged Before Response Parsing
**What goes wrong:** Warning fires but then fallback also fires, double-reporting.
**Why it happens:** Both checks evaluate the same response.
**How to avoid:** This is fine -- both can fire independently. The warning is about token ratio (API billing), the fallback is about text quality (character length). They measure different things.

### Pitfall 4: preproc_skipped Metadata Not Stored in DB
**What goes wrong:** Skipped preproc runs have empty metadata, making post-hoc analysis impossible.
**Why it happens:** The DB schema stores preproc_model, preproc_input_tokens etc. from metadata, but `preproc_skipped` is a new key that may not map to a column.
**How to avoid:** The `preproc_skipped` flag will end up in run_data via `preproc_meta.get("preproc_skipped")`. Either add a column to the schema OR accept that it shows up as NULL preproc_model (which already distinguishes skipped from processed runs).
**Recommendation:** Do NOT add a DB column. The absence of preproc_model + absence of preproc_failed is sufficient signal. The metadata dict serves debugging via `propt inspect`.

### Pitfall 5: Re-pilot Verification Scope Creep
**What goes wrong:** Verification re-runs the entire pilot matrix instead of just type_a preproc conditions.
**Why it happens:** Using `propt pilot` without filters.
**How to avoid:** Run targeted: `propt run --intervention pre_proc_sanitize --limit N` with type_a prompts. Or create a focused verification script.

## Code Examples

### Current apply_intervention (lines 87-138 of run_experiment.py)
```python
def apply_intervention(
    prompt_text: str,
    intervention: str,
    model: str,
    call_fn: Callable[..., Any],
    prompt_id: str = "",
) -> tuple[str, dict[str, Any]]:
    match intervention:
        case "raw":
            return (prompt_text, {})
        case "pre_proc_sanitize":
            return sanitize(prompt_text, model, call_fn)
        case "pre_proc_sanitize_compress":
            return sanitize_and_compress(prompt_text, model, call_fn)
        # ... other cases
```

### Current _process_item call site (line 298 of run_experiment.py)
```python
processed_text, preproc_meta = apply_intervention(
    prompt_text, item["intervention"], item["model"], call_model,
    prompt_id=item["prompt_id"],
)
```

### Current system prompts (prompt_compressor.py lines 31-44)
```python
_SANITIZE_SYSTEM: str = "You are a text corrector."
_COMPRESS_SYSTEM: str = "You are a prompt optimizer."
```

### Current _process_response (prompt_compressor.py lines 162-198)
```python
def _process_response(response, original_text, preproc_model):
    result = response.text.strip()
    metadata = {
        "preproc_model": preproc_model,
        "preproc_input_tokens": response.input_tokens,
        "preproc_output_tokens": response.output_tokens,
        "preproc_ttft_ms": response.ttft_ms,
        "preproc_ttlt_ms": response.ttlt_ms,
        "preproc_raw_output": result,
    }
    if not result or len(result) > len(original_text) * 1.5:
        metadata["preproc_failed"] = True
        return original_text, metadata
    return result, metadata
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_prompt_compressor.py tests/test_run_experiment.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TODO-preproc-sanitize-accuracy | Skip preproc for clean/ESL noise_type | unit | `pytest tests/test_run_experiment.py -x -k "skip"` | Wave 0 |
| TODO-preproc-sanitize-accuracy | preproc_skipped metadata returned | unit | `pytest tests/test_run_experiment.py -x -k "skip"` | Wave 0 |
| TODO-preproc-sanitize-accuracy | Preproc still runs for type_a noise | unit | `pytest tests/test_run_experiment.py -x -k "type_a"` | Wave 0 |
| TODO-preproc-performance-anomaly | Anti-reasoning in system prompts | unit | `pytest tests/test_prompt_compressor.py -x -k "system"` | Existing (update) |
| TODO-preproc-performance-anomaly | Token-ratio warning logged | unit | `pytest tests/test_prompt_compressor.py -x -k "token_ratio"` | Wave 0 |
| TODO-preproc-performance-anomaly | Backward compat: no noise_type = normal preproc | unit | `pytest tests/test_run_experiment.py -x -k "intervention"` | Existing (verify) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_prompt_compressor.py tests/test_run_experiment.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_run_experiment.py` -- needs new tests for noise-aware skip logic in apply_intervention
- [ ] `tests/test_prompt_compressor.py` -- needs test for token-ratio warning logging
- [ ] `tests/test_prompt_compressor.py` -- needs updated system prompt assertions

## Sources

### Primary (HIGH confidence)
- `src/prompt_compressor.py` -- Current implementation reviewed in full
- `src/run_experiment.py` -- Current implementation reviewed in full (apply_intervention lines 87-138, _process_item lines 258-407)
- `tests/test_prompt_compressor.py` -- 26 existing tests reviewed
- `tests/test_run_experiment.py` -- 17+ existing tests reviewed
- `.planning/quick/260327-r3e-inspect-pre-processor-output-and-fix-cha/260327-r3e-SUMMARY.md` -- Prior fix context
- `23-CONTEXT.md` -- All implementation decisions locked

### Secondary (MEDIUM confidence)
- `.planning/todos/pending/2026-03-27-investigate-preproc-sanitize-hurting-accuracy.md` -- Problem statement and pilot data
- `.planning/todos/pending/2026-03-27-investigate-preproc-performance-anomaly.md` -- Performance anomaly details

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all changes to existing modules
- Architecture: HIGH - Clear patterns from CONTEXT.md decisions, well-understood codebase
- Pitfalls: HIGH - Identified from actual code review, not speculation

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- internal codebase changes only)
