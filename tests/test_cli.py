"""Tests for the CLI entry point module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.cli import build_cli, main


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


# ---------------------------------------------------------------------------
# New subcommand registration and routing tests (14-02)
# ---------------------------------------------------------------------------


def test_build_cli_has_all_subcommands():
    """build_cli parser accepts all 7 subcommands."""
    parser = build_cli()
    commands = [
        ("setup", ["setup"]),
        ("show-config", ["show-config"]),
        ("set-config", ["set-config", "key", "val"]),
        ("reset-config", ["reset-config", "key"]),
        ("validate", ["validate"]),
        ("diff", ["diff"]),
        ("list-models", ["list-models"]),
    ]
    for expected_cmd, argv in commands:
        args = parser.parse_args(argv)
        assert args.command == expected_cmd, f"Failed for {expected_cmd}"


def test_build_cli_prog_name_is_propt():
    """parser.prog is 'propt'."""
    parser = build_cli()
    assert parser.prog == "propt"


def test_show_config_parser_flags():
    """show-config accepts --json, --changed, --verbose, optional property."""
    parser = build_cli()
    args = parser.parse_args(["show-config", "--json", "--changed", "--verbose"])
    assert args.json is True
    assert args.changed is True
    assert args.verbose is True

    args2 = parser.parse_args(["show-config", "temperature"])
    assert args2.property == "temperature"


def test_set_config_parser_pairs():
    """set-config accepts variable number of positional args as pairs."""
    parser = build_cli()
    args = parser.parse_args(["set-config", "temperature", "0.5", "repetitions", "3"])
    assert args.pairs == ["temperature", "0.5", "repetitions", "3"]


def test_reset_config_parser_all_flag():
    """reset-config accepts --all flag and property names."""
    parser = build_cli()
    args = parser.parse_args(["reset-config", "--all"])
    assert args.all is True

    args2 = parser.parse_args(["reset-config", "temperature", "repetitions"])
    assert args2.properties == ["temperature", "repetitions"]


def test_main_show_config_routes():
    """main with 'show-config' calls handle_show_config."""
    with patch("sys.argv", ["propt", "show-config"]):
        with patch("src.cli.handle_show_config") as mock_handler:
            main()
            mock_handler.assert_called_once()


def test_main_set_config_routes():
    """main with 'set-config temperature 0.5' calls handle_set_config."""
    with patch("sys.argv", ["propt", "set-config", "temperature", "0.5"]):
        with patch("src.cli.handle_set_config") as mock_handler:
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.pairs == ["temperature", "0.5"]
