"""Pilot validation module for the Linguistic Tax research toolkit.

Provides stratified prompt selection, pilot execution, data completeness
auditing, noise injection sanity checking, grading spot-check, cost projection
with bootstrap CIs, BERTScore fidelity, latency profiling, and structured
PASS/FAIL verdict for the 20-prompt pilot run.
"""

import argparse
import json
import logging
import os
import random
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.stats import bootstrap as scipy_bootstrap

from src.config import ExperimentConfig, derive_seed
from src.model_registry import registry
from src.config_manager import find_config_path, CONFIG_FILENAME
from src.db import query_runs
from src.execution_summary import (
    estimate_cost,
    estimate_runtime,
    format_summary,
    confirm_execution,
    save_execution_plan,
)
from src.noise_generator import inject_type_a_noise

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pilot prompt selection
# ---------------------------------------------------------------------------

def select_pilot_prompts(
    prompts_path: str = "data/prompts.json",
    seed: int = 42,
    n_humaneval: int = 7,
    n_mbpp: int = 7,
    n_gsm8k: int = 6,
    save: bool = True,
    output_path: str = "data/pilot_prompts.json",
) -> list[str]:
    """Select a stratified sample of prompts for the pilot run.

    Groups prompts by benchmark_source and samples a fixed number from
    each group using a seeded RNG for reproducibility.

    Args:
        prompts_path: Path to the full prompts.json file.
        seed: Random seed for deterministic selection.
        n_humaneval: Number of HumanEval prompts to select.
        n_mbpp: Number of MBPP prompts to select.
        n_gsm8k: Number of GSM8K prompts to select.
        save: Whether to write selected IDs to output_path.
        output_path: Path for the output JSON file.

    Returns:
        List of selected prompt IDs.
    """
    with open(prompts_path) as f:
        prompts = json.load(f)

    # Group by benchmark
    groups: dict[str, list[str]] = {
        "humaneval": [],
        "mbpp": [],
        "gsm8k": [],
    }
    for p in prompts:
        source = p["benchmark_source"]
        if source in groups:
            groups[source].append(p["problem_id"])

    rng = random.Random(seed)

    selected: list[str] = []
    for benchmark, count in [
        ("humaneval", n_humaneval),
        ("mbpp", n_mbpp),
        ("gsm8k", n_gsm8k),
    ]:
        pool = sorted(groups[benchmark])  # Sort for determinism before sampling
        sampled = rng.sample(pool, count)
        selected.extend(sampled)
        logger.info("Selected %d/%d %s prompts", count, len(pool), benchmark)

    logger.info("Total pilot prompts selected: %d", len(selected))

    if save:
        with open(output_path, "w") as f:
            json.dump(selected, f, indent=2)
        logger.info("Saved pilot prompt IDs to %s", output_path)

    return selected


# ---------------------------------------------------------------------------
# Matrix filtering
# ---------------------------------------------------------------------------

