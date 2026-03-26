"""Execution engine for the Linguistic Tax research toolkit.

Routes experiment matrix items through intervention strategies,
calls LLM APIs, grades responses inline, and manages resumability.
"""

import argparse
import json
import logging
import random
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from tqdm import tqdm

from src.api_client import APIResponse, call_model, _validate_api_keys
from src.config_manager import find_config_path, CONFIG_FILENAME
from src.config import (
    ExperimentConfig,
    MAX_TOKENS_BY_BENCHMARK,
    derive_seed,
)
from src.model_registry import registry
from src.db import init_database, insert_run, query_runs, save_grade_result
from src.execution_summary import (
    estimate_cost,
    estimate_runtime,
    format_summary,
    confirm_execution,
    save_execution_plan,
    count_completed,
)
from src.grade_results import grade_run
from src.noise_generator import inject_type_a_noise, inject_type_b_noise
from src.prompt_compressor import (
    build_self_correct_prompt,
    sanitize,
    sanitize_and_compress,
)
from src.prompt_repeater import repeat_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic run ID
# ---------------------------------------------------------------------------

def make_run_id(item: dict[str, Any]) -> str:
    """Build a deterministic run ID from experiment matrix item fields.

    The run ID uniquely identifies a single experimental condition + repetition.
    It is used for resumability: completed run IDs are skipped on restart.

    Args:
        item: An experiment matrix item dictionary.

    Returns:
        A pipe-separated string identifying the run.
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


# ---------------------------------------------------------------------------
# Intervention router
# ---------------------------------------------------------------------------

def apply_intervention(
    prompt_text: str,
    intervention: str,
    model: str,
    call_fn: Callable[..., Any],
) -> tuple[str, dict[str, Any]]:
    """Apply the specified intervention strategy to a prompt.

    Routes to the appropriate intervention function based on the intervention
    type string from the experiment matrix.

    Args:
        prompt_text: The prompt text (may be noisy).
        intervention: One of the 5 intervention strategies.
        model: The main model identifier (used for pre-processor lookup).
        call_fn: Callable for making API calls (passed to pre-processor interventions).

    Returns:
        A tuple of (processed_text, metadata_dict).

    Raises:
        ValueError: If intervention is not one of the 5 known strategies.
    """
    match intervention:
        case "raw":
            return (prompt_text, {})
        case "self_correct":
            return (build_self_correct_prompt(prompt_text), {})
        case "prompt_repetition":
            return (repeat_prompt(prompt_text), {})
        case "pre_proc_sanitize":
            return sanitize(prompt_text, model, call_fn)
        case "pre_proc_sanitize_compress":
            return sanitize_and_compress(prompt_text, model, call_fn)
        case "compress_only":
            return sanitize_and_compress(prompt_text, model, call_fn)
        case _:
            raise ValueError(f"Unknown intervention: {intervention}")


# ---------------------------------------------------------------------------
# Model ordering
# ---------------------------------------------------------------------------

def _order_by_model(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Order items by model provider with deterministic shuffle within groups.

    Groups Claude items first and Gemini items second. Each group is
    shuffled independently using a seeded RNG for reproducibility.

    Args:
        items: List of experiment matrix items.
        seed: Random seed for deterministic shuffling.

    Returns:
        Reordered list with Claude items first, Gemini items second.
    """
    claude_items = [x for x in items if x["model"].startswith("claude")]
    gemini_items = [x for x in items if x["model"].startswith("gemini")]

    rng = random.Random(seed)
    rng.shuffle(claude_items)
    rng.shuffle(gemini_items)

    return claude_items + gemini_items


# ---------------------------------------------------------------------------
# Benchmark detection
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


# ---------------------------------------------------------------------------
# Noise application
# ---------------------------------------------------------------------------

_NOISE_TYPE_MAP: dict[str, tuple[str, str | None]] = {
    "clean": ("clean", None),
    "type_a_5pct": ("type_a", "5"),
    "type_a_10pct": ("type_a", "10"),
    "type_a_20pct": ("type_a", "20"),
    "type_b_mandarin": ("type_b", "mandarin"),
    "type_b_spanish": ("type_b", "spanish"),
    "type_b_japanese": ("type_b", "japanese"),
    "type_b_mixed": ("type_b", "mixed"),
}

