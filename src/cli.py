"""CLI entry point for the Linguistic Tax research toolkit.

Provides argparse-based subcommand routing with setup, config viewing,
config modification, validation, diff, and model listing subcommands.
"""

import argparse
import logging
import sys

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
        help="Run the guided setup wizard to configure the slicer",
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
    models_parser.set_defaults(func=handle_list_models)

    # --- argcomplete ---
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    return parser


def main() -> None:
    """CLI entry point. Parses args, routes to subcommand handler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = build_cli()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