def filter_pilot_matrix(
    matrix_path: str = "data/experiment_matrix.json",
    pilot_prompt_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter experiment matrix to pilot prompt IDs only.

    Args:
        matrix_path: Path to the full experiment matrix JSON.
        pilot_prompt_ids: List of prompt IDs to include. If None, returns all.

    Returns:
        Filtered list of matrix items.
    """
    with open(matrix_path) as f:
        matrix = json.load(f)

    if pilot_prompt_ids is None:
        return matrix

    id_set = set(pilot_prompt_ids)
    filtered = [item for item in matrix if item["prompt_id"] in id_set]
    logger.info("Filtered matrix: %d items for %d pilot prompts", len(filtered), len(pilot_prompt_ids))
    return filtered


# ---------------------------------------------------------------------------
# Pilot execution
# ---------------------------------------------------------------------------

def run_pilot(
    budget: float = 200.0,
    db_path: str | None = None,
    select_only: bool = False,
    analyze_only: bool = False,
    yes: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Orchestrate the pilot workflow: selection, execution, analysis.

    Args:
        budget: Maximum budget in USD (not enforced, for reference).
        db_path: Override path to results database.
        select_only: If True, only select prompts and return.
        analyze_only: If True, skip selection and execution, only analyze.
        yes: If True, auto-accept confirmation without prompting.
        dry_run: If True, show summary and exit without executing.

    Returns:
        Summary dict with pilot_prompt_ids, total_items, and status.
    """
    import argparse

    config = ExperimentConfig()
    if db_path:
        config = ExperimentConfig(results_db_path=db_path)

    # Select pilot prompts
    if not analyze_only:
        pilot_ids = select_pilot_prompts()
    else:
        # Load from saved file
        with open("data/pilot_prompts.json") as f:
            pilot_ids = json.load(f)

    if select_only:
        return {
            "pilot_prompt_ids": pilot_ids,
            "total_items": 0,
            "status": "selected",
        }

    # Filter matrix
    filtered = filter_pilot_matrix(
        matrix_path=config.matrix_path,
        pilot_prompt_ids=pilot_ids,
    )

    # Confirmation gate for pilot
    cost_estimate = estimate_cost(filtered)
    runtime_seconds = estimate_runtime(filtered)
    summary = format_summary(
        filtered, 0, len(filtered), cost_estimate, runtime_seconds
    )

    if dry_run:
        print(summary)
        return {
            "pilot_prompt_ids": pilot_ids,
            "total_items": len(filtered),
            "status": "dry_run",
        }

    decision = confirm_execution(
        summary,
        yes=yes,
        budget=budget,
        estimated_cost=cost_estimate["total_cost"],
    )

    if decision == "no":
        print("Pilot aborted.")
        return {
            "pilot_prompt_ids": pilot_ids,
            "total_items": len(filtered),
            "status": "aborted",
        }
    elif decision == "modify":
        print("Re-run with different parameters to modify the pilot.")
        return {
            "pilot_prompt_ids": pilot_ids,
            "total_items": len(filtered),
            "status": "modify",
        }

    save_execution_plan(
        filtered, cost_estimate, runtime_seconds,
        filters={"mode": "pilot"},
        output_path="results/pilot_plan.json",
    )

    if not analyze_only:
        # Write filtered matrix to temp file and run engine
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir="data"
        ) as tmp:
            json.dump(filtered, tmp)
            tmp_matrix_path = tmp.name

        try:
            from src.run_experiment import run_engine

            pilot_config = ExperimentConfig(
                matrix_path=tmp_matrix_path,
                results_db_path=db_path or config.results_db_path,
            )

            args = argparse.Namespace(
                model="all",
                limit=None,
                retry_failed=False,
                dry_run=False,
                db=db_path,
            )
            run_engine(args, config=pilot_config)
        finally:
            os.unlink(tmp_matrix_path)

    return {
        "pilot_prompt_ids": pilot_ids,
        "total_items": len(filtered),
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# Data completeness audit
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = [
    "prompt_text", "prompt_tokens", "raw_output", "completion_tokens",
    "pass_fail", "ttft_ms", "ttlt_ms", "total_cost_usd", "model", "timestamp",
]

_VALID_MODELS = set(registry.target_models())


def audit_data_completeness(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
) -> dict[str, Any]:
    """Audit completed pilot runs for data completeness.

    Checks that required fields are not NULL, token counts are positive,
    models are valid, and timestamps are well-formed.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs to check.

    Returns:
        Dict with total_checked, issues_found, and issues list.
    """
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in pilot_prompt_ids)
    query = (
        f"SELECT * FROM experiment_runs "
        f"WHERE prompt_id IN ({placeholders}) AND status = 'completed'"
    )
    rows = conn.execute(query, pilot_prompt_ids).fetchall()

    issues: list[dict[str, Any]] = []

    for row in rows:
        row_dict = dict(row)
        run_id = row_dict["run_id"]

        # Check required fields not NULL
        for field in _REQUIRED_FIELDS:
            if row_dict.get(field) is None:
                issues.append({
                    "run_id": run_id,
                    "field": field,
                    "issue": f"{field} is NULL",
                })

        # Check token counts positive
        for token_field in ("prompt_tokens", "completion_tokens"):
            val = row_dict.get(token_field)
            if val is not None and val <= 0:
                issues.append({
                    "run_id": run_id,
                    "field": token_field,
                    "issue": f"{token_field} is {val} (must be > 0)",
                })

        # Check valid model
        model = row_dict.get("model")
        if model is not None and model not in _VALID_MODELS:
            issues.append({
                "run_id": run_id,
                "field": "model",
                "issue": f"Unknown model: {model}",
            })

        # Check timestamp format
        ts = row_dict.get("timestamp")
        if ts is not None:
            try:
                from datetime import datetime
                datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                issues.append({
                    "run_id": run_id,
                    "field": "timestamp",
                    "issue": f"Invalid ISO timestamp: {ts}",
                })

    result = {
        "total_checked": len(rows),
        "issues_found": len(issues),
        "issues": issues,
    }

    logger.info(
        "Data audit: %d rows checked, %d issues found",
        result["total_checked"], result["issues_found"],
    )
    return result


