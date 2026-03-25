# Project Research Summary

**Project:** Configurable Models and Dynamic Pricing (Linguistic Tax v2.0)
**Domain:** Python CLI research toolkit — extending hardcoded model config to dynamic, user-configurable model selection with live pricing
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

This milestone transforms a hardcoded 4-model research toolkit into a flexible, user-configurable system. The core challenge is that six module-level constants in `config.py` (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, and related structures) are imported at module load time across 10+ source files, and must become config-driven without breaking backward compatibility with existing saved configs or the existing test suite. The recommended approach is a `ModelRegistry` pattern: introduce a `ModelConfig` dataclass and `ModelRegistry` class that wrap all per-model lookups, built from config at runtime rather than resolved at import time. Only one new external dependency is needed (`python-dotenv`), and only OpenRouter exposes pricing via API — the other three major providers (Anthropic, Google, OpenAI) require a curated hardcoded fallback table.

The most important design decision is the migration strategy: the new `models: tuple[dict, ...]` field in `ExperimentConfig` must coexist with the existing flat per-provider fields (`claude_model`, `gemini_model`, etc.) so that configs saved by the current version continue to load correctly. Build order is critical — the foundation (ModelConfig, ModelRegistry, env_manager) must be in place before any consumer is updated, with existing tests passing as a gate between phases. The setup wizard requires a heavy rewrite to support free-text model entry, multi-provider flows, and `.env` file creation, but this work is well-defined and all infrastructure is buildable from stdlib plus the one new dependency.

The biggest risk is not the new features themselves but the cross-cutting nature of the change: nine critical pitfalls were identified, most stemming from the same root cause — module-level constants that conflate "models we ship defaults for" with "models that are valid to use." Defensive fallbacks (`compute_cost()` returning $0.00 with a warning for unknown models instead of raising `KeyError`) must land in Phase 1, before any dynamic pricing work, because they are prerequisites for custom models to function at all. Security considerations (API keys in `.env` not `experiment_config.json`, correct file permissions, masked key display) must be addressed in the wizard phase.

## Key Findings

### Recommended Stack

The existing stack requires only one new addition. `python-dotenv>=1.2.0` is the single new dependency — it handles `.env` loading into `os.environ` (so no existing `os.environ.get()` calls need changing) and provides `set_key()` for wizard-side key persistence. All three major LLM SDKs (`anthropic 0.86.0`, `google-genai 1.68.0`, `openai 2.29.0`) already support `client.models.list()` for model discovery. `httpx 0.28.1` is already installed as a transitive dependency and can be used directly for the one HTTP call needed (OpenRouter pricing fetch) — adding `requests` would be redundant.

**Core technologies:**
- `python-dotenv>=1.2.0`: `.env` load/write — de facto standard, zero dependencies, single `load_dotenv()` + `set_key()` API
- `httpx` (transitive, already installed): OpenRouter pricing fetch — avoid adding `requests` when `httpx` is already present
- stdlib `dataclasses`: `ModelConfig` and updated `ExperimentConfig` — project already uses frozen dataclasses throughout; no pydantic needed
- `anthropic 0.86.0` / `google-genai 1.68.0` / `openai 2.29.0` `models.list()`: live model discovery — all stable SDK features, no new installs

**What NOT to add:** `litellm` (50+ transitive deps), `pydantic` (overkill for simple config), `requests` (httpx already available), `dynaconf`/`omegaconf` (complexity for a single JSON config file), `keyring` (over-engineered for a single-researcher CLI).

### Expected Features

**Must have (P1 — this milestone):**
- Config models list structure (`ExperimentConfig` gets `models` field) — keystone on which all other P1 features depend
- Config-driven PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS — derived from config at load time, not hardcoded constants
- Relaxed model validation (warn, not reject) — prerequisite for free-text model entry to be useful
- Free-text model entry in wizard with sensible defaults shown
- Multi-provider wizard flow (configure 1-4 providers iteratively)
- `.env` file creation via python-dotenv for API keys
- Experiment scope adapts to configured models (MODELS derived from config)

