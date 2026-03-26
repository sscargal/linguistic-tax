# Phase 19: Setup Wizard Overhaul - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Overhaul the setup wizard to support free-text model entry, multi-provider configuration in a single session, .env API key management, model validation via ping, and budget preview before committing. The existing single-provider wizard (`src/setup_wizard.py`) is replaced entirely.

</domain>

<decisions>
## Implementation Decisions

### Wizard flow structure
- **Provider selection first:** Multi-select from Anthropic/Google/OpenAI/OpenRouter at the start ("Which providers do you want to use?"), then configure each selected provider in sequence
- **Step order within providers:** All API keys upfront (for all selected providers) -> then all model selections. Keys and models are separate phases of the wizard
- **Existing config handling:** If config already exists, show current providers/models and offer: "Add provider / Reconfigure / Start fresh". Pre-fill existing values as defaults
- **Environment check:** Keep the Python version + package check at the start of the wizard (already implemented)
- **File paths:** Show paths being used (informational) but don't prompt for changes. Researcher uses `propt config set` if needed
- **API key handling:** Show masked existing key (e.g., `sk-ant-...7x3f`) with "Keep this? (Y/n)". Only prompt for new key if user says no or key is missing
- **Key write timing:** Write each key to .env immediately via `env_manager.write_env()` AND load into `os.environ` immediately so validation pings work within the same session
- **Validation ping failure:** Warn and continue. "Warning: Could not reach [model]. Keep this model? (Y/n)" -- let user decide
- **Validation ping model:** Use the actual selected target model, not a cheap proxy. Confirms the specific model ID works with the user's key
- **End-of-wizard confirmation:** Show full summary (providers, models, key status, budget estimate) with "Save this configuration? (Y/n)" before writing config file
- **Non-interactive mode:** Preserve `--non-interactive` flag that writes defaults without prompting (CI/scripting use)
- **Keyboard interrupt:** Handle Ctrl+C gracefully at every point in the multi-step flow (partial .env writes should not corrupt state)

### Free-text model entry
- **Primary entry:** Show default with free text: `Target model for Anthropic [claude-sonnet-4-20250514]: ` -- Enter accepts default, or type any model ID
- **Live model browser:** Type `list` at any model prompt to browse available models from the provider's live API
- **Browser UX:** Paginated list, 20 models per page, sorted by newest. Support substring search (case-insensitive) to filter. Navigation: n/p for next/prev, number to select, q to cancel
- **Browser fallback:** If provider API is unreachable, fall back to registry models from `default_models.json` with warning
- **Browser scope:** `list` works at both target model and preproc model prompts
- **Preproc model entry:** Auto-assigned from registry mapping, with override option: "Pre-processor model: claude-haiku-4-5 (auto-assigned). Press Enter to accept or type model ID:"
- **Custom model pricing:** For models not in the registry, skip pricing -- show as "pricing unknown" in budget preview. compute_cost falls back to $0.00 (Phase 16 behavior)
- **Model ID validation:** Accept any typed model ID. Validation ping (already decided) catches invalid IDs. No pre-validation against live list

### Budget preview
- **Timing:** After all models chosen, before the save confirmation step
- **Detail level:** Per-model cost estimate plus total. e.g.:
  ```
  claude-sonnet-4: ~$12.50
  gemini-2.0-flash: ~$1.20
  Total: ~$13.70
  ```
- **Scope:** Show both pilot (20 prompts) and full matrix (200 prompts) cost estimates
- **Preproc costs:** Show separately: "Pre-processing: ~$0.40" as its own line
- **Unknown pricing:** Show as "pricing unknown" per model. Total note: "Total (excluding unknown): ~$X.XX"
- **Budget warning:** Warn if full matrix estimate exceeds $50
- **Implementation:** Use existing `execution_summary.estimate_cost()` under the hood

