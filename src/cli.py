"""CLI entry point for the Linguistic Tax research toolkit.

Provides argparse-based subcommand routing with setup, config viewing,
config modification, validation, diff, and model listing subcommands.
"""

import argparse
import logging
import sys

from src.config import INTERVENTIONS
from src.config_commands import (
    handle_show_config,
    handle_set_config,
    handle_reset_config,
    handle_validate,
    handle_diff,
    handle_list_models,
    property_name_completer,
)
from src.setup_wizard import run_setup_wizard


def _check_config_exists() -> None:
    """Exit with guidance if no config file is found."""
    from src.config_manager import find_config_path

    if find_config_path() is None:
        print(
            "No config found. Run `propt setup` to configure "
            "the toolkit before running experiments."
        )
        sys.exit(1)


def handle_run(args: argparse.Namespace) -> None:
    """Handle the 'run' subcommand by delegating to run_engine.

    Args:
        args: Parsed CLI arguments including model, limit, flags.
    """
    _check_config_exists()
    from src.run_experiment import run_engine

    run_engine(args)


def handle_pilot(args: argparse.Namespace) -> None:
    """Handle the 'pilot' subcommand by delegating to run_pilot.

    Args:
        args: Parsed CLI arguments including yes, budget, dry_run.
    """
    _check_config_exists()
    from src.pilot import run_pilot

    run_pilot(
        budget=args.budget if args.budget is not None else 200.0,
        db_path=args.db,
        yes=args.yes,
        dry_run=args.dry_run,
    )


