# Feature Research

**Domain:** Configurable model registry, dynamic pricing, and .env management for a Python CLI research toolkit
**Researched:** 2026-03-25
**Confidence:** HIGH (based on direct SDK introspection of installed packages + codebase analysis)

## Feature Landscape

### Table Stakes (Users Expect These)

Features the milestone explicitly requires. Missing any = milestone incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Free-text model entry in wizard | Users need arbitrary model IDs (new releases, fine-tunes) | LOW | Replace numbered-list-only selection with default suggestion + free-text fallback. Current wizard already handles `preproc_choice.strip()` free-text for preproc model (line 246-247 of setup_wizard.py) -- extend same pattern to target model. |
| Config-driven PRICE_TABLE | Hardcoded dict rejects unknown models and cannot be updated without code changes | MEDIUM | Move from module-level constant to a function `get_price_table(config)` that merges hardcoded fallbacks with config-stored per-model pricing. `compute_cost()` must use this instead of bare `PRICE_TABLE[model]`. |
| Config-driven PREPROC_MODEL_MAP | Currently 4 hardcoded entries; adding a model requires code change | LOW | Derive from config's `models` list where each entry pairs target + preproc. Fallback: if model not in map, warn and skip preproc interventions. |
| Config-driven RATE_LIMIT_DELAYS | Same hardcoding problem | LOW | Store per-model delay in config. Default 0.5s for unknown models (already used as fallback in execution_summary.py line 172). |
| Relaxed model validation | `validate_config()` currently rejects models not in PRICE_TABLE -- this blocks any new model | LOW | Change from error to warning. Models not in PRICE_TABLE get $0.00 pricing with logged warning. Critical: do NOT silently swallow -- warn so users know cost estimates are missing. |
| .env file creation for API keys | Wizard currently tells users to "set env var" but does not help them do it | MEDIUM | Use `python-dotenv` `set_key()` to write/update `.env`. Load with `load_dotenv()` at CLI entry point. `.env` already in `.gitignore`. Requires adding `python-dotenv>=1.0.0` to dependencies. |
| Multi-provider wizard flow | Current wizard selects one provider; milestone requires configuring 1-4 providers | MEDIUM | After first provider, loop: "Add another provider? (y/n)". Track configured providers. Max 4 (one per provider). Each iteration: pick provider, enter target model, enter preproc model, validate API key. |
| Experiment scope adapts to config | Currently assumes all 4 providers/models exist. MODELS tuple is hardcoded. | MEDIUM | `MODELS` tuple must be derived from config at load time. `pilot.py` and `compute_derived.py` import MODELS directly -- these need to accept config-derived model lists. |
| Enhanced `propt list-models` | Currently shows static PRICE_TABLE. Users need to discover available models. | MEDIUM | Query each provider's `models.list()` API. All 3 SDKs (anthropic, openai, google-genai) support `client.models.list()`. OpenRouter uses OpenAI-compatible endpoint. Show model ID, display name, context window. Pricing NOT available from most APIs (see Differentiators). |

### Differentiators (Competitive Advantage)

