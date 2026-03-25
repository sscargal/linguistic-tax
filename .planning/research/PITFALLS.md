# Pitfalls Research

**Domain:** Adding configurable models, dynamic pricing, and .env management to an existing frozen-dataclass Python CLI research toolkit
**Researched:** 2026-03-25
**Confidence:** HIGH (based on direct codebase analysis of all affected modules)

## Critical Pitfalls

### Pitfall 1: Frozen Dataclass Schema Migration Breaks Existing Saved Configs

**What goes wrong:**
`ExperimentConfig` is `frozen=True` with flat per-provider fields (`claude_model`, `gemini_model`, `openai_model`, `openrouter_model`, `openrouter_preproc_model`). The plan adds a `models` list field containing dicts. But `load_config()` in `config_manager.py` lines 62-72 filters JSON keys to `fields(ExperimentConfig)` names and has tuple coercion logic that checks `isinstance(getattr(defaults, field.name), tuple)`. If the new `models` field is typed as `tuple[dict, ...]`, the coercion will tuple-ify it correctly, but if typed as `list[dict]`, it will be left as-is inside a frozen dataclass (type mismatch). More critically: existing `experiment_config.json` files saved by the current version lack the `models` key entirely. If old flat fields are removed or ignored in favor of `models`, those configs silently lose the user's model selections and fall back to defaults.

**Why it happens:**
The load path was designed for flat scalar/tuple fields only. Adding nested structures (list of dicts) requires rethinking serialization, but the existing code "looks like it works" because unknown keys are silently ignored (line 64).

**How to avoid:**
1. Add an explicit migration function: if a loaded config has old flat fields but no `models` list, auto-construct `models` from the flat fields. Test this path explicitly.
2. Keep the `models` field typed as `tuple[dict, ...]` to match frozen dataclass idiom, or use `field(default_factory=tuple)` since mutable defaults in frozen dataclasses are a footgun.
3. Update `load_config()` to handle nested dict structures -- do NOT rely on existing tuple coercion for the models field.
4. Write a round-trip test: save config with new `models` field, load back, assert equality. Also test loading an OLD config file that only has flat fields.

**Warning signs:**
- `load_config()` returns defaults when you expected saved values
- Tests pass with fresh configs but fail loading configs saved by the previous version
- `validate_config()` errors on configs that previously passed

**Phase to address:**
Phase 1 (Config Schema Extension) -- must be the very first change, before any feature touches the config.

---

### Pitfall 2: MODELS Tuple Used as Hard Allowlist in 4+ Modules

**What goes wrong:**
The `MODELS` tuple in `config.py` line 94 is imported and used as a hard validation gate across the codebase:
- **pilot.py line 274:** `_VALID_MODELS = set(MODELS)` -- rejects any model not in the tuple during data quality audit, flagging custom models as "Unknown model" issues
- **compute_derived.py line 482:** iterates `for model in MODELS:` to compute quadrant migrations -- custom models are silently excluded from ALL analysis output
- **setup_wizard.py lines 30-47:** `PROVIDERS` dict builds model lists by filtering `MODELS` with `startswith()` -- custom models never appear in wizard choices
- **config_manager.py lines 138-151:** `validate_config()` rejects models not in `PRICE_TABLE` -- custom models fail validation

If you make models configurable but forget to update ALL consumption points, custom models are accepted during setup but rejected during pilot runs, excluded from analysis, or fail validation.

**Why it happens:**
Module-level constants evaluated at import time create implicit contracts. `MODELS` conflates two concepts: "models we ship defaults for" and "models that are valid to use." These are now different things.

**How to avoid:**
1. Replace `MODELS` with a function `get_configured_models(config: ExperimentConfig) -> tuple[str, ...]` that derives the list from config.
2. Grep for every import of `MODELS`: `from src.config import.*MODELS` appears in `compute_derived.py`, `pilot.py`, `setup_wizard.py`. Update each.
3. Change `_VALID_MODELS` in `pilot.py` to derive from config or accept any non-empty string.
4. Change `validate_config()` to warn (not error) for models not in PRICE_TABLE.
5. Track this as a cross-cutting concern with a checklist, not a single-file change.

**Warning signs:**
- `propt pilot --model custom-model` fails with "Unknown model" despite setup accepting it
- Analysis output silently missing data for custom models
- Validation errors on valid custom config after setup

**Phase to address:**
Phase 1 (Config Schema) -- define how MODELS is derived. Must track all consumption sites as a checklist across ALL phases.

---

### Pitfall 3: compute_cost() Raises KeyError for Unknown Models, Crashing Mid-Experiment

