# Phase 19: Setup Wizard Overhaul - Research

**Researched:** 2026-03-26
**Domain:** Interactive CLI wizard, .env management, model discovery integration, cost estimation
**Confidence:** HIGH

## Summary

Phase 19 replaces the existing single-provider setup wizard (`src/setup_wizard.py`, ~306 lines) with a multi-provider wizard supporting free-text model entry, .env key management, validation pings, and budget preview. The existing codebase provides strong foundations: `env_manager.write_env()` handles .env creation with chmod 600, `model_discovery.discover_all_models()` queries live models from all 4 providers in parallel, `execution_summary.estimate_cost()` computes per-model costs, and `validate_config()` handles unknown model warnings gracefully.

The wizard is a pure Python CLI flow using `input_fn` injection for testability (established Phase 13 pattern). No new dependencies are needed. The main complexity is the multi-step flow with branching (existing config detection, per-provider vs global preproc, live model browser), graceful Ctrl+C handling at every point, and the budget estimation wiring.

**Primary recommendation:** Decompose the wizard into discrete step functions (provider_selection, key_collection, model_selection, budget_preview, confirmation) that compose into the main flow. Each step function takes `input_fn` and returns structured data, making individual steps independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Provider selection first:** Multi-select from Anthropic/Google/OpenAI/OpenRouter at the start, then configure each selected provider in sequence
- **Step order within providers:** All API keys upfront (for all selected providers) -> then all model selections. Keys and models are separate phases
- **Existing config handling:** If config already exists, show current providers/models and offer: "Add provider / Reconfigure / Start fresh". Pre-fill existing values as defaults
- **Environment check:** Keep Python version + package check at start of wizard
- **File paths:** Show paths being used (informational) but don't prompt for changes
- **API key handling:** Show masked existing key (e.g., `sk-ant-...7x3f`) with "Keep this? (Y/n)". Only prompt for new key if user says no or key is missing
- **Key write timing:** Write each key to .env immediately via `env_manager.write_env()` AND load into `os.environ` immediately so validation pings work within same session
- **Validation ping failure:** Warn and continue. Let user decide whether to keep the model
- **Validation ping model:** Use the actual selected target model, not a cheap proxy
- **End-of-wizard confirmation:** Show full summary with "Save this configuration? (Y/n)" before writing config file
- **Non-interactive mode:** Preserve `--non-interactive` flag
- **Keyboard interrupt:** Handle Ctrl+C gracefully at every point (partial .env writes should not corrupt state)
- **Free-text model entry:** Show default with free text input; Enter accepts default, or type any model ID
- **Live model browser:** Type `list` at any model prompt to browse available models from provider's live API
- **Browser UX:** Paginated 20 models/page, sorted by newest, substring search, n/p navigation, number to select, q to cancel
- **Browser fallback:** If provider API unreachable, fall back to registry models from `default_models.json`
- **Preproc model entry:** Auto-assigned from registry mapping, with override option
- **Custom model pricing:** For models not in registry, skip pricing -- show as "pricing unknown"
- **Model ID validation:** Accept any typed model ID. Validation ping catches invalid IDs
- **Budget preview timing:** After all models chosen, before save confirmation
- **Budget detail:** Per-model cost estimate plus total, both pilot (20 prompts) and full matrix (200 prompts)
- **Preproc costs:** Show separately as own line
- **Budget warning:** Warn if full matrix estimate exceeds $50
- **Target vs preproc explanation:** Before model selection starts, after provider selection. One explanation, not repeated
- **Preproc scope choice:** Ask user: per-provider or one global pre-processor? Default to per-provider
- **Wizard re-entry:** Detect existing config and offer Add/Reconfigure/Start fresh
- **Post-setup next steps:** After saving, show guided next steps
- **Config validation summary:** Run `validate_config()` after all models configured, show warnings before save

### Claude's Discretion
- Exact wording of explanatory text and prompts
- Internal function decomposition and helper structure
- Error message formatting
- How the paginated model browser renders (exact formatting)
- How to compute budget estimate from selected models (wiring to execution_summary)