def build_cli() -> argparse.ArgumentParser:
    """Create the top-level argument parser with all subcommands.

    Returns:
        Configured ArgumentParser with setup and config subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="propt",
        description="propt - Linguistic Tax research toolkit CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- setup (existing) ---
    setup_parser = subparsers.add_parser(
        "setup",
        help="Run the guided setup wizard to configure the experiment toolkit",
    )
    setup_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Write default config without prompting (for CI/scripting)",
    )
    setup_parser.set_defaults(func=run_setup_wizard)

    # --- show-config ---
    show_parser = subparsers.add_parser(
        "show-config", help="Display current configuration"
    )
    prop_arg = show_parser.add_argument(
        "property", nargs="?", default=None, help="Show single property value"
    )
    prop_arg.completer = property_name_completer  # type: ignore[attr-defined]
    show_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    show_parser.add_argument(
        "--changed", action="store_true", help="Show only overridden properties"
    )
    show_parser.add_argument(
        "--verbose", action="store_true", help="Include property descriptions"
    )
    show_parser.set_defaults(func=handle_show_config)

    # --- set-config ---
    set_parser = subparsers.add_parser(
        "set-config", help="Set configuration properties"
    )
    set_parser.add_argument(
        "pairs", nargs="*", help="Key-value pairs: property value [property value ...]"
    )
    set_parser.set_defaults(func=handle_set_config)

    # --- reset-config ---
    reset_parser = subparsers.add_parser(
        "reset-config", help="Reset properties to defaults"
    )
    props_arg = reset_parser.add_argument(
        "properties", nargs="*", help="Property names to reset"
    )
    props_arg.completer = property_name_completer  # type: ignore[attr-defined]
    reset_parser.add_argument(
        "--all", action="store_true", help="Reset all properties to defaults"
    )
    reset_parser.set_defaults(func=handle_reset_config)

    # --- validate ---
    validate_parser = subparsers.add_parser(
        "validate", help="Validate current configuration"
    )
    validate_parser.set_defaults(func=handle_validate)

    # --- diff ---
    diff_parser = subparsers.add_parser(
        "diff", help="Show properties changed from defaults"
    )
    diff_parser.set_defaults(func=handle_diff)

    # --- list-models ---
    models_parser = subparsers.add_parser(
        "list-models", help="List available models with pricing"
    )
    models_parser.add_argument(
        "--json", action="store_true", default=False,
        help="Output as JSON for programmatic use"
    )
    models_parser.set_defaults(func=handle_list_models)

    # --- run ---
    run_parser = subparsers.add_parser(
        "run", help="Run experiments with confirmation gate"
    )
    run_parser.add_argument(
        "--model",
        choices=["claude", "gemini", "gpt", "openrouter", "all"],
        default="all",
        help="Filter to model provider",
    )
    run_parser.add_argument(
        "--limit", type=int, default=None, help="Stop after N items"
    )
    run_parser.add_argument(
        "--retry-failed", action="store_true", help="Reprocess failed items"
    )
    run_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    run_parser.add_argument(
        "--yes", action="store_true", help="Auto-accept without prompting"
    )
    run_parser.add_argument(
        "--budget", type=float, default=None,
        help="Exit non-zero if cost exceeds threshold",
    )
    run_parser.add_argument(
        "--dry-run", action="store_true", help="Show summary only, do not execute"
    )
    run_parser.add_argument(
        "--intervention", type=str, choices=list(INTERVENTIONS), default=None,
        help="Filter to specific intervention",
    )
    run_parser.set_defaults(func=handle_run)

    # --- pilot ---
    pilot_parser = subparsers.add_parser(
        "pilot", help="Run pilot validation with confirmation gate"
    )
    pilot_parser.add_argument(
        "--yes", action="store_true", help="Auto-accept without prompting"
    )
    pilot_parser.add_argument(
        "--budget", type=float, default=None,
        help="Exit non-zero if cost exceeds threshold",
    )
    pilot_parser.add_argument(
        "--dry-run", action="store_true", help="Show summary only, do not execute"
    )
    pilot_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    pilot_parser.set_defaults(func=handle_pilot)

    # --- report ---
    report_parser = subparsers.add_parser(
        "report", help="Show post-run report with actual metrics"
    )
    report_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    report_parser.add_argument(
        "--session", type=str, default=None, help="Session ID (full or prefix)"
    )
    report_parser.add_argument(
        "--benchmark", action="store_true",
        help="Show per-benchmark cross-tabulation with noise types and baselines"
    )
    fmt_group = report_parser.add_mutually_exclusive_group()
    fmt_group.add_argument(
        "--json", action="store_const", const="json", dest="output_format",
        help="Output as structured JSON"
    )
    fmt_group.add_argument(
        "--csv", action="store_const", const="csv", dest="output_format",
        help="Output as CSV tables"
    )
    fmt_group.add_argument(
        "--markdown", action="store_const", const="markdown", dest="output_format",
        help="Output as GitHub-flavored markdown"
    )
    report_parser.set_defaults(func=handle_report, output_format="text")

    # --- clean ---
    clean_parser = subparsers.add_parser(
        "clean", help="Delete experiment results and start fresh"
    )
    clean_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    clean_parser.add_argument(
        "--session", type=str, default=None, help="Delete a specific session"
    )
    clean_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt"
    )
    clean_parser.set_defaults(func=handle_clean)

    # --- regrade ---
    regrade_parser = subparsers.add_parser(
        "regrade", help="Re-grade existing results with updated grading logic"
    )
    regrade_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    regrade_parser.add_argument(
        "--session", type=str, default=None, help="Session ID (full or prefix)"
    )
    regrade_parser.set_defaults(func=handle_regrade)

    # --- inspect ---
    inspect_parser = subparsers.add_parser(
        "inspect", help="Show full details for a specific run"
    )
    inspect_parser.add_argument(
        "run_id", help="The run_id to inspect"
    )
    inspect_parser.add_argument(
        "--db", type=str, default=None, help="Override database path"
    )
    inspect_parser.add_argument(
        "--session", type=str, default=None, help="Session ID (full or prefix)"
    )
    inspect_parser.set_defaults(func=handle_inspect)

    # --- list (sessions) ---
    list_parser = subparsers.add_parser(
        "list", help="List all experiment sessions"
    )
    list_parser.set_defaults(func=handle_list)

    # --- list-runs ---
    list_runs_parser = subparsers.add_parser(
        "list-runs", help="List individual runs within a session"
    )
    list_runs_parser.add_argument(
        "session", help="Session ID (full or prefix)"
    )
    list_runs_parser.add_argument(
        "--model", type=str, default=None, help="Filter by model name"
    )
    list_runs_parser.add_argument(
        "--benchmark", type=str, default=None, help="Filter by benchmark"
    )
    list_runs_parser.add_argument(
        "--intervention", type=str, default=None, help="Filter by intervention"
    )
    list_runs_parser.add_argument(
        "--failed", action="store_true", help="Show only failed runs"
    )
    list_runs_parser.set_defaults(func=handle_list_runs)

    # --- delete-results ---
    delete_parser = subparsers.add_parser(
        "delete-results", help="Delete a session and its results"
    )
    delete_parser.add_argument(
        "session", help="Session ID (full or prefix)"
    )
    delete_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt"
    )
    delete_parser.set_defaults(func=handle_delete_results)

    # --- compare-results ---
    compare_parser = subparsers.add_parser(
        "compare-results", help="Compare two sessions side by side"
    )
    compare_parser.add_argument(
        "session1", help="First session ID"
    )
    compare_parser.add_argument(
        "session2", help="Second session ID"
    )
    compare_parser.set_defaults(func=handle_compare_results)

    # --- argcomplete ---
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    return parser


def _resolve_db_path(args: argparse.Namespace) -> str:
    """Resolve the database path from --db, --session, or latest session.

    Priority: --db > --session > latest session > config default.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Path to the results database.
    """
    if getattr(args, "db", None):
        return args.db

    session_id = getattr(args, "session", None)
    if session_id is not None:
        from src.session import resolve_session
        return resolve_session(session_id)

    # Default: try latest session, fall back to config
    try:
        from src.session import resolve_session
        return resolve_session(None)
    except ValueError:
        from src.config_manager import load_config
        config = load_config()
        return config.results_db_path


def handle_report(args: argparse.Namespace) -> None:
    """Show post-run report with actual metrics from results database."""
    from src.db import init_database
    from src.execution_summary import format_post_run_report

    db_path = _resolve_db_path(args)
    conn = init_database(db_path)
    print(format_post_run_report(conn, benchmark=args.benchmark, output_format=args.output_format))
    conn.close()


def handle_inspect(args: argparse.Namespace) -> None:
    """Show full details for a specific experiment run."""
    import sqlite3
    from src.db import init_database

    db_path_str = _resolve_db_path(args)
    conn = init_database(db_path_str)
    conn.row_factory = sqlite3.Row

    # Query experiment run with LEFT JOIN on grading_details
    row = conn.execute(
        """SELECT e.*, g.fail_reason, g.extraction_method
           FROM experiment_runs e
           LEFT JOIN grading_details g ON e.run_id = g.run_id
           WHERE e.run_id = ?""",
        (args.run_id,),
    ).fetchone()

    if row is None:
        conn.close()
        # Search across all sessions for this run_id
        from src.session import list_sessions
        for session in list_sessions():
            if session["db_path"] == db_path_str:
                continue  # Already checked
            try:
                conn = sqlite3.connect(session["db_path"])
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """SELECT e.*, g.fail_reason, g.extraction_method
                       FROM experiment_runs e
                       LEFT JOIN grading_details g ON e.run_id = g.run_id
                       WHERE e.run_id = ?""",
                    (args.run_id,),
                ).fetchone()
                if row is not None:
                    break
                conn.close()
            except Exception:
                continue

    if row is None:
        print(f"Run not found: {args.run_id}")
        return

    r = dict(row)

    # --- Run Info ---
    print("--- Run Info ---")
    print(f"  run_id:       {r['run_id']}")
    print(f"  prompt_id:    {r['prompt_id']}")
    print(f"  benchmark:    {r['benchmark']}")
    print(f"  model:        {r['model']}")
    print(f"  intervention: {r['intervention']}")
    print(f"  noise_type:   {r['noise_type']}")
    print(f"  noise_level:  {r.get('noise_level', '--')}")
    print(f"  repetition:   {r['repetition']}")
    print(f"  timestamp:    {r.get('timestamp', '--')}")
    print(f"  status:       {r['status']}")
    print()

    # --- Prompt ---
    print("--- Prompt ---")
    prompt = r.get("prompt_text") or "--"
    if len(prompt) > 2000:
        print(f"  {prompt[:2000]}")
        print("  [truncated]")
    else:
        print(f"  {prompt}")
    print()

    # --- Pre-processor ---
    if r.get("preproc_model"):
        print("--- Pre-processor ---")
        print(f"  model:          {r['preproc_model']}")
        print(f"  input_tokens:   {r.get('preproc_input_tokens', '--')}")
        print(f"  output_tokens:  {r.get('preproc_output_tokens', '--')}")
        in_tok = r.get("preproc_input_tokens") or 0
        out_tok = r.get("preproc_output_tokens") or 0
        if in_tok > 0:
            print(f"  token ratio:    {out_tok / in_tok:.2f}x (out/in)")
        print(f"  ttft_ms:        {r.get('preproc_ttft_ms', '--')}")
        print(f"  ttlt_ms:        {r.get('preproc_ttlt_ms', '--')}")
        print(f"  cost:           ${r.get('preproc_cost_usd', 0):.6f}")

        raw_output = r.get("preproc_raw_output")
        if raw_output is not None:
            # Check if fallback was triggered
            prompt_text = r.get("prompt_text") or ""
            is_preproc = r.get("intervention", "") in (
                "pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only"
            )
            if is_preproc and raw_output != prompt_text:
                if len(raw_output) > len(prompt_text) * 1.5 or len(raw_output) == 0:
                    print("  fallback:       YES (raw preproc output shown below, original prompt was used instead)")
                else:
                    print("  fallback:       NO")
            print()
            print("--- Pre-processor Output ---")
            if len(raw_output) > 2000:
                print(f"  {raw_output[:2000]}")
                print("  [truncated]")
            else:
                print(f"  {raw_output}")
        print()

    # --- Model Response ---
    print("--- Model Response ---")
    output = r.get("raw_output") or "--"
    if len(output) > 2000:
        print(f"  {output[:2000]}")
        print("  [truncated]")
    else:
        print(f"  {output}")
    print()

    # --- Grading ---
    print("--- Grading ---")
    pf = r.get("pass_fail")
    print(f"  pass_fail:          {'PASS' if pf == 1 else 'FAIL' if pf == 0 else '--'}")
    print(f"  fail_reason:        {r.get('fail_reason') or '--'}")
    print(f"  extraction_method:  {r.get('extraction_method') or '--'}")
    print()

    # --- Timing ---
    print("--- Timing ---")
    print(f"  ttft_ms:       {r.get('ttft_ms', '--')}")
    print(f"  ttlt_ms:       {r.get('ttlt_ms', '--')}")
    print(f"  generation_ms: {r.get('generation_ms', '--')}")
    print()

    # --- Cost ---
    print("--- Cost ---")
    print(f"  main input:    ${r.get('main_model_input_cost_usd', 0):.6f}")
    print(f"  main output:   ${r.get('main_model_output_cost_usd', 0):.6f}")
    print(f"  preproc:       ${r.get('preproc_cost_usd', 0):.6f}")
    print(f"  total:         ${r.get('total_cost_usd', 0):.6f}")

    conn.close()


def handle_regrade(args: argparse.Namespace) -> None:
    """Re-grade all existing results with updated grading logic."""
    import sqlite3
    from src.config_manager import load_config
    from src.db import init_database
    from src.grade_results import batch_grade
    from src.run_experiment import _get_benchmark

    config = load_config()
    db_path = _resolve_db_path(args)
    conn = init_database(db_path)

    # Count totals before
    total = conn.execute("SELECT COUNT(*) FROM experiment_runs").fetchone()[0]
    if total == 0:
        print("No runs to regrade.")
        conn.close()
        return

    old_passed = conn.execute("SELECT COUNT(*) FROM experiment_runs WHERE pass_fail = 1").fetchone()[0]
    old_rate = old_passed / total * 100

    # Fix benchmark column for misdetected prompts
    fixed = 0
    rows = conn.execute("SELECT DISTINCT prompt_id, benchmark FROM experiment_runs").fetchall()
    for prompt_id, current_bench in rows:
        correct_bench = _get_benchmark(prompt_id)
        if correct_bench != current_bench:
            conn.execute(
                "UPDATE experiment_runs SET benchmark = ? WHERE prompt_id = ?",
                (correct_bench, prompt_id),
            )
            fixed += 1
    if fixed > 0:
        conn.commit()
        print(f"Fixed benchmark classification for {fixed} prompt(s)")

    conn.close()

    # Re-grade all runs
    print(f"Re-grading {total:,} runs...")
    summary = batch_grade(db_path, force=True, prompts_path=config.prompts_path)

    new_passed = summary["passed"]
    new_rate = new_passed / summary["total"] * 100 if summary["total"] > 0 else 0

    print(f"\nRegrade complete:")
    print(f"  Before: {old_passed:,}/{total:,} passed ({old_rate:.1f}%)")
    print(f"  After:  {new_passed:,}/{summary['total']:,} passed ({new_rate:.1f}%)")
    change = new_rate - old_rate
    if abs(change) > 0.1:
        direction = "+" if change > 0 else ""
        print(f"  Change: {direction}{change:.1f}pp")
    if summary["errors"] > 0:
        print(f"  Errors: {summary['errors']}")
    print(f"\nRun `propt report` to see updated results.")


def handle_clean(args: argparse.Namespace) -> None:
    """Delete experiment results database and associated files to start fresh.

    If --session is provided, delegates to delete_session instead of
    file-by-file cleanup.
    """
    session_id = getattr(args, "session", None)
    if session_id:
        from src.session import delete_session, resolve_session

        # Show what will be deleted
        db_path = resolve_session(session_id)
        from pathlib import Path
        session_dir = Path(db_path).parent
        total_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
        if total_size >= 1_048_576:
            size_str = f"{total_size / 1_048_576:.1f} MB"
        elif total_size >= 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size} bytes"

        print(f"Session to delete: {session_dir.name} ({size_str})")

        if not args.yes:
            try:
                confirm = input("\nDelete this session? This cannot be undone. (y/N): ").strip().lower()
            except KeyboardInterrupt:
                print("\nAborted.")
                return
            if confirm not in ("y", "yes"):
                print("Aborted.")
                return

        delete_session(session_id)
        print(f"Deleted session: {session_dir.name}")
        return

    from pathlib import Path
    from src.config_manager import load_config

    config = load_config()
    db_path_str = args.db if args.db else config.results_db_path
    db_path = Path(db_path_str)

    files_to_delete: list[Path] = []
    if db_path.exists():
        files_to_delete.append(db_path)
    # Also clean up execution plan and pilot prompts if they exist
    plan_path = db_path.parent / "execution_plan.json"
    pilot_plan_path = db_path.parent / "pilot_plan.json"
    pilot_prompts_path = Path("data/pilot_prompts.json")
    for p in [plan_path, pilot_plan_path, pilot_prompts_path]:
        if p.exists():
            files_to_delete.append(p)

    if not files_to_delete:
        print("Nothing to clean — no results found.")
        return

    print("Files to delete:")
    for f in files_to_delete:
        size = f.stat().st_size
        if size >= 1_048_576:
            size_str = f"{size / 1_048_576:.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} bytes"
        print(f"  {f} ({size_str})")

    if not args.yes:
        try:
            confirm = input("\nDelete these files? This cannot be undone. (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted.")
            return
        if confirm not in ("y", "yes"):
            print("Aborted.")
            return

    for f in files_to_delete:
        f.unlink()
        print(f"  Deleted: {f}")

    print("\nClean complete. Run `propt pilot` or `propt run` to start fresh.")


def handle_list(args: argparse.Namespace) -> None:
    """List all experiment sessions with metadata."""
    from tabulate import tabulate
    from src.session import list_sessions

    sessions = list_sessions()
    if not sessions:
        print("No sessions found. Run `propt pilot` or `propt run` to create one.")
        return

    table = []
    for i, s in enumerate(sessions, 1):
        models_str = ", ".join(s["models"][:3])
        if len(s["models"]) > 3:
            models_str += f" +{len(s['models']) - 3}"
        date_str = s["created_at"][:19].replace("T", " ") if s["created_at"] else "--"
        cost_str = f"${s['cost']:.4f}" if s["cost"] else "--"
        table.append([
            i, s["session_id"], date_str, models_str,
            s["status"], s["item_count"], cost_str,
        ])

    print(tabulate(
        table,
        headers=["#", "Session ID", "Date", "Models", "Status", "Items", "Cost"],
        tablefmt="simple",
    ))


def handle_list_runs(args: argparse.Namespace) -> None:
    """List individual runs within a session."""
    import sqlite3
    from tabulate import tabulate
    from src.session import resolve_session
    from src.db import init_database

    db_path = resolve_session(args.session)
    conn = init_database(db_path)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT run_id, prompt_id, benchmark, noise_type, intervention,
               model, pass_fail, status
        FROM experiment_runs
    """
    conditions: list[str] = []
    params: list[str] = []

    if args.model:
        conditions.append("model LIKE ?")
        params.append(f"%{args.model}%")
    if args.benchmark:
        conditions.append("benchmark = ?")
        params.append(args.benchmark)
    if args.intervention:
        conditions.append("intervention = ?")
        params.append(args.intervention)
    if args.failed:
        conditions.append("(pass_fail = 0 OR status = 'failed')")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY run_id LIMIT 100"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print("No runs found matching filters.")
        return

    table = []
    for r in rows:
        run_id_short = r["run_id"][:40] + "..." if len(r["run_id"]) > 40 else r["run_id"]
        pf = "PASS" if r["pass_fail"] == 1 else "FAIL" if r["pass_fail"] == 0 else "--"
        table.append([
            run_id_short, r["prompt_id"], r["benchmark"],
            r["noise_type"], r["intervention"], r["model"], pf,
        ])

    print(tabulate(
        table,
        headers=["Run ID", "Prompt", "Benchmark", "Noise", "Intervention", "Model", "Result"],
        tablefmt="simple",
    ))
    if len(rows) == 100:
        print(f"\n(showing first 100 runs, use filters to narrow)")


def handle_delete_results(args: argparse.Namespace) -> None:
    """Delete a session after confirmation."""
    from pathlib import Path
    from src.session import resolve_session, delete_session

    db_path = resolve_session(args.session)
    session_dir = Path(db_path).parent

    total_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
    if total_size >= 1_048_576:
        size_str = f"{total_size / 1_048_576:.1f} MB"
    elif total_size >= 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size} bytes"

    print(f"Session to delete: {args.session} ({size_str})")
    print(f"  Directory: {session_dir}")

    if not args.yes:
        try:
            confirm = input("\nDelete this session? This cannot be undone. (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted.")
            return
        if confirm not in ("y", "yes"):
            print("Aborted.")
            return

    delete_session(args.session)
    print(f"Deleted session: {args.session}")


def handle_compare_results(args: argparse.Namespace) -> None:
    """Compare two sessions side by side."""
    from src.session import compare_sessions

    result = compare_sessions(args.session1, args.session2)
    print(result)


def main() -> None:
    """CLI entry point. Parses args, routes to subcommand handler."""
    from src.env_manager import load_env

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Suppress noisy HTTP-level logs from SDK clients
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    load_env()

    try:
        parser = build_cli()
        args = parser.parse_args()

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
