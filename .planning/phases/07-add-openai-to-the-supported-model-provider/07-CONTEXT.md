# Phase 7: Add OpenAI to the Supported Model Provider - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add OpenAI (GPT-4o) as a full third target model in the experiment pipeline alongside Claude Sonnet and Gemini Pro. This includes API client integration, config/pricing entries, experiment matrix expansion, pre-processor pairing, and updates to analysis/figure modules to handle 3 models. The RDD and PROJECT.md are NOT updated — this is a post-v1 extension.

</domain>

<decisions>
## Implementation Decisions

### Model Selection
- Primary target model: GPT-4o, pinned to latest available version at implementation time (research current pinned version during planning)
- Pre-processor model: GPT-4o-mini, also pinned to a specific version
- Single OpenAI target model only (no o-series or additional models)
- Environment variable: OPENAI_API_KEY (standard convention)
- Dependency: `openai` Python package added as required dependency in pyproject.toml
- Determinism: temperature=0.0 only, no OpenAI-specific seed parameter

### Experiment Scope
- GPT-4o becomes a full 3rd target model in the experiment matrix (all noise types x all interventions x 5 reps)
- Matrix generator auto-includes all models from the MODELS tuple — adding a model to config automatically includes it
- Pilot module extended to validate OpenAI end-to-end before full runs
- Statistical analysis and figure generation modules updated to handle 3 models
- RDD (docs/RDD_Linguistic_Tax_v4.md) stays as-is — it's the finalized v1 paper spec
- PROJECT.md out-of-scope section stays as-is — historically accurate for v1

### API Integration
- Use official `openai` Python SDK (matches pattern: each provider gets its own SDK)
- Add `_call_openai()` function in api_client.py following existing `_call_anthropic`/`_call_google` pattern
- Streaming with `stream_options={"include_usage": true}` for TTFT/TTLT measurement AND token counts in one call
- Model routing: `startswith("gpt")` check in `call_model()` dispatcher
- System messages: _call_openai handles conversion from system param to system role message internally (call_model signature unchanged)
- Rate limit retry: identical pattern to Anthropic — 4 attempts, 1s/4s/16s exponential backoff, double delay on 429
- Rate limit error type: `openai.RateLimitError`
- Update .env.example to include OPENAI_API_KEY

### Cost & Pricing
- Add GPT-4o and GPT-4o-mini to PRICE_TABLE — research exact current rates during planning
- No budget ceiling for OpenAI portion — same approach as other providers (pilot validates cost first)
- Cost rollups treat GPT-4o as just another model — no special OpenAI section in analysis
- Rate limit delays: GPT-4o at 0.2s (same tier as Sonnet), GPT-4o-mini at 0.1s (same tier as Haiku)

### Claude's Discretion
- Exact pinned version strings for GPT-4o and GPT-4o-mini (research latest stable at impl time)
- Exact current pricing for PRICE_TABLE entries
- Internal streaming implementation details for _call_openai
- Any OpenAI-specific error handling beyond rate limits

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing API patterns
- `src/api_client.py` — Current unified API client with _call_anthropic, _call_google, and call_model dispatcher. New _call_openai follows this exact pattern
- `src/config.py` — MODELS tuple, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig. All need OpenAI entries

### Experiment infrastructure
- `src/run_experiment.py` — Execution engine that routes through call_model. Should work with OpenAI once api_client and config are updated
- `src/pilot.py` — Pilot validation module. Needs to include GPT-4o in pilot runs

### Analysis and figures
- `src/compute_derived.py` — Cost rollups and derived metrics. Should handle 3 models via existing PRICE_TABLE lookup
- `src/analyze_results.py` — Statistical analysis. Model is a factor in GLMM — 3rd model should work naturally
- `src/generate_figures.py` — Publication figures. Faceting by model needs to handle 3 panels

### Research design
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative v1 spec. NOT being updated, but defines the experimental design that OpenAI must conform to

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `APIResponse` dataclass: Unified response format — works for any provider, no changes needed
- `call_model()` dispatcher: Simple prefix-based routing, easy to extend with one more elif
- `PRICE_TABLE` / `RATE_LIMIT_DELAYS` / `PREPROC_MODEL_MAP`: Dict-based config, just add entries
- Retry logic in call_model(): Provider-agnostic pattern, just add OpenAI's exception type

### Established Patterns
- Each provider has: SDK import, private `_call_*` function, streaming for TTFT/TTLT, unified APIResponse return
- Config uses module-level dicts and tuples — no registry pattern, just add entries
- Experiment matrix iterates over MODELS tuple — adding a model auto-includes it
- Pre-processor pairing via PREPROC_MODEL_MAP dict

### Integration Points
- `api_client.py`: Add _call_openai, extend call_model routing and retry
- `config.py`: Add to MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig
- `pyproject.toml`: Add openai dependency
- `.env.example`: Add OPENAI_API_KEY
- `pilot.py`: Include GPT-4o in pilot runs
- `generate_figures.py`: Verify 3-model faceting works

</code_context>

<specifics>
## Specific Ideas

No specific requirements — follow existing patterns exactly. The goal is that OpenAI feels like a natural third provider with no special-casing beyond what's needed at the SDK level.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-add-openai-to-the-supported-model-provider*
*Context gathered: 2026-03-23*
