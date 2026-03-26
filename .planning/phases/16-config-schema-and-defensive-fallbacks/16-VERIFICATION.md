---
phase: 16-config-schema-and-defensive-fallbacks
verified: 2026-03-26T00:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 16: Config Schema and Defensive Fallbacks Verification Report

**Phase Goal:** Researcher has a config-driven model registry that replaces hardcoded constants — custom models load without crashes, old configs migrate transparently, and .env files manage API keys
**Verified:** 2026-03-26
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| #   | Truth                                                                                                               | Status     | Evidence                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| 1   | Researcher can add a custom model ID to the config's models list and load it without any validation error or crash  | VERIFIED   | validate_config warns on unknown IDs (not errors); load_config calls registry.reload()    |
| 2   | A v1 flat-field config auto-migrates to the new format on load                                                      | VERIFIED   | `_migrate_v1_to_v2` in config_manager.py detected by absent `config_version`, .bak backup created, flat fields mapped to models list |
| 3   | compute_cost() with an unknown model ID returns $0.00 and logs a warning instead of crashing                       | VERIFIED   | Smoke test confirmed: `registry.compute_cost('unknown', 1000, 1000)` returns 0.0 with warning |
| 4   | PRICE_TABLE, PREPROC_MODEL_MAP, and RATE_LIMIT_DELAYS are built from loaded config at runtime, not hardcoded        | VERIFIED   | Old dict literals removed; replaced by `_RegistryBackedDict` shims delegating to live registry |
| 5   | python-dotenv is installed and env_manager module can load/write .env files                                         | VERIFIED   | `python-dotenv>=1.2.2` in pyproject.toml; env_manager.py with load_env, write_env, check_keys |

**Score:** 5/5 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact                          | Expected                                         | Status     | Details                                                       |
| --------------------------------- | ------------------------------------------------ | ---------- | ------------------------------------------------------------- |
| `data/default_models.json`        | 8 curated models with complete pricing           | VERIFIED   | 8 entries, 4 target + 4 preproc, all fields present           |
| `src/model_registry.py`           | ModelConfig, ModelRegistry, module singleton     | VERIFIED   | 214 lines; all 7 classes/functions present; singleton at L214 |
| `tests/test_model_registry.py`    | Unit tests, min 80 lines                         | VERIFIED   | 287 lines, 30 test functions                                  |

#### Plan 02 Artifacts

| Artifact                   | Expected                                   | Status   | Details                                              |
| -------------------------- | ------------------------------------------ | -------- | ---------------------------------------------------- |
| `src/env_manager.py`       | load_env, write_env, check_keys functions  | VERIFIED | 74 lines; all 3 functions + PROVIDER_KEY_MAP present |
| `tests/test_env_manager.py`| Unit tests, min 40 lines                   | VERIFIED | 119 lines, 13 test functions                         |

#### Plan 03 Artifacts

| Artifact                        | Expected                                              | Status   | Details                                                    |
| ------------------------------- | ----------------------------------------------------- | -------- | ---------------------------------------------------------- |
| `src/config.py`                 | Mutable ExperimentConfig, models list, no old consts  | VERIFIED | `@dataclass` (no frozen), `models: list[dict] \| None`, backward-compat shims present |
| `src/config_manager.py`         | Migration logic, env loading, registry reload         | VERIFIED | 376 lines; `_migrate_v1_to_v2`, `load_env()`, `registry.reload()` all present |
| `tests/test_config.py`          | Updated tests for new shape, min 40 lines             | VERIFIED | 126 lines; `test_config_is_mutable`, `test_models_field_defaults_to_none`, `test_config_version_defaults_to_2` present |
| `tests/test_config_manager.py`  | Migration tests including test_v1_to_v2_migration     | VERIFIED | 297 lines; `test_v1_to_v2_migration`, `test_migration_creates_backup`, `test_validate_unknown_model_warns_not_rejects` all present |

---

### Key Link Verification

