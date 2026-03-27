# Quick Task 260327-r3e: Inspect pre-processor output and fix chatty responses - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Task Boundary

Inspect pre-processor output and fix chatty responses. The pre-processor (gpt-5-nano) generates 869K output tokens from 172K input (5x ratio) for simple sanitization. Need to store preproc output, add inspection tooling, tighten prompts, and reduce max_tokens.

</domain>

<decisions>
## Implementation Decisions

### DB Schema Change
- Use ALTER TABLE to add `preproc_raw_output` column. Existing rows get NULL. No backfill needed since old runs don't have the data stored.

### Inspect Command Scope
- `propt inspect` shows full run details: prompt text, preproc input/output diff, model output, grade result, timing, token counts, cost. A complete run viewer, not just preproc-focused.

### Max Tokens Formula
- Use `max(256, int(len(text) * 1.3))` — 30% headroom. Tight enough to prevent 5x bloat, loose enough for minor expansions from grammar fixes. Apply to both `sanitize()` and `sanitize_and_compress()`.

### Claude's Discretion
- Sanitization prompt tightening wording
- Fallback rate logging format in post-run report
- `propt inspect` argument format (run_id vs prompt_id vs interactive)

</decisions>

<specifics>
## Specific Ideas

- Side-by-side diff view for preproc input vs output in inspect command
- Fallback rate as percentage in post-run report summary section
- Explicit "Do not explain. Output ONLY the corrected text." in sanitization prompts

</specifics>

<canonical_refs>
## Canonical References

- RDD Section 6: Pre-processor intervention definitions
- RDD Section 9.2: Database schema specification

</canonical_refs>
