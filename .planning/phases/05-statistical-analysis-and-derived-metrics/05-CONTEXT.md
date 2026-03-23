# Phase 5: Statistical Analysis and Derived Metrics - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute all statistical analyses and derived metrics defined in the RDD from experimental results in SQLite. This includes GLMM fitting, bootstrap CIs, McNemar's tests, Kendall's tau, BH correction, Consistency Rate, quadrant classification, quadrant migration tracking, cost rollups, and per-benchmark breakdowns. The output is structured data (SQLite, JSON, CSV) ready for Phase 6 visualization. No figures are produced in this phase.

</domain>

<decisions>
## Implementation Decisions

### GLMM Approach & Fallback
- Primary: statsmodels BinomialBayesMixedGLM with logit link on binary pass/fail
- Fixed effects: Noise_Type, Noise_Level, Intervention, Model, benchmark_source (as covariate), all 2-way interactions
- Random effects: Try full spec first — (1|Prompt_ID) + (1|Prompt_ID:Model). If convergence fails, drop interaction term and retry with just (1|Prompt_ID). Log which model was actually fit.
- Fallback chain: statsmodels GLMM → fixed-effects logistic regression with clustered standard errors. Pure Python, no R dependency.
- On fallback: log WARNING-level message, note in output metadata, do not block execution
- Effect sizes: report both odds ratios (OR) with 95% CI AND risk differences (absolute percentage point changes) for readability

### Derived Metrics (compute_derived.py)
- Populate existing `derived_metrics` table in results.db directly
- CR = pairwise pass/fail agreement across 5 runs (not text agreement)
- Quadrant thresholds: CR >= 0.8 for "stable", majority pass (3/5+) for "correct" — configurable via --cr-threshold CLI flag, defaults to RDD value of 0.8
- Quadrant migration: compute transition matrices between quadrants as noise increases (clean→noisy_5pct, clean→noisy_10pct, clean→noisy_20pct). Stored as precomputed data for Phase 6 visualization.
- Cost rollups: per-condition aggregate (model x intervention x noise), not per-prompt. Per-prompt net_token_cost stored in derived_metrics.

### Per-Benchmark Breakdowns
- Add benchmark_source as a fixed effect in GLMM (not separate GLMMs per benchmark)
- Report aggregate metrics (accuracy, CR, cost) separately per benchmark (HumanEval, MBPP, GSM8K) in summary outputs

### BH Correction
- Per-test-type families: separate BH correction for McNemar's, GLMM, and Kendall's p-values (not a single pooled family)
- Store BOTH raw p-values and BH-corrected p-values side by side
- Implementation: statsmodels.stats.multitest.multipletests(method='fdr_bh')

### Output Format & CLI
- Two modules: `compute_derived.py` (per-prompt: CR, quadrants, cost rollups, migration) and `analyze_results.py` (aggregate: GLMM, bootstrap, McNemar's, Kendall's, BH)
- Output triple: JSON files + CSV tables + terminal summary tables
- JSON: results/glmm_results.json, results/mcnemar_results.json, results/bootstrap_results.json, results/kendall_results.json, results/analysis_summary.json
- CSV: results/csv/ directory for LaTeX-ready tabular data
- Terminal: tabulate library for formatted console output
- CLI: argparse subcommands — `analyze_results.py glmm`, `analyze_results.py mcnemar`, `analyze_results.py bootstrap`, `analyze_results.py kendall`, `analyze_results.py all`
- compute_derived.py: single command, processes all prompts

### Sensitivity Analysis
- Robustness check: rerun key metrics after dropping hardest/easiest 10% of prompts
- Complements bootstrap CIs — strengthens paper's claims about result stability

### Effect Size Summary Table
- Auto-generate a summary of all effect sizes (OR, RD, Cohen's d, Kendall's tau) with CIs
- Output as CSV for easy LaTeX import in Phase 6

### Claude's Discretion
- Bootstrap iteration count (RDD says 10,000)
- Internal structure of JSON output files
- Exact tabulate table format (grid, github, etc.)
- Cohen's d computation details for continuous metrics
- Sensitivity analysis threshold (10% is starting point)
- How to handle prompts with incomplete repetitions (fewer than 5 runs)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Statistical Methods
- `docs/RDD_Linguistic_Tax_v4.md` §7.2 — GLMM specification (fixed effects, random effects, link function)
- `docs/RDD_Linguistic_Tax_v4.md` §7.3 — Stability analysis: CR formula, quadrant definitions, migration hypothesis
- `docs/RDD_Linguistic_Tax_v4.md` §7.4 — Kendall's tau rank-order stability method
- `docs/RDD_Linguistic_Tax_v4.md` §7.5 — McNemar's test specification (fragile/recoverable prompts)
- `docs/RDD_Linguistic_Tax_v4.md` §7.6 — BH correction: FDR < 0.05, implementation options
- `docs/RDD_Linguistic_Tax_v4.md` §7.7 — Bootstrap CI procedure (10,000 iterations, 2.5/97.5 percentiles)
- `docs/RDD_Linguistic_Tax_v4.md` §7.8 — Effect size reporting (OR, RD, Cohen's d, Kendall's tau)
- `docs/RDD_Linguistic_Tax_v4.md` §8.1-8.2 — Primary and secondary metrics definitions (R, RR, TR, CR)

### Data Schema
- `docs/RDD_Linguistic_Tax_v4.md` §9.2 — Execution log schema and derived fields specification
- `src/db.py` — SQLite schema including `derived_metrics` table (CR, quadrant, majority_pass, cost fields)

### Project Conventions
- `CLAUDE.md` — Coding conventions (type hints, docstrings, logging module, American English, no print())

### Existing Patterns
- `src/pilot.py` — Bootstrap CI pattern (BCa with percentile fallback), argparse CLI, JSON output to results/

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/pilot.py`: Bootstrap CI implementation with BCa/percentile fallback — can be extracted or referenced for analyze_results.py
- `src/db.py`: `query_runs()` for retrieving experimental results, `derived_metrics` table schema ready for writes
- `src/config.py`: `ExperimentConfig` with price table, `compute_cost()` for cost calculations
- `scipy.stats.bootstrap`: Already a dependency, used in pilot.py

### Established Patterns
- Flat module layout in `src/` — compute_derived.py and analyze_results.py follow this
- argparse CLI with subcommands (run_experiment.py uses subparsers)
- JSON output to `results/` directory for structured data
- Python `logging` module for all output (no print statements)
- Fixed random seeds for all stochastic operations

### Integration Points
- `results/results.db` — reads experiment_runs, writes to derived_metrics
- `results/*.json` — new analysis output files consumed by Phase 6
- `results/csv/` — new directory for LaTeX-ready CSV tables
- `data/prompts.json` — needed for benchmark_source grouping

</code_context>

<specifics>
## Specific Ideas

- Quadrant migration is flagged by the RDD as potentially a "MAJOR FINDING" — the code should make this analysis prominent and easy to interpret
- Per-benchmark breakdowns via GLMM covariate is statistically cleaner than running separate models — captures benchmark differences in a single model
- The sensitivity analysis (drop 10% hardest/easiest prompts) directly addresses the ICLR 2026 evaluation robustness concern mentioned in the RDD
- Effect size summary table should be designed for direct LaTeX import to minimize paper-writing friction
- STATE.md flags GLMM convergence risk — the fallback chain (GLMM → logistic with clustered SEs) is the mitigation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-statistical-analysis-and-derived-metrics*
*Context gathered: 2026-03-23*
