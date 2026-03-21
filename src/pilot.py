"""Pilot validation module for the Linguistic Tax research toolkit.

Provides stratified prompt selection, pilot execution, data completeness
auditing, and noise injection sanity checking for the 20-prompt pilot run.
"""

import json
import logging
import random
import sqlite3
from typing import Any

from src.config import ExperimentConfig, derive_seed
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