_RATE_MAP: dict[str, float] = {
    "5": 0.05,
    "10": 0.10,
    "20": 0.20,
}


def _apply_noise(
    prompt_text: str,
    noise_type: str,
    prompt_id: str,
    answer_type: str,
    base_seed: int,
) -> str:
    """Apply noise to clean prompt text based on noise_type from the matrix.

    Args:
        prompt_text: The clean prompt text.
        noise_type: Noise type from the experiment matrix.
        prompt_id: Prompt identifier for seed derivation.
        answer_type: "code" or "numeric" for keyword protection.
        base_seed: Base seed for deterministic noise generation.

    Returns:
        Noisy prompt text (or original if noise_type is "clean").
    """
    if noise_type == "clean":
        return prompt_text

    category, level = _NOISE_TYPE_MAP.get(noise_type, ("unknown", None))

    if category == "type_a" and level is not None:
        seed = derive_seed(base_seed, prompt_id, "type_a", level)
        rate = _RATE_MAP[level]
        return inject_type_a_noise(prompt_text, error_rate=rate, seed=seed, answer_type=answer_type)
    elif category == "type_b" and level is not None:
        seed = derive_seed(base_seed, prompt_id, "type_b", level)
        return inject_type_b_noise(prompt_text, l1_source=level, seed=seed)
    else:
        logger.warning("Unknown noise_type: %s, returning original text", noise_type)
        return prompt_text


# ---------------------------------------------------------------------------
# Item processing
# ---------------------------------------------------------------------------

