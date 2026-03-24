# Phase 13: Guided Setup Wizard for Project Configuration - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a guided setup wizard as a CLI subcommand that helps new users configure the Linguistic Tax toolkit through a Q&A flow. Creates a JSON config file in the project directory with all configurable properties and sensible defaults. Also create the CLI entry point (`cli.py`) with subcommand architecture that Phase 14 will extend. This phase produces working code — design and implement.

</domain>

<decisions>
## Implementation Decisions

### Config persistence
- Config file format: JSON (zero dependency — Python `json` module handles read + write)
- Config file location: project directory (alongside `src/`, `data/`, etc.) — NOT a global dotfile
- File name: `config.json` (or similar — Claude's discretion on exact name to avoid confusion with `.planning/config.json`)
- All configurable properties from `ExperimentConfig` are included in the config file with sensible defaults
- Runtime behavior: `ExperimentConfig` retains hardcoded defaults. On load, slicer checks for config file — values present override dataclass defaults, missing keys fall back to hardcoded defaults
- Config file only needs to contain what the user changed (sparse override pattern)

### Wizard flow
- Essential config only — wizard asks about: model provider, target model, preproc model, API key env var name, paths (prompts, matrix, results DB)
- Power users edit the JSON directly for advanced settings (seeds, noise rates, repetitions, temperature, rate limits)
- Model selection: pick provider → auto-fills default target + preproc model → user can accept or override
- API key validation: make a minimal test API call to confirm the key works (catches bad keys early, ~$0.001 cost)
- All non-wizard properties are still written to config file with defaults so users can see and edit them

### CLI architecture
- New dedicated CLI entry point: `src/cli.py` with subcommand architecture (argparse subparsers)
- `setup` (or `init`) subcommand launches the wizard
- Phase 14 will add `config show`, `config set`, etc. as additional subcommands
- Existing scripts (`run_experiment.py`, `grade_results.py`, etc.) continue to work as-is — CLI is additive, not replacing

### Auto-detection
- If a user tries to run an experiment and no config file exists, print a message: "No config found. Run `python src/cli.py setup` first." and exit
- Does NOT auto-launch the wizard — guides users without surprising them, safe for CI/scripted environments

### Config validation (in scope)
- On config load, validate: model strings match `PRICE_TABLE` keys, paths exist or are creatable, noise rates are in valid ranges (0-1), repetitions > 0, temperature >= 0
- Catch misconfigurations before experiments start with clear error messages

### Environment check (in scope)
- Wizard checks: Python version (3.11+), required packages installed, API key environment variables are set and non-empty
- Helps new users debug setup issues during initial configuration
- Report clear pass/fail for each check

### Claude's Discretion
- Exact config file name (avoiding confusion with `.planning/config.json`)
- Wizard UX details (colors, progress indicators, confirmation prompts)
- argparse vs click/typer for CLI framework (argparse preferred to match existing patterns)
- How to structure the config loading integration with ExperimentConfig
- Exact validation rules and error message formatting

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Configuration
- `src/config.py` — Current `ExperimentConfig` frozen dataclass, `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`, all module-level constants that define configurable properties
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for experimental parameters (the source of truth for default values)

### Existing CLI patterns
- `src/run_experiment.py` — `_build_parser()` argparse pattern, `if __name__ == "__main__"` entry point
- `src/pilot.py` — Another argparse CLI entry point for reference
- `src/api_client.py` — API call patterns for the validation test call

### Phase 14 (downstream consumer)
- `.planning/phases/14-cli-config-subcommands-for-viewing-and-modifying-settings/` — Phase 14 will extend the CLI created here with config viewing/modification subcommands

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExperimentConfig` dataclass (`src/config.py`): frozen, all defaults defined — wizard writes overrides, loader merges
- `PRICE_TABLE` dict: maps model strings to pricing — useful for wizard to show cost info during model selection
- `PREPROC_MODEL_MAP` dict: maps target model → preproc model — wizard uses this for auto-selection
- `MODELS` tuple: list of supported target models — wizard presents these as choices per provider
- `compute_cost()` function: can be used in environment check to show estimated costs

### Established Patterns
- argparse with `_build_parser()` pattern in `run_experiment.py` — new CLI should follow this
- Environment variables for API keys (not hardcoded) — `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`
- `logging` module for all output (not `print()`) — CLAUDE.md convention

### Integration Points
- `ExperimentConfig` needs a class method or factory function to load from config file + merge with defaults
- `run_experiment.py` needs a config-file-missing check early in `__main__` block
- Other scripts (`grade_results.py`, `analyze_results.py`, etc.) may also need the config check — or just the experiment runner

</code_context>

<specifics>
## Specific Ideas

- User refers to the toolkit as "the slicer" — use this terminology in wizard prompts and messages where appropriate
- The config file must include ALL pertinent variables (not just wizard-asked ones) so users can configure anything by editing the file
- Sensible defaults must be provided for every property
- Phase 14 will extend the same CLI with config subcommands — design the CLI architecture to be extensible

</specifics>

<deferred>
## Deferred Ideas

- **Config profiles** — Named profiles (e.g., "pilot", "full-run", "cheap") that switch between model/parameter sets. Future phase.
- **Dry-run / cost preview** — Show estimated cost and call count before running experiments. Relates to Phase 15 (pre-execution summary gate).
- **Config migration/versioning** — Version the config schema with auto-migration for future changes. Future phase.
- **Multi-provider experiments** — Configure multiple providers at once for comparative runs. Future phase.
- **Experiment templates** — Pre-built configs for common scenarios (quick pilot, full matrix, format experiments). Future phase.
- **Config diff** — Show changes between current config and defaults for reproducibility reporting. Future phase.
- **Export config to paper appendix** — Auto-generate LaTeX table of experimental parameters from config. Future phase.

</deferred>

---

*Phase: 13-guided-setup-wizard-for-project-configuration*
*Context gathered: 2026-03-24*