# ---------------------------------------------------------------------------
# Noise rate verification
# ---------------------------------------------------------------------------

def verify_noise_rates(
    prompts_by_id: dict[str, dict[str, Any]],
    pilot_prompt_ids: list[str],
    base_seed: int = 42,
    tolerance: float = 0.5,
) -> dict[str, Any]:
    """Verify that noise injection rates match expected error rates.

    For each pilot prompt and each Type A rate (5%, 10%, 20%), injects
    noise and measures actual character mutation rate. Flags entries
    where relative deviation exceeds tolerance.

    Args:
        prompts_by_id: Mapping of prompt_id to prompt record dict.
        pilot_prompt_ids: List of prompt IDs to check.
        base_seed: Base seed for deterministic seed derivation.
        tolerance: Maximum allowed relative deviation (0.5 = 50%).

    Returns:
        Dict with total_checks, flagged_count, and flagged list.
    """
    expected_rates = [0.05, 0.10, 0.20]
    rate_labels = ["5", "10", "20"]

    flagged: list[dict[str, Any]] = []
    total_checks = 0

    for pid in pilot_prompt_ids:
        prompt = prompts_by_id.get(pid)
        if prompt is None:
            continue

        clean_text = prompt["prompt_text"]
        answer_type = prompt.get("answer_type", "code")

        for rate, label in zip(expected_rates, rate_labels):
            seed = derive_seed(base_seed, pid, "type_a", label)
            noisy = inject_type_a_noise(clean_text, error_rate=rate, seed=seed, answer_type=answer_type)

            # Measure actual mutation rate
            if len(clean_text) == 0:
                continue

            diffs = sum(1 for a, b in zip(clean_text, noisy) if a != b)
            # Also account for length differences
            diffs += abs(len(clean_text) - len(noisy))
            actual_rate = diffs / len(clean_text)

            # Check relative deviation
            if rate > 0:
                relative_dev = abs(actual_rate - rate) / rate
            else:
                relative_dev = actual_rate

            is_flagged = relative_dev > tolerance
            total_checks += 1

            if is_flagged:
                flagged.append({
                    "prompt_id": pid,
                    "expected_rate": rate,
                    "actual_rate": round(actual_rate, 4),
                    "relative_deviation": round(relative_dev, 4),
                    "flagged": True,
                })

    result = {
        "total_checks": total_checks,
        "flagged_count": len(flagged),
        "flagged": flagged,
    }

    logger.info(
        "Noise rate verification: %d checks, %d flagged",
        result["total_checks"], result["flagged_count"],
    )
    return result


# ---------------------------------------------------------------------------
# Grading spot-check
# ---------------------------------------------------------------------------

def run_spot_check(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
    prompts_by_id: dict[str, dict[str, Any]],
    seed: int = 42,
    code_sample_rate: float = 0.2,
    output_path: str = "results/pilot_spot_check.json",
) -> dict[str, Any]:
    """Generate a grading spot-check report for pilot results.

    Selects ALL GSM8K results and approximately 20% of code (HumanEval/MBPP)
    results for side-by-side comparison of auto-grade vs. expected answer.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.
        prompts_by_id: Mapping of prompt_id to prompt record dict.
        seed: Random seed for code row sampling.
        code_sample_rate: Fraction of code rows to sample (default 0.2).
        output_path: Path for the JSON report file.

    Returns:
        Report dict with sampled results for spot-checking.
    """
    all_runs = query_runs(conn, status="completed")
    id_set = set(pilot_prompt_ids)
    pilot_runs = [r for r in all_runs if r["prompt_id"] in id_set]

    gsm8k_rows = [r for r in pilot_runs if r["benchmark"] == "gsm8k"]
    code_rows = [r for r in pilot_runs if r["benchmark"] in ("humaneval", "mbpp")]

    # ALL GSM8K rows selected
    gsm8k_selected = gsm8k_rows

    # ~20% of code rows, at least 1
    rng = random.Random(seed)
    n_code_sample = max(1, int(len(code_rows) * code_sample_rate))
    if n_code_sample > len(code_rows):
        n_code_sample = len(code_rows)
    code_selected = rng.sample(code_rows, n_code_sample) if code_rows else []

    def _build_sample(row: dict[str, Any]) -> dict[str, Any]:
        pid = row["prompt_id"]
        prompt_info = prompts_by_id.get(pid, {})
        expected = prompt_info.get(
            "canonical_answer",
            prompt_info.get("test_code", "N/A"),
        )
        return {
            "run_id": row["run_id"],
            "prompt_id": pid,
            "benchmark": row["benchmark"],
            "noise_type": row["noise_type"],
            "noise_level": row.get("noise_level"),
            "intervention": row["intervention"],
            "model": row["model"],
            "raw_output": row["raw_output"],
            "pass_fail": row["pass_fail"],
            "expected_answer": expected,
        }

    all_samples = [_build_sample(r) for r in gsm8k_selected] + [
        _build_sample(r) for r in code_selected
    ]

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_prompt_ids": pilot_prompt_ids,
        "total_sampled": len(gsm8k_selected) + len(code_selected),
        "gsm8k_count": len(gsm8k_selected),
        "code_count": len(code_selected),
        "code_sample_rate": code_sample_rate,
        "samples": all_samples,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(
        "Spot-check report: %d GSM8K + %d code samples written to %s",
        report["gsm8k_count"], report["code_count"], output_path,
    )
    return report


