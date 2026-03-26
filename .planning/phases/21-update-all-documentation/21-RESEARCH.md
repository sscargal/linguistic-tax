# Phase 21: Update All Documentation - Research

**Researched:** 2026-03-26
**Domain:** Documentation update (Markdown, Mermaid diagrams, cross-referencing)
**Confidence:** HIGH

## Summary

Phase 21 is a documentation-only phase. No code changes -- every deliverable is a Markdown file update. The goal is to make all user-facing documentation reflect the v2.0 architecture: configurable models via ModelRegistry, .env-based API key management, overhauled setup wizard, live model discovery, and 3 new modules (model_registry, env_manager, model_discovery).

The scope is well-defined: 7 documents need updating (README.md, docs/getting-started.md, docs/architecture.md, docs/contributing.md, docs/analysis-guide.md, docs/README.md, CLAUDE.md). The changes are primarily search-and-replace for stale references (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, "config.py" as source of model data), plus structural rewrites for the setup wizard section and contributing guide's "adding models" section.

**Primary recommendation:** Work document-by-document with a systematic grep sweep at the end. Each document has a clear set of stale patterns to replace and sections to rewrite. The final task should be a cross-document consistency check.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Keep the model/pricing table as a "defaults example" labeled "Default models (configurable via `propt setup`)"
- Update glossary entries to reference `ModelRegistry` in `src/model_registry.py` (replace old `MODELS in src/config.py` and `PREPROC_MODEL_MAP in src/config.py` references)
- Standardize Python version to 3.12+ across all docs (align with CLAUDE.md and pyproject.toml)
- Expand `propt list-models` CLI docs: add `--json` flag to table, show live provider query output with context windows and pricing columns
- Update all sample terminal output to reflect v2.0 actual output
- Change experiment design diagram from "4 Target Models" to "N Target Models (configurable)"
- Present work item count as formula: `prompts x noise x interventions x models x reps` with default example (~82K with 4 models)
- Update `propt set-config` examples to use v2.0 config schema
- Update bibtex citation block with author name and arxiv URL placeholder
- Silent update approach: no "What's New in v2.0" section -- just update everything to reflect current state
- Do a systematic sweep across ALL docs for stale references to old config.py constants, hardcoded model names, and v1.0 patterns
- Lead with .env as primary method for API key management
- Present .env and `export` commands as two equal options in getting-started guide
- Simplify Quick Start to: `git clone`, `uv sync`, `propt setup` (wizard handles keys and config)
- Rewrite the wizard section in getting-started.md with new multi-provider flow (multi-provider loop, .env creation, validation pings, budget preview)
- Wizard-first approach: emphasize `propt setup` as primary configuration path
- Minimal manual config section -- `propt set-config` basics with link to CLI reference
- Mention budget preview feature in wizard description
- Keep existing walkthrough scenarios (update content to v2.0, no new scenarios added)
- Keep 4 default providers in pipeline architecture Mermaid diagram with a note that providers are configurable
- Expand CLI command map diagram: add model_registry, model_discovery, env_manager nodes; show `list-models` -> model_discovery, `setup` -> model_registry + env_manager paths
- Update project structure: 21 Python modules (was 18), 25 test files; add model_registry.py, env_manager.py, model_discovery.py with one-line descriptions
- Brief one-liner module descriptions for 3 new modules in architecture doc (not full writeups)
- Text description (no new diagram) for the ModelRegistry config flow (default_models.json -> ModelRegistry -> consumers)
- Add `data/default_models.json` to project structure tree and data flow documentation
- Add v2.0 design decisions to architecture doc's Design Decisions section (registry pattern, .env management, live model discovery)
- Claude verifies: API call lifecycle diagram and DB schema for any v2.0 changes before updating
- docs/README.md index: verify existing links and descriptions, no new entries
- Update "adding models" section in contributing.md to explain ModelRegistry, default_models.json, and new provider patterns
- Update any references to old config.py constants in contributing.md
- Update SQLite query examples in analysis-guide.md that assume hardcoded model names to work with any configured models
- CLAUDE.md: Full review pass: update module count, architecture section, any stale references to config.py constants or v1.0 patterns
- Allow restructuring where current structure is misleading for v2.0 (e.g., getting-started wizard section may need reordering)
- Otherwise update in place within existing section structure

