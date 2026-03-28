"""Execution engine for the Linguistic Tax research toolkit.

Routes experiment matrix items through intervention strategies,
calls LLM APIs, grades responses inline, and manages resumability.
"""

import argparse
import json
import logging
import os
import random
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from tqdm import tqdm

from src.api_client import APIResponse, call_model, _validate_api_keys, _is_quota_error
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
from src.emphasis_converter import (
    load_emphasis_variant,
    apply_instruction_caps,
    apply_instruction_bold,
    lowercase_sentence_initial,
)

logger = logging.getLogger(__name__)

# Cache for preprocessor results: (prompt_id, noise_type, intervention, model) → (text, meta)
# Preprocessing is deterministic at temp=0, so repeated calls with the same
# input produce identical output. This eliminates ~80% of preproc API calls
# across 5 repetitions.
_preproc_cache: dict[tuple[str, ...], tuple[str, dict[str, Any]]] = {}
_preproc_cache_lock = threading.Lock()


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
    prompt_id: str = "",
    noise_type: str = "",
) -> tuple[str, dict[str, Any]]:
    """Apply the specified intervention strategy to a prompt.

    Routes to the appropriate intervention function based on the intervention
    type string from the experiment matrix.

    Args:
        prompt_text: The prompt text (may be noisy).
        intervention: One of the known intervention strategies.
        model: The main model identifier (used for pre-processor lookup).
        call_fn: Callable for making API calls (passed to pre-processor interventions).
        prompt_id: Prompt identifier (used for emphasis cache lookups).
        noise_type: Noise type string (e.g., "clean", "type_a_5pct", "type_b_esl").
            When provided and not starting with "type_a_", preproc interventions
            are skipped.

    Returns:
        A tuple of (processed_text, metadata_dict).

    Raises:
        ValueError: If intervention is not a known strategy.
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
        case "emphasis_bold" | "emphasis_caps" | "emphasis_quotes" | "emphasis_mixed" | "emphasis_aggressive_caps":
            converted = load_emphasis_variant(
                prompt_id=prompt_id,
                intervention=intervention,
            )
            return (converted, {})
        case "emphasis_instruction_caps":
            return (apply_instruction_caps(prompt_text), {})
        case "emphasis_instruction_bold":
            return (apply_instruction_bold(prompt_text), {})
        case "emphasis_lowercase_initial":
            return (lowercase_sentence_initial(prompt_text), {})
        case _:
            raise ValueError(f"Unknown intervention: {intervention}")


# ---------------------------------------------------------------------------
# Model ordering
# ---------------------------------------------------------------------------

def _order_by_model(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Order items by model with deterministic shuffle within groups.

    Groups items by model ID, shuffles each group independently using
    a seeded RNG for reproducibility, then concatenates all groups
    in sorted model order.

    Args:
        items: List of experiment matrix items.
        seed: Random seed for deterministic shuffling.

    Returns:
        Reordered list grouped by model, shuffled within each group.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item["model"], []).append(item)

    rng = random.Random(seed)
    result: list[dict[str, Any]] = []
    for model in sorted(groups):
        group = groups[model]
        rng.shuffle(group)
        result.extend(group)

    return result


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
    elif prompt_id.startswith("Mbpp/") or prompt_id.startswith("mbpp_"):
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
) -> bool:
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

    Returns:
        True if a quota/daily-limit error was detected (caller should
        skip remaining items for this model). False otherwise.
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

        # Apply intervention (with preproc caching for deterministic calls)
        intervention = item["intervention"]
        _preproc_interventions = {
            "pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only",
        }
        if intervention in _preproc_interventions:
            cache_key = (item["prompt_id"], item["noise_type"], intervention, item["model"])
            with _preproc_cache_lock:
                cached = _preproc_cache.get(cache_key)
            if cached is not None:
                processed_text, preproc_meta = cached
                preproc_meta = {**preproc_meta, "preproc_cached": True}
            else:
                processed_text, preproc_meta = apply_intervention(
                    prompt_text, intervention, item["model"], call_model,
                    prompt_id=item["prompt_id"],
                    noise_type=item["noise_type"],
                )
                with _preproc_cache_lock:
                    _preproc_cache[cache_key] = (processed_text, preproc_meta)
        else:
            processed_text, preproc_meta = apply_intervention(
                prompt_text, intervention, item["model"], call_model,
                prompt_id=item["prompt_id"],
                noise_type=item["noise_type"],
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
            "noisy_prompt_text": prompt_text,
            "prompt_text": processed_text,
            "prompt_tokens": response.input_tokens,
            "raw_output": response.text,
            "completion_tokens": response.output_tokens,
            "pass_fail": 1 if grade_result.passed else 0,
            "ttft_ms": response.ttft_ms,
            "ttlt_ms": response.ttlt_ms,
            "generation_ms": (response.ttlt_ms - response.ttft_ms) if response.ttft_ms and response.ttlt_ms else None,
            "preproc_model": preproc_meta.get("preproc_model"),
            "preproc_input_tokens": preproc_meta.get("preproc_input_tokens"),
            "preproc_output_tokens": preproc_meta.get("preproc_output_tokens"),
            "preproc_ttft_ms": preproc_meta.get("preproc_ttft_ms"),
            "preproc_ttlt_ms": preproc_meta.get("preproc_ttlt_ms"),
            "preproc_raw_output": preproc_meta.get("preproc_raw_output"),
            "preproc_failed": 1 if preproc_meta.get("preproc_failed") else 0,
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
            extracted_value=grade_result.extracted_value,
            expected_value=grade_result.expected_value,
            extracted_raw_match=grade_result.extracted_raw_match,
            extracted_code=grade_result.extracted_code,
        )

        logger.debug(
            "[%d/%d] %s | %s | %s | %s | %.0fms | $%.4f",
            index + 1, total, item["prompt_id"], item["noise_type"],
            item["intervention"], "PASS" if grade_result.passed else "FAIL",
            response.ttlt_ms, total_cost,
        )
        return False

    except Exception as e:
        is_quota = _is_quota_error(e)
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
        return is_quota


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def run_engine(
    args: argparse.Namespace,
    config: ExperimentConfig | None = None,
    show_summary: bool = True,
) -> None:
    """Main execution engine loop.

    Loads the experiment matrix, filters and orders items, then processes
    each through the full pipeline with resumability support.

    Args:
        args: Parsed CLI arguments.
        config: Optional experiment configuration (defaults to load_config()).
        show_summary: If False, skip printing the pre-execution summary.
            Used when the caller (e.g., pilot) has already shown it.
    """
    if config is None:
        from src.config_manager import load_config
        config = load_config()

    # Session management: create a new session unless --db is specified
    session_id = None
    if args.db:
        db_path = args.db
    else:
        from src.session import create_session, update_session_status
        session_id = create_session()
        db_path = f"{os.path.join('results', session_id, 'results.db')}"
        print(f"Session: {session_id}")

    conn = init_database(db_path)

    # Load prompts
    with open(config.prompts_path) as f:
        prompts_list = json.load(f)
    prompts_by_id = {p["problem_id"]: p for p in prompts_list}

    # Load experiment matrix
    with open(config.matrix_path) as f:
        matrix = json.load(f)

    # Remap matrix models to configured models if they don't match
    target_models = registry.target_models()
    target_ids = set(target_models)
    matrix_models = set(item["model"] for item in matrix)
    if not matrix_models.issubset(target_ids):
        from src.pilot import _remap_matrix_models
        matrix = _remap_matrix_models(matrix, target_models)

    # Further filter by --model arg if specified
    if args.model != "all":
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
    cost_estimate = estimate_cost(pending, prompts_path=config.prompts_path)
    runtime_seconds = estimate_runtime(pending)
    completed_count = len(completed_runs)
    total_count = len(matrix)

    if show_summary:
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
    plan_path = (
        os.path.join("results", session_id, "execution_plan.json")
        if session_id
        else "results/execution_plan.json"
    )
    save_execution_plan(pending, cost_estimate, runtime_seconds, filters=filters, output_path=plan_path)

    # Validate API keys and preflight check each model
    unique_models = set(item["model"] for item in pending)
    for model in unique_models:
        _validate_api_keys(model)

    # Also check preproc models
    preproc_models = {registry.get_preproc(m) for m in unique_models}
    preproc_models.discard(None)
    for model in preproc_models:
        _validate_api_keys(model)

    # Preflight: test each model with actual experiment parameters
    print("Preflight checks...")
    all_check_models = unique_models | preproc_models
    for model in sorted(all_check_models):
        try:
            call_model(
                model=model,
                system=None,
                user_message="Respond with OK.",
                max_tokens=10,
                temperature=config.temperature,
            )
            print(f"  OK: {model}")
        except Exception as e:
            err_msg = str(e).lower()
            if "temperature" in err_msg or "max_completion_tokens" in err_msg or "max_tokens" in err_msg:
                # Parameter compatibility — call_model handles this at runtime
                print(f"  OK: {model} (parameter auto-adjusted)")
            else:
                print(f"  FAILED: {model}")
                print(f"    {e}")
                print("\nFix the issue and re-run, or remove this model from your config.")
                conn.close()
                sys.exit(1)
    print()

    # Partition items by model for parallel execution
    items_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pending:
        items_by_model[item["model"]].append(item)

    model_count = len(items_by_model)
    total = len(pending)

    if model_count > 1:
        print(f"Running {model_count} models in parallel: {', '.join(sorted(items_by_model))}")

    # Thread-safe shared state
    lock = threading.Lock()
    cost_so_far = 0.0
    tokens_in = 0
    tokens_out = 0
    pass_count = 0
    completed_count_run = 0
    quota_exhausted_models: set[str] = set()
    skipped_count = 0
    interrupted = threading.Event()

    def _fmt_tokens(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return str(n)

    def _process_model_items(
        model_id: str,
        items: list[dict[str, Any]],
        pbar: tqdm,
    ) -> None:
        """Process all items for a single model sequentially.

        Each model gets its own DB connection for thread safety.
        Shared counters are updated under the lock.
        """
        nonlocal cost_so_far, tokens_in, tokens_out, pass_count
        nonlocal completed_count_run, skipped_count

        model_conn = sqlite3.connect(db_path, check_same_thread=False)
        model_conn.execute("PRAGMA journal_mode=WAL")
        model_conn.execute("PRAGMA foreign_keys=ON")

        try:
            for item in items:
                if interrupted.is_set():
                    break

                model = item["model"]

                with lock:
                    if model in quota_exhausted_models:
                        skipped_count += 1
                        pbar.update(1)
                        continue

                    preproc_model = registry.get_preproc(model)
                    if (preproc_model and preproc_model in quota_exhausted_models
                            and item["intervention"] in (
                                "pre_proc_sanitize", "pre_proc_sanitize_compress",
                                "compress_only")):
                        skipped_count += 1
                        pbar.update(1)
                        continue

                quota_hit = _process_item(
                    item, model_conn, prompts_by_id, config, 0, total,
                )

                if quota_hit:
                    with lock:
                        quota_exhausted_models.add(model)
                        if preproc_model:
                            quota_exhausted_models.add(preproc_model)
                    tqdm.write(
                        f"  Quota exhausted for {model} — skipping remaining items."
                    )

                # Read metrics from the row we just wrote
                row = model_conn.execute(
                    "SELECT total_cost_usd, pass_fail, prompt_tokens, "
                    "completion_tokens, ttlt_ms, status "
                    "FROM experiment_runs WHERE run_id = ?",
                    (make_run_id(item),),
                ).fetchone()

                with lock:
                    last_result = "?"
                    last_ms = 0.0
                    if row:
                        if row[5] == "failed":
                            last_result = "ERR"
                        elif row[5] == "completed":
                            if row[0]:
                                cost_so_far += row[0]
                            if row[2]:
                                tokens_in += row[2]
                            if row[3]:
                                tokens_out += row[3]
                            completed_count_run += 1
                            if row[1] is not None:
                                if row[1]:
                                    pass_count += 1
                                last_result = "PASS" if row[1] else "FAIL"
                        last_ms = row[4] or 0.0

                    pass_rate = (pass_count / completed_count_run * 100) if completed_count_run > 0 else 0
                    pbar.set_postfix_str(
                        f"pass={pass_rate:.1f}% | cost=${cost_so_far:.2f} | "
                        f"last={last_result} {last_ms:.0f}ms | "
                        f"tokens={_fmt_tokens(tokens_in)}/{_fmt_tokens(tokens_out)}"
                    )
                    pbar.update(1)
        finally:
            model_conn.close()

    try:
        with tqdm(total=total, desc="Experiments", unit="item") as pbar:
            if model_count == 0:
                pass  # Nothing to process
            elif model_count == 1:
                # Single model: run in main thread (simpler, no overhead)
                model_id = next(iter(items_by_model))
                _process_model_items(model_id, items_by_model[model_id], pbar)
            else:
                # Multiple models: run each model in its own thread
                with ThreadPoolExecutor(max_workers=model_count) as executor:
                    futures = {
                        executor.submit(
                            _process_model_items, model_id, items, pbar,
                        ): model_id
                        for model_id, items in items_by_model.items()
                    }
                    try:
                        for future in as_completed(futures):
                            model_id = futures[future]
                            exc = future.exception()
                            if exc is not None:
                                tqdm.write(f"  Error in {model_id} worker: {exc}")
                    except KeyboardInterrupt:
                        interrupted.set()
                        raise

    except KeyboardInterrupt:
        print("\nInterrupted. Saving progress...")
        if session_id:
            update_session_status(db_path, "canceled")
        print(f"Completed {completed_count_run} of {total} items.")
        sys.exit(130)

    # Update session status
    if session_id:
        failed_count_pre = total - completed_count_run - skipped_count
        if failed_count_pre > 0:
            update_session_status(db_path, "partial")
        else:
            update_session_status(db_path, "completed")

    # Report quota-exhausted models
    if quota_exhausted_models:
        print(f"\nQuota exhausted for: {', '.join(sorted(quota_exhausted_models))}")
        print(f"  {skipped_count} items skipped.")
        print("  Re-run with `propt run --retry-failed` after the quota resets.")

    # Post-execution summary
    failed_count = total - completed_count_run - skipped_count
    pass_rate_final = (pass_count / completed_count_run * 100) if completed_count_run > 0 else 0
    print(f"\n{'─' * 50}")
    print(f"Complete: {completed_count_run:,} items processed")
    if failed_count > 0:
        print(f"  Failed:  {failed_count:,}")
    if skipped_count > 0:
        print(f"  Skipped: {skipped_count:,} (quota exhausted)")
    print(f"  Pass rate: {pass_rate_final:.1f}%")
    print(f"  Cost:      ${cost_so_far:.2f}")
    print(f"  Tokens:    {_fmt_tokens(tokens_in)} in / {_fmt_tokens(tokens_out)} out")
    print(f"\nNext steps:")
    print(f"  propt report              — detailed post-run report")
    if failed_count > 0:
        print(f"  propt run --retry-failed  — reprocess {failed_count:,} failed items")
    print(f"  propt clean               — reset and start fresh")
    print(f"{'─' * 50}")
    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _check_config_exists() -> None:
    """Exit with guidance if no config file is found."""
    if find_config_path() is None:
        logger.error(
            "No config found. Run `python src/cli.py setup` to configure "
            "the experiment toolkit before running experiments."
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
    from src.env_manager import load_env

    parser = _build_parser()
    args = parser.parse_args()

    load_env()
    _check_config_exists()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    run_engine(args)


if __name__ == "__main__":
    main()