# ---------------------------------------------------------------------------
# Cost projection with bootstrap CIs
# ---------------------------------------------------------------------------

def compute_cost_projection(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
    n_full_prompts: int = 200,
    n_bootstrap: int = 10_000,
    confidence_level: float = 0.95,
    output_path: str = "results/pilot_cost_projection.json",
) -> dict[str, Any]:
    """Project full-run cost from pilot data with bootstrap confidence intervals.

    Aggregates cost per pilot prompt, then scales to the full prompt count
    using bootstrap resampling for confidence intervals.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.
        n_full_prompts: Number of prompts in the full experiment.
        n_bootstrap: Number of bootstrap resamples.
        confidence_level: Confidence level for the CI (e.g. 0.95).
        output_path: Path for the JSON report file.

    Returns:
        Dict with pilot cost, projected cost, CI bounds, and per-condition breakdown.
    """
    all_runs = query_runs(conn, status="completed")
    id_set = set(pilot_prompt_ids)
    pilot_runs = [r for r in all_runs if r["prompt_id"] in id_set]

    # Aggregate cost per prompt
    cost_by_prompt: dict[str, float] = {}
    for r in pilot_runs:
        pid = r["prompt_id"]
        cost_by_prompt[pid] = cost_by_prompt.get(pid, 0.0) + (r.get("total_cost_usd") or 0.0)

    per_prompt_costs = np.array([cost_by_prompt.get(pid, 0.0) for pid in pilot_prompt_ids])
    pilot_total = float(per_prompt_costs.sum())
    scale_factor = n_full_prompts / len(pilot_prompt_ids)
    projected_total = pilot_total * scale_factor

    # Bootstrap CI -- try BCa first, fall back to percentile if degenerate
    import warnings
    if len(per_prompt_costs) < 2:
        # Cannot bootstrap with fewer than 2 observations
        logger.info("Only %d prompt(s) -- skipping bootstrap, using point estimate for CI", len(per_prompt_costs))
        ci_low = projected_total
        ci_high = projected_total
    else:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("error", category=Warning)
                ci_result = scipy_bootstrap(
                    (per_prompt_costs,),
                    np.sum,
                    n_resamples=n_bootstrap,
                    confidence_level=confidence_level,
                    method="bca",
                )
                ci_low_raw = ci_result.confidence_interval.low
                ci_high_raw = ci_result.confidence_interval.high
                if np.isnan(ci_low_raw) or np.isnan(ci_high_raw):
                    raise ValueError("BCa produced NaN")
        except (Warning, ValueError):
            logger.info("BCa bootstrap failed (likely degenerate data), falling back to percentile method")
            ci_result = scipy_bootstrap(
                (per_prompt_costs,),
                np.sum,
                n_resamples=n_bootstrap,
                confidence_level=confidence_level,
                method="percentile",
            )
            ci_low_raw = ci_result.confidence_interval.low
            ci_high_raw = ci_result.confidence_interval.high

        ci_low = float(ci_low_raw * scale_factor)
        ci_high = float(ci_high_raw * scale_factor)

    # Per-condition breakdown
    condition_costs: dict[str, float] = {}
    for r in pilot_runs:
        key = f"{r['model']}|{r['intervention']}|{r['noise_type']}"
        condition_costs[key] = condition_costs.get(key, 0.0) + (r.get("total_cost_usd") or 0.0)

    breakdown = [
        {
            "condition": k,
            "pilot_cost": round(v, 6),
            "projected_cost": round(v * scale_factor, 4),
        }
        for k, v in sorted(condition_costs.items())
    ]

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_prompt_count": len(pilot_prompt_ids),
        "full_prompt_count": n_full_prompts,
        "pilot_total_cost": pilot_total,
        "projected_full_cost": projected_total,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "confidence_level": confidence_level,
        "n_bootstrap": n_bootstrap,
        "per_condition_breakdown": breakdown,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(
        "Cost projection: pilot $%.4f -> projected $%.2f [CI: $%.2f - $%.2f]",
        pilot_total, projected_total, ci_low, ci_high,
    )
    for item in breakdown:
        logger.info("  %s: pilot $%.4f -> projected $%.4f", item["condition"], item["pilot_cost"], item["projected_cost"])

    return result