### Claude's Discretion
- Exact Mermaid diagram layout and styling for new/updated diagrams
- How to word the "configurable" annotations on diagrams and tables
- Whether to add brief transition notes where sections were restructured
- How to structure the contributing guide's updated model addition section

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

This phase uses no libraries or packages. All work is Markdown editing with Mermaid diagram syntax.

### Core Tools
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown | N/A | Documentation format | GitHub renders natively, git-diffable |
| Mermaid | N/A | Diagrams in Markdown | GitHub renders natively, text-based, established in Phase 12 |
| SQLite queries | N/A | Sample queries in analysis guide | Existing pattern from Phase 12 docs |

### No Alternatives Needed
This is pure documentation work. No tooling decisions required.

## Architecture Patterns

### Document Inventory and Change Scope

Each document has a specific set of changes needed. This inventory drives plan structure.

#### 1. README.md (root) -- HEAVY changes
**Stale patterns found:**
- `Python >= 3.11` (line 26) -- change to `3.12+`
- `18 Python modules` (line 279) -- change to `21`
- `19 test files` (line 298) -- change to `25`
- `9 subcommands` (lines 71, 283) -- correct (still 9, verified)
- `MODELS in src/config.py` and `PREPROC_MODEL_MAP in src/config.py` in glossary (lines 371, 373-374) -- change to ModelRegistry refs
- Quick Start section (lines 13-20) -- simplify to clone/sync/setup per decision
- API Keys section (lines 39-48) -- lead with .env, add `export` as alternative
- Configuration section (lines 54-67) -- rewrite wizard description for multi-provider flow
- Models and Pricing table (lines 263-274) -- relabel as "Default models (configurable via `propt setup`)"
- Experiment Design diagram (line 226) -- change "4 Target Models" to "N Target Models (configurable)"
- Work item count (line 228) -- present as formula with default example
- Project Structure tree (lines 277-317) -- add 3 new modules, `data/default_models.json`, update counts
- `list-models` in CLI table (line 82) -- add `--json` flag
- `set-config` examples (lines 164-165) -- update to v2.0 config schema (no more `claude_model`)
- Bibtex citation (lines 381-387) -- add author name and arxiv URL placeholder
- ExperimentConfig sample (lines 252-264 in architecture.md, referenced here) -- not in README but relevant

#### 2. docs/getting-started.md -- HEAVY changes
**Stale patterns found:**
- `Python >= 3.11` (lines 7, 347) -- change to `3.12+`
- Wizard walkthrough (lines 55-66) -- rewrite entirely for multi-provider flow with .env creation, validation pings, budget preview
- `Set Environment Variables` section (lines 32-48) -- restructure: .env first, export as alternative
- Configuration section -- wizard-first approach, minimal manual config
- `9 subcommands` (line 27) -- correct (still 9)
- No mention of `model_registry`, `env_manager`, `model_discovery` -- add where relevant
- Hardcoded model names in provider table (lines 42-47) -- label as defaults
- Sample output (lines 134-161) -- regenerate from v2.0 output if possible

#### 3. docs/architecture.md -- HEAVY changes
**Stale patterns found:**
- Module Reference tables -- missing 3 new modules (model_registry.py, env_manager.py, model_discovery.py)
- Configuration Layer table (line 130) -- references `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP` in config.py
- CLI command map diagram (lines 49-84) -- add model_registry, model_discovery, env_manager nodes
- Pipeline architecture diagram (lines 12-27) -- add configurable note
- `RATE_LIMIT_DELAYS` reference (line 122) -- update to registry
- Configuration System section (lines 248-284) -- ExperimentConfig sample is v1.0 format (claude_model, gemini_model fields)
- Validation section (lines 276-284) -- references `PRICE_TABLE` checks
- No Design Decisions section exists yet -- add one
- No mention of `data/default_models.json` in data flow

#### 4. docs/contributing.md -- MODERATE changes
**Stale patterns found:**
- "Adding a New Model Provider" section (lines 92-170) -- entirely v1.0 pattern (add to MODELS tuple, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS in config.py)
- Project Structure Overview (lines 27-46) -- missing 3 new modules, shows `config.py # ExperimentConfig, MODELS, PRICE_TABLE, constants`
- `from src.config import MODELS` in code conventions (line 83) -- stale import example
- `sample_config` fixture description (line 225) -- may need update for v2.0 ExperimentConfig