### Deferred Ideas (OUT OF SCOPE)
- Config export/import (`propt config export` / `propt config import`)
- Model removal from config (wizard option to remove a previously configured provider/model)
- API key rotation (keeping old key as comment in .env)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIZ-01 | Setup wizard explains what "target model" and "pre-processor model" mean | Wizard flow includes explanation step between provider selection and model selection. 2-3 sentences about target vs preproc distinction |
| WIZ-02 | User can configure 1-4 providers in a single setup session (multi-provider loop) | Multi-select at start, then iterate through selected providers for keys and models |
| WIZ-03 | User can enter custom model IDs via free text with sensible defaults shown | Free-text input with defaults from `default_models.json`. `list` command triggers live model browser |
| WIZ-04 | Wizard creates/updates `.env` file when user provides API keys | Use `env_manager.write_env()` which calls `python-dotenv set_key()`. Verified: creates file if missing, updates in-place, preserves other keys |
| WIZ-05 | Wizard shows estimated experiment cost based on selected models' pricing before completing setup | Wire to `execution_summary.estimate_cost()` with synthetic work items built from selected models. Show pilot + full matrix estimates |
| WIZ-06 | Wizard validates each selected model by pinging the provider API with a tiny request | Modify `validate_api_key()` to accept model_id parameter instead of hardcoded cheap models |
| DSC-03 | User can enter any model ID as free text during setup (not limited to a hardcoded list) | Free-text input is primary mechanism; `list` is supplementary. No pre-validation against live list |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-dotenv | 1.1.1 | .env file read/write | Already in use via `env_manager.py`. `set_key()` creates files, updates in-place |
| anthropic | (installed) | Anthropic API client for validation pings | Already imported in `setup_wizard.py` |
| google-genai | (installed) | Google API client for validation pings | Already imported in `setup_wizard.py` |
| openai | (installed) | OpenAI/OpenRouter API client for validation pings | Already imported in `setup_wizard.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tabulate | (installed) | Table formatting for budget preview | Already used in `execution_summary.py` |

No new dependencies needed. Everything required is already installed.

## Architecture Patterns

### Recommended Module Structure
```
src/
  setup_wizard.py       # Complete rewrite (~500-700 lines estimated)
    - run_setup_wizard()           # Main entry point (preserved signature)
    - check_environment()          # Preserved as-is
    - validate_api_key()           # Updated: accepts model_id param
    - _detect_existing_config()    # New: config re-entry detection
    - _select_providers()          # New: multi-select providers
    - _collect_api_keys()          # New: key entry + .env write + os.environ load
    - _explain_model_roles()       # New: target vs preproc explanation
    - _select_models()             # New: per-provider model selection loop
    - _browse_models()             # New: paginated live model browser
    - _select_preproc_scope()      # New: per-provider vs global preproc
    - _build_budget_preview()      # New: cost estimation display
    - _show_confirmation()         # New: full summary + save prompt
    - _mask_key()                  # New: mask API key for display
```

### Pattern 1: Step Function Composition
**What:** Each wizard step is a standalone function returning structured data, composed in `run_setup_wizard()`.
**When to use:** Always for this wizard.
**Example:**
```python
def _select_providers(
    input_fn: Callable[..., str],
    existing_providers: list[str] | None = None,
) -> list[str]:
    """Multi-select providers. Returns list of provider keys."""
    available = ["anthropic", "google", "openai", "openrouter"]
    print("\nWhich providers do you want to use?")
    for i, p in enumerate(available, 1):
        marker = " (configured)" if existing_providers and p in existing_providers else ""
        print(f"  {i}. {PROVIDER_NAMES[p]}{marker}")
    print("  Enter numbers separated by commas (e.g., 1,2):")

    raw = input_fn("Providers: ")
    # Parse comma-separated numbers, validate, return provider keys
    ...
```

### Pattern 2: input_fn Injection (Preserved)
**What:** All user input goes through `input_fn` parameter, never calls `builtins.input` directly.
**When to use:** Every function that reads user input.
**Why:** Established in Phase 13. Enables testing without monkeypatching.

### Pattern 3: Immediate Key Persistence
**What:** Each API key is written to `.env` AND loaded to `os.environ` immediately after entry.
**When to use:** During the key collection phase.
**Example:**
```python
from src.env_manager import write_env

def _collect_api_keys(
    providers: list[str],
    input_fn: Callable[..., str],
    env_path: Path | None = None,
) -> dict[str, str]:
    """Collect API keys for selected providers. Writes to .env immediately."""
    keys: dict[str, str] = {}
    for provider in providers:
        env_var = PROVIDER_KEY_MAP[provider]
        existing = os.environ.get(env_var, "")

        if existing:
            masked = _mask_key(existing)
            keep = input_fn(f"  {env_var}: {masked} -- Keep this? (Y/n): ")
            if keep.strip().lower() not in ("n", "no"):
                keys[provider] = existing
                continue

        new_key = input_fn(f"  {env_var}: ")
        if new_key.strip():
            write_env(env_var, new_key.strip(), env_path=env_path)
            os.environ[env_var] = new_key.strip()
            keys[provider] = new_key.strip()
    return keys
