"""Derived metrics module for the Linguistic Tax research toolkit.

Computes per-prompt Consistency Rate (CR), stability-correctness quadrant
classification, cost fields, and quadrant migration transition matrices.
Populates the derived_metrics SQLite table and outputs per-condition cost
rollup aggregates as JSON and CSV.

See RDD Sections 7.3 and 8.1-8.2 for CR and quadrant definitions.
"""

import argparse
import json
import logging
import os
import sqlite3
from itertools import combinations
from typing import Any

import pandas as pd
from tabulate import tabulate

from src.config import INTERVENTIONS, NOISE_TYPES
from src.model_registry import registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------


def compute_cr(pass_fail_results: list[int]) -> float:
    """Compute the pairwise Consistency Rate (CR) from pass/fail outcomes.

    Enumerates all C(K,2) pairs of repetitions and counts the fraction
    that agree (both pass or both fail).

    Args:
        pass_fail_results: List of 0/1 outcomes from K repetitions.

    Returns:
        CR value between 0.0 and 1.0. Returns 1.0 for degenerate cases (K < 2).
    """
    k = len(pass_fail_results)
    if k < 2:
        return 1.0

    total_pairs = 0
    agreeing_pairs = 0
    for a, b in combinations(pass_fail_results, 2):
        total_pairs += 1
        if a == b:
            agreeing_pairs += 1

    return agreeing_pairs / total_pairs


def classify_quadrant(
    cr: float, majority_pass: bool, cr_threshold: float = 0.8
) -> str:
    """Classify a prompt-condition into a stability-correctness quadrant.

    The four quadrants are:
    - robust: stable (CR >= threshold) and majority pass
    - confidently_wrong: stable but majority fail
    - lucky: unstable but majority pass
    - broken: unstable and majority fail

    Args:
        cr: Consistency rate for the prompt-condition.
        majority_pass: Whether the majority of repetitions passed.
        cr_threshold: Stability threshold (default 0.8).

    Returns:
        One of 'robust', 'confidently_wrong', 'lucky', 'broken'.
    """
    stable = cr >= cr_threshold
    if stable and majority_pass:
        return "robust"
    elif stable and not majority_pass:
        return "confidently_wrong"
    elif not stable and majority_pass:
        return "lucky"
    else:
        return "broken"


def build_condition_string(noise_type: str, intervention: str) -> str:
    """Build a condition identifier from noise type and intervention.

    Args:
        noise_type: The noise type (e.g., 'clean', 'type_a_10pct').
        intervention: The intervention (e.g., 'raw', 'pre_proc_sanitize').

    Returns:
        Formatted condition string, e.g. 'clean_raw'.
    """
    return f"{noise_type}_{intervention}"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_experiment_data(db_path: str) -> pd.DataFrame:
    """Load completed experiment runs from the SQLite database.

    Filters for rows with status='completed' and non-null pass_fail.

    Args:
        db_path: Path to the SQLite results database.

    Returns:
        DataFrame containing all completed experiment runs.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM experiment_runs WHERE status = 'completed' AND pass_fail IS NOT NULL",
        conn,
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Derived metric computation
# ---------------------------------------------------------------------------


def compute_derived_metrics(
    db_path: str, cr_threshold: float = 0.8
) -> dict[str, Any]:
    """Compute and store derived metrics for all prompt-condition-model triples.

    Groups experiment runs by (prompt_id, noise_type, intervention, model),
    computes CR, quadrant classification, latency stats, and cost fields,
    then writes results to the derived_metrics table.

    Args:
        db_path: Path to the SQLite results database.
        cr_threshold: Stability threshold for quadrant classification.

    Returns:
        Summary dict with quadrant counts, total prompts processed,
        and count of incomplete groups (fewer than 5 repetitions).
    """
    df = load_experiment_data(db_path)

    if df.empty:
        logger.warning("No completed experiment runs found in %s", db_path)
        return {"total": 0, "incomplete_groups": 0, "quadrants": {}}

    conn = sqlite3.connect(db_path)
    # Ensure derived_metrics table exists (it should from init_database)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS derived_metrics (
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

    grouped = df.groupby(["prompt_id", "noise_type", "intervention", "model"])
    quadrant_counts: dict[str, int] = {
        "robust": 0,
        "confidently_wrong": 0,
        "lucky": 0,
        "broken": 0,
    }
    total = 0
    incomplete_groups = 0

    for (prompt_id, noise_type, intervention, model), group in grouped:
        pass_fail_list = group["pass_fail"].astype(int).tolist()
        k = len(pass_fail_list)

        if k < 5:
            logger.warning(
                "Incomplete group: %s/%s/%s/%s has %d runs (expected 5)",
                prompt_id, noise_type, intervention, model, k,
            )
            incomplete_groups += 1

        cr = compute_cr(pass_fail_list)
        pass_count = sum(pass_fail_list)
        majority_pass = pass_count >= k / 2
        quadrant = classify_quadrant(cr, majority_pass, cr_threshold)
        condition = build_condition_string(noise_type, intervention)

        # Latency stats
        total_latency = group["ttft_ms"] + group["ttlt_ms"]
        mean_ttft = group["ttft_ms"].mean()
        mean_ttlt = group["ttlt_ms"].mean()
        mean_total_latency = total_latency.mean()
        std_latency = total_latency.std()

        # Cost
        mean_total_cost = group["total_cost_usd"].mean()

        # Token savings: compare prompt tokens to preproc output tokens
        prompt_tokens = group["prompt_tokens"]
        if "preproc_output_tokens" in group.columns:
            preproc_out = group["preproc_output_tokens"].fillna(group["prompt_tokens"])
            savings = (prompt_tokens - preproc_out).mean()
            token_savings = int(round(savings))
        else:
            token_savings = 0
        net_token_cost = int(round(prompt_tokens.mean())) - token_savings

        conn.execute(
            """INSERT OR REPLACE INTO derived_metrics
            (prompt_id, condition, model, consistency_rate, majority_pass,
             pass_count, quadrant, mean_ttft_ms, mean_ttlt_ms,
             mean_total_latency_ms, mean_total_cost_usd, token_savings,
             net_token_cost, std_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prompt_id, condition, model, cr,
                1 if majority_pass else 0,
                pass_count, quadrant,
                mean_ttft, mean_ttlt, mean_total_latency, mean_total_cost,
                token_savings, net_token_cost, std_latency,
            ),
        )

        quadrant_counts[quadrant] += 1
        total += 1

    conn.commit()
    conn.close()

    logger.info(
        "Computed derived metrics for %d prompt-condition-model triples "
        "(%d incomplete groups)",
        total, incomplete_groups,
    )
    return {
        "total": total,
        "incomplete_groups": incomplete_groups,
        "quadrants": quadrant_counts,
    }


