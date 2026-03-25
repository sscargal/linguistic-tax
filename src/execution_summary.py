"""Pre-execution summary, cost estimation, and confirmation gate.

Provides static cost/runtime estimation from PRICE_TABLE and average token
counts, structured summary display, three-way confirmation gate (Y/N/M)
with --yes and --budget support, resume detection, and execution plan saving.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tabulate import tabulate

from src.config import (
    PRICE_TABLE,
    PREPROC_MODEL_MAP,
    RATE_LIMIT_DELAYS,
    compute_cost,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AVG_TOKENS: dict[str, dict[str, int]] = {
    "humaneval": {"input": 500, "output": 200},
    "mbpp": {"input": 500, "output": 200},
    "gsm8k": {"input": 300, "output": 100},
}

PREPROC_INTERVENTIONS: set[str] = {
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "compress_only",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_benchmark(prompt_id: str) -> str:
    """Derive benchmark name from prompt ID prefix.

    Args:
        prompt_id: The prompt identifier (e.g., "HumanEval/1", "Mbpp/1", "gsm8k_1").

    Returns:
        Benchmark name: "humaneval", "mbpp", or "gsm8k".
    """
    if prompt_id.startswith("HumanEval/"):
        return "humaneval"
    elif prompt_id.startswith("Mbpp/"):
        return "mbpp"
    elif prompt_id.startswith("gsm8k"):
        return "gsm8k"
    else:
        return "unknown"


def _make_run_id(item: dict[str, Any]) -> str:
    """Build a deterministic run ID from experiment matrix item fields.

    Inlined from run_experiment.py to avoid circular imports.

    Args:
        item: An experiment matrix item dictionary.

    Returns:
        Pipe-separated run ID string.
    """
    noise_level = str(item["noise_level"]) if item["noise_level"] is not None else "none"
    parts = [
        item["prompt_id"],
        item["noise_type"],
        noise_level,
        item["intervention"],
        item["model"],
        str(item["repetition_num"]),
    ]
    return "|".join(parts)


def _format_duration(seconds: float) -> str:
    """Format seconds into a human-readable Xh Ym Zs string.

    Args:
        seconds: Number of seconds.

    Returns:
        Formatted duration string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_cost(items: list[dict[str, Any]]) -> dict[str, float]:
    """Estimate total cost for a set of experiment items.

    Uses static average token counts per benchmark and PRICE_TABLE for
    per-model pricing.  Pre-processor costs are computed separately for
    interventions that require a cheap pre-processing model call.

    Args:
        items: List of experiment matrix item dicts, each containing
            at minimum "prompt_id", "model", and "intervention" keys.

    Returns:
        Dict with keys "target_cost", "preproc_cost", "total_cost" in USD.
    """
    target_cost = 0.0
    preproc_cost = 0.0

    for item in items:
        benchmark = _get_benchmark(item["prompt_id"])
        tokens = AVG_TOKENS.get(benchmark, AVG_TOKENS["humaneval"])

        # Target model cost
        target_cost += compute_cost(item["model"], tokens["input"], tokens["output"])

        # Pre-processor cost for applicable interventions
        if item["intervention"] in PREPROC_INTERVENTIONS:
            preproc_model = PREPROC_MODEL_MAP.get(item["model"], item["model"])
            preproc_output = int(tokens["input"] * 0.8)
            preproc_cost += compute_cost(preproc_model, tokens["input"], preproc_output)

    return {
        "target_cost": target_cost,
        "preproc_cost": preproc_cost,
        "total_cost": target_cost + preproc_cost,
    }


def estimate_runtime(items: list[dict[str, Any]]) -> float:
    """Estimate wall-clock runtime from rate-limit delays.

    Sums per-model delay times item count to produce a lower bound on
    execution time (assumes sequential processing per model).

    Args:
        items: List of experiment matrix item dicts with "model" key.

    Returns:
        Estimated wall-clock seconds.
    """
    model_counts: Counter[str] = Counter(item["model"] for item in items)
    total_seconds = 0.0
    for model, count in model_counts.items():
        delay = RATE_LIMIT_DELAYS.get(model, 0.5)
        total_seconds += count * delay
    return total_seconds


def count_completed(
    items: list[dict[str, Any]], conn: Any
) -> tuple[int, int, list[dict[str, Any]]]:
    """Count completed experiment items and return pending ones.

    Queries the database for completed runs, then partitions the input
    items into completed and pending based on run ID matching.

    Args:
        items: Full list of experiment matrix item dicts.
        conn: An open SQLite database connection.

    Returns:
        Tuple of (completed_count, total_count, pending_items).
    """
    from src.db import query_runs

    completed_rows = query_runs(conn, status="completed")
    completed_ids: set[str] = {row["run_id"] for row in completed_rows}

    pending: list[dict[str, Any]] = []
    completed_count = 0

    for item in items:
        run_id = _make_run_id(item)
        if run_id in completed_ids:
            completed_count += 1
        else:
            pending.append(item)

    return completed_count, len(items), pending


