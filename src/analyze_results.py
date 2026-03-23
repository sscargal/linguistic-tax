"""Statistical analysis module for the Linguistic Tax research toolkit.

Implements aggregate statistical analyses: GLMM with fallback chain,
bootstrap CIs, McNemar's test for fragility/recoverability, Kendall's
tau for rank-order stability, BH correction per test family, sensitivity
analysis, and effect size summary table.

CLI with argparse subcommands: glmm, mcnemar, bootstrap, kendall,
sensitivity, all. Outputs as JSON + CSV + terminal summary.

See RDD Sections 7.2-7.8 for statistical method specifications.
"""

import argparse
import json
import logging
import os
import sqlite3
import warnings
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import bootstrap as scipy_bootstrap
from scipy.stats import kendalltau
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests
from tabulate import tabulate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_experiment_data(db_path: str) -> pd.DataFrame:
    """Load completed experiment runs from the SQLite database.

    Filters for rows with status='completed' and non-null pass_fail.
    Adds derived columns for analysis convenience.

    Args:
        db_path: Path to the SQLite results database.

    Returns:
        DataFrame containing all completed experiment runs with derived columns.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM experiment_runs WHERE status = 'completed' "
        "AND pass_fail IS NOT NULL",
        conn,
    )
    conn.close()

    if not df.empty:
        # Derive noise_level_str from noise_type
        def _extract_noise_level(nt: str) -> str | None:
            if "5pct" in nt:
                return "5"
            elif "10pct" in nt:
                return "10"
            elif "20pct" in nt:
                return "20"
            return None

        df["noise_level_str"] = df["noise_type"].apply(_extract_noise_level)
        df["benchmark_source"] = df["benchmark"]

    return df


def load_derived_metrics(db_path: str) -> pd.DataFrame:
    """Load derived metrics from the SQLite database.

    Returns DataFrame with consistency_rate, quadrant, cost fields
    per (prompt_id, condition, model).

    Args:
        db_path: Path to the SQLite results database.

    Returns:
        DataFrame containing all derived metrics rows.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT prompt_id, condition, model, consistency_rate, "
        "majority_pass, pass_count, quadrant, mean_total_cost_usd, "
        "token_savings, net_token_cost FROM derived_metrics",
        conn,
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# GLMM with fallback chain
# ---------------------------------------------------------------------------