# ---------------------------------------------------------------------------
# Quadrant migration
# ---------------------------------------------------------------------------


def compute_quadrant_migration(
    db_path: str,
    model: str,
    from_condition: str,
    to_condition: str,
) -> dict[str, Any]:
    """Compute a quadrant transition matrix between two conditions.

    For each prompt that appears in both conditions, records the
    from-quadrant and to-quadrant to build a 4x4 transition matrix.

    Args:
        db_path: Path to the SQLite results database.
        model: Model identifier to filter on.
        from_condition: Source condition string (e.g., 'clean_raw').
        to_condition: Target condition string (e.g., 'type_a_10pct_raw').

    Returns:
        Dict with from_condition, to_condition, model, n_prompts,
        and transition_matrix (nested dict of counts).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    from_rows = conn.execute(
        "SELECT prompt_id, quadrant FROM derived_metrics "
        "WHERE model = ? AND condition = ?",
        (model, from_condition),
    ).fetchall()

    to_rows = conn.execute(
        "SELECT prompt_id, quadrant FROM derived_metrics "
        "WHERE model = ? AND condition = ?",
        (model, to_condition),
    ).fetchall()

    conn.close()

    from_map = {r["prompt_id"]: r["quadrant"] for r in from_rows}
    to_map = {r["prompt_id"]: r["quadrant"] for r in to_rows}

    quadrants = ["robust", "confidently_wrong", "lucky", "broken"]
    matrix: dict[str, dict[str, int]] = {
        q: {q2: 0 for q2 in quadrants} for q in quadrants
    }

    common_prompts = set(from_map.keys()) & set(to_map.keys())
    for pid in common_prompts:
        fq = from_map[pid]
        tq = to_map[pid]
        matrix[fq][tq] += 1

    logger.info(
        "Quadrant migration %s -> %s (%s): %d prompts",
        from_condition, to_condition, model, len(common_prompts),
    )

    return {
        "from_condition": from_condition,
        "to_condition": to_condition,
        "model": model,
        "n_prompts": len(common_prompts),
        "transition_matrix": matrix,
    }


# ---------------------------------------------------------------------------
# Cost rollups
# ---------------------------------------------------------------------------


def compute_cost_rollups(db_path: str) -> list[dict[str, Any]]:
    """Compute per-condition cost aggregates from experiment runs.

    Groups by (model, noise_type, intervention) and computes mean/sum
    for cost fields and mean token savings.

    Args:
        db_path: Path to the SQLite results database.

    Returns:
        List of rollup dicts, one per (model, noise_type, intervention) group.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT model, noise_type, intervention, "
        "total_cost_usd, preproc_cost_usd, "
        "main_model_input_cost_usd, main_model_output_cost_usd, "
        "prompt_tokens, preproc_output_tokens "
        "FROM experiment_runs WHERE status = 'completed'",
        conn,
    )
    conn.close()

    if df.empty:
        logger.warning("No completed runs for cost rollups")
        return []

    rollups: list[dict[str, Any]] = []
    grouped = df.groupby(["model", "noise_type", "intervention"])

    for (model, noise_type, intervention), group in grouped:
        main_cost = (
            group["main_model_input_cost_usd"].fillna(0)
            + group["main_model_output_cost_usd"].fillna(0)
        )
        preproc_out = group["preproc_output_tokens"].fillna(group["prompt_tokens"])
        token_savings = (group["prompt_tokens"] - preproc_out).mean()

        rollups.append({
            "model": model,
            "noise_type": noise_type,
            "intervention": intervention,
            "n_runs": len(group),
            "mean_total_cost_usd": group["total_cost_usd"].mean(),
            "sum_total_cost_usd": group["total_cost_usd"].sum(),
            "mean_preproc_cost_usd": group["preproc_cost_usd"].fillna(0).mean(),
            "sum_preproc_cost_usd": group["preproc_cost_usd"].fillna(0).sum(),
            "mean_main_cost_usd": main_cost.mean(),
            "mean_token_savings": token_savings,
        })

    logger.info("Computed cost rollups for %d condition groups", len(rollups))
    return rollups


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for computing derived metrics, cost rollups, and migration matrices.

    Parses --db, --cr-threshold, and --output-dir arguments, then runs all
    computations, writes results to DB and output files, and prints
    terminal summary tables.
    """
    parser = argparse.ArgumentParser(
        description="Compute derived metrics for the Linguistic Tax experiment"
    )
    parser.add_argument(
        "--db",
        default="results/results.db",
        help="Path to the SQLite results database",
    )
    parser.add_argument(
        "--cr-threshold",
        type=float,
        default=0.8,
        help="Consistency rate threshold for quadrant classification",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory for output files (JSON, CSV)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 1. Compute derived metrics (writes to DB)
    logger.info("Computing derived metrics from %s", args.db)
    summary = compute_derived_metrics(args.db, cr_threshold=args.cr_threshold)
    logger.info(
        "Derived metrics summary: %d triples, %d incomplete groups",
        summary["total"], summary["incomplete_groups"],
    )

    # Print quadrant distribution
    if summary["quadrants"]:
        quad_table = [
            [q, count, f"{count / max(summary['total'], 1) * 100:.1f}%"]
            for q, count in summary["quadrants"].items()
        ]
        logger.info(
            "Quadrant distribution:\n%s",
            tabulate(quad_table, headers=["Quadrant", "Count", "Pct"], tablefmt="grid"),
        )

    # 2. Cost rollups
    logger.info("Computing cost rollups")
    rollups = compute_cost_rollups(args.db)

    # Write JSON
    os.makedirs(args.output_dir, exist_ok=True)
    rollups_json_path = os.path.join(args.output_dir, "cost_rollups.json")
    with open(rollups_json_path, "w") as f:
        json.dump(rollups, f, indent=2)
    logger.info("Cost rollups written to %s", rollups_json_path)

    # Write CSV
    csv_dir = os.path.join(args.output_dir, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    rollups_csv_path = os.path.join(csv_dir, "cost_rollups.csv")
    if rollups:
        pd.DataFrame(rollups).to_csv(rollups_csv_path, index=False)
    logger.info("Cost rollups CSV written to %s", rollups_csv_path)

    # Print cost rollup table
    if rollups:
        cost_table = [
            [r["model"], r["noise_type"], r["intervention"],
             r["n_runs"], f"${r['mean_total_cost_usd']:.6f}",
             f"${r['sum_total_cost_usd']:.4f}"]
            for r in rollups
        ]
        logger.info(
            "Cost rollups:\n%s",
            tabulate(
                cost_table,
                headers=["Model", "Noise", "Intervention", "N", "Mean Cost", "Total Cost"],
                tablefmt="grid",
            ),
        )

    # 3. Quadrant migration matrices (clean -> noisy for each model)
    noisy_types = ["type_a_5pct", "type_a_10pct", "type_a_20pct"]
    migrations: list[dict[str, Any]] = []

    for model in registry.target_models():
        for noise_type in noisy_types:
            from_cond = build_condition_string("clean", "raw")
            to_cond = build_condition_string(noise_type, "raw")
            try:
                migration = compute_quadrant_migration(
                    args.db, model=model,
                    from_condition=from_cond, to_condition=to_cond,
                )
                migrations.append(migration)
            except Exception:
                logger.exception(
                    "Failed migration %s -> %s for %s",
                    from_cond, to_cond, model,
                )

    # Write migration JSON
    migration_json_path = os.path.join(args.output_dir, "quadrant_migration.json")
    with open(migration_json_path, "w") as f:
        json.dump(migrations, f, indent=2)
    logger.info("Quadrant migration written to %s", migration_json_path)

    # 4. Quadrant distribution CSV
    conn = sqlite3.connect(args.db)
    quad_df = pd.read_sql_query("SELECT * FROM derived_metrics", conn)
    conn.close()

    if not quad_df.empty:
        quad_csv_path = os.path.join(csv_dir, "quadrant_distribution.csv")
        quad_df.to_csv(quad_csv_path, index=False)
        logger.info("Quadrant distribution CSV written to %s", quad_csv_path)

    logger.info("All derived metric computations complete")


if __name__ == "__main__":
    main()