# ---------------------------------------------------------------------------
# Budget gate
# ---------------------------------------------------------------------------

def check_budget_gate(
    projected_cost: float,
    budget_threshold: float = 200.0,
) -> dict[str, Any]:
    """Check whether projected cost exceeds the budget threshold.

    Args:
        projected_cost: Projected cost in USD for the full run.
        budget_threshold: Maximum allowed cost in USD.

    Returns:
        Dict with budget_threshold, projected_cost, and exceeds_budget flag.
    """
    exceeds = projected_cost > budget_threshold
    result = {
        "budget_threshold": budget_threshold,
        "projected_cost": projected_cost,
        "exceeds_budget": exceeds,
    }
    if exceeds:
        logger.warning(
            "Budget gate EXCEEDED: projected $%.2f > threshold $%.2f",
            projected_cost, budget_threshold,
        )
    else:
        logger.info(
            "Budget gate OK: projected $%.2f <= threshold $%.2f",
            projected_cost, budget_threshold,
        )
    return result


# ---------------------------------------------------------------------------
# BERTScore pre-processor fidelity
# ---------------------------------------------------------------------------

# Lazy import wrapper so tests can mock it
try:
    from bert_score import score as bert_score_fn
except ImportError:
    bert_score_fn = None  # type: ignore[assignment]


def check_preproc_fidelity(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
    prompts_by_id: dict[str, dict[str, Any]],
    threshold: float = 0.85,
) -> dict[str, Any]:
    """Check pre-processor semantic fidelity using BERTScore.

    Compares original clean prompt text against the pre-processed text
    stored in the DB for sanitize/compress intervention runs.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.
        prompts_by_id: Mapping of prompt_id to prompt record dict.
        threshold: Minimum BERTScore F1 threshold (default 0.85).

    Returns:
        Dict with mean_f1, min_f1, threshold, flagged_count, total_pairs,
        and flagged_pairs list. Returns {"error": ...} if bert-score unavailable.
    """
    all_runs = query_runs(conn, status="completed")
    id_set = set(pilot_prompt_ids)
    preproc_interventions = {"pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only"}
    preproc_runs = [
        r for r in all_runs
        if r["prompt_id"] in id_set and r["intervention"] in preproc_interventions
    ]

    if not preproc_runs:
        return {
            "mean_f1": None,
            "min_f1": None,
            "threshold": threshold,
            "flagged_count": 0,
            "total_pairs": 0,
            "flagged_pairs": [],
        }

    originals = [prompts_by_id[r["prompt_id"]]["prompt_text"] for r in preproc_runs]
    preprocessed = [r["prompt_text"] for r in preproc_runs]

    try:
        _score_fn = bert_score_fn
        if _score_fn is None:
            raise ImportError("bert-score not installed")
        P, R, F1 = _score_fn(preprocessed, originals, lang="en", verbose=False)
        f1_scores = F1.tolist()
    except (ImportError, TypeError) as exc:
        logger.warning("BERTScore unavailable: %s", exc)
        return {"error": str(exc)}

    flagged_pairs: list[dict[str, Any]] = []
    for i, score_val in enumerate(f1_scores):
        if score_val < threshold:
            flagged_pairs.append({
                "index": i,
                "f1": float(score_val),
                "prompt_id": preproc_runs[i]["prompt_id"],
                "intervention": preproc_runs[i]["intervention"],
                "model": preproc_runs[i]["model"],
            })

    result: dict[str, Any] = {
        "mean_f1": float(sum(f1_scores) / len(f1_scores)),
        "min_f1": float(min(f1_scores)),
        "threshold": threshold,
        "flagged_count": len(flagged_pairs),
        "total_pairs": len(f1_scores),
        "flagged_pairs": flagged_pairs,
    }

    logger.info(
        "Pre-proc fidelity: mean F1=%.4f, min F1=%.4f, %d/%d flagged (threshold=%.2f)",
        result["mean_f1"], result["min_f1"], result["flagged_count"],
        result["total_pairs"], threshold,
    )
    return result