**What goes wrong:**
`compute_cost()` in `config.py` line 155 does `prices = PRICE_TABLE[model]` with no fallback. A custom model not in the price table causes a `KeyError` that crashes execution. This affects 3 call sites:
- `execution_summary.py` line 142: cost estimation before runs -- setup phase crashes
- `run_experiment.py`: cost logging during runs -- mid-experiment crash after spending money
- `pilot.py`: cost auditing after runs -- post-analysis crash

The worst case: the experiment runs 500 API calls successfully, then crashes on cost computation, and the user loses confidence in the tooling.

**Why it happens:**
When PRICE_TABLE was hardcoded to match MODELS exactly, a KeyError was impossible. Once models are user-configurable, missing price entries become the common case.

**How to avoid:**
1. Change `compute_cost()` to return 0.0 with a logged warning for unknown models instead of raising KeyError. Add a `get_price(model) -> dict` that returns `{"input_per_1m": 0.0, "output_per_1m": 0.0}` as fallback.
2. Update `estimate_cost()` in `execution_summary.py` which also calls `compute_cost()` -- ensure fallback propagates.
3. Show a clear warning at setup time: "Pricing unavailable for model X, cost estimates will show $0.00."
4. This defensive fallback must land BEFORE any dynamic pricing work, since it is a prerequisite for custom models to work at all.

**Warning signs:**
- `KeyError` stack traces mentioning `PRICE_TABLE` during `propt run` or `propt pilot`
- Cost estimates showing $0.00 without any warning (silent failure)

**Phase to address:**
Phase 1 (Config Schema) -- defensive fallback in `compute_cost()` is a prerequisite for any custom model to work. Phase 2 (Dynamic Pricing) fills in the actual prices.

---

### Pitfall 4: PREPROC_MODEL_MAP Hard Lookup Crashes During Experiment Execution, Not Setup

**What goes wrong:**
`prompt_compressor.py` line 73 raises `ValueError("No pre-processor model mapping for: {main_model}")` if the model is not in `PREPROC_MODEL_MAP`. This only triggers for `pre_proc_sanitize` and `pre_proc_sanitize_compress` interventions. A custom target model without a preproc mapping passes setup, passes `raw` and `self_correct` runs, then crashes mid-experiment when it hits a sanitize intervention -- potentially after hundreds of successful API calls and dollars spent.

**Why it happens:**
The mapping was built for exactly 4 models. The error is "correct" for the old world but there is no path for user-configured preproc models to enter the map. The failure is delayed because sanitize interventions appear later in the matrix.

**How to avoid:**
1. The new `models` config structure MUST pair target + preproc models explicitly. The wizard must ask for both.
2. Change `get_preproc_model()` to consult the config's models list, falling back to the hardcoded map.
3. Validate at setup time: if a target model lacks a preproc model, warn IMMEDIATELY.
4. Add a test: configure a novel model pair, run through the sanitize intervention, verify no crash.

**Warning signs:**
- `ValueError: No pre-processor model mapping` during experiment runs but NOT during setup
- Only fails on `pre_proc_sanitize*` interventions -- may not appear in quick smoke tests

**Phase to address:**
Phase 1 (Config Schema) -- require target + preproc pairing in the models list. Phase 2 -- make PREPROC_MODEL_MAP config-driven.

---

### Pitfall 5: .env File Created But Never Loaded, or Loads with Wrong Precedence

**What goes wrong:**
The plan says "store API key in .env file" but the codebase reads keys via `os.environ.get()` everywhere (`api_client.py` lines 48-58, `setup_wizard.py` line 109). Two failure modes:
1. `.env` is created but `python-dotenv` is never called -- keys exist on disk but not in the process. User thinks they configured keys but experiments fail with "API key not set."
2. `.env` IS loaded with `override=True` -- it silently overrides keys the user set in their shell profile, causing "I changed my key but it still uses the old one."

**Why it happens:**
`.env` files and shell environment variables are independent systems. Without clear precedence rules and explicit load timing, they conflict in subtle, session-dependent ways.

**How to avoid:**
1. Use `python-dotenv` with `override=False` -- `.env` fills in MISSING vars only, never overrides shell-set ones.
2. Load `.env` exactly once, early, in the CLI entry point (not in library code or tests).
3. Document precedence: shell env vars > `.env` file > no value.
4. In the wizard, when the user provides a key AND the env var is already set, ask: "ANTHROPIC_API_KEY is already set. Save to .env anyway? (Environment variable takes precedence.)"
5. Never overwrite `.env` -- use `dotenv.set_key()` or read-modify-write to preserve existing keys.

