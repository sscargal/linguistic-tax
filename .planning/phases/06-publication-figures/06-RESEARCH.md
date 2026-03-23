# Phase 6: Publication Figures - Research

**Researched:** 2026-03-23
**Domain:** Data visualization for academic publication (matplotlib/seaborn)
**Confidence:** HIGH

## Summary

Phase 6 creates four publication-quality figure types from Phase 5's statistical analysis outputs. The data sources are well-defined: SQLite database (`results/results.db`) with `experiment_runs` and `derived_metrics` tables, plus JSON/CSV output files from `analyze_results.py` and `compute_derived.py`. All plotting uses matplotlib and seaborn, both already declared in `pyproject.toml`.

The primary challenge is not library complexity but data-to-figure mapping: transforming the structured analysis outputs into correctly labeled, faceted plots with the right axes, scales, and annotations. The DB schema and function return types are fully documented in existing code, making this a straightforward data-visualization task.

**Primary recommendation:** Build `src/generate_figures.py` as a single module with one function per figure type, a shared style configuration helper, and an argparse CLI matching the Phase 5 pattern. Read data from SQLite + JSON files, produce PDF + PNG per figure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use seaborn with `whitegrid` style and colorblind-safe palette for all figures
- Font sizing: 12pt axis labels, 14pt titles, 10pt tick labels
- White background with light grid lines
- Consistent style configuration via a shared helper (e.g., `_configure_style()`) applied at module load
- Primary output: PDF (vector) for LaTeX inclusion
- Secondary output: PNG at 300 DPI for quick preview
- Both formats saved for every figure
- Single-column figures: 3.5in wide; double-column: 7in wide
- Figure naming: `robustness_curve`, `quadrant_migration`, `cost_model`, `rank_stability`
- Save to `figures/` directory
- FIG-01: Faceted by model, lines per intervention, x=noise level, y=accuracy, bootstrap CI bands, Type A vs Type B panels
- FIG-02: Scatter with x=accuracy/majority-pass, y=CR, quadrant boundaries at CR=0.8 and majority threshold, marginal counts
- FIG-03: Model x Intervention heatmap with diverging color scale (green=savings, red=cost), per noise level or summary
- FIG-04: Bar chart of tau values with bootstrap CI whiskers, grouped by comparison type, baseline at tau=1.0
- New module: `src/generate_figures.py`
- CLI with argparse subcommands: `accuracy`, `quadrant`, `cost`, `kendall`, `all`
- `--db`, `--output-dir`, `--format` flags
- Matches Phase 5 CLI pattern
- All figures generated from saved analysis data -- never re-runs analysis

### Claude's Discretion
- Exact color choices within colorblind-safe constraint
- Subplot arrangement and spacing
- Legend placement and formatting
- Whether to combine Type A/B noise in single panels or separate
- Annotation text for notable data points
- Figure numbering (paper-specific, can be adjusted later)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIG-01 | Generate accuracy degradation curves (noise level x accuracy, by model and intervention) | Bootstrap CI data from `bootstrap_results.json`; accuracy per condition from `experiment_runs` table grouped by noise_type, intervention, model. Seaborn `lineplot` with CI bands. |
| FIG-02 | Generate stability-correctness quadrant plots | `derived_metrics` table has `consistency_rate`, `majority_pass`, `quadrant` per prompt-condition. Scatter plot with quadrant boundaries. |
| FIG-03 | Generate cost-benefit heatmaps showing net token savings by condition | `cost_rollups.json` / `cost_rollups.csv` from compute_derived. Seaborn `heatmap` with annotated cells. |
| FIG-04 | Generate Kendall's tau rank-order stability visualization | `kendall_results.json` / `kendall_tau.csv` from analyze_results. Bar chart with error bars from bootstrap CIs. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| matplotlib | 3.10.8 | Low-level plotting, PDF/PNG export, figure sizing | Industry standard for publication figures; already in pyproject.toml |
| seaborn | 0.13.2 | High-level statistical plots, color palettes, styling | Built on matplotlib; `whitegrid` style and colorblind palettes are first-class features |
| pandas | >=2.2.0 | DataFrame manipulation for plot data prep | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (transitive) | Array operations for heatmap matrices | Reshaping cost rollups into 2D grid |
| matplotlib.backends.backend_pdf | (built-in) | PDF vector output | Every figure save |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| seaborn heatmap | matplotlib imshow | seaborn heatmap has built-in annotation and better defaults |
| matplotlib PDF | plotly for interactive | PDF is the right choice for ArXiv/LaTeX papers |