# ---------------------------------------------------------------------------
# Latency profiling
# ---------------------------------------------------------------------------

def _compute_latency_stats(values: list[float]) -> dict[str, float]:
    """Compute summary statistics for a list of latency values.

    Args:
        values: List of latency values in milliseconds.

    Returns:
        Dict with mean, p50, p95, max, and min.
    """
    arr = np.array(values)
    p50, p95 = np.percentile(arr, [50, 95])
    return {
        "mean": float(arr.mean()),
        "p50": float(p50),
        "p95": float(p95),
        "max": float(arr.max()),
        "min": float(arr.min()),
    }


def profile_latency(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
) -> dict[str, Any]:
    """Profile TTFT and TTLT latency distributions from pilot data.

    Groups by model and by (model, intervention) to identify latency patterns
    and flag unexpectedly slow conditions.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.

    Returns:
        Dict with by_model, by_condition, estimated_full_run_hours, and latency_flags.
    """
    all_runs = query_runs(conn, status="completed")
    id_set = set(pilot_prompt_ids)
    pilot_runs = [r for r in all_runs if r["prompt_id"] in id_set]

    # Group by model
    by_model_ttft: dict[str, list[float]] = {}
    by_model_ttlt: dict[str, list[float]] = {}
    # Group by model|intervention
    by_cond_ttft: dict[str, list[float]] = {}
    by_cond_ttlt: dict[str, list[float]] = {}

    for r in pilot_runs:
        model = r["model"]
        intv = r["intervention"]
        ttft = r.get("ttft_ms")
        ttlt = r.get("ttlt_ms")
        if ttft is not None:
            by_model_ttft.setdefault(model, []).append(ttft)
            key = f"{model}|{intv}"
            by_cond_ttft.setdefault(key, []).append(ttft)
        if ttlt is not None:
            by_model_ttlt.setdefault(model, []).append(ttlt)
            key = f"{model}|{intv}"
            by_cond_ttlt.setdefault(key, []).append(ttlt)

    by_model: dict[str, dict[str, Any]] = {}
    for model in set(list(by_model_ttft.keys()) + list(by_model_ttlt.keys())):
        by_model[model] = {}
        if model in by_model_ttft:
            by_model[model]["ttft"] = _compute_latency_stats(by_model_ttft[model])
        if model in by_model_ttlt:
            by_model[model]["ttlt"] = _compute_latency_stats(by_model_ttlt[model])

    by_condition: dict[str, dict[str, Any]] = {}
    for key in set(list(by_cond_ttft.keys()) + list(by_cond_ttlt.keys())):
        by_condition[key] = {}
        if key in by_cond_ttft:
            by_condition[key]["ttft"] = _compute_latency_stats(by_cond_ttft[key])
        if key in by_cond_ttlt:
            by_condition[key]["ttlt"] = _compute_latency_stats(by_cond_ttlt[key])

    # Estimate wall-clock time for full run (rough)
    all_ttlt = []
    for vals in by_model_ttlt.values():
        all_ttlt.extend(vals)
    if all_ttlt:
        mean_ttlt = np.mean(all_ttlt)
        # Full run items: scale by 200/len(pilot_prompt_ids)
        n_pilot_items = len(pilot_runs)
        scale = 200 / max(len(pilot_prompt_ids), 1)
        total_items = n_pilot_items * scale
        estimated_hours = float(total_items * mean_ttlt / 1000 / 3600)
    else:
        estimated_hours = 0.0

    # Flag conditions with p95 TTLT > 30s
    latency_flags: list[dict[str, Any]] = []
    for key, stats in by_condition.items():
        if "ttlt" in stats and stats["ttlt"]["p95"] > 30000:
            latency_flags.append({
                "condition": key,
                "p95_ttlt_ms": stats["ttlt"]["p95"],
                "warning": "p95 TTLT exceeds 30 seconds",
            })

    result: dict[str, Any] = {
        "by_model": by_model,
        "by_condition": by_condition,
        "estimated_full_run_hours": estimated_hours,
        "latency_flags": latency_flags,
    }

    logger.info("Latency profile: estimated %.1f hours for full run", estimated_hours)
    if latency_flags:
        for flag in latency_flags:
            logger.warning("Latency flag: %s - p95 TTLT %.0fms", flag["condition"], flag["p95_ttlt_ms"])

    return result


