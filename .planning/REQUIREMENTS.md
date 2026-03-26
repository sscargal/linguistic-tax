# Requirements: Linguistic Tax

**Defined:** 2026-03-25
**Core Value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it

## v2.0 Requirements

Requirements for configurable models and dynamic pricing. Each maps to roadmap phases.

### Configuration

- [x] **CFG-01**: User can configure target and pre-processor models per provider via a `models` list in ExperimentConfig
- [x] **CFG-02**: PRICE_TABLE, PREPROC_MODEL_MAP, and RATE_LIMIT_DELAYS are derived from config at load time, not hardcoded
- [x] **CFG-03**: `compute_cost()` falls back to $0.00 with a warning for models not in the price table (no crash)
- [x] **CFG-04**: `validate_config()` warns instead of rejecting unknown model IDs
- [x] **CFG-05**: Old flat-field configs (claude_model, gemini_model, etc.) automatically migrate to the new models list format on load

### Model Discovery

- [x] **DSC-01**: `propt list-models` queries live models from each configured provider's API
- [x] **DSC-02**: `propt list-models` displays model ID, context window, and pricing (where available from provider)
- [ ] **DSC-03**: User can enter any model ID as free text during setup (not limited to a hardcoded list)

### Setup Wizard

- [ ] **WIZ-01**: Setup wizard explains what "target model" and "pre-processor model" mean in the experiment context
- [ ] **WIZ-02**: User can configure 1-4 providers in a single setup session (multi-provider loop)
- [ ] **WIZ-03**: User can enter custom model IDs via free text with sensible defaults shown
- [ ] **WIZ-04**: Wizard creates/updates `.env` file when user provides API keys
- [ ] **WIZ-05**: Wizard shows estimated experiment cost based on selected models' pricing before completing setup
- [ ] **WIZ-06**: Wizard validates each selected model by pinging the provider API with a tiny request

### Pricing

- [x] **PRC-01**: Curated fallback price table provides pricing for known models when no API pricing is available
- [x] **PRC-02**: OpenRouter live pricing is fetched via its `/api/v1/models` endpoint
- [x] **PRC-03**: Unknown models default to $0.00 pricing with a user-visible warning

### Experiment Scope

- [x] **EXP-01**: Experiment matrix generation uses configured models (not hardcoded MODELS tuple)
- [x] **EXP-02**: `--model` flag on `propt run` works with any configured model
- [x] **EXP-03**: Pilot run adapts to configured models (runs only configured providers)
- [x] **EXP-04**: Derived metrics computation adapts to configured models

## v1.0 Requirements (Validated)

All v1.0 requirements validated and shipped. See PROJECT.md Validated section for full list.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live pricing from Anthropic/Google/OpenAI APIs | These providers do not expose pricing via their SDKs — only model IDs and capabilities |
| Custom provider plugins | Beyond 4 built-in providers; would over-engineer for a research toolkit |
| Web-based model browser | CLI-only research tool — `propt list-models` suffices |
| Automatic model version updates | Pinned versions are essential for reproducibility |
| Multi-user .env management | Single-researcher tool; one .env file at project root |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 16 | Complete |
| CFG-02 | Phase 16 | Complete |
| CFG-03 | Phase 16 | Complete |
| CFG-04 | Phase 16 | Complete |
| CFG-05 | Phase 16 | Complete |
| DSC-01 | Phase 18 | Complete |
| DSC-02 | Phase 18 | Complete |
| DSC-03 | Phase 19 | Pending |
| WIZ-01 | Phase 19 | Pending |
| WIZ-02 | Phase 19 | Pending |
| WIZ-03 | Phase 19 | Pending |
| WIZ-04 | Phase 19 | Pending |
| WIZ-05 | Phase 19 | Pending |
| WIZ-06 | Phase 19 | Pending |
| PRC-01 | Phase 16 | Complete |
| PRC-02 | Phase 18 | Complete |
| PRC-03 | Phase 16 | Complete |
| EXP-01 | Phase 17 | Complete |
| EXP-02 | Phase 17 | Complete |
| EXP-03 | Phase 17 | Complete |
| EXP-04 | Phase 17 | Complete |

**Coverage:**
- v2.0 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after roadmap creation*
