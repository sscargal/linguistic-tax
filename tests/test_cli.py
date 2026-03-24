"""Tests for the CLI entry point module."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_build_cli_has_setup_subcommand():
    """build_cli() returns an ArgumentParser with 'setup' subcommand."""
    from src.cli import build_cli

    parser = build_cli()
    # Parse "setup" -- should not raise
    args = parser.parse_args(["setup"])
    assert args.command == "setup"


def test_build_cli_setup_has_non_interactive_flag():
    """The setup subcommand has a --non-interactive flag."""
    from src.cli import build_cli

    parser = build_cli()
    args = parser.parse_args(["setup", "--non-interactive"])
    assert args.non_interactive is True


def test_build_cli_setup_non_interactive_default_false():
    """--non-interactive defaults to False."""
    from src.cli import build_cli

    parser = build_cli()
    args = parser.parse_args(["setup"])
    assert args.non_interactive is False


def test_main_no_args_exits_1(capsys):
    """main() with no args prints help and exits with code 1."""
    from src.cli import main

    with patch("sys.argv", ["linguistic-tax"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_main_setup_routes_to_wizard():
    """main() with 'setup' calls run_setup_wizard."""
    from src.cli import main

    with patch("sys.argv", ["linguistic-tax", "setup", "--non-interactive"]):
        with patch("src.cli.run_setup_wizard") as mock_wizard:
            main()
            mock_wizard.assert_called_once()
            args = mock_wizard.call_args[0][0]
            assert args.non_interactive is True
