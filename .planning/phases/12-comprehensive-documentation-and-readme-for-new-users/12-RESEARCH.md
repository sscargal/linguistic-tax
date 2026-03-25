# Phase 12: Comprehensive Documentation and README for New Users - Research

**Researched:** 2026-03-25
**Domain:** Technical documentation for a Python research toolkit
**Confidence:** HIGH

## Summary

Phase 12 is a documentation-only phase. No code changes are needed -- the goal is to create user-facing documentation so someone with zero context can understand, install, configure, and run this research toolkit. The codebase is mature (15 phases completed, 18 Python modules, 19 test files, full CLI with 9 subcommands), so documentation can be written against stable, existing interfaces.

The deliverables are 6 markdown files: root `README.md`, `docs/getting-started.md`, `docs/architecture.md`, `docs/analysis-guide.md`, `docs/contributing.md`, and `docs/README.md` (index). All decisions about structure, tone, audience, diagram format, and content scope are locked in CONTEXT.md. Research focuses on documenting the actual codebase state accurately and identifying patterns for effective technical documentation.

**Primary recommendation:** Write documentation directly from source code inspection (cli.py, config.py, pyproject.toml) rather than from memory or CLAUDE.md, since the codebase has evolved through 15 phases. Use Mermaid for all diagrams. Follow Stripe/FastAPI documentation style: commands first, prose second.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- README structure: Lead with research context, comprehensive and self-contained, full CLI reference, sample terminal output, glossary section
- Doc organization: Flat docs/ structure, existing files stay in place, docs/README.md as index, cross-link to RDD and research docs
- Audience and tone: Mixed audience (Python developers who may not know LLM internals), technical-direct Stripe/FastAPI style, inline definitions plus glossary, American English
- Content scope deliverables: README.md (root), docs/getting-started.md, docs/architecture.md, docs/analysis-guide.md, docs/contributing.md, docs/README.md (index)
- Diagram format: Mermaid primary (GitHub renders natively), ASCII fallback for simple inline diagrams
- Essential diagrams: (1) Pipeline architecture, (2) Data flow, (3) Experiment design, (4) CLI command map, (5) API call lifecycle sequence, (6) Full experiment run sequence

### Claude's Discretion
- Exact Mermaid diagram styling and layout choices
- Which CLI commands get the most detailed examples vs brief mention
- How to structure the glossary (alphabetical, grouped by concept, etc.)
- Callout box format for research-term definitions
- How to organize the contributing guide sections

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Standard Stack

This phase produces only markdown files. No libraries are needed.

### Core
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| Markdown | Documentation format | GitHub renders natively, universal |
| Mermaid | Diagrams in markdown | GitHub renders natively, text-based, git-diffable |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| ASCII art | Simple inline diagrams | Directory trees, simple layouts where Mermaid is overkill |
| GitHub-flavored tables | Structured data | CLI flag references, glossaries, comparison tables |

## Architecture Patterns

### Deliverable File Map
```
README.md                          # Root entry point (NEW)
docs/
  README.md                        # Index/navigation hub (NEW)
  getting-started.md               # End-to-end walkthrough (NEW)
  architecture.md                  # Module descriptions + diagrams (NEW)
  analysis-guide.md                # Statistical output interpretation (NEW)
  contributing.md                  # Contributor onboarding (NEW)
  RDD_Linguistic_Tax_v4.md         # EXISTING - do not modify
  prompt_format_research.md        # EXISTING - do not modify
  gsd_project_description.md       # EXISTING - do not modify
  experiments/                     # EXISTING - do not modify
    README.md                      # EXISTING experiment index
    token_efficiency.md            # EXISTING
    structural_markup.md           # EXISTING
    punctuation_micro.md           # EXISTING
    format_noise_interaction.md    # EXISTING
    novel_hypotheses.md            # EXISTING
```

