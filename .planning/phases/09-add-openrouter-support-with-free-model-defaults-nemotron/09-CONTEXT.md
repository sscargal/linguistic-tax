# Phase 9: Add OpenRouter Support with Free Model Defaults (Nemotron) - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add OpenRouter as a 4th model provider gateway, defaulting to free Nemotron models for zero-cost experiment runs. Includes API client integration (`_call_openrouter`), config/pricing entries, experiment matrix expansion, pilot inclusion, unit tests, and QA script updates. The free tier is primarily for the project author's development cost savings; researchers are free to use free or paid models via OpenRouter.

</domain>

<decisions>
## Implementation Decisions

### API Integration Approach
- Claude's discretion on SDK choice (OpenRouter SDK Beta, OpenRouter API directly, or OpenAI SDK) — researcher evaluates all three options from https://openrouter.ai/docs/quickstart and picks the best fit for this project
- New standalone `_call_openrouter()` function in api_client.py following existing `_call_anthropic`, `_call_google`, `_call_openai` pattern — each provider is self-contained
- Streaming for TTFT/TTLT measurement, same pattern as all other providers
- Project-specific HTTP headers: HTTP-Referer and X-Title identifying the Linguistic Tax Research project
- Same retry pattern as other providers: 4 attempts, exponential backoff (1s/4s/16s), double delay on 429
- Standard logging only — no OpenRouter-specific metadata logging
- No health check or pre-flight validation — fail naturally like other providers
- Auto-route on OpenRouter (no provider pinning) — let OpenRouter pick the serving provider

### Model Routing
- `openrouter/` prefix for routing in `call_model()` — e.g., `openrouter/nvidia/llama-3.1-nemotron-70b-instruct:free`
- Prefix stripping happens inside `_call_openrouter()` — call_model just routes, doesn't transform
- Models stored with full prefix in MODELS tuple, PRICE_TABLE, etc. — the `openrouter/` prefix is part of the canonical model ID

### Model Selection
- 1 free target model + 1 free pre-processor model via OpenRouter
- Specific model IDs researched during planning (examine openrouter.ai/models?max_price=0 for best current free models, Nemotron preferred)
- Both target and pre-proc free models via OpenRouter — full zero-cost pipeline
- Named fields in ExperimentConfig: `openrouter_model` and `openrouter_preproc_model`
- Add to main MODELS tuple — auto-included in experiment matrix like any other model
- Same MAX_TOKENS_BY_BENCHMARK limits as other models — if free model can't handle it, that's a data point
- Manual swap if free model disappears — researcher updates config.py with new model ID

### Config & Pricing
- OPENROUTER_API_KEY environment variable (follows PROVIDER_API_KEY pattern)
- Add OPENROUTER_API_KEY to .env.example alongside other keys
- Exact $0 pricing in PRICE_TABLE (input_per_1m: 0.0, output_per_1m: 0.0) — no epsilon values
- Conservative rate limit delay: 0.5s for both target and pre-proc free models (higher than paid models to respect free-tier limits)
- OPENROUTER_BASE_URL as module-level constant in config.py, defaulting to `https://openrouter.ai/api/v1`, overridable via environment variable of the same name

### Experiment Scope
- Full experiment matrix: all 8 noise conditions x 5 interventions x 5 reps — same as every other model
- Include in pilot runs (20-prompt validation before full experiment)
- Include in cost projection with $0 pricing — validates pipeline handles zero-cost models
- No special treatment in analysis — data speaks for itself
- Verify dynamic handling in analysis/figure modules (should handle N models from Phase 7 work)
- No validation at matrix generation time — errors surface at execution time

### Testing & QA
- Unit tests following Phase 8 pattern: mock API responses, test routing, verify config entries, use conftest mock factories
- Test priorities: prefix stripping & routing lifecycle + zero-cost calculation edge cases (both)
- Full lifecycle integration test (with mocked API): config entry → MODELS → experiment matrix → call_model routing → _call_openrouter → APIResponse
- Maintain 80%+ line coverage after adding OpenRouter code
- Update QA script (scripts/qa_script.sh) with OpenRouter-specific validation checks

### Claude's Discretion
- SDK choice for connecting to OpenRouter (OpenRouter SDK Beta, direct API, or OpenAI SDK reuse)
- Exact pinned model IDs for target and pre-processor (researched during planning)
- Internal streaming implementation details for _call_openrouter
- Any OpenRouter-specific error handling beyond standard rate limit retry

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing API patterns
- `src/api_client.py` — Current unified API client with _call_anthropic, _call_google, _call_openai, and call_model dispatcher. New _call_openrouter follows this exact pattern
- `src/config.py` — MODELS tuple, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig. All need OpenRouter entries