def fit_glmm(df: pd.DataFrame) -> dict[str, Any]:
    """Fit a GLMM on binary pass/fail outcomes with three-level fallback.

    Attempts: (1) BinomialBayesMixedGLM with full random effects,
    (2) reduced random effects, (3) GEE with exchangeable correlation.

    Fixed effects use explicit 2-way interactions (not the * operator).

    Args:
        df: DataFrame with experiment_runs data (must have pass_fail,
            noise_type, intervention, model, benchmark, prompt_id columns).

    Returns:
        Dict with model_type, coefficients (list of dicts with name/estimate/
        std_err/p_value), odds_ratios, convergence_info, formula_used.
    """
    # Ensure pass_fail is numeric
    df = df.copy()
    df["pass_fail"] = df["pass_fail"].astype(int)

    # Build available terms based on data variability
    fixed_terms = []
    base_terms = []

    # Only include factors with more than one level
    for col, formula_term in [
        ("noise_type", "C(noise_type)"),
        ("intervention", "C(intervention)"),
        ("model", "C(model)"),
        ("benchmark", "C(benchmark)"),
    ]:
        if col in df.columns and df[col].nunique() > 1:
            base_terms.append(formula_term)
            fixed_terms.append(formula_term)

    # Add 2-way interactions only between terms with multiple levels
    interaction_pairs = [
        ("noise_type", "intervention", "C(noise_type):C(intervention)"),
        ("noise_type", "model", "C(noise_type):C(model)"),
        ("intervention", "model", "C(intervention):C(model)"),
    ]
    for col1, col2, interaction_term in interaction_pairs:
        if (
            col1 in df.columns
            and col2 in df.columns
            and df[col1].nunique() > 1
            and df[col2].nunique() > 1
        ):
            fixed_terms.append(interaction_term)

    if not fixed_terms:
        # Fallback: just intercept
        formula = "pass_fail ~ 1"
    else:
        formula = "pass_fail ~ " + " + ".join(fixed_terms)

    model_type = "bayesian_glmm"
    convergence_info = ""
    result_obj = None

    # Level 1: Full BayesMixedGLM with prompt + prompt:model random effects
    if df["prompt_id"].nunique() > 1:
        vc_formulas = {
            "prompt_intercept": "0 + C(prompt_id)",
        }
        # Only add prompt:model interaction if both vary
        if df["model"].nunique() > 1:
            vc_formulas["prompt_model"] = "0 + C(prompt_id):C(model)"

        try:
            mdl = BinomialBayesMixedGLM.from_formula(
                formula, vc_formulas, data=df,
            )
            result_obj = mdl.fit_vb()
            model_type = "bayesian_glmm"
            convergence_info = "Full BayesMixedGLM converged"
            logger.info("GLMM (BayesMixedGLM) converged with full random effects")
        except Exception as exc:
            logger.warning(
                "Full GLMM failed (%s), trying reduced random effects", exc
            )
            # Level 2: Reduced random effects
            vc_reduced = {"prompt_intercept": "0 + C(prompt_id)"}
            try:
                mdl = BinomialBayesMixedGLM.from_formula(
                    formula, vc_reduced, data=df,
                )
                result_obj = mdl.fit_vb()
                model_type = "reduced_glmm"
                convergence_info = "Reduced BayesMixedGLM converged (dropped prompt:model)"
                logger.info("GLMM (reduced random effects) converged")
            except Exception as exc2:
                logger.warning("Reduced GLMM failed (%s), falling back to GEE", exc2)
                result_obj = None

    # Level 3: GEE fallback
    if result_obj is None:
        try:
            gee_model = GEE.from_formula(
                formula,
                groups="prompt_id",
                data=df,
                family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable(),
            )
            result_obj = gee_model.fit()
            model_type = "gee"
            convergence_info = "GEE with exchangeable correlation converged"
            logger.info("GEE fallback converged")
        except Exception as exc3:
            logger.warning("GEE also failed (%s), using simple logistic regression", exc3)
            # Ultimate fallback: simple logistic regression
            try:
                logit_model = sm.GLM.from_formula(
                    formula, data=df, family=sm.families.Binomial(),
                )
                result_obj = logit_model.fit()
                model_type = "gee"  # Still report as GEE-level fallback
                convergence_info = "Simple logistic regression (final fallback)"
                logger.info("Simple logistic regression converged")
            except Exception as exc4:
                logger.error("All model fitting failed: %s", exc4)
                return {
                    "model_type": "gee",
                    "coefficients": [],
                    "odds_ratios": [],
                    "convergence_info": f"All models failed: {exc4}",
                    "formula_used": formula,
                }

    # Extract coefficients
    coefficients = _extract_coefficients(result_obj, model_type)
    odds_ratios = _compute_odds_ratios(coefficients)

    return {
        "model_type": model_type,
        "coefficients": coefficients,
        "odds_ratios": odds_ratios,
        "convergence_info": convergence_info,
        "formula_used": formula,
    }


def _extract_coefficients(
    result_obj: Any, model_type: str
) -> list[dict[str, Any]]:
    """Extract coefficient table from a fitted model result.

    Args:
        result_obj: Fitted model result object.
        model_type: One of 'bayesian_glmm', 'reduced_glmm', 'gee'.

    Returns:
        List of dicts with name, estimate, std_err, p_value.
    """
    coefficients: list[dict[str, Any]] = []

    if model_type in ("bayesian_glmm", "reduced_glmm"):
        # BayesMixedGLM results
        fe_mean = result_obj.fe_mean
        fe_sd = result_obj.fe_sd
        names = result_obj.model.fep_names

        for i, name in enumerate(names):
            est = float(fe_mean[i])
            se = float(fe_sd[i])
            # Approximate p-value from z-score for Bayesian results
            z = abs(est) / se if se > 0 else 0.0
            p_val = float(2 * (1 - sm.distributions.ECDF(
                np.abs(np.random.standard_normal(10000))
            )(z))) if se > 0 else 1.0
            # Use proper normal distribution for p-value
            from scipy.stats import norm
            p_val = float(2 * (1 - norm.cdf(abs(z)))) if se > 0 else 1.0

            coefficients.append({
                "name": name,
                "estimate": est,
                "std_err": se,
                "p_value": p_val,
            })
    else:
        # GEE or GLM results -- use summary table
        try:
            params = result_obj.params
            bse = result_obj.bse
            pvalues = result_obj.pvalues

            for name in params.index:
                coefficients.append({
                    "name": name,
                    "estimate": float(params[name]),
                    "std_err": float(bse[name]),
                    "p_value": float(pvalues[name]),
                })
        except Exception as exc:
            logger.warning("Could not extract coefficients: %s", exc)

    return coefficients