### Pattern 1: Source-of-Truth Documentation
**What:** Every documented fact (CLI flags, config properties, models, env vars) must be sourced directly from the code, not from memory or CLAUDE.md.
**When to use:** Always -- the codebase has evolved through 15 phases and CLAUDE.md may be slightly behind.
**Key source files:**
- `src/cli.py` -- 9 subcommands: setup, show-config, set-config, reset-config, validate, diff, list-models, run, pilot
- `src/config.py` -- ExperimentConfig defaults, MODELS, INTERVENTIONS, NOISE_TYPES, PRICE_TABLE, PREPROC_MODEL_MAP
- `src/config_manager.py` -- Config file I/O
- `pyproject.toml` -- Dependencies, entry point (`propt = "src.cli:main"`)

### Pattern 2: Stripe/FastAPI Documentation Style
**What:** Lead with runnable commands and concrete examples. Prose explains the "why" after the reader has seen the "what."
**When to use:** All documentation sections.
**Example structure:**
```markdown
## Quick Start

```bash
git clone <repo>
cd linguistic-tax
pip install -e .
propt setup
propt pilot --dry-run
```

This runs the guided setup wizard and shows a dry-run pilot summary.
```

### Pattern 3: Layered Information Architecture
**What:** README provides everything needed for basic usage. docs/ files provide deep dives for specific needs.
**When to use:** Deciding what goes in README vs docs/.
**Rule:** If a user following the quick-start needs it, it goes in README. If it requires sustained focus (architecture deep-dive, statistical interpretation, contributing), it goes in docs/.

### Pattern 4: Cross-Reference Network
**What:** New docs link to existing docs (RDD, experiment specs) and to each other. Never duplicate content -- link to the source.
**When to use:** Whenever referencing experimental parameters, noise types, or analysis methods defined in the RDD.

### Anti-Patterns to Avoid
- **Documenting from memory:** The codebase has 4 model providers, 5 interventions, 8 noise types. Get exact values from config.py.
- **Duplicating the RDD:** Link to it, summarize it, but do not reproduce its content.
- **Stale examples:** Run or trace through actual CLI paths when writing examples.
- **Wall-of-text README:** Use headers, tables, code blocks, and diagrams to break up content.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diagrams | PNG/SVG image files | Mermaid in markdown | Git-diffable, GitHub-rendered, easy to update |
| API docs | Auto-generated API reference | Curated architecture guide | Auto-gen is noisy; 18 modules is small enough for manual curation |
| CLI reference | External man pages | Inline in README with tables | Single source, easy to find |

## Common Pitfalls

### Pitfall 1: Documenting What CLAUDE.md Says Instead of What Code Does
**What goes wrong:** CLAUDE.md was written early and may not reflect all 15 phases of evolution (e.g., it mentions only Anthropic and Google APIs, but OpenAI and OpenRouter were added in Phases 7 and 9).
**Why it happens:** CLAUDE.md is the first file read, creating anchoring bias.
**How to avoid:** For every factual claim (models, commands, flags, env vars), verify against the source code file.
**Warning signs:** Documentation mentions only 2 providers, or misses CLI subcommands.

### Pitfall 2: Mermaid Diagrams That Don't Render on GitHub
**What goes wrong:** Complex Mermaid syntax or unsupported diagram types fail to render.
**Why it happens:** GitHub's Mermaid support is subset of full Mermaid.js.
**How to avoid:** Stick to well-supported types: flowchart (graph TD/LR), sequenceDiagram, classDiagram. Avoid gantt, pie, or experimental types. Keep node labels short. Test by previewing on GitHub.
**Warning signs:** Diagrams with deeply nested subgraphs, special characters in labels, or very long lines.

### Pitfall 3: Getting-Started Guide Assumes Prior Context
**What goes wrong:** Guide skips steps that seem obvious (Python version, venv creation, API key setup).
**Why it happens:** Author knows the project intimately.
**How to avoid:** Start from "just cloned the repo" state. Include: Python >= 3.11 check, venv creation, pip install, env var export for API keys, config setup, first pilot run.
**Warning signs:** First runnable command appears after 3+ paragraphs of context.

