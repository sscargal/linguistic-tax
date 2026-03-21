"""Pilot validation module for the Linguistic Tax research toolkit.

Provides stratified prompt selection, pilot execution, data completeness
auditing, noise injection sanity checking, grading spot-check, cost projection
with bootstrap CIs, BERTScore fidelity, latency profiling, and structured
PASS/FAIL verdict for the 20-prompt pilot run.
"""

import json
import logging
import os
import random
import sqlite3
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.stats import bootstrap as scipy_bootstrap

from src.config import ExperimentConfig, derive_seed
from src.db import query_runs
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
) -> dict[str, Any]:
    """Orchestrate the pilot workflow: selection, execution, analysis.

    Args:
        budget: Maximum budget in USD (not enforced, for reference).
        db_path: Override path to results database.
        select_only: If True, only select prompts and return.
        analyze_only: If True, skip selection and execution, only analyze.

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

_VALID_MODELS = {"claude-sonnet-4-20250514", "gemini-1.5-pro"}


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