#### 5. docs/analysis-guide.md -- LIGHT changes
**Stale patterns found:**
- SQL queries are model-agnostic already (use `model` column, no hardcoded names) -- GOOD
- No references to config.py constants -- GOOD
- May need to verify the module table descriptions still accurate
- **Minimal changes needed** -- mostly a verification pass

#### 6. docs/README.md -- LIGHT changes
- Verify existing links work -- all point to files that still exist
- Descriptions may need minor tweaks if doc content shifted
- No structural changes per decision

#### 7. CLAUDE.md -- MODERATE changes
**Stale patterns found:**
- Architecture tree (lines 16-37) -- missing 3 new modules, missing `data/default_models.json`
- Only lists 7 src/ modules -- should list key modules including new ones
- No mention of model_registry, env_manager, model_discovery
- `Pre-processor calls use a CHEAP model (Haiku or Flash)` (line 66) -- should mention configurable
- Module count not explicitly stated but implied
- Tech Stack mentions only Anthropic and Google APIs -- should include OpenAI and OpenRouter

### Stale Reference Patterns (Grep Targets)

These patterns should be searched across all 7 docs and replaced:

| Pattern | Replacement | Notes |
|---------|-------------|-------|
| `MODELS` (as config constant) | `ModelRegistry` / `data/default_models.json` | Context-dependent wording |
| `PRICE_TABLE` | `ModelRegistry` pricing | Registry provides pricing |
| `PREPROC_MODEL_MAP` | `ModelRegistry` preproc mappings | Registry maps target->preproc |
| `RATE_LIMIT_DELAYS` | `ModelRegistry` rate limits | Registry provides delays |
| `config.py` (as source of model data) | `model_registry.py` / `data/default_models.json` | config.py still exists for ExperimentConfig |
| `Python >= 3.11` / `Python 3.11` | `Python >= 3.12` / `Python 3.12+` | Per CLAUDE.md and pyproject.toml |
| `18 Python modules` | `21 Python modules` | 21 .py files in src/ (including __init__.py) |
| `19 test files` | `25 test files` | 25 .py files in tests/ |
| `claude_model` / `gemini_model` / `openai_model` / `openrouter_model` (as config fields) | `models` list | v2.0 ExperimentConfig uses models list |

### Recommended Plan Structure

Split by document grouping for manageable plan sizes:

1. **Plan 1: README.md + CLAUDE.md** -- The two root-level docs that define the project identity. Heavy overlap in content (project structure, tech stack). Do together for consistency.
2. **Plan 2: docs/getting-started.md** -- Largest rewrite (wizard section). Standalone plan.
3. **Plan 3: docs/architecture.md + docs/contributing.md** -- Architecture reference and contributor guide. Both need module table updates and similar stale reference fixes.
4. **Plan 4: docs/analysis-guide.md + docs/README.md + final sweep** -- Light-touch docs plus the systematic cross-document grep sweep for any remaining stale references.

### Anti-Patterns to Avoid
- **Fabricating sample output:** The CONTEXT.md says to regenerate from actual v2.0 code. Run `propt --help`, `propt list-models --help`, etc. to get real output rather than guessing.
- **Partial grep sweeps:** The systematic sweep must cover ALL docs, not just the ones being actively edited. Final plan should re-grep.
- **Updating .planning/ docs:** Only user-facing docs are in scope. Do not update planning phase docs, roadmap, research docs, etc.
- **Creating new sections/pages:** The CONTEXT.md explicitly says no new docs, no "What's New" section. Update in place.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding stale references | Manual reading | `grep -rn "PATTERN" *.md` | Systematic, catches all occurrences |
| Verifying CLI flags | Guessing from memory | Read `src/cli.py` add_argument calls | Source of truth for flag names |
| Module counts | Counting manually | `ls src/*.py \| wc -l` | Avoids off-by-one errors |
| Sample output | Hand-crafting | Run actual CLI commands or read code | Ensures accuracy |
| ExperimentConfig fields | Guessing v2.0 schema | Read `src/config.py` ExperimentConfig class | Source of truth |

## Common Pitfalls