**Installation:**
Already declared in `pyproject.toml`:
```bash
pip install matplotlib>=3.8.0 seaborn>=0.13.0
```

**Version verification:** matplotlib 3.10.8 and seaborn 0.13.2 are current on PyPI as of 2026-03-23.

## Architecture Patterns

### Recommended Project Structure
```
src/
  generate_figures.py    # New module: all figure generation + CLI
figures/
  robustness_curve.pdf   # FIG-01 output
  robustness_curve.png
  quadrant_migration.pdf # FIG-02 output
  quadrant_migration.png
  cost_model.pdf         # FIG-03 output
  cost_model.png
  rank_stability.pdf     # FIG-04 output
  rank_stability.png
tests/
  test_generate_figures.py  # New test file
```

### Pattern 1: Shared Style Configuration
**What:** A `_configure_style()` function called at module level to set consistent matplotlib/seaborn defaults.
**When to use:** Once, at module import time.
**Example:**
```python
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless environments
import matplotlib.pyplot as plt
import seaborn as sns

def _configure_style() -> None:
    """Apply publication-quality style defaults."""
    sns.set_theme(style="whitegrid", palette="colorblind")
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 12,
        "axes.titlesize": 14,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,
        "pdf.fonttype": 42,  # TrueType fonts in PDF (editable in Illustrator)
        "ps.fonttype": 42,
    })

_configure_style()
```

### Pattern 2: Save Helper
**What:** A `_save_figure()` helper that saves both PDF and PNG based on format flag.
**When to use:** Every figure function calls it at the end.
**Example:**
```python
def _save_figure(
    fig: plt.Figure,
    output_dir: str,
    name: str,
    fmt: str = "both",
) -> list[str]:
    """Save figure in requested formats. Returns list of saved paths."""
    os.makedirs(output_dir, exist_ok=True)
    saved = []
    if fmt in ("pdf", "both"):
        path = os.path.join(output_dir, f"{name}.pdf")
        fig.savefig(path, format="pdf")
        saved.append(path)
    if fmt in ("png", "both"):
        path = os.path.join(output_dir, f"{name}.png")
        fig.savefig(path, format="png")
        saved.append(path)
    plt.close(fig)
    return saved
```

### Pattern 3: Data Loading from Multiple Sources
**What:** Each figure function loads its own data from the appropriate source (SQLite or JSON/CSV).
**When to use:** Keep data loading co-located with figure generation for clarity.
**Example:**
```python
def _load_bootstrap_cis(output_dir: str) -> pd.DataFrame:
    """Load bootstrap CIs from Phase 5 CSV output."""
    csv_path = os.path.join(output_dir, "csv", "bootstrap_cis.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    # Fallback: load from JSON
    json_path = os.path.join(output_dir, "bootstrap_results.json")
    with open(json_path) as f:
        data = json.load(f)
    # Transform dict to DataFrame...
```

### Pattern 4: Per-Figure Function Signature
**What:** Each figure function takes `db_path`, `output_dir`, `fmt` and returns the list of saved file paths.
**When to use:** All four figure functions follow this pattern.
```python
def generate_accuracy_curves(
    db_path: str,
    output_dir: str = "figures",
    fmt: str = "both",
    analysis_dir: str = "results/analysis",
) -> list[str]:
    """Generate accuracy degradation curves (FIG-01)."""
```

### Anti-Patterns to Avoid
- **plt.show() in production code:** Never call `plt.show()` -- use `Agg` backend and save directly
- **Global figure state:** Always use `fig, ax = plt.subplots()` pattern, never `plt.plot()` directly
- **Forgetting plt.close():** Memory leak if figures are not closed after saving
- **Hardcoded data paths:** Accept paths as parameters, use defaults matching project convention

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Colorblind-safe palettes | Custom hex lists | `sns.color_palette("colorblind")` | Validated against common color vision deficiencies |
| Heatmap with annotations | Custom imshow + text loop | `sns.heatmap(annot=True, fmt=".1f")` | Handles alignment, formatting, colorbar automatically |
| CI bands on line plots | Manual fill_between calculations | `sns.lineplot(errorbar=("ci", 95))` or manual `ax.fill_between()` with pre-computed CI bounds | seaborn handles the shading correctly |
| Diverging color scales | Manual cmap construction | `sns.diverging_palette()` or `plt.cm.RdYlGn` | Perceptually uniform, centered at zero |
| PDF font embedding | Manual font configuration | `plt.rcParams["pdf.fonttype"] = 42` | Ensures TrueType fonts render correctly in LaTeX |