**Should have (P2 — same milestone if time permits):**
- Enhanced `propt list-models` with live API queries (model IDs + context windows; pricing NOT available from Anthropic/Google/OpenAI APIs)
- Budget awareness shown at end of wizard (reuses existing `execution_summary.py` infrastructure — low marginal effort)
- Model validation ping at setup (verify model ID + API key work together)

**Defer (v2.x / v3+):**
- OpenRouter live pricing integration — only provider with API-accessible pricing; add when curated fallback table becomes stale
- Model capability filtering in list-models
- Web-scraped pricing for Anthropic/OpenAI/Google — fragile, maintenance burden
- Config migration tool (not needed until a second schema change)

**Critical finding on pricing:** Anthropic, OpenAI, and Google SDKs do NOT return pricing from their `models.list()` endpoints. Only OpenRouter includes `pricing.prompt` and `pricing.completion` in their `/api/v1/models` response. For the other three providers, a curated hardcoded fallback PRICE_TABLE is the only viable pricing source.

### Architecture Approach

The target architecture replaces six parallel hardcoded dicts/tuples in `config.py` with a `ModelRegistry` class built from config at runtime. Two new source files are introduced (`src/pricing_client.py` for per-provider model listing and OpenRouter pricing, `src/env_manager.py` for `.env` I/O), and the existing `ExperimentConfig` frozen dataclass gains a `models: tuple[dict, ...]` field. The backward compatibility strategy — when `models` is empty (default), derive the registry from existing flat fields; when populated, use `models` as source of truth — ensures existing configs continue to work without migration.

**Major components:**
1. `ModelConfig` dataclass + `ModelRegistry` class (in `config.py`) — single source of truth replacing four parallel hardcoded dicts; built from config at runtime, never at import time
2. `src/env_manager.py` (new) — `.env` load/write utilities wrapping python-dotenv; called once at CLI entry point only
3. `src/pricing_client.py` (new) — per-provider model listing; OpenRouter live pricing; hardcoded fallback for Anthropic/Google/OpenAI
4. `setup_wizard.py` (major rewrite) — free-text model entry, multi-provider loop, API key collection with `.env` writing, budget preview
5. `config_manager.py` (modified) — relaxed validation (warn not error); handles new `models` field serialization; backward-compat migration from flat fields

**Key patterns to follow:**
- Registry with fallback defaults: unknown models get $0.00 + logged warning, not a crash
- Backward-compatible config evolution: new structured field alongside existing flat fields; use new when present, fall back to flat fields for old configs
- Provider abstraction in `pricing_client.py`: uniform interface, differing implementations per provider
- Never resolve constants at module import time; always build registry at runtime entry points and pass explicitly

### Critical Pitfalls

1. **Frozen dataclass schema migration breaks existing saved configs** — Add explicit migration: if loaded config has old flat fields but no `models` list, auto-construct `models` from flat fields. Write round-trip tests covering old-format configs. Must be Phase 1's first deliverable.

2. **MODELS tuple used as hard allowlist in 4+ modules** — `pilot.py`, `compute_derived.py`, `setup_wizard.py`, and `config_manager.py` all use `MODELS` as a validation gate. Custom models are accepted at setup but rejected during pilot runs and silently excluded from analysis. Replace with config-driven model list across ALL consumption sites — track as a cross-file checklist, not a single-file change.

3. **`compute_cost()` raises KeyError for unknown models, crashing mid-experiment** — Change to return 0.0 with a logged warning for unknown models instead of raising. This defensive fallback must land in Phase 1, before any dynamic pricing work, because it is a prerequisite for custom models to function.

4. **PREPROC_MODEL_MAP crash during experiment execution, not setup** — Custom target models without a preproc mapping pass setup and `raw`/`self_correct` runs, then crash mid-experiment when hitting a sanitize intervention — potentially after hundreds of successful API calls. The wizard must require explicit target + preproc pairing; `get_preproc_model()` must consult config first.