```

### Pattern 4: Budget Estimation Wiring
**What:** Build synthetic experiment matrix items from selected models, pass to `estimate_cost()`.
**When to use:** Budget preview step.
**Example:**
```python
from src.execution_summary import estimate_cost

def _build_budget_preview(
    models: list[dict],  # [{provider, target_model, preproc_model}, ...]
    prompt_count: int = 200,
) -> dict:
    """Build cost estimate from selected models."""
    # Build synthetic items matching estimate_cost()'s expected format
    items = []
    interventions = ["raw", "self_correct", "pre_proc_sanitize",
                     "pre_proc_sanitize_compress", "prompt_repetition"]
    for model_cfg in models:
        for intervention in interventions:
            for rep in range(5):  # 5 repetitions
                for i in range(prompt_count):
                    items.append({
                        "prompt_id": f"HumanEval/{i}",
                        "model": model_cfg["target_model"],
                        "intervention": intervention,
                    })
    return estimate_cost(items)
```

### Anti-Patterns to Avoid
- **Monolithic wizard function:** Do NOT put everything in `run_setup_wizard()`. The current 120-line function is already at the edge; the new flow is 3-4x more complex.
- **Stateful global mutation:** Do NOT rely on module-level `PROVIDERS` dict being modified during the wizard. Build provider config locally.
- **Silent failure on .env write:** Always confirm key was written by reading it back or checking `os.environ`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env file management | Custom file parser/writer | `python-dotenv set_key()` via `env_manager.write_env()` | Handles quoting, escaping, in-place updates, file creation |
| Cost estimation | Custom per-model math | `execution_summary.estimate_cost()` | Already accounts for preproc interventions, benchmark token averages |
| Model discovery | Custom API queries | `model_discovery.discover_all_models()` + `_get_fallback_models()` | Parallel queries, timeout handling, fallback to registry |
| Config validation | Custom validators | `config_manager.validate_config()` | Already handles unknown model warnings |
| Key masking | Regex-based masking | Simple slice: `key[:6] + "..." + key[-4:]` | Straightforward, no regex needed |

## Common Pitfalls

### Pitfall 1: python-dotenv set_key() Quoting
**What goes wrong:** `set_key()` wraps values in single quotes by default (e.g., `KEY='value'`). This is fine for `load_dotenv()` but could surprise users editing `.env` manually.
**Why it happens:** python-dotenv 1.1.1 default quoting behavior.
**How to avoid:** This is harmless since `load_dotenv()` handles quoted values. Do not strip quotes manually.
**Verified:** `set_key()` creates the file if it doesn't exist, updates existing keys in-place, preserves other keys. Tested empirically.

### Pitfall 2: os.environ Not Updated After write_env()
**What goes wrong:** `write_env()` writes to `.env` file but does NOT update `os.environ`. Validation pings later in the same session won't find the key.
**Why it happens:** `write_env()` calls `set_key()` which only writes to file. `load_env()` uses `override=False` so won't overwrite.
**How to avoid:** After `write_env()`, explicitly set `os.environ[env_var] = value`. This is stated in the CONTEXT.md decisions.

### Pitfall 3: validate_api_key() Hardcodes Cheap Models
**What goes wrong:** Current `validate_api_key()` uses hardcoded model IDs (e.g., `claude-haiku-4-5-20250514`) for validation pings. CONTEXT.md requires using the actual selected target model.
**Why it happens:** Original wizard only needed to validate the key, not the specific model.
**How to avoid:** Add a `model_id` parameter to `validate_api_key()` and use it in the API call. Fall back to provider defaults only if no model specified.

### Pitfall 4: Ctrl+C During .env Write
**What goes wrong:** User presses Ctrl+C after some keys are written to `.env` but before wizard completes. Partial `.env` state.
**Why it happens:** `write_env()` is called immediately per key, so `.env` has been modified.
**How to avoid:** This is actually safe because each `write_env()` call is atomic (single key update). The `.env` file is always in a valid state. Keys written before Ctrl+C persist, which is the correct behavior since they represent confirmed user entries.

### Pitfall 5: Model Browser Pagination with Large Lists
**What goes wrong:** OpenRouter returns 1000+ models. Google returns 100+ models. Naive listing floods the terminal.
**Why it happens:** Live APIs return ALL models, not just relevant ones.
**How to avoid:** Paginate (20/page as decided), sort by newest, provide substring search filter. This is decided in CONTEXT.md.

### Pitfall 6: estimate_cost() Requires Specific Item Format
**What goes wrong:** Passing wrong format to `estimate_cost()` causes KeyError or incorrect estimates.
**Why it happens:** `estimate_cost()` expects items with `prompt_id`, `model`, and `intervention` keys.
**How to avoid:** Build synthetic items that match the expected format. Use a representative set of prompt IDs covering all benchmarks (HumanEval, Mbpp, GSM8K) for accurate average token estimates.

### Pitfall 7: Config Re-entry with v2 Format
**What goes wrong:** Existing config uses `models` list (v2 format). Need to extract currently configured providers and models from this structure.
**Why it happens:** v2 config stores models as a list of dicts, not flat fields.
**How to avoid:** Parse `models` list from existing config, group by provider, extract target and preproc model IDs to pre-fill wizard defaults.

## Code Examples

### Masking API Keys
```python
def _mask_key(key: str) -> str:
    """Mask an API key for display, showing first 6 and last 4 chars."""
    if len(key) <= 10:
        return "****"
    return f"{key[:6]}...{key[-4:]}"