Features that go beyond the minimum. The context document confirms these were "additional features (confirmed by user)."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live pricing from provider APIs | Saves manual price-table maintenance; catches price drops | HIGH | **Critical finding: Anthropic, OpenAI, and Google SDKs do NOT return pricing data from their models endpoints.** Anthropic `ModelInfo` fields: `id, capabilities, created_at, display_name, max_input_tokens, max_tokens, type`. OpenAI `Model` fields: `id, created, object, owned_by`. Google `Model` fields: `name, display_name, description, input_token_limit, output_token_limit, ...`. Only OpenRouter includes pricing in their `/api/v1/models` response (non-standard extension). Mitigation: use curated fallback table and accept user overrides during setup. |
| Budget awareness at setup time | Shows estimated experiment cost BEFORE committing. Prevents $50 surprise bills. | LOW | Already have `execution_summary.py` with cost estimation. Wire it into wizard as a final confirmation step using the configured models' pricing. Low complexity because infrastructure exists. |
| Model validation ping at setup | Verifies model ID + API key work together. Catches typos in model names immediately. | LOW | Current `validate_api_key()` uses hardcoded cheap models. Change to ping the actual selected model with `max_tokens=1`. If it fails, warn but allow (model might not support tiny requests). |
| Target vs preproc explanation in wizard | Users unfamiliar with the experiment design need context | LOW | Add 2-3 line explanation before each model prompt. "Target model: the LLM being tested for accuracy. Pre-processor model: a cheaper LLM used to clean/compress prompts before sending to the target." Pure text, no code complexity. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-discover ALL available models from APIs | Seems convenient to list every model | Model lists are huge (OpenAI returns 50+, OpenRouter returns 300+). Most are irrelevant (embedding models, image models, deprecated models). Filtering is complex and provider-specific. | Show curated defaults per provider. Allow free-text entry. `propt list-models --provider X` queries live but filters to chat/completion models only. |
| Persist API keys in config JSON | Single file for all config seems simpler | API keys in JSON risk accidental git commits. JSON lacks the `.env` ecosystem tooling (docker-compose, shell sourcing, CI/CD). | Use `.env` file (already gitignored) with `python-dotenv`. Config JSON stores model choices only, never secrets. |
| Real-time pricing updates during experiment runs | Ensures cost tracking uses latest prices | Adds network calls in the hot path. Pricing rarely changes mid-experiment. Adds failure mode if pricing endpoint is down. | Fetch pricing once at setup/config time. Cache in config. Use cached values during runs. |
| Support unlimited providers/models | Why limit to 4? | Experiment design assumes cross-provider comparison with bounded matrix. More models = combinatorial explosion of experiment runs. Each model adds ~5000 API calls to the full matrix. | Cap at 4 providers (one model per provider) per the experiment design. Document why in wizard. |
| Automatic model version pinning (resolve "claude-sonnet-4" to "claude-sonnet-4-20250514") | Prevents version drift | Not all providers support version aliases. Resolution logic differs per provider. Creates hidden behavior that hurts reproducibility -- user should see exactly what they typed. | Accept whatever the user types. Log the exact model ID returned in API responses for auditing. |

## Feature Dependencies

```
[.env management (python-dotenv)]
    └──enables──> [Wizard API key collection]
                      └──enables──> [Model validation ping]
                                        └──enables──> [Live model listing]

[Config-driven PRICE_TABLE]
    └──enables──> [Budget awareness at setup]
    └──enables──> [Relaxed model validation]

[Config models list structure]
    └──enables──> [Config-driven PREPROC_MODEL_MAP]
    └──enables──> [Config-driven RATE_LIMIT_DELAYS]
    └──enables──> [Experiment scope adapts to config]
    └──enables──> [Multi-provider wizard flow]

[Free-text model entry] ──requires──> [Relaxed model validation]

[Enhanced propt list-models] ──requires──> [API key available in env]
```

### Dependency Notes

- **Free-text model entry requires relaxed validation:** If validation still rejects unknown models, free-text is useless. Must relax validation BEFORE or simultaneously with free-text entry.
- **Config models list is the keystone:** PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, experiment scope, and the wizard all depend on the new config structure. Build this first.
- **python-dotenv must be added as dependency:** Required before .env features work. This is the only new external dependency needed.
- **Budget awareness at setup reuses execution_summary.py:** Low marginal effort once pricing is config-driven.
- **Live model listing requires valid API keys in environment:** The `models.list()` calls need authentication. Must load .env before attempting.

## MVP Definition

### Launch With (this milestone)

- [ ] Config models list structure (ExperimentConfig gets `models` list field) -- keystone dependency
- [ ] Config-driven PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS -- derived from config at load time
- [ ] Relaxed model validation (warn, not reject) -- unblocks free-text
- [ ] Free-text model entry in wizard with sensible defaults shown
- [ ] Multi-provider wizard flow (configure 1-4 providers iteratively)
- [ ] .env file creation via python-dotenv for API keys
- [ ] Experiment scope adapts to configured models (MODELS derived from config)
- [ ] Enhanced `propt list-models` with live API queries (model IDs + context windows, NOT pricing)
- [ ] Budget awareness shown at end of wizard using existing execution_summary infrastructure

### Add After Validation (v2.x)

- [ ] OpenRouter pricing integration -- only provider with API-accessible pricing. Add when other providers catch up or if curated table becomes stale.
- [ ] Model capability filtering in list-models -- filter by supports_chat, supports_tools, etc. using Anthropic `ModelCapabilities` and Google `supported_actions` fields.

### Future Consideration (v3+)

