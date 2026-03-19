# Phase 1: Foundation and Data Infrastructure - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the complete deterministic data foundation: configuration module with pinned model versions and seed registry, SQLite schema and helpers matching the RDD, noise generators for Type A (character-level at 5/10/20%) and Type B (ESL syntactic), 200 curated benchmark prompts, and the materialized experiment matrix. No API calls in this phase — everything is testable offline.

</domain>

<decisions>
## Implementation Decisions

### Benchmark Prompt Selection
- Equal split across HumanEval, MBPP, and GSM8K (~67 prompts each) for balanced representation across code generation and math reasoning
- No difficulty filtering — random sample from each benchmark to avoid selection bias
- Store prompts in `data/prompts.json` with canonical answers for grading validation
- Each prompt record includes: benchmark_source, problem_id, prompt_text, canonical_answer, answer_type (code/numeric)

### Noise Keyword Protection
- Protected tokens: function names, variable names, operators, and language keywords in code prompts; mathematical operators and numbers in GSM8K prompts
- Protection mechanism: regex-based token identification before mutation pass, identified tokens are skipped during noise injection
- Protection applies to Type A (character-level) noise only — Type B (ESL) operates on syntactic structure, not character-level

### ESL Pattern Design (Type B Noise)
- 5-8 patterns per L1 source language (Mandarin, Spanish, Japanese), covering: article/preposition errors, word order deviations, tense errors, pluralization errors
- Mixed ESL mode combines patterns from multiple L1 sources
- Apply uniformly — one ESL transformation pass per prompt (consistent treatment for analysis)
- Patterns should be rule-based templates, not random — each pattern is a deterministic transformation

### Experiment Matrix Structure
- Each work item is a self-contained JSON object: prompt_id, noise_type, noise_level, intervention, model, repetition_num, status
- Eager generation — materialize full matrix as `data/experiment_matrix.json` before any execution
- Matrix enables: progress tracking, cost estimation, and resumability before API calls begin
- Include clean (no-noise) baseline conditions in the matrix as explicit rows

### Seed Management
- Independent `random.Random(seed)` instances per noise source — no global `random.seed()` calls
- Seed registry in config module maps each randomness source to its seed value
- Seeds are deterministic functions of (base_seed, prompt_id, noise_type, noise_level) for reproducibility

### Claude's Discretion
- Exact SQLite schema column names and types (must match RDD Section 9.2 intent but implementation details are flexible)
- Config module implementation pattern (dataclass, dict, or module-level constants)
- JSON file structure details beyond the specified fields
- Test fixture organization

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experimental Design
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for ALL experimental parameters, noise types, intervention types, metrics, and SQLite schema (Section 9.2)

### Project Conventions
- `CLAUDE.md` — Coding conventions, tech stack constraints, what NOT to do
- `pyproject.toml` — Dependencies (NOTE: `google-generativeai` must be replaced with `google-genai` but this is a Phase 3 concern — Phase 1 has no API calls)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — codebase is greenfield (only `__init__.py` files exist in `src/` and `tests/`)

### Established Patterns
- `pyproject.toml` with uv for package management
- pytest configured with `testpaths = ["tests"]`

### Integration Points
- `data/` directory for prompts and matrix (needs to be created)
- `results/` directory for SQLite database (needs to be created, gitignored)
- `src/` flat module layout — each module is a standalone Python file

</code_context>

<specifics>
## Specific Ideas

- The RDD (docs/RDD_Linguistic_Tax_v4.md) is the authoritative spec — all parameter values, noise definitions, and schema come from there
- Noise generators must be CLI-invocable per the project description (e.g., `python src/noise_generator.py --input data/prompts.json --type char --rate 0.10 --seed 42`)
- Research identified that `google-generativeai` in pyproject.toml is deprecated — but this only matters in Phase 3 when API calls begin

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-and-data-infrastructure*
*Context gathered: 2026-03-19*
