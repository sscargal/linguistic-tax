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
    report_parser.set_defaults(func=handle_report)

    # --- argcomplete ---
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    return parser


def handle_report(args: argparse.Namespace) -> None:
    """Show post-run report with actual metrics from results database."""
    from src.config_manager import load_config
    from src.db import init_database
    from src.execution_summary import format_post_run_report

    config = load_config()
    db_path = args.db if args.db else config.results_db_path
    conn = init_database(db_path)
    print(format_post_run_report(conn))
    conn.close()


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