**Warning signs:**
- API key validation passes during wizard but fails during `propt run`
- User changes key in `.env` but experiments use old shell-exported key
- Tests that mock `os.environ` break because `python-dotenv` loads before the mock

**Phase to address:**
Phase 3 (Setup Wizard Enhancement) -- must decide `.env` loading strategy before writing the first key.

---

### Pitfall 6: Provider Pricing API Calls Block or Crash the Setup Wizard

**What goes wrong:**
Querying provider pricing APIs during setup introduces network dependency. These calls can timeout (corporate proxies, slow DNS), return unexpected formats (API schema changes), require auth (some pricing endpoints need a valid key), or be rate-limited. If errors are not caught, the wizard crashes mid-flow. Worst case: wizard partially completes, writes an incomplete config, then crashes -- leaving a broken state that confuses the user on next run.

**Why it happens:**
Setup code is written with "happy path" assumptions. Developers test with working internet and valid keys. Real users have intermittent connectivity, proxies, and provider-specific quirks.

**How to avoid:**
1. Set aggressive timeouts on all pricing API calls (5 seconds max).
2. Wrap every pricing call in try/except and fall back to hardcoded PRICE_TABLE values.
3. Never block setup completion on pricing data -- pricing is nice-to-have, not required.
4. Write config atomically: build the full dict, validate, THEN write. Never write partial configs.
5. Show clear feedback: "Fetching pricing from Anthropic... failed (timeout), using cached pricing."

**Warning signs:**
- Setup wizard hangs for 30+ seconds
- "Connection refused" or "timeout" errors during `propt setup`
- Config file exists but has missing or null fields

**Phase to address:**
Phase 2 (Dynamic Pricing APIs) -- defensive fetching from the start. Never write a pricing fetch without timeout and fallback in the same function.

---

### Pitfall 7: api_client.py Provider Detection via String Prefix Breaks for Non-Standard Model IDs