**Key insight:** seaborn handles the statistical visualization patterns (faceted plots, CI bands, heatmaps) that would be 50+ lines of raw matplotlib. Use seaborn's high-level API wherever possible, drop to matplotlib only for custom annotations.

## Common Pitfalls

### Pitfall 1: Non-Agg Backend in Headless Environments
**What goes wrong:** `matplotlib.pyplot` tries to open a display window, crashes in SSH/CI
**Why it happens:** Default backend requires a display
**How to avoid:** `matplotlib.use("Agg")` BEFORE importing `pyplot`
**Warning signs:** `TclError: no display name` or `_tkinter.TclError`

### Pitfall 2: Rasterized Text in PDFs
**What goes wrong:** Text in PDF figures becomes bitmap, looks terrible when zoomed
**Why it happens:** Default font type is Type 3 (bitmap)
**How to avoid:** Set `pdf.fonttype = 42` (TrueType) in rcParams
**Warning signs:** Fuzzy text in PDF viewer at high zoom

### Pitfall 3: Figure Sizing for LaTeX Columns
**What goes wrong:** Figures look wrong in the paper -- text too small or too large
**Why it happens:** Creating figures at screen size then scaling down in LaTeX
**How to avoid:** Create at exact target size (3.5in for single column, 7in for double) so font sizes match
**Warning signs:** Need `\includegraphics[width=\columnwidth]` scaling in LaTeX

### Pitfall 4: Color Scale Centering for Diverging Data
**What goes wrong:** Heatmap green/red boundary is not at zero
**Why it happens:** `vmin`/`vmax` auto-computed from data range, not centered at 0
**How to avoid:** Explicitly set `center=0` in `sns.heatmap()` for diverging data
**Warning signs:** All cells appear one color despite having positive and negative values

### Pitfall 5: Overcrowded Facets
**What goes wrong:** 2 models x 5 interventions x 8 noise types = too many lines
**Why it happens:** Trying to show everything in one plot
**How to avoid:** Facet by model (2 panels), group lines by intervention, separate Type A vs Type B as subplot rows
**Warning signs:** Legend has 10+ entries, lines overlap heavily

### Pitfall 6: Memory Leaks from Unclosed Figures
**What goes wrong:** Generating all 4 figures consumes excessive memory
**Why it happens:** matplotlib figures persist in memory until explicitly closed
**How to avoid:** Call `plt.close(fig)` after every save, or use `_save_figure()` helper
**Warning signs:** Memory warnings, slow execution when generating multiple figures

## Code Examples

### FIG-01: Accuracy Degradation Curves
```python
# Core approach: load experiment data, compute accuracy per condition, plot with CI bands
def generate_accuracy_curves(db_path: str, output_dir: str, fmt: str, analysis_dir: str) -> list[str]:
    from src.analyze_results import load_experiment_data

    df = load_experiment_data(db_path)

    # For Type A noise: order x-axis as clean -> 5% -> 10% -> 20%
    noise_order = ["clean", "type_a_5pct", "type_a_10pct", "type_a_20pct"]
    noise_labels = {"clean": "Clean", "type_a_5pct": "5%", "type_a_10pct": "10%", "type_a_20pct": "20%"}

    # Compute per-condition accuracy
    acc = (
        df[df["noise_type"].isin(noise_order)]
        .groupby(["model", "intervention", "noise_type"])["pass_fail"]
        .mean()
        .reset_index()
        .rename(columns={"pass_fail": "accuracy"})
    )

    # Load bootstrap CIs for error bands
    bootstrap_csv = os.path.join(analysis_dir, "csv", "bootstrap_cis.csv")
    if os.path.exists(bootstrap_csv):
        ci_df = pd.read_csv(bootstrap_csv)
        # Merge CI bounds for fill_between

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5), sharey=True)  # Double-column, one panel per model
    for idx, model in enumerate(MODELS):
        ax = axes[idx]
        model_data = acc[acc["model"] == model]
        for intervention in INTERVENTIONS:
            subset = model_data[model_data["intervention"] == intervention]
            # Plot line with markers
            ax.plot(...)
            # Fill CI bands with fill_between
        ax.set_title(model_label)
        ax.set_xlabel("Noise Level")
        if idx == 0:
            ax.set_ylabel("Accuracy")
    axes[-1].legend(...)
    fig.tight_layout()
    return _save_figure(fig, output_dir, "robustness_curve", fmt)
```