### Pitfall 4: Glossary Terms Not Matching Code Constants
**What goes wrong:** Glossary defines "Type A noise" but code uses `type_a_5pct`, `type_a_10pct`, `type_a_20pct`.
**Why it happens:** Human-readable terms diverge from code identifiers.
**How to avoid:** Include both forms: "Type A noise (character-level typos) -- code values: `type_a_5pct`, `type_a_10pct`, `type_a_20pct`."

### Pitfall 5: Analysis Guide Without Concrete Examples
**What goes wrong:** Guide explains what metrics mean in abstract but reader cannot map to actual output.
**Why it happens:** Author understands the statistics but forgets readers need grounding.
**How to avoid:** Include sample SQLite queries with expected output format. Show what GLMM output looks like and how to read it.

## Code Examples

These are not code to implement -- they are reference data extracted from the codebase for documentation accuracy.

### CLI Subcommands (from src/cli.py)
```
propt setup              # Guided setup wizard (--non-interactive for CI)
propt show-config        # Display config (--json, --changed, --verbose, [property])
propt set-config         # Set config values (key value pairs)
propt reset-config       # Reset to defaults (--all, or specific properties)
propt validate           # Validate current config
propt diff               # Show changes from defaults
propt list-models        # List models with pricing
propt run                # Run experiments (--model, --limit, --intervention, --yes, --budget, --dry-run, --retry-failed, --db)
propt pilot              # Run pilot (--yes, --budget, --dry-run, --db)
```

### Environment Variables Required
```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # For Claude models
export GOOGLE_API_KEY="AIza..."           # For Gemini models
export OPENAI_API_KEY="sk-..."            # For GPT models
export OPENROUTER_API_KEY="sk-or-..."     # For OpenRouter models
```

### Models and Pricing (from src/config.py PRICE_TABLE)
| Model | Input $/1M | Output $/1M | Role |
|-------|-----------|------------|------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 | Target |
| claude-haiku-4-5-20250514 | $1.00 | $5.00 | Pre-processor |
| gemini-1.5-pro | $1.25 | $5.00 | Target |
| gemini-2.0-flash | $0.10 | $0.40 | Pre-processor |
| gpt-4o-2024-11-20 | $2.50 | $10.00 | Target |
| gpt-4o-mini-2024-07-18 | $0.15 | $0.60 | Pre-processor |
| nvidia/nemotron-3-super-120b-a12b:free | $0.00 | $0.00 | Target (free) |
| nvidia/nemotron-3-nano-30b-a3b:free | $0.00 | $0.00 | Pre-processor (free) |

### Noise Types (from src/config.py NOISE_TYPES)
| Code Value | Human Name | Description |
|-----------|------------|-------------|
| clean | Clean | Original prompt, no noise |
| type_a_5pct | Type A 5% | Character-level typos at 5% rate |
| type_a_10pct | Type A 10% | Character-level typos at 10% rate |
| type_a_20pct | Type A 20% | Character-level typos at 20% rate |
| type_b_mandarin | Type B Mandarin | ESL patterns from Mandarin L1 transfer |
| type_b_spanish | Type B Spanish | ESL patterns from Spanish L1 transfer |
| type_b_japanese | Type B Japanese | ESL patterns from Japanese L1 transfer |
| type_b_mixed | Type B Mixed | Combined ESL patterns |

### Interventions (from src/config.py INTERVENTIONS)
| Code Value | Human Name | Description |
|-----------|------------|-------------|
| raw | Raw | No intervention, send as-is |
| self_correct | Self-Correct | Zero-overhead prompt prefix |
| pre_proc_sanitize | Pre-Proc Sanitize | Cheap model cleans noisy prompt |
| pre_proc_sanitize_compress | Pre-Proc Sanitize+Compress | Cheap model cleans and compresses |
| prompt_repetition | Prompt Repetition | Query duplication per Leviathan et al. |

