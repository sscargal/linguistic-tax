# Phase 14: CLI Config Subcommands for Viewing and Modifying Settings - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add subcommands to the existing CLI for viewing, modifying, validating, and diffing experiment configuration. The `show-config` command displays all properties with current values, defaults, and modification indicators. `set-config` modifies any property with type coercion and immediate validation. `reset-config` reverts properties to defaults. Additional commands: `validate`, `diff`, `list-models`. Also: rename the CLI entry point from `python src/cli.py` to `propt` (registered as a pyproject.toml script entry), and add shell tab completion for property names.

</domain>

<decisions>
## Implementation Decisions

### CLI naming and structure
- Top-level command name: `propt` (short for "prompt optimizer") — registered as a pyproject.toml console_scripts entry point
- Flat top-level subcommands (not nested under `config`): `setup`, `show-config`, `set-config`, `reset-config`, `validate`, `diff`, `list-models`
- Existing `setup` subcommand remains unchanged
- Existing scripts (`run_experiment.py`, `pilot.py`, etc.) continue to work as-is

### show-config command
- Default output: human-readable terminal table with 3 columns: Property, Value, Default
- Both columns always show the actual value (no blanks or dashes for matching values)
- Modified properties marked with `*` indicator
- Supports `--json` flag for machine-readable JSON output
- Supports `--changed` flag to filter to overridden properties only
- Supports `--verbose` flag to add a description column explaining each property
- Supports querying a single property: `propt show-config temperature` prints just the value
- Single-property query with `--json` wraps in JSON: `{"temperature": 0.5}`

### set-config command
- Auto-creates config file if it doesn't exist (sparse override pattern — only the set value is written)
- Accepts multiple key-value pairs: `propt set-config temperature 0.5 repetitions 3`
- Type coercion auto-detected from ExperimentConfig default type:
  - `str` → string as-is
  - `int` → int conversion
  - `float` → float conversion
  - `tuple` → comma-separated parsing (e.g., `0.05,0.10,0.20` → tuple of floats)
- Validates immediately before saving — rejects invalid model names, out-of-range values, missing paths
- Shows change summary after setting: `temperature: 0.0 → 0.5`

### reset-config command
- Removes the key from the sparse config file, reverting to ExperimentConfig default
- `propt reset-config temperature` → removes temperature override
- `propt reset-config --all` → resets entire config to defaults (deletes the file or empties it)

### validate command
- `propt validate` — runs validate_config on current effective config, reports all errors
- Exit code 0 for valid, non-zero for errors
- Useful as a pre-flight check before experiment execution

### diff command
- `propt diff` — shows only properties that differ from defaults, in a diff-like format
- Shows old (default) and new (current) values side by side

### list-models command
- `propt list-models` — prints all valid model strings from PRICE_TABLE with pricing info
- Useful companion when deciding which model to set

### Tab completion
- Generate shell completions for property names in `set-config`, `show-config`, `reset-config`
- Scope: bash and zsh at minimum

### Claude's Discretion
- Exact table formatting implementation (rich library vs manual formatting vs simple columnar)
- Tab completion implementation approach (argcomplete, custom, or shtab)
- Exact diff output format
- Property description text for --verbose mode
- Whether `list-models` groups by provider or shows a flat list

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI architecture (Phase 13 foundation)
- `src/cli.py` — Current CLI entry point with argparse subparsers, `build_cli()` and `main()` functions
- `src/config_manager.py` — Config file I/O: `load_config`, `save_config`, `validate_config`, `get_full_config_dict`, `find_config_path`
- `src/setup_wizard.py` — Setup wizard implementation (Phase 13) — must remain functional

### Configuration
- `src/config.py` — `ExperimentConfig` frozen dataclass (all fields and defaults), `PRICE_TABLE`, `MODELS`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`

### Phase 13 context (upstream decisions)
- `.planning/phases/13-guided-setup-wizard-for-project-configuration/13-CONTEXT.md` — Config persistence decisions: sparse override pattern, JSON format, project-directory location

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config_manager.load_config()`: loads JSON + merges with ExperimentConfig defaults — already handles the sparse override pattern
- `config_manager.save_config()`: writes dict to JSON with tuple→list conversion
- `config_manager.validate_config()`: validates model names, rates, paths, repetitions, temperature — reuse for `validate` and `set-config` validation
- `config_manager.get_full_config_dict()`: returns all ExperimentConfig fields as dict — powers show-config
- `ExperimentConfig` dataclass fields: the source of truth for property names, types, and defaults
- `PRICE_TABLE`: model→pricing dict — powers list-models command

### Established Patterns
- argparse with subparsers in `cli.py` — extend with new subcommands
- `logging` module for output (not `print()`) — per CLAUDE.md convention
- `dataclasses.fields()` for introspecting ExperimentConfig — already used in config_manager
- isinstance check on defaults for tuple detection — established in Phase 13

### Integration Points
- `build_cli()` in `src/cli.py` — add new subcommand parsers here
- `pyproject.toml` — add `[project.scripts]` entry: `propt = "src.cli:main"`
- `config_manager.save_config()` — set-config will load, modify, validate, then save
- `config_manager.find_config_path()` — all commands need to locate the config file

</code_context>

<specifics>
## Specific Ideas

- The user refers to the toolkit as "the slicer" — but the CLI command is `propt` (prompt optimizer)
- Change summary on set should show the transition: `temperature: 0.0 → 0.5`
- Tab completion for property names is in scope — reduces friction for users who don't remember exact field names
- `list-models` with pricing helps users choose cost-effective models without reading source code

</specifics>

<deferred>
## Deferred Ideas

- **`propt doctor`** — Standalone environment health check (Python version, packages, API keys). Extracted from setup wizard as independent command.
- **Config profiles** — Named profiles (e.g., "pilot", "full-run", "cheap") for switching between parameter sets. From Phase 13 deferred list.
- **`propt export --latex`** — Export config as LaTeX table for paper appendix. From Phase 13 deferred list.
- **`propt run` / `propt pilot`** — Wrap existing scripts as CLI subcommands for unified experience.
- **Config file versioning** — Schema version field with auto-migration for future changes. From Phase 13 deferred list.
- **`propt cost-estimate`** — Compute expected API cost from current config. Relates to Phase 15 pre-execution gate.

</deferred>

---

*Phase: 14-cli-config-subcommands-for-viewing-and-modifying-settings*
*Context gathered: 2026-03-25*