- [ ] Web-scraped pricing for Anthropic/OpenAI/Google -- fragile, maintenance burden, defer until there is a real need beyond the hardcoded fallback table.
- [ ] Config migration tool -- if config schema changes again, auto-migrate old configs. Not needed until there is a second schema change.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Depends On |
|---------|------------|---------------------|----------|------------|
| Config models list structure | HIGH | MEDIUM | P1 | Nothing (keystone) |
| Config-driven PRICE_TABLE | HIGH | MEDIUM | P1 | Config models list |
| Config-driven PREPROC_MODEL_MAP | HIGH | LOW | P1 | Config models list |
| Config-driven RATE_LIMIT_DELAYS | MEDIUM | LOW | P1 | Config models list |
| Relaxed model validation | HIGH | LOW | P1 | Config-driven PRICE_TABLE |
| Free-text model entry | HIGH | LOW | P1 | Relaxed validation |
| .env file creation | HIGH | MEDIUM | P1 | python-dotenv dependency |
| Multi-provider wizard flow | HIGH | MEDIUM | P1 | Config models list, .env |
| Experiment scope adapts | HIGH | MEDIUM | P1 | Config models list |
| Target/preproc explanation text | MEDIUM | LOW | P1 | Nothing |
| Enhanced propt list-models | MEDIUM | MEDIUM | P2 | .env loaded, API keys |
| Budget awareness at setup | MEDIUM | LOW | P2 | Config-driven PRICE_TABLE |
| Model validation ping | MEDIUM | LOW | P2 | .env loaded, API keys |
| Live pricing (OpenRouter only) | LOW | MEDIUM | P3 | Enhanced list-models |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add in same milestone if time permits
- P3: Nice to have, defer to future

## Refactoring Surface Analysis

Files that import hardcoded constants and need updates:

| File | Imports | Change Required |
|------|---------|-----------------|
| `src/config.py` | Defines PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, MODELS | Keep as fallback defaults. Add functions to derive from config. |
| `src/config_manager.py` | PRICE_TABLE for validation | Change validation to warn-only for unknown models |
| `src/setup_wizard.py` | MODELS, PREPROC_MODEL_MAP | Derive from config; add multi-provider flow, .env writing |
| `src/api_client.py` | RATE_LIMIT_DELAYS | Accept config-derived delays or fall back to defaults |
| `src/run_experiment.py` | PREPROC_MODEL_MAP, PRICE_TABLE | Use config-derived versions |
| `src/execution_summary.py` | PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS | Use config-derived versions |
| `src/prompt_compressor.py` | PREPROC_MODEL_MAP | Use config-derived version; change ValueError to warning for unknown models |
| `src/config_commands.py` | PRICE_TABLE | Use config-derived version for list-models |
| `src/pilot.py` | MODELS | Derive from config |
| `src/compute_derived.py` | MODELS | Derive from config |
| `src/cli.py` | INTERVENTIONS (no change needed) | Add `load_dotenv()` call at entry point |

## Provider API Capabilities (Verified via SDK Introspection)

What each provider's `models.list()` actually returns:

| Provider | SDK | List Models? | Fields Available | Pricing in API? |
|----------|-----|-------------|------------------|-----------------|
| Anthropic | anthropic 0.84.0 | Yes, `client.models.list()` | id, display_name, capabilities, max_input_tokens, max_tokens, created_at | **NO** |
| Google | google-genai 1.45.0 | Yes, `client.models.list()` | name, display_name, description, input_token_limit, output_token_limit, supported_actions, temperature, thinking | **NO** |
| OpenAI | openai 2.29.0 | Yes, `client.models.list()` | id, created, owned_by | **NO** (minimal metadata) |
| OpenRouter | openai 2.29.0 (custom base_url) | Yes, via `/api/v1/models` | id, pricing (prompt/completion per token), context_length, top_provider | **YES** (non-standard extension) |

**Implication:** "Dynamic pricing from provider APIs" is only feasible for OpenRouter. For Anthropic, Google, and OpenAI, pricing must come from a curated fallback table or user input. This is the single most important finding for implementation planning.

## Sources

- Anthropic SDK v0.84.0 `ModelInfo` type: fields are `id, capabilities, created_at, display_name, max_input_tokens, max_tokens, type` (verified via `anthropic.types.ModelInfo.model_fields.keys()`)
- OpenAI SDK v2.29.0 `Model` type: fields are `id, created, object, owned_by` (verified via `openai.types.Model.model_fields.keys()`)
- Google GenAI SDK v1.45.0 `Model` type: fields include `name, display_name, description, input_token_limit, output_token_limit, supported_actions` (verified via `google.genai.types.Model.model_fields.keys()`)
- python-dotenv v1.1.1 is available in system but NOT in project dependencies (needs adding to pyproject.toml)
- `.env` already in `.gitignore` (line 13)
- Current codebase: 10 source files import hardcoded model constants (verified via grep)

---
*Feature research for: Configurable Models and Dynamic Pricing milestone*
*Researched: 2026-03-25*