### FIG-02: Quadrant Scatter Plot
```python
# Load derived_metrics, scatter with quadrant boundaries
def generate_quadrant_plot(db_path: str, output_dir: str, fmt: str) -> list[str]:
    from src.analyze_results import load_derived_metrics

    dm = load_derived_metrics(db_path)
    # dm has: prompt_id, condition, model, consistency_rate, majority_pass, quadrant

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5))
    for idx, model in enumerate(MODELS):
        ax = axes[idx]
        subset = dm[dm["model"] == model]
        # Color by quadrant
        colors = subset["quadrant"].map(QUADRANT_COLORS)
        ax.scatter(subset["majority_pass"], subset["consistency_rate"],
                   c=colors, alpha=0.6, s=15, edgecolors="none")
        # Draw quadrant boundaries
        ax.axhline(y=0.8, color="gray", linestyle="--", linewidth=0.8)
        ax.axvline(x=0.5, color="gray", linestyle="--", linewidth=0.8)
        # Annotate quadrant counts
        for quad, label in QUADRANT_LABELS.items():
            count = (subset["quadrant"] == quad).sum()
            ax.text(x_pos, y_pos, f"{label}\nn={count}", ha="center", fontsize=8)
    return _save_figure(fig, output_dir, "quadrant_migration", fmt)
```

### FIG-03: Cost-Benefit Heatmap
```python
# Pivot cost rollups into model x intervention grid
def generate_cost_heatmap(db_path: str, output_dir: str, fmt: str, analysis_dir: str) -> list[str]:
    rollup_path = os.path.join(analysis_dir, "cost_rollups.json")
    with open(rollup_path) as f:
        rollups = json.load(f)
    df = pd.DataFrame(rollups)

    # Pivot to intervention (rows) x model (columns) with net savings as values
    pivot = df.pivot_table(
        index="intervention", columns="model",
        values="mean_token_savings",  # or net_token_cost
        aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(3.5, 3.5))  # Single-column
    sns.heatmap(pivot, annot=True, fmt=".0f", center=0,
                cmap=sns.diverging_palette(10, 130, as_cmap=True),  # red-green
                ax=ax, linewidths=0.5)
    ax.set_title("Net Token Savings by Condition")
    return _save_figure(fig, output_dir, "cost_model", fmt)
```

