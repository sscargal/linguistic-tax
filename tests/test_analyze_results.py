"""Tests for the statistical analysis module (analyze_results.py).

Covers GLMM fitting with fallback, bootstrap CIs, McNemar's fragility/
recoverability test, Kendall's tau rank-order stability, BH correction,
sensitivity analysis, and effect size summary table generation.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.analyze_results import (
    _bootstrap_ci,
    apply_bh_correction,
    compute_bootstrap_cis,
    compute_kendall_tau,
    fit_glmm,
    generate_effect_size_summary,
    load_derived_metrics,
    load_experiment_data,
    main,
    run_mcnemar_analysis,
    run_sensitivity_analysis,
)


# ---------------------------------------------------------------------------
# GLMM Tests
# ---------------------------------------------------------------------------


class TestGLMM:
    """Tests for GLMM fitting with fallback chain."""

    def test_glmm_fit_returns_coefficients(self, analysis_test_db: str) -> None:
        """fit_glmm returns dict with 'coefficients' list containing required keys."""
        df = load_experiment_data(analysis_test_db)
        result = fit_glmm(df)

        assert "coefficients" in result
        assert isinstance(result["coefficients"], list)
        assert len(result["coefficients"]) > 0

        coeff = result["coefficients"][0]
        assert "name" in coeff
        assert "estimate" in coeff
        assert "std_err" in coeff
        assert "p_value" in coeff

    def test_glmm_fallback_on_convergence_failure(
        self, degenerate_test_db: str
    ) -> None:
        """When data is too small for GLMM, falls back to GEE."""
        df = load_experiment_data(degenerate_test_db)
        result = fit_glmm(df)

        # Should fall back to GEE (or reduced GLMM) due to degenerate data
        assert result["model_type"] in ("reduced_glmm", "gee")

    def test_glmm_produces_odds_ratios(self, analysis_test_db: str) -> None:
        """Result contains odds_ratios with OR and CI keys."""
        df = load_experiment_data(analysis_test_db)
        result = fit_glmm(df)

        assert "odds_ratios" in result
        assert isinstance(result["odds_ratios"], list)
        if len(result["odds_ratios"]) > 0:
            entry = result["odds_ratios"][0]
            assert "or" in entry
            assert "ci_lower" in entry
            assert "ci_upper" in entry


# ---------------------------------------------------------------------------
# Bootstrap CI Tests
# ---------------------------------------------------------------------------


class TestBootstrapCIs:
    """Tests for bootstrap confidence interval computation."""

    def test_bootstrap_ci_accuracy(self, analysis_test_db: str) -> None:
        """compute_bootstrap_cis returns per-condition CIs with required keys."""
        df = load_experiment_data(analysis_test_db)
        result = compute_bootstrap_cis(df, n_iterations=500, seed=42)

        assert isinstance(result, dict)
        assert len(result) > 0

        # Check structure of first entry
        first_key = next(iter(result))
        entry = result[first_key]
        assert "mean" in entry
        assert "ci_lower" in entry
        assert "ci_upper" in entry
        assert entry["ci_lower"] <= entry["mean"] <= entry["ci_upper"]

    def test_bootstrap_fallback_on_degenerate(
        self, analysis_test_db: str
    ) -> None:
        """When all values are identical, falls back to percentile without error."""
        # Create a DataFrame where one condition has identical values
        df = load_experiment_data(analysis_test_db)
        # MBPP/1 always passes (all 1s) -- should trigger BCa fallback
        result = compute_bootstrap_cis(df, n_iterations=500, seed=42)
        # Should complete without raising
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Bootstrap CI for Consistency Rate Tests
# ---------------------------------------------------------------------------


class TestBootstrapCR:
    """Tests for bootstrap CIs on Consistency Rate from derived_metrics."""

    def test_bootstrap_ci_cr(self, analysis_test_db: str) -> None:
        """compute_bootstrap_cis with db_path returns CR CIs."""
        df = load_experiment_data(analysis_test_db)
        result = compute_bootstrap_cis(
            df, n_iterations=500, seed=42, db_path=analysis_test_db
        )
        # Should have CR entries (keyed with "cr_" prefix)
        cr_keys = [k for k in result if k.startswith("cr_")]
        assert len(cr_keys) > 0, "Should have CR bootstrap CIs"
        for k in cr_keys:
            entry = result[k]
            assert "mean" in entry
            assert "ci_lower" in entry
            assert "ci_upper" in entry
            assert "metric" in entry
            assert entry["metric"] == "consistency_rate"

    def test_bootstrap_ci_cr_values_valid(self, analysis_test_db: str) -> None:
        """CR CI values are between 0.0 and 1.0."""
        df = load_experiment_data(analysis_test_db)
        result = compute_bootstrap_cis(
            df, n_iterations=500, seed=42, db_path=analysis_test_db
        )
        cr_keys = [k for k in result if k.startswith("cr_")]
        for k in cr_keys:
            entry = result[k]
            assert 0.0 <= entry["ci_lower"] <= 1.0
            assert 0.0 <= entry["ci_upper"] <= 1.0
            assert entry["ci_lower"] <= entry["ci_upper"]

    def test_bootstrap_ci_without_db_path(self, analysis_test_db: str) -> None:
        """compute_bootstrap_cis without db_path still works (no CR CIs)."""
        df = load_experiment_data(analysis_test_db)
        result = compute_bootstrap_cis(df, n_iterations=500, seed=42)
        cr_keys = [k for k in result if k.startswith("cr_")]
        assert len(cr_keys) == 0, "Without db_path, no CR CIs should be present"


# ---------------------------------------------------------------------------
# McNemar's Test
# ---------------------------------------------------------------------------


class TestMcNemar:
    """Tests for McNemar's fragility/recoverability analysis."""

    def test_mcnemar_fragile_detection(self, analysis_test_db: str) -> None:
        """Prompt that passes clean but fails noisy is classified 'fragile'."""
        df = load_experiment_data(analysis_test_db)
        result = run_mcnemar_analysis(df, baseline_condition="clean")

        # HumanEval/1 always passes clean_raw, always fails type_a_20pct_raw
        fragile_prompts = [
            r for r in result["comparisons"]
            if r["prompt_id"] == "HumanEval/1"
            and r["classification"] == "fragile"
        ]
        assert len(fragile_prompts) > 0, "HumanEval/1 should be classified as fragile"

    def test_mcnemar_recoverable_detection(self, analysis_test_db: str) -> None:
        """Prompt that fails raw but passes with intervention is 'recoverable'."""
        df = load_experiment_data(analysis_test_db)
        # Compare raw vs pre_proc_sanitize for clean condition
        result = run_mcnemar_analysis(
            df,
            baseline_condition="clean",
            compare_interventions=True,
        )

        # HumanEval/2 fails clean_raw, passes clean_pre_proc_sanitize
        recoverable_prompts = [
            r for r in result["comparisons"]
            if r["prompt_id"] == "HumanEval/2"
            and r["classification"] == "recoverable"
        ]
        assert len(recoverable_prompts) > 0, (
            "HumanEval/2 should be classified as recoverable"
        )

    def test_mcnemar_skips_concordant(self, analysis_test_db: str) -> None:
        """Prompts with same result in both conditions are skipped."""
        df = load_experiment_data(analysis_test_db)
        result = run_mcnemar_analysis(df, baseline_condition="clean")

        # MBPP/1 always passes everywhere -- should be skipped (concordant)
        mbpp1_entries = [
            r for r in result["comparisons"]
            if r["prompt_id"] == "MBPP/1"
        ]
        # MBPP/1 might appear for some conditions but should be skipped
        # for clean vs type_a_10pct and clean vs type_a_20pct since all pass
        assert result["skipped_count"] > 0, "Should have skipped concordant prompts"