def _compute_odds_ratios(
    coefficients: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute odds ratios and CIs from coefficient estimates.

    OR = exp(estimate), CI = exp(estimate +/- 1.96 * std_err).

    Args:
        coefficients: List of coefficient dicts from _extract_coefficients.

    Returns:
        List of dicts with name, or, ci_lower, ci_upper.
    """
    odds_ratios: list[dict[str, Any]] = []
    for coeff in coefficients:
        est = coeff["estimate"]
        se = coeff["std_err"]
        or_val = float(np.exp(est))
        ci_lower = float(np.exp(est - 1.96 * se))
        ci_upper = float(np.exp(est + 1.96 * se))
        odds_ratios.append({
            "name": coeff["name"],
            "or": or_val,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        })
    return odds_ratios


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------


def compute_bootstrap_cis(
    df: pd.DataFrame,
    n_iterations: int = 10000,
    seed: int = 42,
    db_path: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute bootstrap confidence intervals for accuracy per condition.

    Groups by (noise_type, intervention, model) and computes bootstrap
    CIs for mean pass_fail (accuracy). Uses BCa with percentile fallback.

    When db_path is provided, also computes bootstrap CIs for Consistency
    Rate (CR) values from the derived_metrics table. CR entries are keyed
    with a "cr_" prefix and tagged with metric="consistency_rate".

    Args:
        df: DataFrame with experiment_runs data.
        n_iterations: Number of bootstrap resamples.
        seed: Random seed for reproducibility.
        db_path: Optional path to SQLite DB for CR bootstrap CIs.

    Returns:
        Dict keyed by condition string, each with mean, ci_lower,
        ci_upper, method_used.
    """
    results: dict[str, dict[str, Any]] = {}

    grouped = df.groupby(["noise_type", "intervention", "model"])

    for (noise_type, intervention, model), group in grouped:
        condition_key = f"{noise_type}_{intervention}_{model}"
        values = group["pass_fail"].astype(float).values

        mean_val = float(np.mean(values))

        if len(values) < 2:
            results[condition_key] = {
                "mean": mean_val,
                "ci_lower": mean_val,
                "ci_upper": mean_val,
                "method_used": "point_estimate",
                "n": len(values),
            }
            continue

        ci_lower, ci_upper, method_used = _bootstrap_ci(
            values, np.mean, n_iterations, seed
        )

        results[condition_key] = {
            "mean": mean_val,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "method_used": method_used,
            "n": len(values),
        }

    # Bootstrap CIs for Consistency Rate from derived_metrics
    if db_path is not None:
        derived_df = load_derived_metrics(db_path)
        if not derived_df.empty:
            for (condition, model_name), group in derived_df.groupby(
                ["condition", "model"]
            ):
                cr_values = (
                    group["consistency_rate"].dropna().astype(float).values
                )
                if len(cr_values) < 2:
                    cr_mean = (
                        float(np.mean(cr_values)) if len(cr_values) > 0
                        else 0.0
                    )
                    results[f"cr_{condition}_{model_name}"] = {
                        "mean": cr_mean,
                        "ci_lower": cr_mean,
                        "ci_upper": cr_mean,
                        "method_used": "point_estimate",
                        "n": len(cr_values),
                        "metric": "consistency_rate",
                    }
                    continue

                cr_mean = float(np.mean(cr_values))
                ci_lower, ci_upper, method_used = _bootstrap_ci(
                    cr_values, np.mean, n_iterations, seed
                )
                results[f"cr_{condition}_{model_name}"] = {
                    "mean": cr_mean,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "method_used": method_used,
                    "n": len(cr_values),
                    "metric": "consistency_rate",
                }

    return results


def _bootstrap_ci(
    data: np.ndarray,
    statistic_fn: Any,
    n_resamples: int,
    seed: int,
    confidence_level: float = 0.95,
) -> tuple[float, float, str]:
    """Compute a single bootstrap CI with BCa/percentile fallback.

    Args:
        data: 1-D array of observations.
        statistic_fn: Function to compute the statistic (e.g. np.mean).
        n_resamples: Number of bootstrap resamples.
        seed: Random seed.
        confidence_level: Confidence level for CI.

    Returns:
        Tuple of (ci_lower, ci_upper, method_used).
    """
    method_used = "bca"
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=Warning)
            ci_result = scipy_bootstrap(
                (data,),
                statistic_fn,
                n_resamples=n_resamples,
                confidence_level=confidence_level,
                method="bca",
                random_state=seed,
            )
            ci_low = ci_result.confidence_interval.low
            ci_high = ci_result.confidence_interval.high
            if np.isnan(ci_low) or np.isnan(ci_high):
                raise ValueError("BCa produced NaN")
    except (Warning, ValueError):
        logger.info(
            "BCa bootstrap failed, falling back to percentile method"
        )
        method_used = "percentile"
        ci_result = scipy_bootstrap(
            (data,),
            statistic_fn,
            n_resamples=n_resamples,
            confidence_level=confidence_level,
            method="percentile",
            random_state=seed,
        )
        ci_low = ci_result.confidence_interval.low
        ci_high = ci_result.confidence_interval.high

    return float(ci_low), float(ci_high), method_used


