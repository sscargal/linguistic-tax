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

from src.model_registry import registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AVG_TOKENS: dict[str, dict[str, int]] = {
    "humaneval": {"input": 500, "output": 200},
    "mbpp": {"input": 500, "output": 200},
    "gsm8k": {"input": 300, "output": 100},
}

# Estimated output/input ratio per benchmark (output tokens are harder
# to predict — use benchmark-appropriate multipliers)
_OUTPUT_RATIO: dict[str, float] = {
    "humaneval": 1.5,  # Code generation: output typically longer than prompt
    "mbpp": 2.0,       # Short prompts, longer code output
    "gsm8k": 1.0,      # Math: output roughly matches input length
}

PREPROC_INTERVENTIONS: set[str] = {
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "compress_only",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_prompt_tokens(prompts_path: str = "data/prompts.json") -> dict[str, int]:
    """Compute actual input token counts per prompt from the prompts file.

    Uses tiktoken cl100k_base encoding for token counting.

    Args:
        prompts_path: Path to the prompts JSON file.

    Returns:
        Dict mapping prompt_id to input token count.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        with open(prompts_path) as f:
            prompts = json.load(f)
        return {p["problem_id"]: len(enc.encode(p["prompt_text"])) for p in prompts}
    except Exception:
        logger.debug("Could not compute prompt tokens, using estimates")
        return {}


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


def estimate_cost(
    items: list[dict[str, Any]],
    prompts_path: str = "data/prompts.json",
) -> dict[str, float]:
    """Estimate total cost for a set of experiment items.

    Computes actual input token counts from the prompts file via tiktoken,
    falling back to static averages if unavailable. Pre-processor costs
    are computed separately for interventions that use a cheap model call.

    Args:
        items: List of experiment matrix item dicts, each containing
            at minimum "prompt_id", "model", and "intervention" keys.
        prompts_path: Path to prompts JSON for actual token counting.

    Returns:
        Dict with keys "target_cost", "preproc_cost", "total_cost" in USD,
        plus "target_input_tokens", "target_output_tokens",
        "preproc_input_tokens", "preproc_output_tokens" counts.
    """
    prompt_tokens = _compute_prompt_tokens(prompts_path)

    target_cost = 0.0
    preproc_cost = 0.0
    target_input_tokens = 0
    target_output_tokens = 0
    preproc_input_tokens = 0
    preproc_output_tokens = 0

    for item in items:
        benchmark = _get_benchmark(item["prompt_id"])
        fallback = AVG_TOKENS.get(benchmark, AVG_TOKENS["humaneval"])
        input_toks = prompt_tokens.get(item["prompt_id"], fallback["input"])
        output_ratio = _OUTPUT_RATIO.get(benchmark, 1.5)
        output_toks = int(input_toks * output_ratio)

        # Target model cost
        target_cost += registry.compute_cost(item["model"], input_toks, output_toks)
        target_input_tokens += input_toks
        target_output_tokens += output_toks

        # Pre-processor cost for applicable interventions
        if item["intervention"] in PREPROC_INTERVENTIONS:
            preproc_model = registry.get_preproc(item["model"]) or item["model"]
            preproc_output = int(input_toks * 0.8)
            preproc_cost += registry.compute_cost(preproc_model, input_toks, preproc_output)
            preproc_input_tokens += input_toks
            preproc_output_tokens += preproc_output

    return {
        "target_cost": target_cost,
        "preproc_cost": preproc_cost,
        "total_cost": target_cost + preproc_cost,
        "target_input_tokens": target_input_tokens,
        "target_output_tokens": target_output_tokens,
        "preproc_input_tokens": preproc_input_tokens,
        "preproc_output_tokens": preproc_output_tokens,
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
        delay = registry.get_delay(model)
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

    # Models section — show target models and their pre-processors
    prompt_tokens = _compute_prompt_tokens()
    model_counts: Counter[str] = Counter(item["model"] for item in items)
    model_table = []
    for model, count in sorted(model_counts.items()):
        per_model_cost = 0.0
        for item in items:
            if item["model"] == model:
                benchmark = _get_benchmark(item["prompt_id"])
                fallback = AVG_TOKENS.get(benchmark, AVG_TOKENS["humaneval"])
                input_toks = prompt_tokens.get(item["prompt_id"], fallback["input"])
                output_toks = int(input_toks * _OUTPUT_RATIO.get(benchmark, 1.5))
                per_model_cost += registry.compute_cost(model, input_toks, output_toks)
        model_table.append([model, "target", count, f"${per_model_cost:.2f}"])

        # Show the pre-processor model for this target
        preproc_model = registry.get_preproc(model)
        if preproc_model and preproc_model != model:
            preproc_calls = sum(1 for item in items
                                if item["model"] == model
                                and item["intervention"] in PREPROC_INTERVENTIONS)
            preproc_per_model = 0.0
            for item in items:
                if item["model"] == model and item["intervention"] in PREPROC_INTERVENTIONS:
                    benchmark = _get_benchmark(item["prompt_id"])
                    fallback = AVG_TOKENS.get(benchmark, AVG_TOKENS["humaneval"])
                    input_toks = prompt_tokens.get(item["prompt_id"], fallback["input"])
                    preproc_output = int(input_toks * 0.8)
                    preproc_per_model += registry.compute_cost(preproc_model, input_toks, preproc_output)
            model_table.append([f"  {preproc_model}", "preproc", preproc_calls, f"${preproc_per_model:.2f}"])

    lines.append("Models:")
    lines.append(tabulate(model_table, headers=["Model", "Role", "API Calls", "Est. Cost"], tablefmt="simple"))
    lines.append("")

    # Interventions section
    intervention_counts: Counter[str] = Counter(item["intervention"] for item in items)
    intervention_table = [[intervention, count] for intervention, count in sorted(intervention_counts.items())]
    lines.append("Interventions:")
    lines.append(tabulate(intervention_table, headers=["Intervention", "API Calls"], tablefmt="simple"))
    lines.append("")

    # Noise Conditions section
    noise_counts: Counter[str] = Counter(item["noise_type"] for item in items)
    noise_table = [[noise_type, count] for noise_type, count in sorted(noise_counts.items())]
    lines.append("Noise Conditions:")
    lines.append(tabulate(noise_table, headers=["Noise Type", "API Calls"], tablefmt="simple"))
    lines.append("")

    # Token and cost section
    target_in = cost_estimate.get("target_input_tokens", 0)
    target_out = cost_estimate.get("target_output_tokens", 0)
    preproc_in = cost_estimate.get("preproc_input_tokens", 0)
    preproc_out = cost_estimate.get("preproc_output_tokens", 0)

    lines.append("Estimated Tokens:")
    lines.append(f"  Target model:      {target_in:,} in / {target_out:,} out")
    lines.append(f"  Pre-processor:     {preproc_in:,} in / {preproc_out:,} out")
    lines.append(f"  Total:             {target_in + preproc_in:,} in / {target_out + preproc_out:,} out")
    lines.append("")

    lines.append("Estimated Cost:")
    lines.append(f"  Target model:      ${cost_estimate['target_cost']:.2f}")
    lines.append(f"  Pre-processor:     ${cost_estimate['preproc_cost']:.2f}")
    lines.append(f"  Total:             ${cost_estimate['total_cost']:.2f}")
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
