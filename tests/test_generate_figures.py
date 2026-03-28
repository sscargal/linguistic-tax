"""Tests for the publication figure generation module.

Tests all 4 figure types (accuracy curves, quadrant plot, cost heatmap,
Kendall tau bar chart) using synthetic data, plus shared style configuration
and save helpers.
"""

import json
import os
import random
import sqlite3
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from src.generate_figures import (
    _configure_style,
    _save_figure,
    generate_accuracy_curves,
    generate_cost_heatmap,
    generate_kendall_plot,
    generate_quadrant_plot,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_db(tmp_path):
    """Create a small SQLite database with synthetic experiment data.

    Populates experiment_runs and derived_metrics tables with deterministic
    data for 10 prompts x 2 models x 3 noise types x 2 interventions x 5 reps.
    """
    db_path = str(tmp_path / "synthetic.db")
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE experiment_runs (
            run_id TEXT PRIMARY KEY,
            prompt_id TEXT NOT NULL,
            benchmark TEXT NOT NULL,
            noise_type TEXT NOT NULL,
            noise_level TEXT,
            intervention TEXT NOT NULL,
            model TEXT NOT NULL,
            repetition INTEGER NOT NULL,
            prompt_tokens INTEGER,
            preproc_output_tokens INTEGER,
            completion_tokens INTEGER,
            pass_fail INTEGER,
            total_cost_usd REAL,
            preproc_cost_usd REAL,
            main_model_input_cost_usd REAL,
            main_model_output_cost_usd REAL,
            status TEXT DEFAULT 'completed',
            ttft_ms REAL,
            ttlt_ms REAL
        )
    """)

    conn.execute("""
        CREATE TABLE derived_metrics (
            prompt_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            model TEXT NOT NULL,
            consistency_rate REAL,
            majority_pass INTEGER,
            pass_count INTEGER,
            quadrant TEXT,
            mean_ttft_ms REAL,
            mean_ttlt_ms REAL,
            mean_total_latency_ms REAL,
            mean_total_cost_usd REAL,
            token_savings INTEGER,
            net_token_cost INTEGER,
            std_latency_ms REAL,
            PRIMARY KEY (prompt_id, condition, model)
        )
    """)

    rng = random.Random(42)
    models = ["claude-sonnet-4-20250514", "gemini-1.5-pro"]
    noise_types = ["clean", "type_a_5pct", "type_a_10pct"]
    interventions = ["raw", "preproc_sanitize"]
    prompts = [f"HumanEval/{i}" for i in range(1, 11)]
    quadrants = ["robust", "confidently_wrong", "lucky", "broken"]

    for prompt_id in prompts:
        for model in models:
            for noise_type in noise_types:
                for intervention in interventions:
                    for rep in range(1, 6):
                        run_id = f"{prompt_id}_{noise_type}_{intervention}_{model}_rep{rep}"
                        pf = rng.randint(0, 1)
                        conn.execute(
                            "INSERT INTO experiment_runs "
                            "(run_id, prompt_id, benchmark, noise_type, noise_level, "
                            "intervention, model, repetition, prompt_tokens, "
                            "preproc_output_tokens, completion_tokens, pass_fail, "
                            "total_cost_usd, preproc_cost_usd, "
                            "main_model_input_cost_usd, main_model_output_cost_usd, "
                            "status, ttft_ms, ttlt_ms) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                run_id, prompt_id, "humaneval", noise_type,
                                noise_type if noise_type != "clean" else "",
                                intervention, model, rep,
                                100, 85, 50, pf,
                                0.001, 0.0, 0.0005, 0.0005,
                                "completed", 50.0, 200.0,
                            ),
                        )

                    # Add a derived_metrics row for this condition
                    cr = rng.uniform(0.3, 1.0)
                    mp = rng.randint(0, 1)
                    q = rng.choice(quadrants)
                    condition = f"{noise_type}_{intervention}"
                    conn.execute(
                        "INSERT INTO derived_metrics "
                        "(prompt_id, condition, model, consistency_rate, "
                        "majority_pass, pass_count, quadrant) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (prompt_id, condition, model, cr, mp, rng.randint(0, 5), q),
                    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def synthetic_analysis_dir(tmp_path):
    """Create synthetic analysis output files matching Phase 5 format.

    Produces bootstrap_results.json, cost_rollups.json, kendall_results.json,
    and their CSV counterparts.
    """
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    csv_dir = analysis_dir / "csv"
    csv_dir.mkdir()

    # bootstrap_results.json
    bootstrap_data = {
        "clean_raw": {"mean": 0.85, "ci_lower": 0.80, "ci_upper": 0.90},
        "type_a_5pct_raw": {"mean": 0.75, "ci_lower": 0.70, "ci_upper": 0.80},
        "type_a_10pct_raw": {"mean": 0.65, "ci_lower": 0.58, "ci_upper": 0.72},
        "type_a_20pct_raw": {"mean": 0.50, "ci_lower": 0.42, "ci_upper": 0.58},
    }
    with open(analysis_dir / "bootstrap_results.json", "w") as f:
        json.dump(bootstrap_data, f)

    # csv/bootstrap_cis.csv
    with open(csv_dir / "bootstrap_cis.csv", "w") as f:
        f.write("condition,mean,ci_lower,ci_upper\n")
        for cond, vals in bootstrap_data.items():
            f.write(f"{cond},{vals['mean']},{vals['ci_lower']},{vals['ci_upper']}\n")

    # cost_rollups.json
    cost_data = [
        {"model": "claude-sonnet-4-20250514", "intervention": "raw",
         "noise_type": "clean", "mean_token_savings": 0},
        {"model": "claude-sonnet-4-20250514", "intervention": "preproc_sanitize",
         "noise_type": "type_a_10pct", "mean_token_savings": -15},
        {"model": "gemini-1.5-pro", "intervention": "raw",
         "noise_type": "clean", "mean_token_savings": 0},
        {"model": "gemini-1.5-pro", "intervention": "preproc_sanitize",
         "noise_type": "type_a_10pct", "mean_token_savings": -12},
    ]
    with open(analysis_dir / "cost_rollups.json", "w") as f:
        json.dump(cost_data, f)

    # csv/cost_rollups.csv
    with open(csv_dir / "cost_rollups.csv", "w") as f:
        f.write("model,intervention,noise_type,mean_token_savings\n")
        for row in cost_data:
            f.write(f"{row['model']},{row['intervention']},{row['noise_type']},{row['mean_token_savings']}\n")

    # kendall_results.json
    kendall_data = [
        {"model": "claude-sonnet-4-20250514", "noisy_condition": "type_a_5pct",
         "tau": 0.85, "p_value": 0.01, "ci_lower": 0.75, "ci_upper": 0.95},
        {"model": "claude-sonnet-4-20250514", "noisy_condition": "type_a_10pct",
         "tau": 0.70, "p_value": 0.02, "ci_lower": 0.58, "ci_upper": 0.82},
        {"model": "gemini-1.5-pro", "noisy_condition": "type_a_5pct",
         "tau": 0.90, "p_value": 0.005, "ci_lower": 0.82, "ci_upper": 0.98},
        {"model": "gemini-1.5-pro", "noisy_condition": "type_a_10pct",
         "tau": 0.75, "p_value": 0.015, "ci_lower": 0.63, "ci_upper": 0.87},
    ]
    with open(analysis_dir / "kendall_results.json", "w") as f:
        json.dump(kendall_data, f)

    # csv/kendall_tau.csv
    with open(csv_dir / "kendall_tau.csv", "w") as f:
        f.write("model,noisy_condition,tau,p_value,ci_lower,ci_upper\n")
        for row in kendall_data:
            f.write(
                f"{row['model']},{row['noisy_condition']},{row['tau']},"
                f"{row['p_value']},{row['ci_lower']},{row['ci_upper']}\n"
            )

    return str(analysis_dir)


# ---------------------------------------------------------------------------
# Style configuration tests
# ---------------------------------------------------------------------------


class TestConfigureStyle:
    """Tests for _configure_style shared settings."""

    def test_configure_style(self):
        """After calling _configure_style, rcParams match publication spec."""
        _configure_style()
        params = matplotlib.rcParams
        assert params["axes.labelsize"] == 12
        assert params["axes.titlesize"] == 14
        assert params["xtick.labelsize"] == 10
        assert params["ytick.labelsize"] == 10
        assert params["pdf.fonttype"] == 42
        assert params["savefig.dpi"] == 300


# ---------------------------------------------------------------------------
# Save figure tests
# ---------------------------------------------------------------------------


class TestSaveFigure:
    """Tests for the _save_figure helper."""

    def test_save_figure_both(self, tmp_path):
        """fmt='both' produces both PDF and PNG, each with valid headers."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        output_dir = str(tmp_path / "out")

        paths = _save_figure(fig, output_dir, "test_fig", fmt="both")

        pdf_path = os.path.join(output_dir, "test_fig.pdf")
        png_path = os.path.join(output_dir, "test_fig.png")
        assert os.path.exists(pdf_path)
        assert os.path.exists(png_path)
        assert os.path.getsize(pdf_path) > 0
        assert os.path.getsize(png_path) > 0

        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"
        with open(png_path, "rb") as f:
            assert f.read(4) == b"\x89PNG"

        assert len(paths) == 2

    def test_save_figure_pdf_only(self, tmp_path):
        """fmt='pdf' produces only PDF, no PNG."""
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        output_dir = str(tmp_path / "out")

        _save_figure(fig, output_dir, "test_pdf", fmt="pdf")

        assert os.path.exists(os.path.join(output_dir, "test_pdf.pdf"))
        assert not os.path.exists(os.path.join(output_dir, "test_pdf.png"))

    def test_save_figure_png_only(self, tmp_path):
        """fmt='png' produces only PNG, no PDF."""
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        output_dir = str(tmp_path / "out")

        _save_figure(fig, output_dir, "test_png", fmt="png")

        assert not os.path.exists(os.path.join(output_dir, "test_png.pdf"))
        assert os.path.exists(os.path.join(output_dir, "test_png.png"))


# ---------------------------------------------------------------------------
# Figure generation tests
# ---------------------------------------------------------------------------


class TestAccuracyCurves:
    """Tests for generate_accuracy_curves."""

    def test_accuracy_curves(self, synthetic_db, synthetic_analysis_dir, tmp_path):
        """Produces robustness_curve PDF+PNG at double-column width (7in)."""
        output_dir = str(tmp_path / "figs")

        paths = generate_accuracy_curves(
            db_path=synthetic_db,
            output_dir=output_dir,
            fmt="both",
            analysis_dir=synthetic_analysis_dir,
        )

        pdf_path = os.path.join(output_dir, "robustness_curve.pdf")
        png_path = os.path.join(output_dir, "robustness_curve.png")
        assert os.path.exists(pdf_path)
        assert os.path.exists(png_path)
        assert os.path.getsize(pdf_path) > 0
        assert os.path.getsize(png_path) > 0

        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"
        with open(png_path, "rb") as f:
            assert f.read(4) == b"\x89PNG"

        assert len(paths) == 2


class TestQuadrantPlot:
    """Tests for generate_quadrant_plot."""

    def test_quadrant_plot(self, synthetic_db, tmp_path):
        """Produces quadrant_migration PDF+PNG at double-column width (7in)."""
        output_dir = str(tmp_path / "figs")

        paths = generate_quadrant_plot(
            db_path=synthetic_db,
            output_dir=output_dir,
            fmt="both",
        )

        pdf_path = os.path.join(output_dir, "quadrant_migration.pdf")
        png_path = os.path.join(output_dir, "quadrant_migration.png")
        assert os.path.exists(pdf_path)
        assert os.path.exists(png_path)
        assert os.path.getsize(pdf_path) > 0
        assert os.path.getsize(png_path) > 0

        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

        assert len(paths) == 2


class TestCostHeatmap:
    """Tests for generate_cost_heatmap."""

    def test_cost_heatmap(self, synthetic_db, synthetic_analysis_dir, tmp_path):
        """Produces cost_model PDF+PNG at single-column width (3.5in)."""
        output_dir = str(tmp_path / "figs")

        paths = generate_cost_heatmap(
            db_path=synthetic_db,
            output_dir=output_dir,
            fmt="both",
            analysis_dir=synthetic_analysis_dir,
        )

        pdf_path = os.path.join(output_dir, "cost_model.pdf")
        png_path = os.path.join(output_dir, "cost_model.png")
        assert os.path.exists(pdf_path)
        assert os.path.exists(png_path)
        assert os.path.getsize(pdf_path) > 0
        assert os.path.getsize(png_path) > 0

        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

        assert len(paths) == 2


class TestKendallPlot:
    """Tests for generate_kendall_plot."""

    def test_kendall_plot(self, synthetic_db, synthetic_analysis_dir, tmp_path):
        """Produces rank_stability PDF+PNG at single-column width (3.5in)."""
        output_dir = str(tmp_path / "figs")

        paths = generate_kendall_plot(
            db_path=synthetic_db,
            output_dir=output_dir,
            fmt="both",
            analysis_dir=synthetic_analysis_dir,
        )

        pdf_path = os.path.join(output_dir, "rank_stability.pdf")
        png_path = os.path.join(output_dir, "rank_stability.png")
        assert os.path.exists(pdf_path)
        assert os.path.exists(png_path)
        assert os.path.getsize(pdf_path) > 0
        assert os.path.getsize(png_path) > 0

        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

        assert len(paths) == 2


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the argparse CLI interface."""

    def test_cli_all_subcommand(self, synthetic_db, synthetic_analysis_dir, tmp_path):
        """Running CLI with 'all' generates all 8 output files."""
        output_dir = str(tmp_path / "figs")

        result = subprocess.run(
            [
                sys.executable, "-m", "src.generate_figures",
                "all",
                "--db", synthetic_db,
                "--output-dir", output_dir,
                "--analysis-dir", synthetic_analysis_dir,
            ],
            capture_output=True,
            text=True,
            cwd="/home/steve/linguistic-tax",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        expected_files = [
            "robustness_curve.pdf", "robustness_curve.png",
            "quadrant_migration.pdf", "quadrant_migration.png",
            "cost_model.pdf", "cost_model.png",
            "rank_stability.pdf", "rank_stability.png",
        ]
        for fname in expected_files:
            fpath = os.path.join(output_dir, fname)
            assert os.path.exists(fpath), f"Missing: {fname}"
            assert os.path.getsize(fpath) > 0, f"Empty: {fname}"

    def test_cli_single_subcommand(self, synthetic_db, synthetic_analysis_dir, tmp_path):
        """Running CLI with 'accuracy' generates only robustness_curve files."""
        output_dir = str(tmp_path / "figs")

        result = subprocess.run(
            [
                sys.executable, "-m", "src.generate_figures",
                "accuracy",
                "--db", synthetic_db,
                "--output-dir", output_dir,
                "--analysis-dir", synthetic_analysis_dir,
            ],
            capture_output=True,
            text=True,
            cwd="/home/steve/linguistic-tax",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        assert os.path.exists(os.path.join(output_dir, "robustness_curve.pdf"))
        assert os.path.exists(os.path.join(output_dir, "robustness_curve.png"))
        # Other figures should NOT be generated
        assert not os.path.exists(os.path.join(output_dir, "quadrant_migration.pdf"))
        assert not os.path.exists(os.path.join(output_dir, "cost_model.pdf"))
        assert not os.path.exists(os.path.join(output_dir, "rank_stability.pdf"))


# ---------------------------------------------------------------------------
# Empty data edge case tests
# ---------------------------------------------------------------------------


class TestEmptyDataHandling:
    """Tests for graceful handling of empty/missing data."""

    def test_accuracy_curves_empty_db(self, tmp_path):
        """generate_accuracy_curves with empty DB returns empty list."""
        from src.db import init_database
        db_path = str(tmp_path / "empty.db")
        conn = init_database(db_path)
        conn.close()
        result = generate_accuracy_curves(db_path, str(tmp_path / "figs"))
        assert result == []

    def test_quadrant_plot_empty_db(self, tmp_path):
        """generate_quadrant_plot with no derived_metrics returns empty list."""
        from src.db import init_database
        db_path = str(tmp_path / "empty.db")
        conn = init_database(db_path)
        conn.close()
        result = generate_quadrant_plot(db_path, str(tmp_path / "figs"))
        assert result == []

    def test_cost_heatmap_missing_file(self, tmp_path):
        """generate_cost_heatmap with missing cost_rollups.json returns empty list."""
        result = generate_cost_heatmap(
            "dummy.db",
            str(tmp_path / "figs"),
            analysis_dir=str(tmp_path / "nonexistent"),
        )
        assert result == []

    def test_kendall_plot_missing_file(self, tmp_path):
        """generate_kendall_plot with missing kendall_results.json returns empty list."""
        result = generate_kendall_plot(
            "dummy.db",
            str(tmp_path / "figs"),
            analysis_dir=str(tmp_path / "nonexistent"),
        )
        assert result == []