```

### Multi-Select Provider Input
```python
def _parse_provider_selection(raw: str, available: list[str]) -> list[str]:
    """Parse comma-separated numbers into provider keys."""
    selected = []
    for part in raw.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(available):
                selected.append(available[idx])
        except ValueError:
            continue
    return selected if selected else [available[0]]  # Default to first
```

### Building Budget Preview Items
```python
def _build_preview_items(
    models: list[dict],  # [{target_model: str, ...}]
    prompt_count: int,
) -> list[dict]:
    """Build synthetic experiment items for cost estimation."""
    interventions = ["raw", "self_correct", "pre_proc_sanitize",
                     "pre_proc_sanitize_compress", "prompt_repetition"]
    noise_types = ["none", "type_a", "type_a", "type_a", "type_b"]  # Rough distribution
    items = []
    for mcfg in models:
        for intervention in interventions:
            for rep in range(5):
                for i in range(prompt_count):
                    items.append({
                        "prompt_id": f"HumanEval/{i}" if i < 80 else
                                     f"Mbpp/{i}" if i < 160 else f"gsm8k_{i}",
                        "model": mcfg["target_model"],
                        "intervention": intervention,
                        "noise_type": noise_types[0],  # Doesn't affect cost
                        "noise_level": None,
                        "repetition_num": rep + 1,
                    })
    return items
```

### Updated validate_api_key with Model Parameter
```python
def validate_api_key(
    provider: str,
    env_var: str,
    model_id: str | None = None,
) -> tuple[bool, str]:
    """Validate an API key by making a minimal test call with the specified model."""
    key = os.environ.get(env_var)
    if not key:
        return (False, f"Environment variable {env_var} is not set")

    try:
        if provider == "anthropic":
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model=model_id or "claude-haiku-4-5-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        # ... similar for other providers
```

### Paginated Model Browser
```python
def _browse_models(
    provider: str,
    input_fn: Callable[..., str],
    timeout: float = 5.0,
) -> str | None:
    """Interactive paginated model browser. Returns selected model_id or None."""
    from src.model_discovery import discover_all_models, _get_fallback_models

    # Try live query for this provider
    result = discover_all_models(timeout=timeout)
    models = result.models.get(provider, [])
    if not models:
        models = _get_fallback_models(provider)
        if models:
            print(f"  (Using cached model list -- live API unreachable)")

    if not models:
        print(f"  No models found for {provider}")
        return None

    # Sort by model_id (newest typically have higher version numbers)
    models.sort(key=lambda m: m.model_id, reverse=True)

    page_size = 20
    page = 0
    search_filter = ""

    while True:
        filtered = [m for m in models if search_filter.lower() in m.model_id.lower()] if search_filter else models
        total_pages = (len(filtered) + page_size - 1) // page_size
        start = page * page_size
        page_models = filtered[start:start + page_size]

        # Display page
        for i, m in enumerate(page_models, start + 1):
            ctx = f" ({m.context_window:,} tokens)" if m.context_window else ""
            print(f"  {i}. {m.model_id}{ctx}")
        print(f"  Page {page + 1}/{total_pages} | n=next p=prev #=select /text=search q=quit")

        choice = input_fn("  > ")
        # Handle navigation...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-provider wizard (select 1 of 4) | Multi-provider wizard (select 1-4) | Phase 19 | Entire wizard flow redesigned |
