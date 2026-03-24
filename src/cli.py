"""CLI entry point for the Linguistic Tax research toolkit.

Provides argparse-based subcommand routing. Currently supports
the 'setup' subcommand for guided project configuration.
"""

import argparse
import logging
import sys

from src.setup_wizard import run_setup_wizard


def build_cli() -> argparse.ArgumentParser:
    """Create the top-level argument parser with subcommands.

    Returns:
        Configured ArgumentParser with 'setup' subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="linguistic-tax",
        description="Linguistic Tax research toolkit CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

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