def format_summary(
    items: list[dict[str, Any]],
    completed_count: int,
    total_count: int,
    cost_estimate: dict[str, float],
    runtime_seconds: float,
) -> str:
    """Build a structured pre-execution summary string.

    Sections: Models, Interventions, Noise Conditions, Cost, Runtime.
    Uses tabulate for aligned column output.

    Args:
        items: The items to be executed (pending items if resuming).
        completed_count: Number of already-completed items (0 if fresh run).
        total_count: Total items in the experiment matrix.
        cost_estimate: Dict from estimate_cost with target/preproc/total keys.
        runtime_seconds: Estimated wall-clock seconds from estimate_runtime.

    Returns:
        Multi-line formatted summary string.
    """
    lines: list[str] = []
    lines.append("=== Pre-Execution Summary ===")
    lines.append("")

    # Resume status
    if completed_count > 0:
        remaining = len(items)
        lines.append(
            f"Resuming: {completed_count} of {total_count} done, "
            f"{remaining} remaining"
        )
        lines.append("")

    # Models section
    model_counts: Counter[str] = Counter(item["model"] for item in items)
    model_table = []
    for model, count in sorted(model_counts.items()):
        per_model_cost = sum(
            compute_cost(item["model"], AVG_TOKENS.get(_get_benchmark(item["prompt_id"]), AVG_TOKENS["humaneval"])["input"],
                         AVG_TOKENS.get(_get_benchmark(item["prompt_id"]), AVG_TOKENS["humaneval"])["output"])
            for item in items if item["model"] == model
        )
        model_table.append([model, count, f"${per_model_cost:.2f}"])
    lines.append("Models:")
    lines.append(tabulate(model_table, headers=["Model", "Items", "Est. Cost"], tablefmt="simple"))
    lines.append("")

    # Interventions section
    intervention_counts: Counter[str] = Counter(item["intervention"] for item in items)
    intervention_table = [[intervention, count] for intervention, count in sorted(intervention_counts.items())]
    lines.append("Interventions:")
    lines.append(tabulate(intervention_table, headers=["Intervention", "Items"], tablefmt="simple"))
    lines.append("")

    # Noise Conditions section
    noise_counts: Counter[str] = Counter(item["noise_type"] for item in items)
    noise_table = [[noise_type, count] for noise_type, count in sorted(noise_counts.items())]
    lines.append("Noise Conditions:")
    lines.append(tabulate(noise_table, headers=["Noise Type", "Items"], tablefmt="simple"))
    lines.append("")

    # Cost section
    lines.append("Cost:")
    lines.append(f"  Target model cost:    ${cost_estimate['target_cost']:.2f}")
    lines.append(f"  Pre-processor cost:   ${cost_estimate['preproc_cost']:.2f}")
    lines.append(f"  Total estimated cost:  ${cost_estimate['total_cost']:.2f}")
    lines.append("")

    # Runtime section
    lines.append("Runtime:")
    lines.append(f"  Estimated runtime: {_format_duration(runtime_seconds)}")

    return "\n".join(lines)


def confirm_execution(
    summary: str,
    yes: bool = False,
    budget: float | None = None,
    estimated_cost: float = 0.0,
    input_fn: Callable[[str], str] = input,
) -> str:
    """Display summary and prompt for execution confirmation.

    Supports three modes: auto-accept (--yes), budget gate (--budget),
    and interactive three-way prompt (Y/N/M).

    Args:
        summary: The formatted summary string to display.
        yes: If True, auto-accept without prompting.
        budget: Optional cost threshold. If estimated_cost exceeds this,
            print a warning and exit non-zero.
        estimated_cost: The total estimated cost for budget comparison.
        input_fn: Callable for reading user input (injectable for testing).

    Returns:
        One of "yes", "no", or "modify".
    """
    print(summary)

    # Budget gate check (before auto-accept)
    if budget is not None and estimated_cost > budget:
        print(
            f"\nWARNING: Estimated cost ${estimated_cost:.2f} "
            f"exceeds budget ${budget:.2f}"
        )
        sys.exit(1)

    if yes:
        return "yes"

    try:
        while True:
            choice = input_fn("[Y]es to run, [N]o to abort, [M]odify filters: ").strip().lower()
            if choice in ("y", "yes"):
                return "yes"
            elif choice in ("n", "no"):
                return "no"
            elif choice in ("m", "modify"):
                return "modify"
            else:
                print("Invalid choice. Enter Y, N, or M.")
    except KeyboardInterrupt:
        print("\nAborted.")
        return "no"


def save_execution_plan(
    items: list[dict[str, Any]],
    cost_estimate: dict[str, float],
    runtime_estimate: float,
    filters: dict[str, Any] | None = None,
    output_path: str = "results/execution_plan.json",
) -> None:
    """Save the pre-execution plan to a JSON file.

    Records item counts, cost projections, models, interventions, noise
    types, filters, and a timestamp for post-hoc reproducibility checks.

    Args:
        items: List of experiment matrix item dicts to be executed.
        cost_estimate: Dict from estimate_cost.
        runtime_estimate: Estimated wall-clock seconds.
        filters: Optional dict of active filter parameters.
        output_path: Path to write the JSON file.
    """
    plan = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "models": sorted({item["model"] for item in items}),
        "interventions": sorted({item["intervention"] for item in items}),
        "noise_types": sorted({item["noise_type"] for item in items}),
        "cost_estimate": cost_estimate,
        "runtime_estimate_seconds": runtime_estimate,
        "filters": filters or {},
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2) + "\n")
    logger.debug("Execution plan saved to %s", output_path)