### Pitfall 1: Inconsistent Python Version
**What goes wrong:** Some docs say 3.11, others say 3.12+.
**Why it happens:** CLAUDE.md says 3.12+, but Phase 12 docs were written when 3.11 was the requirement. PROJECT.md still says 3.11+.
**How to avoid:** Grep for all `3.11` references in docs, update to `3.12+`. Do NOT update .planning/ files (out of scope).
**Warning signs:** Any doc mentioning Python 3.11.

### Pitfall 2: config.py Still Exists
**What goes wrong:** Over-correcting by removing all references to config.py.
**Why it happens:** config.py still exists and still holds ExperimentConfig, NOISE_TYPES, INTERVENTIONS, derive_seed(), compute_cost(). Only the model data (MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS) moved to model_registry.
**How to avoid:** Only update references that specifically point to config.py for model/pricing data. References to ExperimentConfig, NOISE_TYPES, INTERVENTIONS in config.py remain correct.
**Warning signs:** Docs that say "config.py no longer exists" or remove all config.py references.

### Pitfall 3: ExperimentConfig v2 Schema
**What goes wrong:** Docs show the old ExperimentConfig with flat model fields (claude_model, gemini_model, etc.).
**Why it happens:** The architecture.md has a full ExperimentConfig code block from v1.0.
**How to avoid:** Replace with v2.0 ExperimentConfig showing `models: list[dict] | None = None` and `config_version: int = 2`. Read `src/config.py` for the current definition.
**Warning signs:** Any doc showing `claude_model`, `gemini_model`, `openai_model`, `openrouter_model` as config fields.

### Pitfall 4: Wizard Description Mismatch
**What goes wrong:** Wizard description doesn't match the actual v2.0 wizard flow.
**Why it happens:** The wizard was completely overhauled in Phase 19 (multi-provider loop, .env creation, validation pings, budget preview).
**How to avoid:** Read `src/setup_wizard.py` to understand the actual flow before writing the description. The CONTEXT.md lists the key features.
**Warning signs:** Wizard description mentioning "Provider selection -- choose from..." (v1.0 single-provider pattern).

### Pitfall 5: Stale set-config Examples
**What goes wrong:** Examples show `propt set-config claude_model "..."` which is a v1.0 pattern.
**Why it happens:** v2.0 uses a `models` list in ExperimentConfig, not flat model fields.
**How to avoid:** Check what config properties are actually settable via `propt set-config` by reading `src/config_commands.py` and `src/config_manager.py`.
**Warning signs:** Any `set-config` example using `claude_model`, `gemini_model`, etc.

### Pitfall 6: Missing data/default_models.json in Trees
**What goes wrong:** Project structure trees don't mention default_models.json.
**Why it happens:** This file was added in Phase 16 but docs were written in Phase 12.
**How to avoid:** Add `default_models.json` to every project structure tree with a one-liner description.
**Warning signs:** Any `data/` section that only shows prompts.json and experiment_matrix.json.

## Code Examples

### Current ExperimentConfig (v2.0) -- from src/config.py
```python
@dataclass
class ExperimentConfig:
    models: list[dict] | None = None
    config_version: int = 2
    base_seed: int = 42
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    type_a_weights: tuple[float, ...] = (0.40, 0.25, 0.20, 0.15)
    repetitions: int = 5
    temperature: float = 0.0
    prompts_path: str = "data/prompts.json"
    matrix_path: str = "data/experiment_matrix.json"
    results_db_path: str = "results/results.db"
```

### ModelConfig dataclass -- from src/model_registry.py
```python
@dataclass
class ModelConfig:
    model_id: str
    provider: str
    role: str
    preproc_model_id: str | None = None
    input_price_per_1m: float | None = None
    output_price_per_1m: float | None = None
    rate_limit_delay: float | None = None
```

### CLI list-models flags -- from src/cli.py
```python
models_parser = subparsers.add_parser("list-models", help="List available models with pricing")
models_parser.add_argument("--json", action="store_true", default=False, ...)
```

### Updated CLI Reference Table Entry (for plans to use)
```markdown
| `propt list-models` | List available models with pricing | `--json` |
```