### FIG-04: Kendall's Tau Bar Chart
```python
def generate_kendall_plot(db_path: str, output_dir: str, fmt: str, analysis_dir: str) -> list[str]:
    kendall_path = os.path.join(analysis_dir, "kendall_results.json")
    with open(kendall_path) as f:
        kendall_data = json.load(f)
    df = pd.DataFrame(kendall_data)

    fig, ax = plt.subplots(figsize=(3.5, 3.5))  # Single-column
    # Group bars by model, x-axis = noisy condition
    sns.barplot(data=df, x="noisy_condition", y="tau", hue="model", ax=ax)
    # Add CI whiskers if available from bootstrap
    ax.axhline(y=1.0, color="gray", linestyle="--", linewidth=0.8, label="Perfect agreement")
    ax.set_ylabel("Kendall's tau")
    ax.set_xlabel("Condition")
    ax.set_ylim(0, 1.05)
    plt.xticks(rotation=45, ha="right")
    return _save_figure(fig, output_dir, "rank_stability", fmt)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `plt.savefig()` default Type 3 fonts | `pdf.fonttype = 42` TrueType | Long-standing best practice | Editable text in vector PDFs |
| seaborn `set()` deprecated | `sns.set_theme()` | seaborn 0.11+ | Use `set_theme()` not `set()` |
| Manual CI band calculation | seaborn built-in `errorbar` param | seaborn 0.12+ | `lineplot(errorbar=...)` replaces manual approach |

**Deprecated/outdated:**
- `sns.set()`: Replaced by `sns.set_theme()` in seaborn 0.11
- `sns.distplot()`: Replaced by `sns.histplot()` / `sns.kdeplot()` (not used here, but avoid if needed)

## Data Sources Reference

### SQLite Tables (via `db_path`)

**`experiment_runs`** -- raw data for FIG-01:
- Key columns: `model`, `noise_type`, `intervention`, `pass_fail`, `prompt_id`, `repetition`
- Filter: `status='completed' AND pass_fail IS NOT NULL`

**`derived_metrics`** -- pre-computed for FIG-02:
- Key columns: `prompt_id`, `condition`, `model`, `consistency_rate`, `majority_pass`, `quadrant`
- `condition` format: `{noise_type}_{intervention}` (e.g., `type_a_10pct_raw`)

### JSON/CSV Files (from Phase 5 output)

| File | Content | Used By |
|------|---------|---------|
| `bootstrap_results.json` | CI bounds per condition | FIG-01 (error bands) |
| `csv/bootstrap_cis.csv` | Same as above, tabular | FIG-01 (easier to merge) |
| `kendall_results.json` | tau values per model x condition | FIG-04 |
| `csv/kendall_tau.csv` | Same as above, tabular | FIG-04 |
| `cost_rollups.json` | Per-condition cost aggregates | FIG-03 |
| `csv/cost_rollups.csv` | Same as above, tabular | FIG-03 |

### Config Constants (from `src/config.py`)

| Constant | Values | Used For |
|----------|--------|----------|
| `MODELS` | `("claude-sonnet-4-20250514", "gemini-1.5-pro")` | Facet labels, iteration |
| `NOISE_TYPES` | 8 values (clean + 3 Type A + 4 Type B) | X-axis ordering |
| `INTERVENTIONS` | 5 values (raw through prompt_repetition) | Line/bar grouping |

## Open Questions

1. **Analysis output directory location**
   - What we know: `analyze_results.py` writes to `--output-dir` (likely `results/analysis/`), `compute_derived.py` writes to its own `--output-dir`
   - What's unclear: Exact path used during Phase 5 execution
   - Recommendation: Accept `--analysis-dir` CLI flag with sensible default (`results/analysis/`), fallback to loading from DB directly

2. **Bootstrap CIs for Kendall's tau**
   - What we know: `compute_bootstrap_cis()` computes CIs for accuracy per condition. Kendall's tau results include `tau` and `p_value` but not explicit CIs.
   - What's unclear: Whether bootstrap CIs specifically for tau are pre-computed
   - Recommendation: If tau CIs aren't in Phase 5 output, plot p-value significance markers (stars) instead of CI whiskers, or compute simple bootstrap CIs for tau within the figure function

3. **Type B noise grouping**
   - What we know: Type B has 4 L1 variants (Mandarin, Spanish, Japanese, mixed)
   - What's unclear: Whether to show all 4 separately or aggregate into single "Type B" category
   - Recommendation: Claude's discretion per CONTEXT.md. Suggest showing "Type B mixed" as representative + a supplementary figure with all 4 if space permits

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_generate_figures.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIG-01 | Accuracy degradation curves generated as PDF+PNG | unit | `pytest tests/test_generate_figures.py::test_accuracy_curves -x` | No -- Wave 0 |
| FIG-02 | Quadrant scatter plots generated with correct boundaries | unit | `pytest tests/test_generate_figures.py::test_quadrant_plot -x` | No -- Wave 0 |
| FIG-03 | Cost heatmap generated with diverging scale | unit | `pytest tests/test_generate_figures.py::test_cost_heatmap -x` | No -- Wave 0 |
| FIG-04 | Kendall tau bar chart generated with baseline reference | unit | `pytest tests/test_generate_figures.py::test_kendall_plot -x` | No -- Wave 0 |

### Testing Strategy
Tests should use **synthetic/mock data** (not real experiment results) to verify:
1. Each figure function produces PDF and PNG files at expected paths
2. Files are non-empty and valid (PDF header check, PNG header check)
3. Figure dimensions match specification (3.5in or 7in wide)
4. Style configuration is applied (spot-check rcParams)
5. CLI subcommands work with `--format`, `--db`, `--output-dir` flags

Use `tmp_path` pytest fixture for output directories. Create a small in-memory SQLite DB with synthetic data matching the schema for DB-dependent tests.

### Sampling Rate
- **Per task commit:** `pytest tests/test_generate_figures.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_generate_figures.py` -- covers FIG-01 through FIG-04
- [ ] Synthetic test data fixture (small SQLite DB with ~10 prompts, 5 reps, 2 models)
- [ ] matplotlib must be installed in test environment (`pip install matplotlib seaborn`)

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/analyze_results.py`, `src/compute_derived.py`, `src/db.py`, `src/config.py` -- actual function signatures and return types
- `docs/RDD_Linguistic_Tax_v4.md` lines 696-830 -- metric definitions for axis labels
- `docs/RDD_Linguistic_Tax_v4.md` lines 1693-1720 -- figure deliverables and naming
- PyPI: matplotlib 3.10.8, seaborn 0.13.2 -- verified current versions

### Secondary (MEDIUM confidence)
- matplotlib documentation for `pdf.fonttype = 42` best practice
- seaborn `set_theme()` API (replacing deprecated `set()`)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- matplotlib and seaborn already in pyproject.toml, versions verified
- Architecture: HIGH -- follows established project patterns (argparse CLI, SQLite data loading)
- Pitfalls: HIGH -- well-known matplotlib publication pitfalls, verified from experience
- Data sources: HIGH -- read actual function signatures and DB schema from codebase

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable domain, 30 days)
