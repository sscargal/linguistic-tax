---
name: generate-figures
description: Generate publication-quality figures for the Linguistic Tax ArXiv paper. Use this skill whenever the user wants to create plots, generate figures, make charts for the paper, visualize results, create accuracy curves, quadrant plots, cost heatmaps, or rank stability charts. Also trigger when the user says "make the figures", "generate plots", "create the paper figures", "visualize the results", "accuracy curve", "quadrant scatter", or "cost heatmap".
---

# Generate Figures

Produce the 4 publication-quality figure types required by the ArXiv paper, following journal formatting standards.

## Figure types

### 1. Accuracy degradation curves (`accuracy`)

Double-column figure showing noise level (x-axis) vs. accuracy (y-axis) with one line per intervention, faceted by model. This is Figure 1 in the paper — the "noise cliff" visualization.

```bash
python -m src.generate_figures accuracy --db results/results.db
```

**What to look for:** A sharp drop at some noise threshold (supports H1) vs. gradual linear decline (doesn't support H1). Intervention lines above the "raw" line show recovery.

### 2. Stability-correctness quadrant scatter (`quadrant`)

Double-column scatter plot showing consistency rate (x-axis) vs. accuracy (y-axis) with quadrant boundaries. Points colored by noise condition. Shows migration patterns.

```bash
python -m src.generate_figures quadrant --db results/results.db
```

**What to look for:** Points migrating from upper-right (robust) to upper-left (confidently wrong = H5) vs. lower-left (broken = visible failure).

### 3. Cost-benefit heatmap (`cost`)

Single-column heatmap showing net token cost (or savings) per intervention x noise level cell. Green = net savings, red = net cost.

```bash
python -m src.generate_figures cost --db results/results.db
```

**What to look for:** Whether Sanitize+Compress achieves net positive ROI (green cells) at higher noise levels (supports H3).

### 4. Kendall's tau rank-stability bar chart (`rank`)

Single-column bar chart showing Kendall's tau per noise level. Higher tau = more uniform tax, lower tau = more targeted.

```bash
python -m src.generate_figures rank --db results/results.db
```

**What to look for:** Tau values dropping as noise increases = noise disproportionately breaks some prompts.

### All figures at once

```bash
python -m src.generate_figures all --db results/results.db
```

## Output location

Figures are saved to `figures/` as both PDF and PNG:
- `figures/accuracy_degradation.{pdf,png}`
- `figures/quadrant_scatter.{pdf,png}`
- `figures/cost_heatmap.{pdf,png}`
- `figures/rank_stability.{pdf,png}`

## Style specifications

All figures use:
- **Seaborn whitegrid** style with **colorblind-safe** palette
- Font sizes: 12pt axes labels, 14pt titles, 10pt ticks
- **PDF fonttype=42** for editable text in vector output
- **300 DPI** for raster output
- Tight bounding box with 0.1" padding

These match ArXiv and journal submission requirements.

## Reviewing figures

After generating, review each figure for:

1. **Readability**: Can you read all axis labels and legends at the expected print size?
2. **Color**: Does the colorblind palette distinguish all lines/points?
3. **Completeness**: Are all configured models and conditions represented? (Model count varies based on registry configuration)
4. **Formatting**: Do PDF versions have editable text (not rasterized)?
5. **Data accuracy**: Do the plotted values match the analysis output?

To view PNG figures:
```bash
xdg-open figures/accuracy_degradation.png  # Linux
open figures/accuracy_degradation.png       # macOS
```

## Customization

If the default figures need adjustment, the source is `src/generate_figures.py`. Common tweaks:
- Adjust figure dimensions for single vs. double column
- Change color palette
- Add/remove annotation text
- Adjust axis ranges
- Overlay bootstrap CI bands from analysis output

## Prerequisites

- Experiment runs must be completed in `results/results.db`
- For best results, run `python -m src.compute_derived` first (needed for quadrant and cost figures)
- Model set is determined by the configuration — figures automatically adapt to however many models are in the results
- Python packages: matplotlib, seaborn, pandas, numpy
