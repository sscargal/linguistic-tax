# Quick Task 260325-tx5: Make models fully configurable with dynamic pricing and flexible setup wizard - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Task Boundary

Make models fully configurable: setup wizard allows free-text model entry with sensible defaults, pulls latest pricing from provider APIs, stores target+preproc models in config. Remove hardcoded model validation that rejects unknown models. Fall back gracefully for unknown model pricing. Update PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS to be config-driven not code-driven.

</domain>

<decisions>
## Implementation Decisions

### Pricing Source
- **Per-provider APIs**: Query each provider's own pricing/models API (Anthropic, Google, OpenAI, OpenRouter) during setup and for `propt list-models`.
- Keep current PRICE_TABLE values as offline/fallback defaults.
- When a model isn't in the price table and can't be fetched, fall back to $0.00 with a warning.

### Wizard Flow
- **Single provider as minimum**: Keep the current pick-one-provider flow as the starting point.
- After configuring the first provider (target + preproc), offer to add more providers/models for comparison. Walk through each additional provider step-by-step.
- **Maximum 4 model configurations** (one per provider, matching the experiment design).
- Add clear descriptions explaining what "target model" vs "pre-processor model" means in the experiment context.
- Allow **free-text model entry** — show defaults but accept any model ID.
- **API key handling**: If the API key env var is not set, ask for it and store in `.env` file.
- **Experiment scope adapts to config**: Tests/experiments run based on the number of providers and models actually configured, not all 4.

### Config Structure
- **Extend ExperimentConfig**: Add a `models` list field where each entry holds provider, target_model, preproc_model, and pricing info.
- `PRICE_TABLE`, `PREPROC_MODEL_MAP`, and `RATE_LIMIT_DELAYS` become **derived from config at load time** rather than hardcoded constants.
- Keep current flat fields (claude_model, gemini_model, etc.) for backward compatibility during transition, but the `models` list is the source of truth.
- `MODELS` tuple used throughout the codebase should be derived from the config's models list.

### Additional Features (confirmed by user)
- **Model validation at setup**: Ping selected model with a tiny request to verify it exists and API key works (extend current behavior to custom models).
- **Enhanced `propt list-models`**: Query live models from provider APIs, not just show the hardcoded table. Show pricing, availability.
- **Budget awareness at setup**: Show estimated experiment cost based on selected models' pricing during setup, so users know the cost before committing.

</decisions>

<specifics>
## Specific Ideas

- The `.env` file should be created/updated when users provide API keys during setup
- Current `validate_config()` rejects unknown models — must change to warn-only for models not in PRICE_TABLE
- `PROVIDERS` dict in setup_wizard.py currently builds model lists from hardcoded `MODELS` tuple — needs to show defaults but allow free entry
- Experiment matrix generation must adapt to configured models (not assume all 4 providers)
- `--model` flag on `propt run` should work with whatever models are configured

</specifics>

<canonical_refs>
## Canonical References

- `src/config.py` — ExperimentConfig, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS
- `src/config_manager.py` — load_config, save_config, validate_config
- `src/setup_wizard.py` — PROVIDERS, run_setup_wizard
- `docs/RDD_Linguistic_Tax_v4.md` — Research Design Document (experiment spec)

</canonical_refs>
