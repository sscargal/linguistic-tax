# Phase 12: Comprehensive Documentation and README for New Users - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Create comprehensive user-facing documentation so someone with zero context can understand, install, configure, and use this research toolkit. Covers README.md, getting-started guide, architecture overview, analysis interpretation guide, contributing guide, and docs/ index. No new features — documentation only.

</domain>

<decisions>
## Implementation Decisions

### README structure
- Lead with research context: the research question ("How does prompt noise degrade LLM accuracy?"), what the toolkit measures, then what it does
- Comprehensive README — self-contained with full install, all CLI commands, config reference, sample output. docs/ has deep-dive content
- Full CLI reference for all `propt` subcommands with flags and examples, emphasizing the most commonly used commands
- Include sample terminal output showing what `propt run`, `propt pilot`, and analysis commands actually produce
- Glossary section in README for project-specific terms (also defined inline on first use in each doc)

### Doc organization
- Flat structure in docs/ with naming convention: `getting-started.md`, `architecture.md`, `analysis-guide.md`, `contributing.md`
- Existing files (RDD, `prompt_format_research.md`, `experiments/`) stay where they are
- `docs/README.md` as index page listing all docs with one-liner descriptions and links (GitHub auto-renders)
- Cross-link new user docs to RDD and research docs where relevant
- Experiment suite docs (docs/experiments/) mentioned and linked from user-facing documentation

### Audience and tone
- Mixed audience: developers who know Python but may not know LLM internals. Include callout boxes or glossary for research-specific terms
- Technical-direct tone — clear, concise, no fluff. Commands and examples speak louder than prose (Stripe/FastAPI style)
- Inline definitions on first use: "Type A noise (character-level typos at 5/10/20% rates)" PLUS a dedicated glossary for quick reference
- American English throughout (consistent with codebase convention)

### Content scope — deliverables
- **README.md** (root) — research context, install, quick-start, full CLI reference, sample output, glossary
- **docs/getting-started.md** — full end-to-end walkthrough (clone → setup → configure → pilot → view results) plus additional walkthroughs for each scenario (custom experiment, analyzing existing results, etc.)
- **docs/architecture.md** — module descriptions, data flow, how components connect, with diagrams
- **docs/analysis-guide.md** — how to read statistical output, what metrics mean, how to generate and interpret figures. Includes ready-to-run SQLite queries for common research questions
- **docs/contributing.md** — comprehensive contributor onboarding: dev setup, architecture deep-dive, adding new interventions/models, test patterns, CI, PR process
- **docs/README.md** — index page mapping all documentation

### Diagram format
- Mermaid as primary diagram format (GitHub renders natively, text-based, easy to update)
- ASCII art as fallback for simple inline diagrams
- Essential diagrams:
  1. Pipeline architecture — modules: prompts → noise → intervention → API → grading → analysis → figures
  2. Data flow — JSON prompts → experiment matrix → SQLite results → derived metrics → figures
  3. Experiment design — visual of factorial design: models × noise types × interventions × repetitions
  4. CLI command map — which `propt` subcommands map to which workflow stages
  5. API call lifecycle sequence diagram — engine → intervention router → pre-processor API → target model API → grader → DB (in architecture docs)
  6. Full experiment run sequence diagram — end-to-end from `propt run` through to results (in getting-started guide)

### Claude's Discretion
- Exact Mermaid diagram styling and layout choices
- Which CLI commands get the most detailed examples vs brief mention
- How to structure the glossary (alphabetical, grouped by concept, etc.)
- Callout box format for research-term definitions
- How to organize the contributing guide sections

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research spec
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for all experimental parameters, metrics, noise types, intervention types, and analysis methods

### Existing documentation to integrate
- `docs/prompt_format_research.md` — Literature survey on prompt format effects (Phase 10 output)
- `docs/experiments/README.md` — Master index of micro-formatting experiment specs (Phase 11 output)
- `CLAUDE.md` — Project overview, architecture, conventions, tech stack (reference for accuracy)

### CLI and config
- `src/cli.py` — CLI entry point with all subcommand definitions (source of truth for CLI reference)
- `src/config.py` — ExperimentConfig and all configuration constants
- `src/config_manager.py` — Config file I/O and validation
- `src/config_commands.py` — Config subcommand handlers

### Core modules (for architecture docs)
- `src/noise_generator.py` — Type A and Type B noise generation
- `src/prompt_compressor.py` — Prompt sanitization and compression
- `src/prompt_repeater.py` — Prompt repetition intervention
- `src/run_experiment.py` — Execution engine
- `src/grade_results.py` — Grading pipeline
- `src/analyze_results.py` — Statistical analysis
- `src/compute_derived.py` — Derived metrics (CR, quadrants, cost)
- `src/generate_figures.py` — Publication figure generation
- `src/execution_summary.py` — Pre-execution summary and confirmation gate
- `src/pilot.py` — Pilot validation

### Project metadata
- `pyproject.toml` — Dependencies, entry points, project metadata

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `propt --help` already provides basic subcommand listing — can reference for accuracy
- `pyproject.toml` has project metadata (name, version, description, dependencies) — source for install instructions
- `scripts/qa_script.sh` exists — reference for test/QA workflow in contributing guide
- `docs/experiments/README.md` — existing well-structured index that documents experiment specs

### Established Patterns
- 18 Python modules in `src/` with `src.` import prefix — all have docstrings on public functions
- `propt` CLI with 9 subcommands registered via argparse subparsers
- SQLite for all results storage — `src/db.py` handles schema and queries
- Environment variables for API keys: ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY

### Integration Points
- README.md will be the new project root entry point (currently only CLAUDE.md exists at root)
- docs/README.md will serve as navigation hub for the docs/ directory
- New docs cross-reference existing RDD, research docs, and experiment specs

</code_context>

<specifics>
## Specific Ideas

- Diagrams must be easily editable to update when architecture changes (e.g., v2) — no manual-overhead-heavy formats like hand-drawn PNGs
- Mermaid chosen specifically because it's text-in-markdown, GitHub-rendered, and git-diffable
- Getting-started guide should have multiple walkthroughs: the primary end-to-end pilot walkthrough, plus scenario-specific ones (custom experiment, analyzing existing results)
- Analysis guide should include copy-paste SQLite queries for common research questions ("accuracy by noise level", "cost per model")

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-comprehensive-documentation-and-readme-for-new-users*
*Context gathered: 2026-03-25*