| From                    | To                       | Via                            | Status  | Details                                            |
| ----------------------- | ------------------------ | ------------------------------ | ------- | -------------------------------------------------- |
| `src/model_registry.py` | `data/default_models.json` | `json.load` in `_load_default_models()` | WIRED   | L57: resolves path via `Path(__file__).resolve().parent.parent / "data" / "default_models.json"` |
| `src/model_registry.py` | `logging`                | `logger.warning` for unknown models | WIRED   | L166: `logger.warning(...)` inside `compute_cost` |
| `src/config_manager.py` | `src/model_registry.py`  | `registry.reload()` after loading config | WIRED   | L238: `registry.reload(model_configs)`            |
| `src/config_manager.py` | `src/env_manager.py`     | `load_env()` at start of load_config | WIRED   | L15: import; L195: `load_env()` first call in function |
| `src/config_manager.py` | `data/default_models.json` | `_load_default_models` for migration pricing | WIRED   | L16: import; L61, L307: two call sites            |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                            | Status     | Evidence                                                   |
| ----------- | ----------- | ---------------------------------------------------------------------- | ---------- | ---------------------------------------------------------- |
| CFG-01      | 16-01       | User configures models via `models` list in ExperimentConfig           | SATISFIED  | `models: list[dict] \| None = None` in ExperimentConfig; load_config converts to ModelConfig list and reloads registry |
| CFG-02      | 16-01       | PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS derived at runtime   | SATISFIED  | Hardcoded dict literals removed; `_RegistryBackedDict` shims delegate to live registry on every access |
| CFG-03      | 16-01       | compute_cost() falls back to $0.00 with warning for unknown models     | SATISFIED  | `registry.compute_cost('unknown', ...)` confirmed returns 0.0 with logged warning |
| CFG-04      | 16-03       | validate_config() warns instead of rejecting unknown model IDs         | SATISFIED  | L311-316 in config_manager.py: `logger.warning(...)` instead of `errors.append(...)` for unknown model IDs |
| CFG-05      | 16-03       | Old flat-field configs auto-migrate on load                            | SATISFIED  | `_migrate_v1_to_v2` detects missing `config_version`, creates .bak, maps old flat fields to models list |
| PRC-01      | 16-01       | Curated fallback price table for known models                          | SATISFIED  | `data/default_models.json` has complete pricing for all 8 models |
| PRC-03      | 16-01       | Unknown models default to $0.00 with user-visible warning              | SATISFIED  | Once-per-model warning via `_warned_unknown` set; warning message includes `"Run 'propt list-models'"` |

**Orphaned requirements:** None. All 7 requirement IDs from PLAN frontmatter are accounted for. REQUIREMENTS.md traceability table confirms all 7 marked Complete at Phase 16.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

No anti-patterns detected. No TODOs, FIXMEs, placeholder returns, or stub implementations found in any phase 16 source file.

Note: The backward-compat shims (`_RegistryBackedDict`, `_LazyModels`, `compute_cost` wrapper) in `config.py` are intentional bridge code documented in the SUMMARY as pending Phase 17 removal. They are fully wired delegations — not stubs.

---

### Human Verification Required

None. All phase 16 behaviors are programmatically verifiable: model registry lookups, file I/O, config migration, warning logging, and test suite pass/fail.

---

### Test Suite Results

| Test File                         | Tests | Result    |
| --------------------------------- | ----- | --------- |
| `tests/test_model_registry.py`    | 30    | All pass  |
| `tests/test_env_manager.py`       | 13    | All pass  |
| `tests/test_config.py`            | (subset of 90) | All pass |
| `tests/test_config_manager.py`    | (subset of 90) | All pass  |
| **Full suite (541 tests)**        | **541** | **All pass, 0 regressions** |

---

### Commit Verification

All commits documented in SUMMARY files verified present in git history:

- `fcddfc4` — test(16-01): add failing tests for ModelConfig and ModelRegistry
- `20b86d5` — feat(16-01): implement ModelConfig, ModelRegistry, and default_models.json
- `6d62146` — chore(16-02): add python-dotenv dependency
- `253b38a` — test(16-02): add failing tests for env_manager module
- `9467940` — feat(16-02): implement env_manager module with load/write/check
- `68841da` — feat(16-03): update ExperimentConfig to v2 format with models list
- `0aa8850` — feat(16-03): add migration logic, env loading, and registry reload to config_manager

---

### Notable Deviation: Backward-Compat Shims

Plan 03 specified removing old constants entirely. The implementation added registry-backed shims instead to keep the full test suite passing until Phase 17 migrates consumers. This is a sound engineering decision: the hardcoded data is gone, the names are live proxies, and the deferred cleanup is explicitly planned. This deviation does not constitute a gap — the ROADMAP success criteria are all met and no consumer code is broken.

---

_Verified: 2026-03-26_
_Verifier: Claude (gsd-verifier)_