### Target vs preproc explanation
- **When:** Before model selection starts, after provider selection. One explanation, not repeated per provider
- **Depth:** 2-3 sentences. Explain what target models do, what preproc models do, recommend cheap/fast models for preproc
- **Preproc scope choice:** Ask user: "Use a separate pre-processor per provider, or one global pre-processor?" Default to per-provider (matches existing architecture). If global, show as single line in summary
- **Preproc recommendation:** Mention that preproc models should be cheap and fast (Haiku, Flash) since they run on every prompt

### Additional features (in scope)
- **Wizard re-entry:** Detect existing config and offer: Add provider / Reconfigure / Start fresh
- **Post-setup next steps:** After saving, show guided next steps: "Run 'propt pilot' to test with 20 prompts" or "Run 'propt list-models' to verify"
- **Config validation summary:** Run `validate_config()` after all models configured, show warnings before save confirmation

### Claude's Discretion
- Exact wording of explanatory text and prompts
- Internal function decomposition and helper structure
- Error message formatting
- How the paginated model browser renders (exact formatting)
- How to compute budget estimate from selected models (wiring to execution_summary)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` -- WIZ-01 through WIZ-06 and DSC-03 define the acceptance criteria for this phase

### Existing wizard
- `src/setup_wizard.py` -- Current single-provider wizard being replaced. Preserve input_fn injection pattern for testability

### Supporting modules
- `src/env_manager.py` -- .env read/write with chmod 600. Use write_env() for key persistence
- `src/model_discovery.py` -- Live model listing from all 4 providers. discover_all_models() for live browser
- `src/model_registry.py` -- ModelConfig, ModelRegistry, default model data, preproc mappings
- `src/execution_summary.py` -- estimate_cost() for budget preview computation
- `src/config_manager.py` -- get_full_config_dict(), save_config(), validate_config()

### Data
- `data/default_models.json` -- Curated default model configs (fallback when live API unreachable)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `env_manager.write_env()`: Already creates .env with chmod 600, handles missing file creation
- `env_manager.load_env()`: Loads .env without overriding existing env vars
- `env_manager.check_keys()`: Checks which providers have API keys set
- `validate_api_key()`: Already does validation ping per provider (needs update to use selected model instead of hardcoded cheap model)
- `model_discovery.discover_all_models()`: Parallel provider query with timeout and fallback
- `model_discovery._get_fallback_models()`: Registry fallback when API unreachable
- `execution_summary.estimate_cost()`: Cost estimation from work items
- `check_environment()`: Python version + package check (keep as-is)
- `_build_providers()`: Builds provider list from registry (keep pattern)

### Established Patterns
- `input_fn` parameter injection for wizard testability (Phase 13 decision -- preserve this)
- `_build_providers()` builds provider config from registry at runtime (Phase 17 decision)
- `validate_config()` warns instead of rejecting unknown model IDs (Phase 16 decision)
- Unknown preproc models warn and return model-itself as fallback (Phase 17 decision)

### Integration Points
- CLI entry point: `propt setup` subcommand in `src/cli.py` or `src/main.py`
- Config persistence: `config_manager.save_config()` writes to `experiment_config.json`
- .env file: Project root `.env` for API keys
- Model registry: `registry.reload()` after config changes to update runtime state

</code_context>

<specifics>
## Specific Ideas

- Flow should feel like a modern CLI wizard (think `npm init` or `gh auth login`) -- clear steps, sensible defaults, minimal friction
- "All keys upfront, then all models" was chosen to separate concerns and avoid mid-flow API dependency issues
- User explicitly wants the live model browser to be a secondary option (type 'list'), not the primary flow
- Models change frequently -- the free-text entry is the primary mechanism, live browser is supplementary
- Preproc scope choice (per-provider vs global) lets the user decide their preference

</specifics>

<deferred>
## Deferred Ideas

- **Config export/import** -- `propt config export` / `propt config import` for sharing configs between machines
- **Model removal from config** -- Wizard option to remove a previously configured provider/model
- **API key rotation** -- When updating .env, keep old key as a comment (`# OLD_KEY=...`) as safety net

</deferred>

---

*Phase: 19-setup-wizard-overhaul*
*Context gathered: 2026-03-26*