### Dependencies (from pyproject.toml)
```
anthropic>=0.40.0, google-genai>=1.0.0, openai>=2.0.0,
bert-score>=0.3.13, statsmodels>=0.14.0, scipy>=1.12.0,
pandas>=2.2.0, matplotlib>=3.8.0, seaborn>=0.13.0,
pytest>=8.0.0, pytest-cov>=6.0.0, tiktoken>=0.7.0,
datasets>=4.8.3, tabulate>=0.9.0, argcomplete>=3.0.0, tqdm>=4.66.0
```

### Project Structure (actual, verified)
```
linguistic-tax/
  src/                          # 18 Python modules
    __init__.py
    analyze_results.py          # GLMM, bootstrap CIs, McNemar's, Kendall's tau
    api_client.py               # Multi-provider API wrapper (Anthropic, Google, OpenAI, OpenRouter)
    cli.py                      # CLI entry point with 9 subcommands
    compute_derived.py          # CR, quadrant classification, cost rollups
    config.py                   # Pinned models, experiment parameters, pricing
    config_commands.py          # Config subcommand handlers
    config_manager.py           # Config file I/O and validation
    db.py                       # SQLite schema and queries
    execution_summary.py        # Pre-execution summary and confirmation gate
    generate_figures.py         # Publication figure generation
    grade_results.py            # HumanEval sandbox + GSM8K regex grading
    noise_generator.py          # Type A + Type B noise injection
    pilot.py                    # Pilot validation (20-prompt subset)
    prompt_compressor.py        # Sanitize + compress via cheap model
    prompt_repeater.py          # <QUERY><QUERY> duplication
    run_experiment.py           # Execution engine
    setup_wizard.py             # Interactive setup wizard
  tests/                        # 19 test files
  data/
    prompts.json                # 200 clean benchmark prompts
    experiment_matrix.json      # Full factorial design (~82K items)
    pilot_prompts.json          # 20-prompt pilot subset
  docs/
    RDD_Linguistic_Tax_v4.md    # Research Design Document
    prompt_format_research.md   # Literature survey (Phase 10)
    experiments/                # Micro-formatting experiment specs (Phase 11)
      README.md + 5 spec files
  scripts/
    curate_prompts.py           # Prompt curation script
    generate_matrix.py          # Matrix generation script
    qa_script.sh                # Comprehensive QA checklist
  results/                      # Gitignored, populated by experiments
  CLAUDE.md                     # Project instructions
  pyproject.toml                # Project metadata and dependencies
```

## Mermaid Diagram Specifications

### Diagram 1: Pipeline Architecture (flowchart LR)
```
prompts.json -> Noise Generator -> Intervention Router -> {Raw, Self-Correct, Pre-Proc Sanitize, Sanitize+Compress, Repetition} -> API Client -> {Claude, Gemini, GPT, OpenRouter} -> Grader -> SQLite DB
```

### Diagram 2: Data Flow (flowchart TD)
```
JSON prompts + experiment_matrix.json -> run_experiment.py -> results.db -> analyze_results.py + compute_derived.py -> derived tables in DB -> generate_figures.py -> figures/
```

### Diagram 3: Experiment Design (flowchart or table)
```
200 prompts x 8 noise types x 5 interventions x 4 models x 5 repetitions = ~82K items (full matrix)
```

### Diagram 4: CLI Command Map (flowchart)
```
propt -> {setup, show-config, set-config, reset-config, validate, diff, list-models, run, pilot}
setup -> config_manager -> experiment_config.json
run -> execution_summary -> run_experiment -> API -> grading -> DB
pilot -> execution_summary -> pilot.py -> API -> grading -> DB
```

