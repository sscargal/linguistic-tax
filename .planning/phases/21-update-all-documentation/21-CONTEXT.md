# Phase 21: Update All Documentation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all user-facing documentation to reflect v2.0 changes: configurable models via ModelRegistry, .env API key management, overhauled multi-provider setup wizard, live model discovery, 3 new modules (model_registry, env_manager, model_discovery). No new features — documentation updates only. RDD and experiment spec docs are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Model and pricing references
- Keep the model/pricing table as a "defaults example" labeled "Default models (configurable via `propt setup`)"
- Update glossary entries to reference `ModelRegistry` in `src/model_registry.py` (replace old `MODELS in src/config.py` and `PREPROC_MODEL_MAP in src/config.py` references)
- Standardize Python version to 3.12+ across all docs (align with CLAUDE.md and pyproject.toml)
- Expand `propt list-models` CLI docs: add `--json` flag to table, show live provider query output with context windows and pricing columns
- Update all sample terminal output to reflect v2.0 actual output
- Change experiment design diagram from "4 Target Models" to "N Target Models (configurable)"
- Present work item count as formula: `prompts x noise x interventions x models x reps` with default example (~82K with 4 models)
- Update `propt set-config` examples to use v2.0 config schema
- Update bibtex citation block with author name and arxiv URL placeholder
- Silent update approach: no "What's New in v2.0" section — just update everything to reflect current state
- Do a systematic sweep across ALL docs for stale references to old config.py constants, hardcoded model names, and v1.0 patterns

### API keys and .env files
- Lead with .env as primary method for API key management
- Present .env and `export` commands as two equal options in getting-started guide
- Simplify Quick Start to: `git clone`, `uv sync`, `propt setup` (wizard handles keys and config)

### Setup wizard documentation
- Rewrite the wizard section in getting-started.md with new multi-provider flow (multi-provider loop, .env creation, validation pings, budget preview)
- Wizard-first approach: emphasize `propt setup` as primary configuration path
- Minimal manual config section — `propt set-config` basics with link to CLI reference
- Mention budget preview feature in wizard description
- Keep existing walkthrough scenarios (update content to v2.0, no new scenarios added)

### Architecture and structure updates
- Keep 4 default providers in pipeline architecture Mermaid diagram with a note that providers are configurable
- Expand CLI command map diagram: add model_registry, model_discovery, env_manager nodes; show `list-models` -> model_discovery, `setup` -> model_registry + env_manager paths
- Update project structure: 21 Python modules (was 18), 25 test files; add model_registry.py, env_manager.py, model_discovery.py with one-line descriptions
- Brief one-liner module descriptions for 3 new modules in architecture doc (not full writeups)
- Text description (no new diagram) for the ModelRegistry config flow (default_models.json -> ModelRegistry -> consumers)
- Add `data/default_models.json` to project structure tree and data flow documentation
- Add v2.0 design decisions to architecture doc's Design Decisions section (registry pattern, .env management, live model discovery)
- Claude verifies: API call lifecycle diagram and DB schema for any v2.0 changes before updating
- docs/README.md index: verify existing links and descriptions, no new entries

### Contributing guide
- Update "adding models" section to explain ModelRegistry, default_models.json, and new provider patterns
- Update any references to old config.py constants

### Analysis guide
- Update SQLite query examples that assume hardcoded model names to work with any configured models

### CLAUDE.md
- Full review pass: update module count, architecture section, any stale references to config.py constants or v1.0 patterns

### Doc structure
- Allow restructuring where current structure is misleading for v2.0 (e.g., getting-started wizard section may need reordering)
- Otherwise update in place within existing section structure

### Claude's Discretion
- Exact Mermaid diagram layout and styling for new/updated diagrams
- How to word the "configurable" annotations on diagrams and tables
- Whether to add brief transition notes where sections were restructured
- How to structure the contributing guide's updated model addition section

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documents to update
- `README.md` — Root readme with quick start, CLI reference, models table, project structure, glossary, sample output, citation
- `docs/getting-started.md` — Setup walkthrough, env vars, manual config, pilot run guide
- `docs/architecture.md` — Module descriptions, Mermaid diagrams, data flow, design decisions, DB schema
- `docs/contributing.md` — Dev setup, model addition guide, testing patterns
- `docs/analysis-guide.md` — Statistical interpretation, SQLite query examples
- `docs/README.md` — Documentation index page with links
- `CLAUDE.md` — Project instructions for Claude Code (module list, architecture section)

### Source of truth for v2.0 changes
- `src/model_registry.py` — ModelConfig dataclass, ModelRegistry class, replaces hardcoded MODELS/PRICE_TABLE/PREPROC_MODEL_MAP
- `src/env_manager.py` — .env file creation and management
- `src/model_discovery.py` — Live model listing from provider APIs
- `src/setup_wizard.py` — Overhauled multi-provider wizard with .env creation, validation pings, budget preview
- `src/config.py` — ExperimentConfig v2 with models list (no more flat model fields)
- `data/default_models.json` — Default model configurations for 4 providers
- `src/cli.py` — CLI entry point (source of truth for subcommand flags including list-models --json)

### Prior documentation context
- `.planning/phases/12-comprehensive-documentation-and-readme-for-new-users/12-CONTEXT.md` — Phase 12 decisions on doc tone, structure, Mermaid format, audience

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All existing docs follow Phase 12 conventions: Mermaid diagrams, technical-direct tone, American English
- docs/README.md index page already structured with tables and quick links
- CLAUDE.md has established format for architecture section

### Established Patterns
- 21 Python modules in `src/` with `src.` import prefix
- 25 test files in `tests/`
- `propt` CLI with subcommands registered via argparse subparsers
- `data/default_models.json` feeds ModelRegistry at import time
- `.env` file at project root for API keys (python-dotenv integration)

### Integration Points
- All docs cross-reference each other via relative links
- README.md links to docs/ guides
- docs/README.md serves as navigation hub
- Architecture diagrams reference source module paths

</code_context>

<specifics>
## Specific Ideas

- Quick Start should be as minimal as possible: clone, sync, setup — wizard handles the rest
- The systematic sweep for stale references is critical — grep for patterns like `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`, `config.py` in docs to find all stale refs
- Sample output should be regenerated from actual v2.0 code where possible, not hand-crafted
- The bibtex citation should include author placeholder and arxiv URL placeholder, ready for when the paper is published

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-update-all-documentation*
*Context gathered: 2026-03-26*