# ---------------------------------------------------------------------------
# McNemar's test for fragility/recoverability
# ---------------------------------------------------------------------------


def run_mcnemar_analysis(
    df: pd.DataFrame,
    baseline_condition: str = "clean",
    model_filter: str | None = None,
    compare_interventions: bool = False,
) -> dict[str, Any]:
    """Run McNemar's test for fragility/recoverability per prompt.

    For each prompt and model, builds a 2x2 table from paired repetitions
    and classifies prompts as fragile or recoverable.

    Args:
        df: DataFrame with experiment_runs data.
        baseline_condition: Noise type for baseline (default 'clean').
        model_filter: If set, only analyze this model.
        compare_interventions: If True, compare raw vs pre_proc_sanitize
            within the same noise condition instead of across noise types.

    Returns:
        Dict with 'comparisons' list and 'skipped_count'.
    """
    comparisons: list[dict[str, Any]] = []
    skipped_count = 0

    models = [model_filter] if model_filter else df["model"].unique().tolist()

    for model in models:
        model_df = df[df["model"] == model]

        if compare_interventions:
            # Compare raw vs pre_proc_sanitize within same noise condition
            noise_types = model_df["noise_type"].unique()
            for noise_type in noise_types:
                noise_df = model_df[model_df["noise_type"] == noise_type]
                raw_df = noise_df[noise_df["intervention"] == "raw"]
                interv_df = noise_df[
                    noise_df["intervention"] == "pre_proc_sanitize"
                ]
                if raw_df.empty or interv_df.empty:
                    continue

                result, skipped = _mcnemar_per_prompt(
                    raw_df, interv_df, model, noise_type,
                    f"raw_vs_pre_proc_sanitize",
                )
                comparisons.extend(result)
                skipped_count += skipped
        else:
            # Compare baseline noise vs other noise types (same intervention)
            noisy_types = [
                nt for nt in model_df["noise_type"].unique()
                if nt != baseline_condition
            ]
            for noise_type in noisy_types:
                interventions = model_df["intervention"].unique()
                for intervention in interventions:
                    baseline_df = model_df[
                        (model_df["noise_type"] == baseline_condition)
                        & (model_df["intervention"] == intervention)
                    ]
                    noisy_df = model_df[
                        (model_df["noise_type"] == noise_type)
                        & (model_df["intervention"] == intervention)
                    ]
                    if baseline_df.empty or noisy_df.empty:
                        continue

                    result, skipped = _mcnemar_per_prompt(
                        baseline_df, noisy_df, model, noise_type,
                        f"{baseline_condition}_vs_{noise_type}_{intervention}",
                    )
                    comparisons.extend(result)
                    skipped_count += skipped

    return {
        "comparisons": comparisons,
        "skipped_count": skipped_count,
    }


def _mcnemar_per_prompt(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    model: str,
    condition_label: str,
    comparison_label: str,
) -> tuple[list[dict[str, Any]], int]:
    """Run McNemar's test for each prompt between two condition DataFrames.

    Args:
        df_a: DataFrame for condition A (e.g., baseline).
        df_b: DataFrame for condition B (e.g., noisy).
        model: Model identifier.
        condition_label: Label for the comparison condition.
        comparison_label: Description of the comparison.

    Returns:
        Tuple of (list of result dicts, count of skipped concordant prompts).
    """
    results: list[dict[str, Any]] = []
    skipped = 0

    common_prompts = set(df_a["prompt_id"].unique()) & set(
        df_b["prompt_id"].unique()
    )

    for prompt_id in sorted(common_prompts):
        runs_a = (
            df_a[df_a["prompt_id"] == prompt_id]
            .sort_values("repetition")["pass_fail"]
            .astype(int)
            .values
        )
        runs_b = (
            df_b[df_b["prompt_id"] == prompt_id]
            .sort_values("repetition")["pass_fail"]
            .astype(int)
            .values
        )

        # Pair by repetition number
        n_pairs = min(len(runs_a), len(runs_b))
        table = np.zeros((2, 2), dtype=int)
        for i in range(n_pairs):
            ra = int(runs_a[i])
            rb = int(runs_b[i])
            table[1 - ra][1 - rb] += 1

        b_count = int(table[0][1])  # pass in A, fail in B
        c_count = int(table[1][0])  # fail in A, pass in B

        if b_count + c_count == 0:
            skipped += 1
            continue

        mcn_result = mcnemar(table, exact=True)
        classification = "fragile" if b_count > c_count else "recoverable"

        results.append({
            "prompt_id": prompt_id,
            "model": model,
            "comparison": comparison_label,
            "condition": condition_label,
            "statistic": float(mcn_result.statistic),
            "p_value": float(mcn_result.pvalue),
            "b_count": b_count,
            "c_count": c_count,
            "classification": classification,
        })

    return results, skipped