5. **`.env` loaded with wrong precedence or not loaded at all** — Use `load_dotenv(override=False)` so `.env` fills in missing vars only, never overrides shell-set ones. Call exactly once at the CLI entry point. After writing a key to `.env` in the wizard, also set `os.environ[key] = value` so it is live in the current process.

6. **Module-level constant copies ignore runtime config** — `api_client.py` copies `RATE_LIMIT_DELAYS` at import; `setup_wizard.py` builds `PROVIDERS` dict at import; `pilot.py` builds `_VALID_MODELS` at import. All freeze hardcoded defaults permanently. Replace with functions that read from config or pass config explicitly.

7. **String prefix routing in `api_client.py` breaks for non-standard model IDs** — Store explicit `provider` field alongside model in config; route by provider field, not `model.startswith("claude")`. Keep prefix detection only as a backward-compat fallback.

8. **Pricing API calls block or crash the setup wizard** — Set 5-second timeouts on all pricing API calls, wrap in try/except, fall back to hardcoded table. Write config atomically (build full dict, validate, then write). Never block setup completion on pricing data.

9. **Experiment matrix assumes fixed 4-model count** — Filter matrix items by configured models before execution. Consider generating matrix at runtime from config rather than treating the pre-generated JSON as an immutable artifact.

## Implications for Roadmap

Based on the dependency graph across all four research files, the build order is strictly determined by what must be in place before other components can function and what can change existing behavior. All phases must pass existing tests before proceeding to the next.

### Phase 1: Foundation — Config Schema and Defensive Fallbacks

**Rationale:** All other phases depend on the `ModelConfig`/`ModelRegistry` abstraction and the defensive `compute_cost()` fallback. These must land first and must not change any existing behavior. This phase is the keystone identified in FEATURES.md; pitfalls 1, 2, 3, 4, 7, and 9 all require groundwork here.

**Delivers:** `ModelConfig` dataclass, `ModelRegistry` class with `defaults()` classmethod wrapping current hardcoded values, `models` field added to `ExperimentConfig`, backward-compat migration in `load_config()` (auto-construct `models` from flat fields when `models` is empty), relaxed model validation (warn not error), `compute_cost()` returning 0.0 with warning for unknown models, `src/env_manager.py`, `python-dotenv` added to `pyproject.toml`, `experiment_config.json` added to `.gitignore`.

**Addresses:** Config models list structure (P1 keystone), relaxed model validation (P1), defensive pricing fallback.

**Avoids:** Pitfalls 1 (schema migration), 2 (MODELS allowlist — pattern decided here), 3 (KeyError crash), 4 (PREPROC crash — structure defined), 7 (prefix routing — provider field added to schema), 9 (matrix assumption — model list now config-driven).

**Test gate:** All existing tests pass. `ModelRegistry.defaults()` returns identical data to current hardcoded dicts. Round-trip test: save old-format config, load with new code, assert no data loss. `compute_cost("novel-model-xyz", 1000, 500)` returns 0.0 with a warning log.

### Phase 2: Registry Consumers — Swap Imports to Registry

**Rationale:** Once the registry exists (Phase 1), consumers can be updated one by one without changing behavior. This is the lowest-risk phase — identical outputs, better structure. Must complete before Phase 4 (the wizard needs consumers ready to accept registry instances).

**Delivers:** `prompt_compressor.py`, `execution_summary.py`, `api_client.py`, and `run_experiment.py` updated to accept registry parameter. Standalone `compute_cost()` kept with deprecation warning for backward compat. Module-level constant copies (`_rate_delays`, etc.) replaced with registry lookups.

**Addresses:** Config-driven PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, PRICE_TABLE (wired into consumers).

**Avoids:** Pitfall 6 (module-level stale constants resolved for all consumer modules in this phase).

**Test gate:** All existing tests pass. Behavior identical to Phase 1. Custom model name through the sanitize intervention pipeline does not raise ValueError.