### Diagram 5: API Call Lifecycle (sequenceDiagram)
```
run_engine -> InterventionRouter -> [optional: PreProcessor API] -> TargetModel API -> Grader -> DB.insert
```

### Diagram 6: Full Experiment Run (sequenceDiagram)
```
User -> propt run -> load config -> build work items -> execution_summary (cost/count) -> confirm gate -> tqdm loop -> API calls -> grade -> store -> complete
```

## Recommended Glossary Structure

Alphabetical within two groups: Research Concepts and Technical Terms. This serves both the LLM researcher who needs to understand "Consistency Rate" and the developer who needs to understand "pre-processor model."

**Research Concepts:** Consistency Rate (CR), GLMM, Kendall's tau, Linguistic Tax, McNemar's test, Quadrant Classification (Robust/Confidently-Wrong/Lucky/Broken), Type A noise, Type B noise

**Technical Terms:** Experiment matrix, Intervention, Noise level, Pre-processor model, Target model, Work item

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0.0 |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

This is a documentation-only phase. Validation is manual review, not automated tests.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | README.md exists and renders | manual-only | N/A -- visual review on GitHub | N/A |
| DOC-02 | All Mermaid diagrams render | manual-only | N/A -- visual review on GitHub | N/A |
| DOC-03 | CLI reference matches actual flags | manual-only | `propt --help` cross-check | N/A |
| DOC-04 | Getting-started walkthrough is runnable | manual-only | Follow steps on fresh clone | N/A |
| DOC-05 | All internal links resolve | smoke | `grep -r '](docs/' README.md docs/` link check | N/A |
| DOC-06 | docs/README.md index covers all files | manual-only | Visual cross-check | N/A |

### Sampling Rate
- **Per task commit:** Visual review of rendered markdown
- **Per wave merge:** Cross-check all internal links resolve
- **Phase gate:** All 6 deliverable files exist, render correctly, internal links valid

### Wave 0 Gaps
None -- no test infrastructure needed for a documentation-only phase. Validation is manual review of rendered markdown.

## Open Questions

1. **Real world noisy prompts directory**
   - What we know: CLAUDE.md references `data/real_world_noisy/` but it does not exist in the current file listing. The data/ directory only contains prompts.json, experiment_matrix.json, and pilot_prompts.json.
   - What's unclear: Whether this directory was planned but never created, or was removed.
   - Recommendation: Do not document `data/real_world_noisy/` unless it exists at implementation time. Document what actually exists.

2. **Figures directory**
   - What we know: `figures/` directory does not currently exist (it would be created when generate_figures.py runs).
   - What's unclear: Whether to document it as "created on first figure generation" or list it in the project structure.
   - Recommendation: Document it with a note that it is created by `generate_figures.py` when analysis is run.

3. **Sample terminal output**
   - What we know: CONTEXT.md requires sample terminal output for `propt run`, `propt pilot`, and analysis commands.
   - What's unclear: Exact output format without running commands.
   - Recommendation: Construct representative output based on execution_summary.py formatting code and CLI handler patterns. Mark as "approximate" if not verified against actual runs.

## Sources

### Primary (HIGH confidence)
- `src/cli.py` -- All 9 subcommands with exact flags verified
- `src/config.py` -- All models, pricing, noise types, interventions verified
- `pyproject.toml` -- Dependencies and entry point verified
- `docs/experiments/README.md` -- Experiment suite structure verified
- File system listing -- Verified all existing files and directories

### Secondary (MEDIUM confidence)
- `CLAUDE.md` -- Project overview accurate at high level but slightly behind on provider count
- `docs/RDD_Linguistic_Tax_v4.md` -- Referenced but not fully re-read for this research

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- documentation-only, no libraries needed
- Architecture: HIGH -- all deliverables and structure locked in CONTEXT.md
- Pitfalls: HIGH -- based on direct codebase inspection revealing divergences from CLAUDE.md
- Code examples: HIGH -- all data extracted directly from source files

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable -- documentation of existing codebase)
