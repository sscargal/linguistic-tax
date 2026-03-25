# Phase 16: Config Schema and Defensive Fallbacks - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace hardcoded model constants (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) with a config-driven ModelConfig/ModelRegistry system. Add backward-compatible migration for old flat-field configs, make cost computation defensive for unknown models, and add .env file management via python-dotenv. Old module-level constants are removed entirely (no backward-compat aliases — no users to break).

</domain>

<decisions>
## Implementation Decisions

### Config file format
- Models represented as a **list of self-contained model objects** in the config JSON
- Each model entry carries: model_id, provider, role, preproc_model_id (if target), input_price_per_1m, output_price_per_1m, rate_limit_delay
- Preproc models are **separate entries** in the models list (role: "preproc"), not nested inside target models
- All 8 models (4 targets + 4 preproc) listed explicitly in the default config — nothing hidden
- Provider field is **explicit** (provider: "anthropic" | "google" | "openai" | "openrouter") — no string inference from model_id
- Provider is a free string (no enum enforcement) — validation warns on unknown providers but accepts them
- Add **config_version: 2** field for programmatic format detection
- Default config **ships with the project** pre-populated with all 8 models — wizard can override but config works out of the box
- Unknown property values use **null in JSON / None in Python** — explicit distinction between "free" (0.0) and "unknown" (null). Code applies sensible defaults (0.0 for pricing, 0.5s for delay) when None

### Internal Python representation
- New **ModelConfig dataclass** (mutable, not frozen) with fields matching the JSON model object
- New **ModelRegistry class** in a dedicated `src/model_registry.py` file — provides get_price(), get_preproc(), get_delay(), target_models(), compute_cost() methods
- Registry is a **module-level singleton** created at import time from loaded config
- compute_cost() moves to a **method on ModelRegistry** (not standalone function)
- **ExperimentConfig becomes mutable** (remove frozen=True) — wizard can build and modify incrementally
- Old flat fields (claude_model, gemini_model, openai_model, openrouter_model, openrouter_preproc_model) **stripped entirely** from ExperimentConfig
- Old module-level constants (PRICE_TABLE, MODELS, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) **removed entirely** — no backward-compat aliases
- Tests use **new API only** (get_price, get_preproc, etc.) — no dict-style access properties on registry

### Default models source of truth
- **data/default_models.json** — a separate JSON file with complete model entries (all 8 models, full pricing, delays, preproc mappings, roles, providers)
- Used by migration (populate pricing from defaults) and by "no config" path
- This is the single source of truth for curated model defaults

### Migration strategy
- **Auto-migrate on load**: load_config() detects old v1.0 format (flat fields, no models list) and converts to new format
- Creates **.bak backup** of old config before rewriting
- Populates **pricing/delays from defaults** (data/default_models.json) — migrated config is immediately functional
- Old flat fields **stripped entirely** from ExperimentConfig — migration converts them to models list entries
- **config_version field** added for format detection: no version = v1, version 2 = current
- **Config diff on migration**: log a clear diff showing what changed (old fields to new models list)
- Sweep codebase for any old-format config files and update them (TODO if needed)

### Fallback behavior
- compute_cost() returns **$0.00 with warning** for unknown models (no crash)
- Warning logged **once per unknown model** — subsequent calls silent (avoid log flooding during experiment runs)
- validate_config() **warns but accepts** unknown model IDs (CFG-04) — logs warning, suggests `propt list-models`
- Unknown models **allowed to run experiments** — if provider is valid, API call goes through or fails naturally
- Missing preproc model (referenced but not in config): **auto-add with defaults** ($0.00 pricing, 0.5s delay)

### env_manager
- New module: `src/env_manager.py` with three capabilities: load_env(), write_env(), check_keys()
- .env file at **project root only** — not configurable
- **Auto-load during load_config()** — load_env() called first so API keys are always available
- Set **chmod 600** on .env file when creating or writing (owner-only read/write)
- No .env.example template — docs and wizard handle key guidance
- Provider-to-API-key mapping **hardcoded** in env_manager: {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}

### Additional capabilities (from brainstorm)
- **registry.reload()** method — allows wizard to update registry after config changes without restarting Python
- **Provider health check**: registry.check_provider(provider) verifies API key exists and optionally pings the API (groundwork for Phase 19's model validation)

### Claude's Discretion
- Internal implementation details of ModelRegistry (data structures, caching)
- Exact warning message wording
- Test organization and test helper utilities
- Order of migration steps within load_config()

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specification
- `docs/RDD_Linguistic_Tax_v4.md` — Research Design Document defining all experimental parameters, model requirements, and reproducibility constraints

### Requirements
- `.planning/REQUIREMENTS.md` — v2.0 requirements CFG-01 through CFG-05, PRC-01, PRC-03 (all mapped to Phase 16)

### Current implementation
- `src/config.py` — Current hardcoded constants (PRICE_TABLE, MODELS, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, ExperimentConfig, compute_cost)
- `src/config_manager.py` — Current load_config(), validate_config(), save_config() with hardcoded model validation
- `src/api_client.py` — Uses RATE_LIMIT_DELAYS, needs to switch to registry
- `src/execution_summary.py` — Imports PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS
- `src/prompt_compressor.py` — Imports PREPROC_MODEL_MAP with strict validation
- `src/setup_wizard.py` — Imports MODELS, PREPROC_MODEL_MAP
- `src/pilot.py` — Uses MODELS for _VALID_MODELS set
- `src/config_commands.py` — Uses PRICE_TABLE for list-models display
- `src/run_experiment.py` — Imports PREPROC_MODEL_MAP

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExperimentConfig` dataclass in config.py — will be modified (unfrozen, flat fields removed, models list added)
- `config_manager.py` load_config/validate_config/save_config — migration logic hooks into load_config
- `derive_seed()` in config.py — unchanged, stays as-is
- NOISE_TYPES, INTERVENTIONS constants — unchanged, stay in config.py

### Established Patterns
- Frozen dataclass for config (will change to mutable)
- Module-level constants imported directly (will change to registry)
- JSON config file at project root (stays, format changes)
- python logging module for all output (env_manager and registry follow this)

### Integration Points
- `load_config()` in config_manager.py — entry point for migration and env loading
- Module-level imports of PRICE_TABLE/MODELS/etc. in 8+ files — all need updating (Phase 17 scope, but registry must be ready)
- `compute_cost()` currently standalone in config.py — moves to ModelRegistry method
- `experiment_config.json` — file format changes with config_version field

</code_context>

<specifics>
## Specific Ideas

- Config file format should be user-friendly: self-contained model objects where you can copy/paste a block to add a new model
- Wizard behavior with existing configs (delete/backup/update options) is Phase 19 scope — noted for that phase
- null/None distinction is important: 0.0 = free model, null = unknown pricing
- No .env.example — wizard and docs handle key guidance directly

</specifics>

<deferred>
## Deferred Ideas

- **Wizard config file handling** (Phase 19): When config exists, wizard should ask: delete and start over, backup and create new, update existing, or cancel
- **Consumer migration** (Phase 17): Swap all hardcoded imports to registry lookups across 8+ consumer modules
- **Live pricing from OpenRouter API** (Phase 18): Fetch real pricing via /api/v1/models endpoint

</deferred>

---

*Phase: 16-config-schema-and-defensive-fallbacks*
*Context gathered: 2026-03-25*