### Phase 3: Pricing Client — Live Model Discovery

**Rationale:** Independent of Phase 2 (no shared dependencies), but benefits from the registry being in place. Enables the `propt list-models` enhancement and the budget preview needed in the wizard (Phase 4). All pricing fetches must include defensive fallbacks from the first line of code.

**Delivers:** `src/pricing_client.py` with per-provider `list_models()` and `fetch_pricing()`. OpenRouter live pricing (the only provider that exposes it via API — others return model IDs only). Hardcoded fallback for Anthropic/Google/OpenAI. Updated `config_commands.py` `handle_list_models()`.

**Addresses:** Enhanced `propt list-models` (P2), OpenRouter pricing groundwork for v2.x.

**Avoids:** Pitfall 8 (pricing API failures — all calls have 5s timeout + try/except + fallback; config written atomically).

**Test gate:** `propt list-models` shows live model availability from provider APIs. Mocked timeout responses fall back gracefully to hardcoded prices with a clear warning message.

### Phase 4: Setup Wizard Overhaul — User-Facing Changes

**Rationale:** Depends on Phases 1 (registry and env_manager), 2 (consumers ready), and 3 (pricing client for budget preview). The wizard is the heaviest rewrite and the most user-visible change. Security requirements — API keys in `.env` not in config JSON, correct `.env` file permissions, masked key display — must be addressed here.

**Delivers:** Free-text model entry with defaults shown, multi-provider loop (1-4 providers), API key collection writing to `.env` via `env_manager`, model validation ping, budget preview using existing `execution_summary.py` infrastructure, explanatory text for target vs. preproc model distinction. `cli.py` updated to call `env_manager.load_dotenv()` at startup with `override=False`.

**Addresses:** Free-text model entry (P1), multi-provider wizard flow (P1), `.env` file creation (P1), budget awareness (P2), model validation ping (P2), target/preproc explanation text.

**Avoids:** Pitfall 5 (`.env` precedence — `override=False`, called once at entry point, key also set in current process). Security pitfalls (keys only in `.env`, never in config JSON; `chmod 0o600` on `.env`; masked key display; `experiment_config.json` in `.gitignore`).

**Test gate:** Full wizard flow works with free-text model names not in hardcoded defaults. `.env` created with correct permissions (0o600). `propt run` works after fresh `.env` creation in a new shell session (not just during wizard session). Setting a key in shell env and running wizard does not overwrite it.

### Phase 5: Experiment Scope Adaptation — Matrix and Pilot

**Rationale:** Final phase; depends on Phase 2 (registry consumers) and Phase 4 (wizard populates models config). Lowest risk since the registry infrastructure is already in place; this phase wires up the entry points that iterate over configured models.

**Delivers:** `scripts/generate_matrix.py`, `pilot.py`, `compute_derived.py` use `registry.get_models()` instead of `MODELS` tuple. `cli.py --model flag` accepts configured provider names dynamically. Matrix filtered to configured models before execution.

**Addresses:** Experiment scope adapts to config (P1 — final wiring), dynamic model list in compute_derived and pilot.

**Avoids:** Pitfall 9 (matrix assumes 4 models — now filtered to configured models). Remaining instances of pitfall 2 (MODELS as allowlist in `pilot.py` and `compute_derived.py`).

**Test gate:** Matrix generation adapts to 1, 2, and 4 configured providers. Pilot runs with subset of providers without "Unknown model" errors. Analysis output contains exactly the configured models, no more.

### Phase Ordering Rationale

- Phases 1 and 2 are zero-risk (new code paths, identical behavior); Phase 1 must come first because all later phases depend on the registry abstraction
- Phase 3 is independent of Phase 2 but is sequenced third because the wizard (Phase 4) needs the pricing client for budget preview
- Phase 4 is sequenced after 1, 2, and 3 because it needs all infrastructure in place and carries the most security requirements
- Phase 5 is last because it depends on the wizard (Phase 4) having populated the `models` config field
- This ordering mirrors the "Suggested Build Order" in ARCHITECTURE.md and the "Phase to address" annotations in PITFALLS.md, with no contradictions between the two

