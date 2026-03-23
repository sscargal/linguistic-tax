# Phase 6: Publication Figures - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate publication-quality figures for all key results, ready for the ArXiv paper. Four figure types: accuracy degradation curves, stability-correctness quadrant plots, cost-benefit heatmaps, and Kendall's tau rank-order visualizations. All figures read from Phase 5's analysis outputs (SQLite, JSON, CSV) and save to `figures/`. No new analysis or metrics are computed in this phase.

</domain>

<decisions>
## Implementation Decisions

### Plot Styling
- Use seaborn with `whitegrid` style and colorblind-safe palette for all figures
- Font sizing: 12pt axis labels, 14pt titles, 10pt tick labels — legible at column width
- White background with light grid lines — clean for academic papers
- Consistent style configuration via a shared helper (e.g., `_configure_style()`) applied at module load

### Output Format & Resolution
- Primary output: PDF (vector) for LaTeX inclusion
- Secondary output: PNG at 300 DPI for quick preview and README use
- Both formats saved for every figure
- Single-column figures: 3.5in wide; double-column: 7in wide; aspect ratio per figure type
- Save to `figures/` directory with names matching RDD: `robustness_curve`, `quadrant_migration`, `cost_model`, `rank_stability`

### Figure Composition
- **FIG-01 Accuracy degradation curves:** Faceted by model (Claude, Gemini), lines per intervention type, x-axis = noise level (clean, 5%, 10%, 20%), y-axis = accuracy. Include bootstrap CI bands from Phase 5 data. Separate panels or line groups for Type A vs Type B noise.
- **FIG-02 Quadrant plots:** Scatter plot with each prompt-condition as a point in the 4-quadrant space (x = accuracy/majority-pass, y = CR). Quadrant boundaries at CR=0.8 and majority threshold. Include marginal counts per quadrant. Faceted by intervention or noise condition as most informative.
- **FIG-03 Cost-benefit heatmaps:** Model x Intervention grid with net token savings (or net cost delta) as cell values. Diverging color scale (green = savings, red = cost increase). Separate heatmaps per noise level or a single summary.
- **FIG-04 Kendall's tau visualization:** Bar chart of tau values by condition with bootstrap CI whiskers. Group by comparison type (e.g., clean vs. noisy rankings). Clear baseline at tau=1.0 (perfect agreement).

### CLI Interface
- New module: `src/generate_figures.py`
- CLI with argparse subcommands: `accuracy`, `quadrant`, `cost`, `kendall`, `all`
- `--db` flag for database path (default: `results/results.db`)
- `--output-dir` flag (default: `figures/`)
- `--format` flag: `pdf`, `png`, `both` (default: `both`)
- Matches Phase 5 CLI pattern (argparse with subcommands)
- All figures generated from saved analysis data — never requires re-running analysis

### Claude's Discretion
- Exact color choices within colorblind-safe constraint
- Subplot arrangement and spacing
- Legend placement and formatting
- Whether to combine Type A/B noise in single panels or separate
- Annotation text for notable data points
- Figure numbering (paper-specific, can be adjusted later)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research Design
- `docs/RDD_Linguistic_Tax_v4.md` — Lines 1693-1720: figure deliverables and naming; Lines 1768-1802: paper findings that figures must illustrate; Section 7 (lines ~700-830): metric definitions for axis labels and scales

### Phase 5 Outputs (data sources)
- `src/analyze_results.py` — Functions: `compute_bootstrap_cis()`, `run_mcnemar_analysis()`, `compute_kendall_tau()`, `run_sensitivity_analysis()` — these produce the data that figures consume
- `src/compute_derived.py` — Functions: `compute_derived_metrics()`, `compute_quadrant_migration()`, `compute_cost_rollups()` — derived metrics stored in SQLite

### Requirements
- `.planning/REQUIREMENTS.md` — FIG-01 through FIG-04 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/analyze_results.py`: All statistical analysis functions return structured dicts/DataFrames — direct input for plotting
- `src/compute_derived.py`: `compute_cost_rollups()` returns list of dicts, `compute_quadrant_migration()` returns transition matrices
- `src/db.py`: Database connection and query utilities
- `src/config.py`: Configuration access (model names, noise levels, intervention types for axis labels)

### Established Patterns
- CLI pattern: argparse with subcommands (see `analyze_results.py` main block)
- Data loading: pandas DataFrames from SQLite via `pd.read_sql_query()`
- Output pattern: JSON + CSV side by side (figures will add PDF + PNG)
- All modules use Python logging, not print statements

### Integration Points
- Reads from `results/results.db` (same database all modules use)
- Reads JSON/CSV output from Phase 5 analysis runs (e.g., bootstrap CI files)
- Writes to `figures/` directory (currently empty, gitignored results but figures should be tracked)
- matplotlib and seaborn already in pyproject.toml dependencies

</code_context>

<specifics>
## Specific Ideas

- RDD specifies figure directory names: `figures/robustness_curve`, `figures/quadrant_migration`, `figures/cost_model` — follow this naming
- Paper has 7 findings (Section 15, VII) — figures should map clearly to findings 1, 3, 4/5, and rank-order analysis
- Break-even curve (Finding 6) may be derivable from cost data — Claude's discretion on whether to include as bonus

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-publication-figures*
*Context gathered: 2026-03-23*