### OpenRouter documentation
- https://openrouter.ai/docs/quickstart — Three API interface options (SDK Beta, direct API, OpenAI SDK)
- https://openrouter.ai/models?max_price=0 — Free model catalog for selecting target and pre-processor models

### Prior provider integration
- `.planning/phases/07-add-openai-to-the-supported-model-provider/07-CONTEXT.md` — Phase 7 decisions for GPT-4o integration; OpenRouter follows the same architectural pattern

### Experiment infrastructure
- `src/run_experiment.py` — Execution engine that routes through call_model
- `src/pilot.py` — Pilot validation module; needs to include OpenRouter model
- `src/compute_derived.py` — Cost rollups; must handle $0 pricing without errors
- `src/analyze_results.py` — Statistical analysis; model is a GLMM factor
- `src/generate_figures.py` — Publication figures; verify N-model dynamic faceting

### Testing infrastructure
- `tests/conftest.py` — Mock factory fixtures from Phase 8
- `scripts/qa_script.sh` — QA validation script; needs OpenRouter checks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `APIResponse` dataclass: Unified response format — works for any provider, no changes needed
- `call_model()` dispatcher: Simple prefix-based routing with `startswith()`, easy to extend with one more elif for `openrouter/`
- `PRICE_TABLE` / `RATE_LIMIT_DELAYS` / `PREPROC_MODEL_MAP`: Dict-based config, just add entries
- Retry logic in call_model(): Provider-agnostic pattern with per-provider exception types
- conftest.py mock factories: Reusable API response mocking from Phase 8

### Established Patterns
- Each provider has: SDK import, private `_call_*` function, streaming for TTFT/TTLT, unified APIResponse return
- Config uses module-level dicts and tuples — no registry pattern, just add entries
- Experiment matrix iterates over MODELS tuple — adding a model auto-includes it
- Pre-processor pairing via PREPROC_MODEL_MAP dict
- _validate_api_keys uses startswith() prefix matching for key selection
- Rate limit delays in mutable _rate_delays dict, doubled on 429

### Integration Points
- `api_client.py`: Add _call_openrouter, extend call_model routing, add rate limit exception handling
- `config.py`: Add to MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig fields, OPENROUTER_BASE_URL constant
- `pyproject.toml`: Add openrouter dependency if using dedicated SDK (depends on Claude's SDK choice)
- `.env.example`: Add OPENROUTER_API_KEY
- `pilot.py`: Include OpenRouter model in pilot runs
- `generate_figures.py`: Verify N-model faceting still works with 5th model

</code_context>

<specifics>
## Specific Ideas

- The free tier is primarily for the author's personal development cost savings — not a research constraint. Researchers are free to use any combination of free and paid models across providers
- OpenRouter gives access to models from many providers (Nvidia, Meta, Mistral, etc.) — enables model diversity studies
- Config precedence principle: CLI args > env vars > config file > hardcoded defaults (full implementation deferred to Phase 14, but env var override for OPENROUTER_BASE_URL follows this principle now)

</specifics>

<deferred>
## Deferred Ideas

- **Dynamic model discovery**: Query provider APIs for available models with search/filter, auto-eliminate non-text models (speech-to-text, image generation) — fits Phase 13 (setup wizard) and Phase 14 (CLI config)
- **Provider auto-detection**: Auto-enable/disable providers based on which API keys are configured; minimum 1 target + 1 pre-proc required — fits Phase 13/14
- **Per-run model selection**: CLI-driven enable/disable of models per experiment run — fits Phase 14
- **Full config precedence system**: CLI args > env vars > config file > hardcoded defaults across all config values — fits Phase 14
- **OpenRouter model catalog browsing**: Browse/search OpenRouter's model catalog from CLI, filter by price, capability, context window — fits Phase 13/14
- **Multi-provider model comparison**: Same model via different providers (e.g., Llama via OpenRouter vs. direct) to test proxy latency/result differences — new future phase
- **Free model comparisons**: Use OpenRouter free tier to test 5-10 free models and compare noise sensitivity across architectures — new future phase
- **Model diversity study**: Expand paper's model coverage using OpenRouter's multi-provider access — new future phase

</deferred>

---

*Phase: 09-add-openrouter-support-with-free-model-defaults-nemotron*
*Context gathered: 2026-03-24*