### Research Flags

Phases with well-documented patterns (standard implementation, skip deeper research):
- **Phase 1 (Foundation):** Frozen dataclass extension and backward-compat migration are well-documented Python patterns. The specific fields, types, and migration logic are fully specified in ARCHITECTURE.md and PITFALLS.md.
- **Phase 2 (Registry Consumers):** Mechanical parameter threading. No open design decisions.
- **Phase 5 (Scope Adaptation):** Straightforward wiring once Phases 1-4 are complete.

Phases that may benefit from targeted research during planning:
- **Phase 3 (Pricing Client):** OpenRouter `/api/v1/models` response schema is noted as MEDIUM confidence in ARCHITECTURE.md (sourced from training data, not verified live during research). Verify the exact `pricing.prompt`/`pricing.completion` field structure and units (per-token strings vs. per-1M floats) against a live call before writing the parser.
- **Phase 4 (Wizard):** Two python-dotenv edge cases need verification against the actual installed version: (1) does `set_key()` create the `.env` file if it does not exist? (2) what exactly happens when `override=False` and a key is already in `os.environ`? Verify these before writing the wizard.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All SDK fields verified via live introspection of installed packages. python-dotenv behavior verified. Only one MEDIUM finding: OpenRouter pricing schema from training data, not a live call. |
| Features | HIGH | Derived from direct codebase analysis (grep for all MODELS importers, field introspection of all three SDKs). Priority ordering is clear from dependency graph. |
| Architecture | HIGH | Component boundaries and data flow derived from reading all source files. Build order validated against pitfall analysis — no contradictions. |
| Pitfalls | HIGH | All 9 pitfalls are grounded in specific line numbers in the existing codebase. Not speculative. |

**Overall confidence:** HIGH

### Gaps to Address

- **OpenRouter pricing schema:** Noted as MEDIUM confidence (training data, not verified live). Before writing `pricing_client.py`, make a single live HTTP call to `https://openrouter.ai/api/v1/models` and verify `pricing.prompt` / `pricing.completion` field structure and units.
- **python-dotenv `set_key()` on a missing `.env` file:** Verify whether it creates the file automatically and what the default permissions are. Affects wizard implementation in Phase 4.
- **`experiment_config.json` in `.gitignore`:** PITFALLS.md notes it is NOT currently gitignored. This is a security gap — it does not store API keys today, but add it to `.gitignore` during Phase 1 as a precaution.

## Sources

### Primary (HIGH confidence)
- Anthropic SDK v0.86.0 — `ModelInfo` field verification via `anthropic.types.ModelInfo.model_json_schema()`: `id`, `display_name`, `created_at`, `max_tokens`, `max_input_tokens`, `capabilities`. No pricing fields.
- Google genai SDK v1.68.0 — `Model` field verification via `types.Model.model_json_schema()`: `name`, `displayName`, `inputTokenLimit`, `outputTokenLimit`. No pricing fields.
- OpenAI SDK v2.29.0 — `models.list()` verified via `dir(client.models)`: `id`, `created`, `object`, `owned_by`. No pricing fields.
- python-dotenv 1.2.2 — confirmed available via `uv pip install --dry-run python-dotenv`
- httpx 0.28.1 — confirmed installed as transitive dependency via `uv pip show httpx`
- Direct codebase analysis — all 10 source files that import model constants, specific line numbers for each pitfall

### Secondary (MEDIUM confidence)
- OpenRouter `/api/v1/models` endpoint — returns `pricing.prompt` and `pricing.completion` per-token strings. Verified via live HTTP call per STACK.md; noted as training-data source in ARCHITECTURE.md. Treat as MEDIUM until confirmed during Phase 3 implementation.

### Tertiary (LOW confidence)
- None identified. All research findings are grounded in either live SDK introspection or direct source code analysis.

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