**What goes wrong:**
`_validate_api_keys()` in `api_client.py` lines 48-58 routes models using `model.startswith("claude")`, `startswith("gemini")`, `startswith("gpt")`, `startswith("openrouter/")`. Custom models with non-standard naming (e.g., Google's `models/gemini-2.5-pro`, or a hypothetical `anthropic/claude-next`) either route to the wrong provider, fail to match any condition (silently skipping key validation), or use the wrong SDK entirely.

**Why it happens:**
String prefix matching was adequate for exactly 4 known patterns. User-configurable models have arbitrary naming.

**How to avoid:**
1. Store the provider alongside the model in config: `{"provider": "anthropic", "target_model": "...", ...}`.
2. Route API calls by the explicit provider field, not model name prefix.
3. Keep prefix detection only as a fallback heuristic for backward compat.
4. Test with a model name that matches NO prefix pattern -- verify it uses the explicit provider or raises a clear error.

**Warning signs:**
- API calls silently use the wrong SDK
- "API key not set" errors when the key IS set (wrong provider matched)
- No validation at all for models with non-standard prefixes

**Phase to address:**
Phase 1 (Config Schema) -- provider must be stored with the model. Phase 4 (API Client) -- routing must use provider field.

---

### Pitfall 8: Experiment Matrix Assumes Fixed 4-Model Count

**What goes wrong:**
The experiment matrix in `data/experiment_matrix.json` is pre-generated with entries for all 4 hardcoded models. If the user only configures 2 providers, running the matrix attempts API calls for unconfigured models, fails on missing keys, and either crashes or skips entries unpredictably. If the matrix IS regenerated for 2 models, existing results in `results.db` from previous runs (with 4 models) may become orphaned or cause analysis confusion.

**Why it happens:**
The matrix was designed as a static artifact generated once. Making models dynamic means the matrix must be dynamic too, but code treats it as immutable input.

**How to avoid:**
1. Filter matrix items by configured models before execution -- add `filter_matrix_by_config(items, config)`.
2. When model list changes, do NOT delete old results. Mark runs with a config version/timestamp.
3. Add a check at run start: "Matrix contains models X, Y, Z but only A, B are configured. Running A, B only."
4. Consider generating the matrix at runtime from config rather than as a static file.

**Warning signs:**
- "ANTHROPIC_API_KEY not set" when you never configured Anthropic
- Progress bar shows more items than expected
- Analysis includes models the user did not configure

**Phase to address:**
Phase 5 (Experiment Scope Adaptation) -- but Phase 1 must make model list config-driven so the matrix can consume it.

---

### Pitfall 9: Module-Level Constants Evaluated at Import Time Ignore Runtime Config

**What goes wrong:**
Several modules copy config constants at import time into module-level state:
- `api_client.py` line 36: `_rate_delays = dict(RATE_LIMIT_DELAYS)` -- copies once at import, never updated
- `setup_wizard.py` lines 27-48: `PROVIDERS` dict built from `MODELS` at import -- never reflects config
- `pilot.py` line 274: `_VALID_MODELS = set(MODELS)` -- frozen at import time

Even after loading a config with custom models, these module-level values still reflect the hardcoded defaults. Custom models get the 0.5s fallback delay (not their configured value), never appear in PROVIDERS, and fail the _VALID_MODELS check.

**Why it happens:**
Python evaluates module-level expressions once at first import. This pattern is fine for truly constant values but breaks when constants become config-driven.

**How to avoid:**
1. Replace module-level constant copies with functions that read from current config: `def get_rate_delay(model, config) -> float`.
2. For `_rate_delays` in api_client.py, either accept config as a parameter or add a `reinitialize_delays(config)` function called after config load.
3. For `PROVIDERS` in setup_wizard.py, build the dict inside `run_setup_wizard()`, not at module level.
4. Never copy a "constant" that will become dynamic -- use a function call or lazy property instead.

**Warning signs:**
- Custom model always uses 0.5s rate delay regardless of config
- `propt setup` shows only default models even after config changes
- Pilot audit flags custom models as unknown

**Phase to address:**
Phase 1 (Config Schema) -- decide the pattern (function vs. lazy init). Apply it consistently across all affected modules in their respective phases.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep flat model fields alongside new `models` list | Backward compat with existing configs | Two sources of truth; every feature must update both | During transition only -- set removal date (v3.0), add deprecation warnings |
| Fall back to $0.00 for unknown pricing | Unblocks custom model usage | Users run expensive experiments with no cost guardrails | Always, but MUST log a visible warning, not just debug-level |
| Import-time `MODELS` constant derived from defaults | Simple, no loader needed | Custom models only work if config loaded before module imports | Never -- refactor to lazy evaluation from the start |
| String prefix routing in api_client.py | Avoids schema change | Breaks silently with non-standard model names | Only as fallback behind explicit provider field |
| Monolithic PRICE_TABLE dict for all pricing | Single lookup point | Cannot handle per-config pricing, stale prices not obvious | Only as fallback behind dynamic pricing |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| python-dotenv loading | Calling `load_dotenv()` in library code or multiple places | Call once in CLI entry point with `override=False` |
| python-dotenv in tests | `load_dotenv()` runs before test fixtures mock `os.environ` | Use `monkeypatch.setenv()` in tests; ensure `load_dotenv()` is not called during test imports |
| Provider pricing APIs | Treating them as reliable (always available, stable schema) | Wrap in timeout + try/except, cache results, hardcoded fallback |
| `.env` file writing | `open(path, 'w')` overwrites entire file, destroying other keys | Use `python-dotenv`'s `set_key()` or read-modify-write to preserve existing keys |
| Frozen dataclass extension | Adding mutable default (list/dict) as field default | Use `field(default_factory=...)` -- but frozen dataclass + mutable inner values is still a footgun |
| JSON serialization of tuples | `json.dump(tuple)` produces `[...]` which loads as list | Current code handles this (lines 69-70, 92-93) but new nested types need explicit handling |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys in `experiment_config.json` | Config may be committed (it is NOT in `.gitignore` currently) | Keys go ONLY in `.env` or env vars. Add `experiment_config.json` to `.gitignore`. |
| `.env` file created with default permissions | Other users on shared systems can read keys | `os.chmod(env_path, 0o600)` after creating `.env` |
| Logging API keys during setup debug output | Key exposure in terminal scrollback or log files | Log only "key is set" / masked display (`sk-...abc`), never the value |
| Pricing API responses cached with auth tokens | Cached responses may contain account metadata | Extract only pricing fields; never cache full API responses |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Pricing fetch fails silently, shows $0.00 budget | User thinks experiment is free, gets surprise bill | Explicit warning: "Could not fetch pricing for X. Estimates show $0.00 but actual costs may apply." |
| Validation rejects entire config on one bad field | User loses all wizard input | Validate incrementally during wizard steps, not just at end. Save valid fields, highlight invalid ones. |
| No way to test a custom model before experiment | Wrong model ID discovered after 100 API calls | Add `propt test-model <model-id>` that sends a single "Hi" request |
| `.env` created but user does not know they need to restart shell | Keys saved but not in current session | After writing `.env`, also `os.environ[key] = value` in current process. Tell user: "Key loaded for this session." |
| Wizard asks for preproc model without explanation | User picks wrong model or skips | Explain: "Pre-processor sanitizes prompts before the target model. Should be cheap/fast (Haiku, Flash, GPT-4o-mini)." |
| `propt list-models` shows only hardcoded models | User cannot discover available models for their provider | Query provider API for live model list with pricing; fall back to hardcoded list on failure |

## "Looks Done But Isn't" Checklist

- [ ] **Config migration:** Old `experiment_config.json` files load correctly with new schema -- test with a config saved by the CURRENT version
- [ ] **MODELS derivation:** Every file that imports `MODELS` uses config-driven model list -- grep `from src.config import.*MODELS` (currently: compute_derived.py, pilot.py, setup_wizard.py)
- [ ] **PRICE_TABLE fallback:** `compute_cost()` handles unknown models without crashing -- test with `compute_cost("novel-model", 1000, 500)`
- [ ] **PREPROC_MODEL_MAP:** Custom target models have preproc mappings -- test `sanitize()` with a custom model pair
- [ ] **RATE_LIMIT_DELAYS:** Custom models get sensible default delay -- check `api_client._rate_delays` after config load
- [ ] **Validation softened:** `validate_config()` warns (not errors) for unknown models -- test with custom model name
- [ ] **api_client routing:** Custom models route to correct provider -- test with model name that has no standard prefix
- [ ] **Matrix filtering:** Matrix adapts to configured models -- test with 1, 2, and 4 providers
- [ ] **`.env` loading:** Keys from `.env` available to experiment runs, not just wizard -- test `propt run` after fresh `.env` creation
- [ ] **`.env` not committed:** `.env` is in `.gitignore` (already true); `experiment_config.json` also in `.gitignore` (verify)
- [ ] **Module-level copies:** `_rate_delays`, `PROVIDERS`, `_VALID_MODELS` reflect config, not hardcoded defaults

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupt config from partial wizard write | LOW | Delete `experiment_config.json`, re-run `propt setup`. Defaults are safe. |
| Wrong model ID used for API calls | MEDIUM | Results are in SQLite with model field -- filter/delete bad runs, re-run with correct model. |
| `.env` overwrites existing keys | LOW | User re-exports correct key or edits `.env` manually. |
| PRICE_TABLE KeyError mid-experiment | LOW | Fix `compute_cost()`, re-run. Check if cost was stored at insert time -- those rows may need recomputation. |
| Schema migration breaks load_config | MEDIUM | Backup old config, delete, re-run setup. DB results unaffected (independent schema). |
| Module-level stale constants | LOW | Add a `reinitialize()` call after config load. No data loss, just wrong behavior until fixed. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Frozen dataclass schema migration | Phase 1 (Config Schema) | Round-trip test: save old config, load with new code, no data loss |
| MODELS tuple as allowlist | Phase 1 (Config Schema) | Grep all MODELS imports, verify each uses config-driven source |
| compute_cost KeyError | Phase 1 + Phase 2 (Pricing) | `compute_cost("unknown-model", 1000, 500)` returns 0.0 with warning |
| PREPROC_MODEL_MAP crash | Phase 1 + Phase 2 | Custom model pair through full sanitize pipeline without crash |
| .env file conflicts | Phase 3 (Wizard) | Set key in env, write different key to .env, verify env var wins |
| Pricing API failures | Phase 2 (Dynamic Pricing) | Mocked timeout/error responses, verify fallback to cached prices |
| String prefix routing | Phase 1 + Phase 4 (API Client) | Non-standard model name routes correctly via explicit provider field |
| Fixed experiment matrix | Phase 5 (Scope Adaptation) | 2 configured providers -> matrix has only 2 models |
| Module-level stale constants | Phase 1 (pattern decision) + each subsequent phase | After config load, verify module-level values reflect config |

## Sources

- Direct codebase analysis: `src/config.py`, `src/config_manager.py`, `src/setup_wizard.py`, `src/api_client.py`, `src/pilot.py`, `src/compute_derived.py`, `src/prompt_compressor.py`, `src/execution_summary.py`, `src/run_experiment.py`
- Context decisions: `.planning/quick/260325-tx5-make-models-fully-configurable-with-dyna/260325-tx5-CONTEXT.md`
- Existing test patterns: `tests/test_config_manager.py`
- python-dotenv documentation (load precedence, set_key API)

---
*Pitfalls research for: Configurable models, dynamic pricing, and .env management in Linguistic Tax toolkit*
*Researched: 2026-03-25*