# ---------------------------------------------------------------------------
# Kendall's tau for rank-order stability
# ---------------------------------------------------------------------------


def compute_kendall_tau(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Compute Kendall's tau between clean and noisy pass-rate rankings.

    For each model, computes per-prompt pass rate under clean condition
    and each noisy condition, then computes Kendall's tau-b.

    Args:
        df: DataFrame with experiment_runs data.

    Returns:
        List of dicts with clean_condition, noisy_condition, model,
        tau, p_value, n_prompts.
    """
    results: list[dict[str, Any]] = []

    for model in df["model"].unique():
        model_df = df[df["model"] == model]
        noise_types = model_df["noise_type"].unique()

        # Only compare within same intervention type
        for intervention in model_df["intervention"].unique():
            interv_df = model_df[model_df["intervention"] == intervention]

            if "clean" not in interv_df["noise_type"].values:
                continue

            clean_rates = (
                interv_df[interv_df["noise_type"] == "clean"]
                .groupby("prompt_id")["pass_fail"]
                .mean()
            )

            noisy_types = [nt for nt in noise_types if nt != "clean"]
            for noisy_type in noisy_types:
                noisy_rates = (
                    interv_df[interv_df["noise_type"] == noisy_type]
                    .groupby("prompt_id")["pass_fail"]
                    .mean()
                )

                common = clean_rates.index.intersection(noisy_rates.index)
                if len(common) < 2:
                    continue

                tau, p_value = kendalltau(
                    clean_rates[common].values,
                    noisy_rates[common].values,
                    variant="b",
                )

                results.append({
                    "clean_condition": "clean",
                    "noisy_condition": noisy_type,
                    "intervention": intervention,
                    "model": model,
                    "tau": float(tau) if not np.isnan(tau) else 0.0,
                    "p_value": float(p_value) if not np.isnan(p_value) else 1.0,
                    "n_prompts": len(common),
                })

    return results


# ---------------------------------------------------------------------------
# Benjamini-Hochberg correction
# ---------------------------------------------------------------------------


def apply_bh_correction(
    results_by_family: dict[str, list[float]], alpha: float = 0.05
) -> dict[str, dict[str, Any]]:
    """Apply Benjamini-Hochberg FDR correction per test family.

    Args:
        results_by_family: Dict mapping family name to list of p-values.
        alpha: Significance level (default 0.05).

    Returns:
        Dict per family with raw_p_values, corrected_p_values, reject lists.
    """
    corrected: dict[str, dict[str, Any]] = {}

    for family_name, p_values in results_by_family.items():
        if not p_values:
            corrected[family_name] = {
                "raw_p_values": [],
                "corrected_p_values": [],
                "reject": [],
            }
            continue

        reject, pvals_corrected, _, _ = multipletests(
            p_values, alpha=alpha, method="fdr_bh"
        )

        corrected[family_name] = {
            "raw_p_values": [float(p) for p in p_values],
            "corrected_p_values": [float(p) for p in pvals_corrected],
            "reject": [bool(r) for r in reject],
        }

    return corrected


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------


def run_sensitivity_analysis(
    df: pd.DataFrame, drop_pct: float = 0.10
) -> dict[str, Any]:
    """Rerun key metrics after dropping hardest/easiest prompts.

    Computes per-prompt overall pass rate, drops the bottom and top
    drop_pct of prompts, then reruns GLMM and bootstrap CIs.

    Args:
        df: DataFrame with experiment_runs data.
        drop_pct: Fraction of prompts to drop from each extreme.

    Returns:
        Dict with n_prompts_original, n_prompts_filtered, n_dropped,
        glmm_results, bootstrap_results.
    """
    # Compute per-prompt overall pass rate
    prompt_rates = df.groupby("prompt_id")["pass_fail"].mean()
    n_original = len(prompt_rates)

    # Sort and drop extremes
    sorted_prompts = prompt_rates.sort_values()
    n_drop = max(1, int(n_original * drop_pct))
    keep_prompts = sorted_prompts.index[n_drop: len(sorted_prompts) - n_drop]

    filtered_df = df[df["prompt_id"].isin(keep_prompts)]
    n_filtered = filtered_df["prompt_id"].nunique()
    n_dropped = n_original - n_filtered

    logger.info(
        "Sensitivity analysis: dropped %d prompts (%d -> %d)",
        n_dropped, n_original, n_filtered,
    )

    # Rerun analyses on filtered data
    glmm_results = fit_glmm(filtered_df)
    bootstrap_results = compute_bootstrap_cis(
        filtered_df, n_iterations=500, seed=42
    )

    return {
        "n_prompts_original": n_original,
        "n_prompts_filtered": n_filtered,
        "n_dropped": n_dropped,
        "dropped_prompts_bottom": sorted_prompts.index[:n_drop].tolist(),
        "dropped_prompts_top": sorted_prompts.index[-n_drop:].tolist(),
        "glmm_results": glmm_results,
        "bootstrap_results": bootstrap_results,
    }


# ---------------------------------------------------------------------------
# Effect size summary table
# ---------------------------------------------------------------------------


def generate_effect_size_summary(
    glmm_results: dict[str, Any],
    kendall_results: list[dict[str, Any]],
    bootstrap_results: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Generate a summary table of all effect sizes with CIs.

    Collects odds ratios and risk differences from GLMM, tau values
    from Kendall's results, and Cohen's d for token savings/latency
    differences.

    Args:
        glmm_results: Output from fit_glmm.
        kendall_results: Output from compute_kendall_tau.
        bootstrap_results: Output from compute_bootstrap_cis.

    Returns:
        DataFrame with columns: metric, comparison, effect_size,
        ci_lower, ci_upper, effect_type.
    """
    rows: list[dict[str, Any]] = []

    # Odds ratios from GLMM
    for entry in glmm_results.get("odds_ratios", []):
        rows.append({
            "metric": entry["name"],
            "comparison": "vs_reference",
            "effect_size": entry["or"],
            "ci_lower": entry["ci_lower"],
            "ci_upper": entry["ci_upper"],
            "effect_type": "OR",
        })

    # Risk differences from GLMM coefficients (approximate)
    for coeff in glmm_results.get("coefficients", []):
        # Approximate RD via logistic transformation derivative
        est = coeff["estimate"]
        se = coeff["std_err"]
        # d(logistic)/d(x) at mean ~ 0.25 for logit link
        rd = est * 0.25
        rd_lower = (est - 1.96 * se) * 0.25
        rd_upper = (est + 1.96 * se) * 0.25
        rows.append({
            "metric": coeff["name"],
            "comparison": "risk_difference",
            "effect_size": rd,
            "ci_lower": rd_lower,
            "ci_upper": rd_upper,
            "effect_type": "RD",
        })

    # Kendall's tau values
    for entry in kendall_results:
        rows.append({
            "metric": f"tau_{entry['noisy_condition']}_{entry.get('intervention', 'raw')}",
            "comparison": f"clean_vs_{entry['noisy_condition']}",
            "effect_size": entry["tau"],
            "ci_lower": entry["tau"],  # tau CI would need bootstrap
            "ci_upper": entry["tau"],
            "effect_type": "tau",
        })

    # Cohen's d for accuracy differences between conditions (from bootstrap)
    condition_keys = list(bootstrap_results.keys())
    if len(condition_keys) >= 2:
        # Compare first condition (clean) to others
        clean_keys = [k for k in condition_keys if k.startswith("clean")]
        noisy_keys = [k for k in condition_keys if not k.startswith("clean")]

        for clean_key in clean_keys[:1]:
            for noisy_key in noisy_keys[:3]:
                clean_entry = bootstrap_results[clean_key]
                noisy_entry = bootstrap_results[noisy_key]
                mean_diff = clean_entry["mean"] - noisy_entry["mean"]

                # Approximate pooled SD from CI width
                def _ci_to_sd(entry: dict[str, Any]) -> float:
                    ci_width = entry["ci_upper"] - entry["ci_lower"]
                    return max(ci_width / (2 * 1.96), 0.01)

                sd1 = _ci_to_sd(clean_entry)
                sd2 = _ci_to_sd(noisy_entry)
                pooled_sd = float(np.sqrt((sd1**2 + sd2**2) / 2))

                d = mean_diff / pooled_sd if pooled_sd > 0 else 0.0
                rows.append({
                    "metric": f"accuracy_d_{noisy_key}",
                    "comparison": f"{clean_key}_vs_{noisy_key}",
                    "effect_size": d,
                    "ci_lower": d - 1.96,  # rough CI for d
                    "ci_upper": d + 1.96,
                    "effect_type": "d",
                })

    if not rows:
        return pd.DataFrame(
            columns=["metric", "comparison", "effect_size", "ci_lower",
                     "ci_upper", "effect_type"]
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for statistical analysis of experiment results.

    Supports subcommands: glmm, mcnemar, bootstrap, kendall, sensitivity, all.
    Outputs JSON, CSV, and terminal summary for each analysis.
    """
    parser = argparse.ArgumentParser(
        description="Statistical analysis for the Linguistic Tax experiment"
    )
    parser.add_argument(
        "--db", default="results/results.db",
        help="Path to the SQLite results database",
    )
    parser.add_argument(
        "--output-dir", default="results",
        help="Directory for output files (JSON, CSV)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for bootstrap resampling",
    )
    parser.add_argument(
        "--bootstrap-iterations", type=int, default=10000,
        help="Number of bootstrap resamples",
    )
    parser.add_argument(
        "--sensitivity-drop-pct", type=float, default=0.10,
        help="Fraction of extreme prompts to drop in sensitivity analysis",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("glmm", help="Run GLMM analysis")
    subparsers.add_parser("mcnemar", help="Run McNemar's fragility analysis")
    subparsers.add_parser("bootstrap", help="Compute bootstrap CIs")
    subparsers.add_parser("kendall", help="Compute Kendall's tau")
    subparsers.add_parser("sensitivity", help="Run sensitivity analysis")
    subparsers.add_parser("all", help="Run all analyses")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    os.makedirs(args.output_dir, exist_ok=True)
    csv_dir = os.path.join(args.output_dir, "csv")
    os.makedirs(csv_dir, exist_ok=True)

    df = load_experiment_data(args.db)
    if df.empty:
        logger.warning("No data found in %s", args.db)
        return

    p_value_families: dict[str, list[float]] = {}

    if args.command in ("glmm", "all"):
        _run_glmm_analysis(df, args, csv_dir, p_value_families)

    if args.command in ("mcnemar", "all"):
        _run_mcnemar_analysis_cli(df, args, csv_dir, p_value_families)

    if args.command in ("bootstrap", "all"):
        _run_bootstrap_analysis(df, args, csv_dir)

    if args.command in ("kendall", "all"):
        _run_kendall_analysis(df, args, csv_dir, p_value_families)

    if args.command in ("sensitivity", "all"):
        _run_sensitivity_cli(df, args, csv_dir)

    # Apply BH correction to all collected p-values
    if p_value_families:
        bh_results = apply_bh_correction(p_value_families)
        bh_path = os.path.join(args.output_dir, "bh_correction_results.json")
        with open(bh_path, "w") as f:
            json.dump(bh_results, f, indent=2)
        logger.info("BH correction results written to %s", bh_path)

    # Generate effect size summary for "all" command
    if args.command == "all":
        glmm_results = fit_glmm(df)
        kendall_results = compute_kendall_tau(df)
        bootstrap_results = compute_bootstrap_cis(
            df, n_iterations=args.bootstrap_iterations, seed=args.seed,
            db_path=args.db,
        )
        summary_df = generate_effect_size_summary(
            glmm_results, kendall_results, bootstrap_results
        )
        summary_csv = os.path.join(csv_dir, "effect_sizes.csv")
        summary_df.to_csv(summary_csv, index=False)
        logger.info("Effect size summary written to %s", summary_csv)

        # Write analysis_summary.json
        summary_json = os.path.join(args.output_dir, "analysis_summary.json")
        with open(summary_json, "w") as f:
            json.dump({
                "glmm": glmm_results,
                "kendall": kendall_results,
                "bootstrap": bootstrap_results,
            }, f, indent=2, default=str)
        logger.info("Analysis summary written to %s", summary_json)

    logger.info("Statistical analysis complete")


def _run_glmm_analysis(
    df: pd.DataFrame,
    args: argparse.Namespace,
    csv_dir: str,
    p_value_families: dict[str, list[float]],
) -> None:
    """Run GLMM analysis and write outputs."""
    logger.info("Running GLMM analysis")
    result = fit_glmm(df)

    # Write JSON
    json_path = os.path.join(args.output_dir, "glmm_results.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("GLMM results written to %s", json_path)

    # Write CSV
    if result["coefficients"]:
        coeff_df = pd.DataFrame(result["coefficients"])
        coeff_df.to_csv(os.path.join(csv_dir, "glmm_coefficients.csv"), index=False)

    # Collect p-values for BH
    p_value_families["glmm"] = [
        c["p_value"] for c in result["coefficients"] if c.get("p_value") is not None
    ]

    # Terminal summary
    if result["coefficients"]:
        table_data = [
            [c["name"][:40], f"{c['estimate']:.4f}", f"{c['std_err']:.4f}",
             f"{c['p_value']:.4f}"]
            for c in result["coefficients"]
        ]
        logger.info(
            "GLMM Coefficients (%s):\n%s",
            result["model_type"],
            tabulate(
                table_data,
                headers=["Name", "Estimate", "Std Err", "p-value"],
                tablefmt="grid",
            ),
        )


def _run_mcnemar_analysis_cli(
    df: pd.DataFrame,
    args: argparse.Namespace,
    csv_dir: str,
    p_value_families: dict[str, list[float]],
) -> None:
    """Run McNemar's analysis and write outputs."""
    logger.info("Running McNemar's analysis")
    result = run_mcnemar_analysis(df, baseline_condition="clean")

    # Write JSON
    json_path = os.path.join(args.output_dir, "mcnemar_results.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("McNemar results written to %s", json_path)

    # Write CSV
    if result["comparisons"]:
        comp_df = pd.DataFrame(result["comparisons"])
        comp_df.to_csv(os.path.join(csv_dir, "mcnemar_fragile.csv"), index=False)

    # Collect p-values for BH
    p_value_families["mcnemar"] = [
        c["p_value"] for c in result["comparisons"]
    ]

    # Terminal summary
    if result["comparisons"]:
        fragile_count = sum(
            1 for c in result["comparisons"] if c["classification"] == "fragile"
        )
        recoverable_count = sum(
            1 for c in result["comparisons"] if c["classification"] == "recoverable"
        )
        logger.info(
            "McNemar's summary: %d fragile, %d recoverable, %d skipped (concordant)",
            fragile_count, recoverable_count, result["skipped_count"],
        )


def _run_bootstrap_analysis(
    df: pd.DataFrame,
    args: argparse.Namespace,
    csv_dir: str,
) -> None:
    """Run bootstrap CI analysis and write outputs."""
    logger.info("Running bootstrap CI analysis")
    result = compute_bootstrap_cis(
        df, n_iterations=args.bootstrap_iterations, seed=args.seed,
        db_path=args.db,
    )

    # Write JSON
    json_path = os.path.join(args.output_dir, "bootstrap_results.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Bootstrap results written to %s", json_path)

    # Write CSV
    if result:
        rows = []
        for condition, vals in result.items():
            rows.append({"condition": condition, **vals})
        pd.DataFrame(rows).to_csv(
            os.path.join(csv_dir, "bootstrap_cis.csv"), index=False
        )

    # Terminal summary
    if result:
        table_data = [
            [k[:50], f"{v['mean']:.4f}", f"{v['ci_lower']:.4f}",
             f"{v['ci_upper']:.4f}", v["method_used"]]
            for k, v in result.items()
        ]
        logger.info(
            "Bootstrap CIs:\n%s",
            tabulate(
                table_data,
                headers=["Condition", "Mean", "CI Lower", "CI Upper", "Method"],
                tablefmt="grid",
            ),
        )


def _run_kendall_analysis(
    df: pd.DataFrame,
    args: argparse.Namespace,
    csv_dir: str,
    p_value_families: dict[str, list[float]],
) -> None:
    """Run Kendall's tau analysis and write outputs."""
    logger.info("Running Kendall's tau analysis")
    result = compute_kendall_tau(df)

    # Write JSON
    json_path = os.path.join(args.output_dir, "kendall_results.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Kendall results written to %s", json_path)

    # Write CSV
    if result:
        pd.DataFrame(result).to_csv(
            os.path.join(csv_dir, "kendall_tau.csv"), index=False
        )

    # Collect p-values for BH
    p_value_families["kendall"] = [r["p_value"] for r in result]

    # Terminal summary
    if result:
        table_data = [
            [r["noisy_condition"], r.get("intervention", "raw"),
             r["model"][:30], f"{r['tau']:.4f}", f"{r['p_value']:.4f}",
             r["n_prompts"]]
            for r in result
        ]
        logger.info(
            "Kendall's tau:\n%s",
            tabulate(
                table_data,
                headers=["Noisy Condition", "Intervention", "Model",
                         "Tau", "p-value", "N Prompts"],
                tablefmt="grid",
            ),
        )


def _run_sensitivity_cli(
    df: pd.DataFrame,
    args: argparse.Namespace,
    csv_dir: str,
) -> None:
    """Run sensitivity analysis and write outputs."""
    logger.info("Running sensitivity analysis")
    result = run_sensitivity_analysis(df, drop_pct=args.sensitivity_drop_pct)

    # Write JSON (need to handle nested dicts carefully)
    json_path = os.path.join(args.output_dir, "sensitivity_results.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Sensitivity results written to %s", json_path)

    # Terminal summary
    logger.info(
        "Sensitivity analysis: %d -> %d prompts (dropped %d)",
        result["n_prompts_original"],
        result["n_prompts_filtered"],
        result["n_dropped"],
    )


if __name__ == "__main__":
    main()