# ---------------------------------------------------------------------------
# Power analysis (rough estimate)
# ---------------------------------------------------------------------------

def estimate_power(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
) -> dict[str, Any]:
    """Estimate whether N=200 is sufficient based on observed pilot effect sizes.

    Uses a simplified binomial power calculation comparing clean+raw pass rates
    against each noisy+raw condition. This is a rough informational estimate,
    not the full GLMM power analysis planned for Phase 5.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.

    Returns:
        Dict with observed_effects, required_n, n_200_sufficient, and note.
    """
    from scipy.stats import norm

    all_runs = query_runs(conn, status="completed")
    id_set = set(pilot_prompt_ids)
    pilot_runs = [r for r in all_runs if r["prompt_id"] in id_set]

    # Compute pass rates for clean+raw vs. noisy+raw
    raw_runs = [r for r in pilot_runs if r["intervention"] == "raw"]

    def _pass_rate(runs: list[dict]) -> float | None:
        if not runs:
            return None
        passed = sum(1 for r in runs if r.get("pass_fail") == 1)
        return passed / len(runs)

    clean_raw = [r for r in raw_runs if r["noise_type"] == "clean"]
    clean_rate = _pass_rate(clean_raw)

    noisy_types = set(r["noise_type"] for r in raw_runs if r["noise_type"] != "clean")

    observed_effects: list[dict[str, Any]] = []
    required_n_list: list[dict[str, Any]] = []

    z_alpha = norm.ppf(1 - 0.05 / 2)  # two-sided alpha=0.05
    z_beta = norm.ppf(0.80)  # power=0.80

    for noise_type in sorted(noisy_types):
        noisy_raw = [r for r in raw_runs if r["noise_type"] == noise_type]
        noisy_rate = _pass_rate(noisy_raw)

        if clean_rate is None or noisy_rate is None:
            continue

        effect_size = clean_rate - noisy_rate
        observed_effects.append({
            "noise_type": noise_type,
            "clean_rate": round(clean_rate, 4),
            "noisy_rate": round(noisy_rate, 4),
            "effect_size": round(effect_size, 4),
        })

        # Required N per group via z-test on two proportions
        if abs(effect_size) > 0.001:
            p1, p2 = clean_rate, noisy_rate
            numerator = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))
            denominator = (p1 - p2) ** 2
            n_required = int(np.ceil(numerator / denominator))
        else:
            n_required = None  # Effect too small to estimate

        required_n_list.append({
            "noise_type": noise_type,
            "required_n_per_group": n_required,
        })

    # Check if 200 is sufficient for all observed effects
    n_200_sufficient = all(
        item["required_n_per_group"] is not None and item["required_n_per_group"] <= 200
        for item in required_n_list
    ) if required_n_list else True

    return {
        "observed_effects": observed_effects,
        "required_n": required_n_list,
        "n_200_sufficient": n_200_sufficient,
        "note": "Rough estimate; full GLMM power analysis in Phase 5",
    }


# ---------------------------------------------------------------------------
# Structured verdict
# ---------------------------------------------------------------------------