def _process_item(
    item: dict[str, Any],
    conn: Any,
    prompts_by_id: dict[str, dict[str, Any]],
    config: ExperimentConfig,
    index: int,
    total: int,
) -> None:
    """Process a single experiment matrix item through the full pipeline.

    Applies noise, routes through intervention, calls the LLM API,
    grades the response inline, and writes results to the database.

    Args:
        item: Experiment matrix item dictionary.
        conn: Open SQLite database connection.
        prompts_by_id: Mapping of prompt_id to prompt record.
        config: Experiment configuration.
        index: Zero-based index of current item in the processing queue.
        total: Total number of items to process.
    """
    run_id = make_run_id(item)
    benchmark = _get_benchmark(item["prompt_id"])

    try:
        prompt_record = prompts_by_id[item["prompt_id"]]
        clean_text = prompt_record["prompt_text"]
        answer_type = prompt_record.get("answer_type", "code")

        # Apply noise to clean text
        prompt_text = _apply_noise(
            clean_text, item["noise_type"], item["prompt_id"],
            answer_type, config.base_seed,
        )

        # Apply intervention
        processed_text, preproc_meta = apply_intervention(
            prompt_text, item["intervention"], item["model"], call_model,
        )

        # Determine max tokens
        max_tokens = MAX_TOKENS_BY_BENCHMARK.get(benchmark, 2048)

        # Call the LLM API
        response: APIResponse = call_model(
            model=item["model"],
            system=None,
            user_message=processed_text,
            max_tokens=max_tokens,
            temperature=config.temperature,
        )

        # Compute costs
        main_input_cost = registry.compute_cost(item["model"], response.input_tokens, 0)
        main_output_cost = registry.compute_cost(item["model"], 0, response.output_tokens)

        preproc_cost = 0.0
        if "preproc_model" in preproc_meta:
            preproc_cost = registry.compute_cost(
                preproc_meta["preproc_model"],
                preproc_meta.get("preproc_input_tokens", 0),
                preproc_meta.get("preproc_output_tokens", 0),
            )

        total_cost = main_input_cost + main_output_cost + preproc_cost

        # Grade inline
        grade_result = grade_run(response.text, prompt_record)

        # Build run_data
        run_data: dict[str, Any] = {
            "run_id": run_id,
            "prompt_id": item["prompt_id"],
            "benchmark": benchmark,
            "noise_type": item["noise_type"],
            "noise_level": str(item["noise_level"]) if item["noise_level"] is not None else None,
            "intervention": item["intervention"],
            "model": item["model"],
            "repetition": item["repetition_num"],
            "prompt_text": processed_text,
            "prompt_tokens": response.input_tokens,
            "optimized_tokens": preproc_meta.get("preproc_output_tokens"),
            "raw_output": response.text,
            "completion_tokens": response.output_tokens,
            "pass_fail": 1 if grade_result.passed else 0,
            "ttft_ms": response.ttft_ms,
            "ttlt_ms": response.ttlt_ms,
            "preproc_model": preproc_meta.get("preproc_model"),
            "preproc_input_tokens": preproc_meta.get("preproc_input_tokens"),
            "preproc_output_tokens": preproc_meta.get("preproc_output_tokens"),
            "preproc_ttft_ms": preproc_meta.get("preproc_ttft_ms"),
            "preproc_ttlt_ms": preproc_meta.get("preproc_ttlt_ms"),
            "main_model_input_cost_usd": main_input_cost,
            "main_model_output_cost_usd": main_output_cost,
            "preproc_cost_usd": preproc_cost,
            "total_cost_usd": total_cost,
            "temperature": config.temperature,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }

        insert_run(conn, run_data)

        # Save detailed grading results
        save_grade_result(
            conn, run_id, grade_result.passed, grade_result.fail_reason,
            grade_result.stdout, grade_result.stderr,
            grade_result.execution_time_ms, grade_result.extraction_method,
        )

        logger.info(
            "[%d/%d] %s | %s | %s | %s | %.0fms | $%.4f",
            index + 1, total, item["prompt_id"], item["noise_type"],
            item["intervention"], "PASS" if grade_result.passed else "FAIL",
            response.ttlt_ms, total_cost,
        )

    except Exception as e:
        logger.error(
            "[%d/%d] %s | %s | %s | FAILED: %s",
            index + 1, total, item["prompt_id"], item["noise_type"],
            item["intervention"], str(e),
        )
        # Write failed run to DB
        run_data = {
            "run_id": run_id,
            "prompt_id": item["prompt_id"],
            "benchmark": benchmark,
            "noise_type": item["noise_type"],
            "noise_level": str(item["noise_level"]) if item["noise_level"] is not None else None,
            "intervention": item["intervention"],
            "model": item["model"],
            "repetition": item["repetition_num"],
            "temperature": config.temperature,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
        }
        try:
            insert_run(conn, run_data)
        except Exception:
            logger.exception("Failed to insert failed run record for %s", run_id)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def run_engine(args: argparse.Namespace, config: ExperimentConfig | None = None) -> None:
    """Main execution engine loop.

    Loads the experiment matrix, filters and orders items, then processes
    each through the full pipeline with resumability support.

    Args:
        args: Parsed CLI arguments.
        config: Optional experiment configuration (defaults to ExperimentConfig()).
    """
    config = config or ExperimentConfig()

    # Override DB path if specified
    db_path = args.db if args.db else config.results_db_path
    conn = init_database(db_path)

    # Load prompts
    with open(config.prompts_path) as f:
        prompts_list = json.load(f)
    prompts_by_id = {p["problem_id"]: p for p in prompts_list}

    # Load experiment matrix
    with open(config.matrix_path) as f:
        matrix = json.load(f)

    # Validate and filter by model
    if args.model != "all":
        target_ids = set(registry.target_models())
        if args.model in target_ids:
            # Exact model_id match
            matrix = [item for item in matrix if item["model"] == args.model]
        else:
            # Treat as provider prefix
            matrix = [
                item for item in matrix
                if item["model"].startswith(args.model)
            ]
            if not matrix:
                available = ", ".join(sorted(target_ids))
                raise SystemExit(
                    f"Unknown model or prefix '{args.model}'. "
                    f"Available models: {available}"
                )

    # Get completed run_ids for resumability
    completed_runs = {r["run_id"] for r in query_runs(conn, status="completed")}
    logger.info("Found %d completed runs in database", len(completed_runs))

    # Get failed run_ids
    failed_runs = {r["run_id"] for r in query_runs(conn, status="failed")}

    # Filter to pending items: exclude completed and failed
    skip_ids = completed_runs | failed_runs
    pending = [item for item in matrix if make_run_id(item) not in skip_ids]

    # Handle --retry-failed: re-add failed items after clearing old rows
    if args.retry_failed and failed_runs:
        # Delete old failed rows to avoid IntegrityError on re-insert
        for failed_id in failed_runs:
            conn.execute(
                "DELETE FROM experiment_runs WHERE run_id = ?", (failed_id,)
            )
        conn.commit()
        logger.info("Cleared %d failed runs for retry", len(failed_runs))

        # Add back items whose run_id was in the failed set
        failed_items = [
            item for item in matrix if make_run_id(item) in failed_runs
        ]
        pending.extend(failed_items)

    # Filter by intervention
    if hasattr(args, "intervention") and args.intervention:
        pending = [
            item for item in pending if item["intervention"] == args.intervention
        ]

    # Order by model (claude first, gemini second, shuffled within)
    pending = _order_by_model(pending, config.base_seed)

    # Apply limit
    if args.limit is not None:
        pending = pending[: args.limit]

    logger.info("Processing %d items", len(pending))

    # Confirmation gate
    cost_estimate = estimate_cost(pending)
    runtime_seconds = estimate_runtime(pending)
    completed_count = len(completed_runs)
    total_count = len(matrix)
    summary = format_summary(
        pending, completed_count, total_count, cost_estimate, runtime_seconds
    )

    # --dry-run: show summary and exit
    if args.dry_run:
        print(summary)
        conn.close()
        return

    # Confirmation prompt
    yes_flag = getattr(args, "yes", False)
    budget_flag = getattr(args, "budget", None)

    decision = confirm_execution(
        summary,
        yes=yes_flag,
        budget=budget_flag,
        estimated_cost=cost_estimate["total_cost"],
    )

    if decision == "no":
        print("Aborted.")
        conn.close()
        return
    elif decision == "modify":
        print(
            "Modify filters by re-running with different "
            "--model, --limit, or --intervention flags."
        )
        print("Use `propt set-config` for full configuration changes.")
        conn.close()
        return

    # Save execution plan before running
    filters: dict[str, Any] = {"model": args.model, "limit": args.limit}
    if hasattr(args, "intervention"):
        filters["intervention"] = args.intervention
    save_execution_plan(pending, cost_estimate, runtime_seconds, filters=filters)

    # Validate API keys for models in pending items
    unique_models = set(item["model"] for item in pending)
    for model in unique_models:
        _validate_api_keys(model)

    # Process items with tqdm progress bar
    total = len(pending)
    cost_so_far = 0.0
    try:
        with tqdm(total=total, desc="Experiments", unit="item") as pbar:
            for i, item in enumerate(pending):
                _process_item(item, conn, prompts_by_id, config, i, total)
                # Query cost from last inserted row
                row = conn.execute(
                    "SELECT total_cost_usd FROM experiment_runs WHERE run_id = ?",
                    (make_run_id(item),),
                ).fetchone()
                if row and row[0]:
                    cost_so_far += row[0]
                pbar.set_postfix(cost=f"${cost_so_far:.2f}")
                pbar.update(1)
    except KeyboardInterrupt:
        print("\nInterrupted. Saving progress...")
        conn.close()
        print(f"Completed {i} of {total} items.")
        sys.exit(130)

    logger.info("Engine complete: %d items processed", total)
    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _check_config_exists() -> None:
    """Exit with guidance if no config file is found."""
    if find_config_path() is None:
        logger.error(
            "No config found. Run `python src/cli.py setup` to configure "
            "the slicer before running experiments."
        )
        sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the execution engine CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Execution engine for the Linguistic Tax research toolkit.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        help="Model ID, provider prefix (e.g. claude, gemini), or 'all' (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N items (default: no limit)",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Reprocess items with status='failed'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without making API calls",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Override path to results database",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-accept without prompting",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="Exit non-zero if cost exceeds threshold",
    )
    parser.add_argument(
        "--intervention",
        type=str,
        default=None,
        help="Filter to specific intervention",
    )
    return parser


def main() -> None:
    """CLI entry point for the execution engine."""
    _check_config_exists()
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    run_engine(args)


if __name__ == "__main__":
    main()