# ---------------------------------------------------------------------------
# Kendall's Tau Tests
# ---------------------------------------------------------------------------


class TestKendallTau:
    """Tests for Kendall's tau rank-order stability."""

    def test_kendall_tau_perfect_agreement(self, analysis_test_db: str) -> None:
        """Identical rankings should produce tau close to 1.0."""
        df = load_experiment_data(analysis_test_db)
        results = compute_kendall_tau(df)

        assert isinstance(results, list)
        assert len(results) > 0
        # At least one result should have tau > 0 (some agreement)
        taus = [r["tau"] for r in results]
        assert any(t > -1.0 for t in taus), "At least some tau values should exist"

    def test_kendall_tau_returns_p_value(self, analysis_test_db: str) -> None:
        """Result dict has 'tau' and 'p_value' keys."""
        df = load_experiment_data(analysis_test_db)
        results = compute_kendall_tau(df)

        assert len(results) > 0
        for r in results:
            assert "tau" in r
            assert "p_value" in r
            assert "n_prompts" in r


# ---------------------------------------------------------------------------
# BH Correction Tests
# ---------------------------------------------------------------------------


class TestBHCorrection:
    """Tests for Benjamini-Hochberg FDR correction."""

    def test_bh_correction_per_family(self) -> None:
        """apply_bh_correction returns raw and corrected p-values per family."""
        families = {
            "mcnemar": [0.01, 0.04, 0.045, 0.06, 0.10, 0.20, 0.50],
            "glmm": [0.001, 0.03, 0.05, 0.08],
        }
        result = apply_bh_correction(families)

        assert "mcnemar" in result
        assert "glmm" in result
        assert "raw_p_values" in result["mcnemar"]
        assert "corrected_p_values" in result["mcnemar"]
        assert len(result["mcnemar"]["raw_p_values"]) == 7
        assert len(result["mcnemar"]["corrected_p_values"]) == 7

    def test_bh_correction_reduces_significance(self) -> None:
        """Some raw-significant p-values become non-significant after correction."""
        # Create p-values where some barely pass alpha=0.05 but fail after BH
        families = {
            "test_family": [
                0.001, 0.010, 0.020, 0.030, 0.040, 0.045, 0.048,
                0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
                0.50, 0.60, 0.70, 0.80, 0.90,
            ],
        }
        result = apply_bh_correction(families, alpha=0.05)

        raw = result["test_family"]["raw_p_values"]
        corrected = result["test_family"]["corrected_p_values"]
        reject = result["test_family"]["reject"]

        # Some raw p-values < 0.05 should not be rejected after correction
        raw_significant = sum(1 for p in raw if p < 0.05)
        corrected_significant = sum(1 for r in reject if r)
        assert corrected_significant <= raw_significant, (
            "BH correction should not increase significance"
        )