def run_pilot_verdict(
    conn: sqlite3.Connection,
    pilot_prompt_ids: list[str],
    prompts_by_id: dict[str, dict[str, Any]],
    budget: float = 200.0,
    output_path: str = "results/pilot_verdict.json",
) -> dict[str, Any]:
    """Produce a structured PASS/FAIL verdict for the pilot run.

    Aggregates all validation checks (completeness, noise, cost, spot-check,
    latency, power, fidelity) into a single report with an overall verdict.

    Args:
        conn: Open SQLite database connection.
        pilot_prompt_ids: List of pilot prompt IDs.
        prompts_by_id: Mapping of prompt_id to prompt record dict.
        budget: Budget threshold in USD for cost gate.
        output_path: Path for the JSON verdict report.

    Returns:
        Verdict dict with overall PASS/FAIL and all sub-reports.
    """
    all_runs = query_runs(conn, status="completed")
    failed_runs = query_runs(conn, status="failed")
    id_set = set(pilot_prompt_ids)

    completed = [r for r in all_runs if r["prompt_id"] in id_set]
    failed = [r for r in failed_runs if r["prompt_id"] in id_set]

    total = len(completed) + len(failed)
    completion_rate = len(completed) / total if total > 0 else 0.0

    # Check for systematic failures: any model+intervention combo with 0% completion
    systematic_failures: list[dict[str, str]] = []
    group_counts: dict[str, dict[str, int]] = {}
    for r in completed + failed:
        key = f"{r['model']}|{r['intervention']}"
        if key not in group_counts:
            group_counts[key] = {"completed": 0, "failed": 0}
        if r.get("status") == "completed":
            group_counts[key]["completed"] += 1
        else:
            group_counts[key]["failed"] += 1

    for key, counts in group_counts.items():
        if counts["completed"] == 0 and counts["failed"] > 0:
            model, intv = key.split("|", 1)
            systematic_failures.append({"model": model, "intervention": intv})

    # Zero variance check
    condition_results: dict[str, set[int]] = {}
    for r in completed:
        cond_key = f"{r['prompt_id']}|{r['noise_type']}|{r['intervention']}|{r['model']}"
        pf = r.get("pass_fail")
        if pf is not None:
            condition_results.setdefault(cond_key, set()).add(pf)

    zero_var_count = sum(1 for vals in condition_results.values() if len(vals) == 1)
    total_conditions = len(condition_results)
    zero_variance_pct = (zero_var_count / total_conditions * 100) if total_conditions > 0 else 0.0

    # Run all sub-checks
    data_audit = audit_data_completeness(conn, pilot_prompt_ids)
    noise_check = verify_noise_rates(prompts_by_id, pilot_prompt_ids)
    cost_proj = compute_cost_projection(conn, pilot_prompt_ids)
    budget_check = check_budget_gate(cost_proj["projected_full_cost"], budget)
    spot_check = run_spot_check(conn, pilot_prompt_ids, prompts_by_id)
    latency = profile_latency(conn, pilot_prompt_ids)
    power = estimate_power(conn, pilot_prompt_ids)

    # BERTScore fidelity (optional)
    try:
        fidelity = check_preproc_fidelity(conn, pilot_prompt_ids, prompts_by_id)
    except Exception as exc:
        logger.warning("BERTScore fidelity check failed: %s", exc)
        fidelity = {"error": str(exc)}

    # Determine overall verdict
    flagged_issues: list[str] = []
    overall = "PASS"

    if completion_rate < 0.95:
        overall = "FAIL"
        flagged_issues.append(f"Completion rate {completion_rate:.1%} < 95%")

    if systematic_failures:
        overall = "FAIL"
        for sf in systematic_failures:
            flagged_issues.append(f"Systematic failure: {sf['model']}|{sf['intervention']}")

    if budget_check["exceeds_budget"]:
        flagged_issues.append(
            f"Budget warning: projected ${cost_proj['projected_full_cost']:.2f} > ${budget:.2f}"
        )

    verdict: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_verdict": overall,
        "completion_rate": completion_rate,
        "systematic_failures": systematic_failures,
        "zero_variance_pct": zero_variance_pct,
        "data_audit": data_audit,
        "noise_check": noise_check,
        "cost_projection": cost_proj,
        "budget_gate": budget_check,
        "spot_check_summary": {
            "total_sampled": spot_check["total_sampled"],
            "gsm8k_count": spot_check["gsm8k_count"],
            "code_count": spot_check["code_count"],
        },
        "latency": latency,
        "power_analysis": power,
        "preproc_fidelity": fidelity,
        "flagged_issues": flagged_issues,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(verdict, f, indent=2, default=str)

    logger.info(
        "Pilot verdict: %s | completion=%.1f%% | projected=$%.2f | flags=%d",
        overall, completion_rate * 100, cost_proj["projected_full_cost"],
        len(flagged_issues),
    )
    return verdict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the pilot CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Pilot validation for the Linguistic Tax research toolkit.",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=200.0,
        help="Budget threshold for full run cost projection (default: 200.0)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Override path to results database",
    )
    parser.add_argument(
        "--select-only",
        action="store_true",
        help="Only select pilot prompts, do not run or analyze",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze existing results, do not run experiment",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-accept without prompting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show summary only, do not execute",
    )
    return parser


def _check_config_exists() -> None:
    """Exit with guidance if no config file is found."""
    if find_config_path() is None:
        logger.error(
            "No config found. Run `python src/cli.py setup` to configure "
            "the slicer before running experiments."
        )
        sys.exit(1)


def main() -> None:
    """Entry point for the pilot validation CLI."""
    _check_config_exists()
    parser = _build_parser()
    args = parser.parse_args()
    result = run_pilot(
        budget=args.budget,
        db_path=args.db,
        select_only=args.select_only,
        analyze_only=args.analyze_only,
        yes=args.yes,
        dry_run=args.dry_run,
    )
    logger.info("Pilot result: %s", result.get("status", "unknown"))


if __name__ == "__main__":
    main()
