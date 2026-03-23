"""Publication figure generation for the Linguistic Tax research paper.

Produces 4 figure types required by the ArXiv paper:
1. Accuracy degradation curves (robustness_curve) -- double-column
2. Stability-correctness quadrant scatter (quadrant_migration) -- double-column
3. Cost-benefit heatmap (cost_model) -- single-column
4. Kendall tau rank-stability bar chart (rank_stability) -- single-column

All figures use seaborn whitegrid style with colorblind-safe palette,
12pt/14pt/10pt font sizing, and PDF fonttype=42 for editable text.

Usage:
    python -m src.generate_figures all --db results/results.db
    python -m src.generate_figures accuracy --db results/results.db
"""

import matplotlib
matplotlib.use("Agg")

import argparse
import json
import logging
import os
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared style configuration
# ---------------------------------------------------------------------------


def _configure_style() -> None:
    """Configure matplotlib and seaborn for publication-quality output.

    Sets whitegrid style, colorblind palette, font sizes matching journal
    specs, and PDF fonttype=42 for editable text in vector output.
    """
    sns.set_theme(style="whitegrid", palette="colorblind")
    matplotlib.rcParams.update({
        "axes.labelsize": 12,
        "axes.titlesize": 14,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


_configure_style()


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------


def _save_figure(
    fig: plt.Figure, output_dir: str, name: str, fmt: str = "both"
) -> list[str]:
    """Save a matplotlib figure as PDF and/or PNG.

    Args:
        fig: The matplotlib Figure to save.
        output_dir: Directory to write output files.
        name: Base filename (without extension).
        fmt: Output format -- 'pdf', 'png', or 'both'.

    Returns:
        List of file paths that were saved.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved: list[str] = []

    if fmt in ("pdf", "both"):
        pdf_path = os.path.join(output_dir, f"{name}.pdf")
        fig.savefig(pdf_path, format="pdf")
        saved.append(pdf_path)
        logger.info("Saved %s", pdf_path)

    if fmt in ("png", "both"):
        png_path = os.path.join(output_dir, f"{name}.png")
        fig.savefig(png_path, format="png")
        saved.append(png_path)
        logger.info("Saved %s", png_path)

    plt.close(fig)
    return saved


# ---------------------------------------------------------------------------
# Figure 1: Accuracy degradation curves
# ---------------------------------------------------------------------------

# Noise level ordering for x-axis
_NOISE_LEVEL_ORDER = ["clean", "type_a_5pct", "type_a_10pct", "type_a_20pct"]
_NOISE_LEVEL_LABELS = ["Clean", "5%", "10%", "20%"]


def generate_accuracy_curves(
    db_path: str,
    output_dir: str = "figures",
    fmt: str = "both",
    analysis_dir: str = "results/analysis",
) -> list[str]:
    """Generate accuracy degradation curves faceted by model.

    Plots noise level on x-axis vs accuracy on y-axis with one line per
    intervention. Optionally overlays bootstrap CI bands from analysis output.

    Args:
        db_path: Path to SQLite results database.
        output_dir: Directory for output figures.
        fmt: Output format ('pdf', 'png', or 'both').
        analysis_dir: Directory containing Phase 5 analysis outputs.

    Returns:
        List of saved file paths.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT model, noise_type, intervention, pass_fail "
        "FROM experiment_runs "
        "WHERE status = 'completed' AND pass_fail IS NOT NULL",
        conn,
    )
    conn.close()

    if df.empty:
        logger.warning("No experiment data found for accuracy curves")
        return []

    # Filter to Type A noise levels only
    df = df[df["noise_type"].isin(_NOISE_LEVEL_ORDER)]

    # Compute per-condition accuracy
    acc = (
        df.groupby(["model", "intervention", "noise_type"])["pass_fail"]
        .mean()
        .reset_index()
        .rename(columns={"pass_fail": "accuracy"})
    )

    # Load bootstrap CIs if available
    ci_df = None
    ci_path = os.path.join(analysis_dir, "csv", "bootstrap_cis.csv")
    if os.path.exists(ci_path):
        try:
            ci_df = pd.read_csv(ci_path)
        except Exception:
            logger.warning("Could not load bootstrap CIs from %s", ci_path)

    models = sorted(acc["model"].unique())
    n_models = len(models)

    fig, axes = plt.subplots(1, max(n_models, 2), figsize=(7, 3.5), sharey=True)
    if n_models == 1:
        axes = [axes[0]]
    else:
        axes = list(axes[:n_models])

    palette = sns.color_palette("colorblind")

    for idx, model in enumerate(models):
        ax = axes[idx]
        model_data = acc[acc["model"] == model]
        interventions = sorted(model_data["intervention"].unique())

        for j, intervention in enumerate(interventions):
            idata = model_data[model_data["intervention"] == intervention]
            # Map noise types to numeric positions
            x_vals = []
            y_vals = []
            for nt in _NOISE_LEVEL_ORDER:
                row = idata[idata["noise_type"] == nt]
                if not row.empty:
                    x_vals.append(_NOISE_LEVEL_ORDER.index(nt))
                    y_vals.append(row["accuracy"].iloc[0])

            color = palette[j % len(palette)]
            ax.plot(x_vals, y_vals, marker="o", label=intervention, color=color)

            # Add CI bands if available
            if ci_df is not None:
                for xi, nt in zip(x_vals, [_NOISE_LEVEL_ORDER[x] for x in x_vals]):
                    cond_key = f"{nt}_{intervention}"
                    ci_row = ci_df[ci_df["condition"] == cond_key]
                    if not ci_row.empty:
                        ax.fill_between(
                            [xi - 0.15, xi + 0.15],
                            ci_row["ci_lower"].iloc[0],
                            ci_row["ci_upper"].iloc[0],
                            alpha=0.15,
                            color=color,
                        )

        ax.set_xticks(range(len(_NOISE_LEVEL_LABELS)))
        ax.set_xticklabels(_NOISE_LEVEL_LABELS)
        ax.set_title(model)
        ax.set_xlabel("Noise Level")
        if idx == 0:
            ax.set_ylabel("Accuracy")

    # Legend on rightmost active panel
    axes[-1].legend(loc="best", framealpha=0.8)

    # Hide unused axes if n_models < 2
    if n_models < 2:
        for extra_ax in fig.axes[n_models:]:
            extra_ax.set_visible(False)

    fig.tight_layout()
    return _save_figure(fig, output_dir, "robustness_curve", fmt)


# ---------------------------------------------------------------------------
# Figure 2: Stability-correctness quadrant scatter
# ---------------------------------------------------------------------------


def generate_quadrant_plot(
    db_path: str,
    output_dir: str = "figures",
    fmt: str = "both",
) -> list[str]:
    """Generate stability-correctness quadrant scatter plot faceted by model.

    Each point is a prompt-condition with CR on y-axis and majority_pass on
    x-axis. Quadrant boundaries at CR=0.8 and majority_pass=0.5.

    Args:
        db_path: Path to SQLite results database.
        output_dir: Directory for output figures.
        fmt: Output format ('pdf', 'png', or 'both').

    Returns:
        List of saved file paths.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT prompt_id, condition, model, consistency_rate, majority_pass, quadrant "
        "FROM derived_metrics",
        conn,
    )
    conn.close()

    if df.empty:
        logger.warning("No derived metrics found for quadrant plot")
        return []

    models = sorted(df["model"].unique())
    n_models = len(models)

    fig, axes = plt.subplots(1, max(n_models, 2), figsize=(7, 3.5))
    if n_models == 1:
        axes = [axes[0]]
    else:
        axes = list(axes[:n_models])

    quadrant_colors = {
        "robust": sns.color_palette("colorblind")[2],       # green
        "confidently_wrong": sns.color_palette("colorblind")[3],  # red-ish
        "lucky": sns.color_palette("colorblind")[1],        # orange
        "broken": sns.color_palette("colorblind")[4],       # purple
    }

    rng = np.random.default_rng(42)

    for idx, model in enumerate(models):
        ax = axes[idx]
        model_data = df[df["model"] == model]

        # Add small jitter for visibility
        x_jitter = model_data["majority_pass"].astype(float) + rng.normal(0, 0.02, len(model_data))
        y_jitter = model_data["consistency_rate"] + rng.normal(0, 0.01, len(model_data))

        for quad_name, color in quadrant_colors.items():
            mask = model_data["quadrant"] == quad_name
            if mask.any():
                ax.scatter(
                    x_jitter[mask],
                    y_jitter[mask],
                    c=[color],
                    label=quad_name,
                    alpha=0.6,
                    s=20,
                    edgecolors="none",
                )

        # Quadrant boundaries
        ax.axhline(y=0.8, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.axvline(x=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)

        # Annotate quadrant counts
        for quad_name, (x_pos, y_pos) in {
            "robust": (0.75, 0.9),
            "confidently_wrong": (0.25, 0.9),
            "lucky": (0.75, 0.4),
            "broken": (0.25, 0.4),
        }.items():
            n = (model_data["quadrant"] == quad_name).sum()
            ax.text(
                x_pos, y_pos, f"n={n}",
                ha="center", va="center",
                fontsize=8, fontweight="bold",
                transform=ax.transAxes if False else None,
            )

        ax.set_title(model)
        ax.set_xlabel("Majority Pass Rate")
        if idx == 0:
            ax.set_ylabel("Consistency Rate (CR)")

    axes[-1].legend(loc="best", framealpha=0.8, fontsize=8)

    # Hide unused axes
    if n_models < 2:
        for extra_ax in fig.axes[n_models:]:
            extra_ax.set_visible(False)

    fig.tight_layout()
    return _save_figure(fig, output_dir, "quadrant_migration", fmt)


# ---------------------------------------------------------------------------
# Figure 3: Cost-benefit heatmap
# ---------------------------------------------------------------------------


def generate_cost_heatmap(
    db_path: str,
    output_dir: str = "figures",
    fmt: str = "both",
    analysis_dir: str = "results/analysis",
) -> list[str]:
    """Generate cost-benefit heatmap with diverging color scale.

    Shows net token savings by intervention and model, centered at zero.

    Args:
        db_path: Path to SQLite results database (not used directly but
            kept for consistent interface).
        output_dir: Directory for output figures.
        fmt: Output format ('pdf', 'png', or 'both').
        analysis_dir: Directory containing Phase 5 analysis outputs.

    Returns:
        List of saved file paths.
    """
    cost_path = os.path.join(analysis_dir, "cost_rollups.json")
    if not os.path.exists(cost_path):
        logger.warning("cost_rollups.json not found at %s", cost_path)
        return []

    with open(cost_path) as f:
        cost_data = json.load(f)

    cost_df = pd.DataFrame(cost_data)

    if cost_df.empty:
        logger.warning("Empty cost rollup data")
        return []

    pivot = cost_df.pivot_table(
        index="intervention",
        columns="model",
        values="mean_token_savings",
        aggfunc="mean",
    )

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    cmap = sns.diverging_palette(10, 130, as_cmap=True)
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".0f",
        center=0,
        cmap=cmap,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Net Token Savings by Condition")

    fig.tight_layout()
    return _save_figure(fig, output_dir, "cost_model", fmt)


# ---------------------------------------------------------------------------
# Figure 4: Kendall tau bar chart
# ---------------------------------------------------------------------------


def generate_kendall_plot(
    db_path: str,
    output_dir: str = "figures",
    fmt: str = "both",
    analysis_dir: str = "results/analysis",
) -> list[str]:
    """Generate Kendall tau rank-stability bar chart.

    Shows tau values per noisy condition with CI whiskers and a tau=1.0
    reference line for perfect agreement.

    Args:
        db_path: Path to SQLite results database (not used directly but
            kept for consistent interface).
        output_dir: Directory for output figures.
        fmt: Output format ('pdf', 'png', or 'both').
        analysis_dir: Directory containing Phase 5 analysis outputs.

    Returns:
        List of saved file paths.
    """
    kendall_path = os.path.join(analysis_dir, "kendall_results.json")
    if not os.path.exists(kendall_path):
        logger.warning("kendall_results.json not found at %s", kendall_path)
        return []

    with open(kendall_path) as f:
        kendall_data = json.load(f)

    kdf = pd.DataFrame(kendall_data)

    if kdf.empty:
        logger.warning("Empty Kendall tau data")
        return []

    fig, ax = plt.subplots(figsize=(3.5, 3.5))

    sns.barplot(
        data=kdf,
        x="noisy_condition",
        y="tau",
        hue="model",
        ax=ax,
    )

    # Add CI whiskers if available
    if "ci_lower" in kdf.columns and "ci_upper" in kdf.columns:
        # Get bar positions from the rendered bars
        conditions = kdf["noisy_condition"].unique()
        models = kdf["model"].unique()
        n_models = len(models)
        n_conditions = len(conditions)

        bar_width = 0.8 / n_models
        for i, model in enumerate(models):
            model_data = kdf[kdf["model"] == model]
            for j, cond in enumerate(conditions):
                row = model_data[model_data["noisy_condition"] == cond]
                if not row.empty:
                    x_pos = j + (i - (n_models - 1) / 2) * bar_width
                    tau_val = row["tau"].iloc[0]
                    ci_lo = row["ci_lower"].iloc[0]
                    ci_hi = row["ci_upper"].iloc[0]
                    ax.errorbar(
                        x_pos, tau_val,
                        yerr=[[tau_val - ci_lo], [ci_hi - tau_val]],
                        fmt="none", color="black", capsize=3, linewidth=1,
                    )

    # Reference line for perfect agreement
    ax.axhline(y=1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)

    ax.set_ylabel("Kendall's tau")
    ax.set_xlabel("Condition")
    ax.set_ylim(0, 1.05)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    fig.tight_layout()
    return _save_figure(fig, output_dir, "rank_stability", fmt)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the figure generation CLI.

    Supports subcommands: accuracy, quadrant, cost, kendall, all.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Generate publication-quality figures for the Linguistic Tax paper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common argument defaults
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default="results/results.db", help="Path to SQLite database")
    common.add_argument("--output-dir", default="figures", help="Output directory for figures")
    common.add_argument(
        "--format", dest="fmt", choices=["pdf", "png", "both"],
        default="both", help="Output format",
    )
    common.add_argument("--analysis-dir", default="results/analysis", help="Analysis output directory")

    subparsers.add_parser("accuracy", parents=[common], help="Generate accuracy curves")
    subparsers.add_parser("quadrant", parents=[common], help="Generate quadrant scatter")
    subparsers.add_parser("cost", parents=[common], help="Generate cost heatmap")
    subparsers.add_parser("kendall", parents=[common], help="Generate Kendall tau chart")
    subparsers.add_parser("all", parents=[common], help="Generate all figures")

    args = parser.parse_args()

    if args.command in ("accuracy", "all"):
        paths = generate_accuracy_curves(args.db, args.output_dir, args.fmt, args.analysis_dir)
        logger.info("Accuracy curves: %s", paths)

    if args.command in ("quadrant", "all"):
        paths = generate_quadrant_plot(args.db, args.output_dir, args.fmt)
        logger.info("Quadrant plot: %s", paths)

    if args.command in ("cost", "all"):
        paths = generate_cost_heatmap(args.db, args.output_dir, args.fmt, args.analysis_dir)
        logger.info("Cost heatmap: %s", paths)

    if args.command in ("kendall", "all"):
        paths = generate_kendall_plot(args.db, args.output_dir, args.fmt, args.analysis_dir)
        logger.info("Kendall plot: %s", paths)


if __name__ == "__main__":
    main()