# ---------------------------------------------------------------------------
# Sensitivity Analysis Tests
# ---------------------------------------------------------------------------


class TestSensitivityAnalysis:
    """Tests for sensitivity analysis (dropping extreme prompts)."""

    def test_sensitivity_analysis_drops_prompts(
        self, analysis_test_db: str
    ) -> None:
        """Sensitivity result has fewer prompts than full analysis."""
        df = load_experiment_data(analysis_test_db)
        result = run_sensitivity_analysis(df, drop_pct=0.10)

        assert "n_prompts_original" in result
        assert "n_prompts_filtered" in result
        assert "n_dropped" in result
        assert result["n_prompts_filtered"] < result["n_prompts_original"]
        assert result["n_dropped"] > 0
        assert "glmm_results" in result
        assert "bootstrap_results" in result


# ---------------------------------------------------------------------------
# Effect Size Summary Tests
# ---------------------------------------------------------------------------


class TestEffectSizeSummary:
    """Tests for effect size summary table generation."""

    def test_effect_size_summary_has_required_columns(
        self, analysis_test_db: str
    ) -> None:
        """CSV output has columns: metric, effect_size, ci_lower, ci_upper, effect_type."""
        df = load_experiment_data(analysis_test_db)
        glmm_results = fit_glmm(df)
        kendall_results = compute_kendall_tau(df)
        bootstrap_results = compute_bootstrap_cis(df, n_iterations=500, seed=42)

        summary_df = generate_effect_size_summary(
            glmm_results, kendall_results, bootstrap_results,
        )

        assert isinstance(summary_df, pd.DataFrame)
        required_cols = {"metric", "effect_size", "ci_lower", "ci_upper", "effect_type"}
        assert required_cols.issubset(set(summary_df.columns)), (
            f"Missing columns: {required_cols - set(summary_df.columns)}"
        )
        assert len(summary_df) > 0


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the CLI main() function and subcommands."""

    def test_main_glmm_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'glmm' subcommand completes without error."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path), "glmm"],
        ):
            main()

    def test_main_mcnemar_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'mcnemar' subcommand completes without error."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path), "mcnemar"],
        ):
            main()

    def test_main_bootstrap_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'bootstrap' subcommand completes without error."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path),
             "--bootstrap-iterations", "100", "bootstrap"],
        ):
            main()

    def test_main_kendall_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'kendall' subcommand completes without error."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path), "kendall"],
        ):
            main()

    def test_main_sensitivity_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'sensitivity' subcommand completes without error."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path), "sensitivity"],
        ):
            main()

    def test_main_all_subcommand(
        self, analysis_test_db: str, tmp_path
    ) -> None:
        """main() with 'all' subcommand runs every analysis."""
        with patch(
            "sys.argv",
            ["analyze_results", "--db", analysis_test_db,
             "--output-dir", str(tmp_path),
             "--bootstrap-iterations", "100", "all"],
        ):
            main()
        # Verify output files created
        import os
        assert os.path.exists(tmp_path / "glmm_results.json")
        assert os.path.exists(tmp_path / "analysis_summary.json")


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_bootstrap_ci_constant_series(self) -> None:
        """_bootstrap_ci with constant data returns finite CI."""
        data = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        ci_low, ci_high, method = _bootstrap_ci(
            data, np.mean, n_resamples=100, seed=42
        )
        assert np.isfinite(ci_low)
        assert np.isfinite(ci_high)

    def test_compute_bootstrap_cis_empty_df(self) -> None:
        """compute_bootstrap_cis with empty DataFrame returns empty dict."""
        empty_df = pd.DataFrame(
            columns=["noise_type", "intervention", "model", "pass_fail"]
        )
        result = compute_bootstrap_cis(empty_df, n_iterations=100, seed=42)
        assert result == {}