### Updated Project Structure Tree (for plans to use)
Key additions to `src/` section:
```
    env_manager.py                  # .env file loading, writing, and API key management
    model_discovery.py              # Live model queries from provider APIs
    model_registry.py               # Config-driven pricing, preproc mappings, rate limits
```
Key additions to `data/` section:
```
    default_models.json             # Default model configurations for 4 providers
```
Key count changes:
```
  src/                              # 21 Python modules
  tests/                            # 25 test files
```

## State of the Art

| Old Approach (v1.0) | Current Approach (v2.0) | When Changed | Impact on Docs |
|---------------------|------------------------|--------------|----------------|
| Hardcoded MODELS tuple in config.py | ModelRegistry with data/default_models.json | Phase 16 | All model references, contributing guide |
| Hardcoded PRICE_TABLE dict | ModelRegistry pricing from JSON + live discovery | Phase 16/18 | Pricing docs, architecture |
| Flat config fields (claude_model, etc.) | `models` list in ExperimentConfig | Phase 16 | Config examples, set-config docs |
| `export` only for API keys | .env file + export as options | Phase 16 | Getting started, README quick start |
| Single-provider wizard | Multi-provider loop with .env, validation, budget | Phase 19 | Getting-started wizard section |
| No live model discovery | `propt list-models` queries provider APIs | Phase 18 | CLI reference, architecture |

## Open Questions

1. **What does `propt set-config` accept in v2.0?**
   - What we know: v1.0 accepted `claude_model`, `gemini_model`, etc. v2.0 uses a `models` list.
   - What's unclear: Can you `set-config` individual model fields or only experiment parameters?
   - Recommendation: Implementer should read `src/config_commands.py` handle_set_config() to determine valid v2.0 properties before writing set-config examples.

2. **What does v2.0 `propt pilot --dry-run` output look like?**
   - What we know: The sample output in getting-started.md is from v1.0.
   - What's unclear: Exact formatting of v2.0 output (may show "configurable" indicators).
   - Recommendation: Implementer should run `propt pilot --dry-run` (or read execution_summary.py format_summary()) to capture actual v2.0 output.

3. **Has the DB schema changed in v2.0?**
   - What we know: CONTEXT.md says to verify before updating.
   - What's unclear: Whether any columns were added/removed for configurable models.
   - Recommendation: Implementer should read `src/db.py` init_database() to verify schema matches what architecture.md documents.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

This is a documentation-only phase. No automated tests apply to Markdown file content. Validation is structural:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N/A | All stale references removed | manual-only | `grep -rn "PRICE_TABLE\|PREPROC_MODEL_MAP\|RATE_LIMIT_DELAYS" docs/ README.md CLAUDE.md` | N/A |
| N/A | Python version consistent | manual-only | `grep -rn "3\.11" docs/ README.md CLAUDE.md` | N/A |
| N/A | Module counts accurate | manual-only | `ls src/*.py \| wc -l` compared to docs | N/A |
| N/A | All internal links valid | manual-only | Visual inspection of relative links | N/A |
| N/A | Existing tests still pass | unit | `pytest tests/ -x -q` | Yes |

### Sampling Rate
- **Per task commit:** `grep -rn "PRICE_TABLE\|PREPROC_MODEL_MAP\|3\.11\|18 Python" docs/ README.md CLAUDE.md` (stale pattern check)
- **Per wave merge:** `pytest tests/ -x -q` (ensure no code was accidentally changed)
- **Phase gate:** All grep patterns return zero results + pytest green

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements (documentation phase, no new tests needed)

## Sources

### Primary (HIGH confidence)
- Direct file reads of all 7 target documents (README.md, docs/*.md, CLAUDE.md)
- Direct file reads of v2.0 source files (src/config.py, src/model_registry.py, src/env_manager.py, src/model_discovery.py, src/cli.py)
- Direct file reads of data/default_models.json
- Grep results across all .md files for stale patterns
- `ls src/*.py | wc -l` = 21 modules, `ls tests/*.py | wc -l` = 25 test files
- Phase 21 CONTEXT.md (user decisions)
- Phase 12 CONTEXT.md (documentation conventions)

### Secondary (MEDIUM confidence)
- None needed -- all findings from direct source inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no libraries, pure Markdown editing
- Architecture: HIGH - all target documents read, all stale patterns identified via grep
- Pitfalls: HIGH - based on direct inspection of v1.0 vs v2.0 differences in source code

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- documentation phase, no external dependencies)
