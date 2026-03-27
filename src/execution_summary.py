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

    target_input_cost = 0.0
    target_output_cost = 0.0
    preproc_input_cost = 0.0
    preproc_output_cost = 0.0
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

        # Target model cost (split by input/output)
        inp_price, out_price = registry.get_price(item["model"])
        target_input_cost += input_toks * inp_price / 1_000_000
        target_output_cost += output_toks * out_price / 1_000_000
        target_input_tokens += input_toks
        target_output_tokens += output_toks

        # Pre-processor cost for applicable interventions
        if item["intervention"] in PREPROC_INTERVENTIONS:
            preproc_model = registry.get_preproc(item["model"]) or item["model"]
            preproc_output = int(input_toks * 0.8)
            p_inp_price, p_out_price = registry.get_price(preproc_model)
            preproc_input_cost += input_toks * p_inp_price / 1_000_000
            preproc_output_cost += preproc_output * p_out_price / 1_000_000
            preproc_input_tokens += input_toks
            preproc_output_tokens += preproc_output

    target_cost = target_input_cost + target_output_cost
    preproc_cost = preproc_input_cost + preproc_output_cost

    return {
        "target_cost": target_cost,
        "preproc_cost": preproc_cost,
        "total_cost": target_cost + preproc_cost,
        "target_input_cost": target_input_cost,
        "target_output_cost": target_output_cost,
        "preproc_input_cost": preproc_input_cost,
        "preproc_output_cost": preproc_output_cost,
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

    # Models section — show separate input/output pricing rates
    model_counts: Counter[str] = Counter(item["model"] for item in items)
    model_table = []

    def _fmt_price(price: float) -> str:
        return f"${price:.2f}"

    for model in sorted(model_counts):
        inp_price, out_price = registry.get_price(model)
        model_table.append([model, "target", _fmt_price(inp_price), _fmt_price(out_price)])

        preproc_model = registry.get_preproc(model)
        if preproc_model and preproc_model != model:
            p_inp, p_out = registry.get_price(preproc_model)
            model_table.append([f"  {preproc_model}", "preproc", _fmt_price(p_inp), _fmt_price(p_out)])

    lines.append("Models:")
    lines.append(tabulate(model_table, headers=["Model", "Role", "Input (per 1M)", "Output (per 1M)"], tablefmt="simple"))
    lines.append("")

    # Experiment design breakdown
    lines.append("Experiment Design:")

    # Interventions
    intervention_counts: Counter[str] = Counter(item["intervention"] for item in items)
    intervention_table = [[intervention, count] for intervention, count in sorted(intervention_counts.items())]
    lines.append(tabulate(intervention_table, headers=["  Intervention", "API Calls"], tablefmt="simple"))
    lines.append("")

    # Noise Conditions
    noise_counts: Counter[str] = Counter(item["noise_type"] for item in items)
    noise_table = [[noise_type, count] for noise_type, count in sorted(noise_counts.items())]
    lines.append(tabulate(noise_table, headers=["  Noise Type", "API Calls"], tablefmt="simple"))
    lines.append("")

    # Totals section — API calls, tokens, cost, runtime together
    total_target_calls = sum(model_counts.values())
    total_preproc_calls = sum(
        1 for item in items if item["intervention"] in PREPROC_INTERVENTIONS
    )

    target_in = cost_estimate.get("target_input_tokens", 0)
    target_out = cost_estimate.get("target_output_tokens", 0)
    preproc_in = cost_estimate.get("preproc_input_tokens", 0)
    preproc_out = cost_estimate.get("preproc_output_tokens", 0)

    t_in_cost = cost_estimate.get("target_input_cost", 0.0)
    t_out_cost = cost_estimate.get("target_output_cost", 0.0)
    p_in_cost = cost_estimate.get("preproc_input_cost", 0.0)
    p_out_cost = cost_estimate.get("preproc_output_cost", 0.0)

    lines.append("Estimates:")
    lines.append(f"                     {'API Calls':>12}  {'Tokens (in / out)':>24}  {'Cost (in + out)':>20}")
    lines.append(f"                     {'─' * 12}  {'─' * 24}  {'─' * 20}")
    lines.append(f"  Target model:      {total_target_calls:>12,}  {target_in:>10,} / {target_out:<12,}  ${t_in_cost:.2f} + ${t_out_cost:.2f} = ${cost_estimate['target_cost']:.2f}")
    lines.append(f"  Pre-processor:     {total_preproc_calls:>12,}  {preproc_in:>10,} / {preproc_out:<12,}  ${p_in_cost:.2f} + ${p_out_cost:.2f} = ${cost_estimate['preproc_cost']:.2f}")
    lines.append(f"                     {'─' * 12}  {'─' * 24}  {'─' * 20}")
    lines.append(f"  Total:             {total_target_calls + total_preproc_calls:>12,}  {target_in + preproc_in:>10,} / {target_out + preproc_out:<12,}  ${cost_estimate['total_cost']:.2f}")
    lines.append("")
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
            choice = input_fn("[Y]es to run, [N]o to abort, [M]odify filters (default: Y): ").strip().lower()
            if choice in ("", "y", "yes"):
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


def format_post_run_report(conn: Any) -> str:
    """Generate a post-run report comparing actual metrics against estimates.

    Queries results.db for completed runs and summarizes actual token counts,
    costs, timing, and pass rates. Shows per-model and per-intervention
    breakdowns.

    Args:
        conn: An open SQLite database connection.

    Returns:
        Multi-line formatted report string.
    """
    import sqlite3

    conn.row_factory = sqlite3.Row
    lines: list[str] = []
    lines.append("=== Post-Run Report ===")
    lines.append("")

    # Overall stats
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
        FROM experiment_runs
    """).fetchone()

    total = row["total"]
    completed = row["completed"]
    failed = row["failed"]
    pending_count = row["pending"]

    if total == 0:
        lines.append("No runs found in database.")
        return "\n".join(lines)

    lines.append(f"Runs: {completed:,} completed, {failed:,} failed, {pending_count:,} pending ({total:,} total)")
    lines.append("")

    # Per-model breakdown
    model_rows = conn.execute("""
        SELECT
            model,
            COUNT(*) as calls,
            SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed,
            COALESCE(SUM(prompt_tokens), 0) as input_tokens,
            COALESCE(SUM(completion_tokens), 0) as output_tokens,
            COALESCE(SUM(main_model_input_cost_usd), 0) + COALESCE(SUM(main_model_output_cost_usd), 0) as model_cost,
            AVG(ttft_ms) as avg_ttft,
            AVG(ttlt_ms) as avg_ttlt
        FROM experiment_runs
        WHERE status='completed'
        GROUP BY model
        ORDER BY model
    """).fetchall()

    if model_rows:
        model_table = []
        for r in model_rows:
            pass_rate = (r["passed"] / r["calls"] * 100) if r["calls"] > 0 else 0
            model_table.append([
                r["model"],
                "target",
                f"{r['calls']:,}",
                f"{r['input_tokens']:,} / {r['output_tokens']:,}",
                f"${r['model_cost']:.4f}",
                f"{pass_rate:.1f}%",
            ])

        # Pre-processor stats
        preproc_rows = conn.execute("""
            SELECT
                preproc_model,
                COUNT(*) as calls,
                COALESCE(SUM(preproc_input_tokens), 0) as input_tokens,
                COALESCE(SUM(preproc_output_tokens), 0) as output_tokens,
                COALESCE(SUM(preproc_cost_usd), 0) as preproc_cost,
                AVG(preproc_ttft_ms) as avg_ttft,
                AVG(preproc_ttlt_ms) as avg_ttlt
            FROM experiment_runs
            WHERE status='completed' AND preproc_model IS NOT NULL
            GROUP BY preproc_model
            ORDER BY preproc_model
        """).fetchall()

        for r in preproc_rows:
            model_table.append([
                f"  {r['preproc_model']}",
                "preproc",
                f"{r['calls']:,}",
                f"{r['input_tokens']:,} / {r['output_tokens']:,}",
                f"${r['preproc_cost']:.4f}",
                "--",
            ])

        lines.append("Models:")
        lines.append(tabulate(
            model_table,
            headers=["Model", "Role", "API Calls", "Tokens (in/out)", "Cost", "Pass Rate"],
            tablefmt="simple",
        ))
        lines.append("")

    # Timing summary
    timing_row = conn.execute("""
        SELECT
            AVG(ttft_ms) as avg_ttft,
            AVG(ttlt_ms) as avg_ttlt,
            MIN(ttft_ms) as min_ttft,
            MAX(ttft_ms) as max_ttft,
            AVG(preproc_ttft_ms) as avg_preproc_ttft,
            AVG(preproc_ttlt_ms) as avg_preproc_ttlt
        FROM experiment_runs
        WHERE status='completed'
    """).fetchone()

    if timing_row and timing_row["avg_ttft"] is not None:
        lines.append("Timing (completed runs):")
        lines.append(f"  Target TTFT:       avg {timing_row['avg_ttft']:.0f}ms  (min {timing_row['min_ttft']:.0f}ms, max {timing_row['max_ttft']:.0f}ms)")
        lines.append(f"  Target TTLT:       avg {timing_row['avg_ttlt']:.0f}ms")
        if timing_row["avg_preproc_ttft"] is not None:
            lines.append(f"  Pre-proc TTFT:     avg {timing_row['avg_preproc_ttft']:.0f}ms")
            lines.append(f"  Pre-proc TTLT:     avg {timing_row['avg_preproc_ttlt']:.0f}ms")
        lines.append("")

    # Per-intervention breakdown
    intervention_rows = conn.execute("""
        SELECT
            intervention,
            COUNT(*) as calls,
            SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed,
            COALESCE(SUM(total_cost_usd), 0) as cost
        FROM experiment_runs
        WHERE status='completed'
        GROUP BY intervention
        ORDER BY intervention
    """).fetchall()

    if intervention_rows:
        int_table = []
        for r in intervention_rows:
            pass_rate = (r["passed"] / r["calls"] * 100) if r["calls"] > 0 else 0
            int_table.append([
                r["intervention"], f"{r['calls']:,}", f"{pass_rate:.1f}%", f"${r['cost']:.4f}",
            ])
        lines.append("Interventions:")
        lines.append(tabulate(
            int_table,
            headers=["Intervention", "API Calls", "Pass Rate", "Cost"],
            tablefmt="simple",
        ))
        lines.append("")

    # Per-noise breakdown
    noise_rows = conn.execute("""
        SELECT
            noise_type,
            COUNT(*) as calls,
            SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed
        FROM experiment_runs
        WHERE status='completed'
        GROUP BY noise_type
        ORDER BY noise_type
    """).fetchall()

    if noise_rows:
        noise_table = []
        for r in noise_rows:
            pass_rate = (r["passed"] / r["calls"] * 100) if r["calls"] > 0 else 0
            noise_table.append([r["noise_type"], f"{r['calls']:,}", f"{pass_rate:.1f}%"])
        lines.append("Noise Conditions:")
        lines.append(tabulate(
            noise_table,
            headers=["Noise Type", "API Calls", "Pass Rate"],
            tablefmt="simple",
        ))
        lines.append("")

    # Cost totals
    cost_row = conn.execute("""
        SELECT
            COALESCE(SUM(main_model_input_cost_usd), 0) + COALESCE(SUM(main_model_output_cost_usd), 0) as target_cost,
            COALESCE(SUM(preproc_cost_usd), 0) as preproc_cost,
            COALESCE(SUM(total_cost_usd), 0) as total_cost,
            COALESCE(SUM(prompt_tokens), 0) as total_input_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_output_tokens,
            COALESCE(SUM(preproc_input_tokens), 0) as preproc_input_tokens,
            COALESCE(SUM(preproc_output_tokens), 0) as preproc_output_tokens
        FROM experiment_runs
        WHERE status='completed'
    """).fetchone()

    lines.append("Actual Totals:")
    lines.append(f"  Target tokens:     {cost_row['total_input_tokens']:,} in / {cost_row['total_output_tokens']:,} out")
    lines.append(f"  Pre-proc tokens:   {cost_row['preproc_input_tokens']:,} in / {cost_row['preproc_output_tokens']:,} out")
    lines.append(f"  Target cost:       ${cost_row['target_cost']:.4f}")
    lines.append(f"  Pre-proc cost:     ${cost_row['preproc_cost']:.4f}")
    lines.append(f"  Total cost:        ${cost_row['total_cost']:.4f}")

    return "\n".join(lines)