| Hardcoded model lists in PROVIDERS dict | Free-text entry with live browser | Phase 19 | PROVIDERS dict becomes provider metadata only (names, env vars) |
| No .env management in wizard | Write keys to .env with chmod 600 | Phase 19 | `env_manager` integration |
| Hardcoded validation ping models | Ping with actual selected model | Phase 19 | Validates specific model access, not just API key |
| No cost preview | Budget preview before confirmation | Phase 19 | Uses `execution_summary.estimate_cost()` |

## Open Questions

1. **discover_all_models() queries ALL providers in parallel**
   - What we know: It checks for API keys and skips providers without keys. It uses ThreadPoolExecutor with timeout.
   - What's unclear: For the model browser, we only need ONE provider's models at a time. Calling `discover_all_models()` is wasteful.
   - Recommendation: Extract single-provider query functions (`_query_anthropic`, etc.) and call them directly in the browser. They're already module-level functions in `model_discovery.py`.

2. **Budget estimation accuracy for unknown models**
   - What we know: Models not in registry return $0.00 pricing. CONTEXT.md says show as "pricing unknown".
   - What's unclear: How to compute a meaningful total when some models have unknown pricing.
   - Recommendation: Show per-model lines with "pricing unknown" for unregistered models. Total line shows "Total (excluding unknown): ~$X.XX" as specified in CONTEXT.md.

3. **Preproc scope choice persistence**
   - What we know: User chooses per-provider or global preproc. Config uses `models` list with `preproc_model_id` per target model.
   - What's unclear: How to represent "global preproc" in the v2 config format.
   - Recommendation: If global, set the same `preproc_model_id` on all target models in the `models` list. No schema change needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed) |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -x -q` |
| Full suite command | `.venv/bin/python3 -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIZ-01 | Wizard explains target vs preproc distinction | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "explain" -x` | Needs new tests |
| WIZ-02 | Multi-provider selection (1-4 providers) | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "multi_provider" -x` | Needs new tests |
| WIZ-03 | Free-text model entry with defaults | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "free_text" -x` | Needs new tests |
| WIZ-04 | .env file creation/update on key entry | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "env_write" -x` | Needs new tests |
| WIZ-05 | Budget preview display | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "budget" -x` | Needs new tests |
| WIZ-06 | Model validation ping with actual model | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "validate" -x` | Partial (existing tests use hardcoded models) |
| DSC-03 | Accept any model ID as free text | unit | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -k "free_text or custom" -x` | Needs new tests |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -x -q`
- **Per wave merge:** `.venv/bin/python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_setup_wizard.py` -- Existing 18 tests need major rewrite/expansion to cover new multi-provider flow
- [ ] Tests for `_mask_key()`, `_parse_provider_selection()`, `_browse_models()`, `_build_budget_preview()`
- [ ] Tests for Ctrl+C at each wizard step
- [ ] Tests for existing config re-entry (Add/Reconfigure/Start fresh)
- [ ] Tests for `validate_api_key()` with model_id parameter

## Sources

### Primary (HIGH confidence)
- `src/setup_wizard.py` -- Current implementation (306 lines), direct code review
- `src/env_manager.py` -- .env management, direct code review
- `src/model_discovery.py` -- Live model queries, direct code review
- `src/model_registry.py` -- ModelConfig, registry, direct code review
- `src/execution_summary.py` -- estimate_cost(), direct code review
- `src/config_manager.py` -- Config persistence, direct code review
- `src/config.py` -- ExperimentConfig dataclass, direct code review
- `data/default_models.json` -- Default model configurations, direct file review
- `tests/test_setup_wizard.py` -- Existing 18 tests, direct code review
- python-dotenv `set_key()` behavior -- Verified empirically: creates file if missing, updates in-place, preserves other keys

### Secondary (MEDIUM confidence)
- `src/cli.py` -- CLI entry point, `propt setup` subcommand routing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and in use
- Architecture: HIGH - Building on established patterns (input_fn injection, env_manager, model_registry)
- Pitfalls: HIGH - Verified empirically (set_key behavior) and via code review (os.environ gap, hardcoded models)

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable domain, no external dependencies changing)
