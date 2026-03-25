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


# ---------------------------------------------------------------------------
# Phase 15: run and pilot subcommand tests
# ---------------------------------------------------------------------------


def test_build_cli_has_run_subcommand():
    """build_cli parser accepts 'run' subcommand."""
    parser = build_cli()
    args = parser.parse_args(["run"])
    assert args.command == "run"


def test_build_cli_has_pilot_subcommand():
    """build_cli parser accepts 'pilot' subcommand."""
    parser = build_cli()
    args = parser.parse_args(["pilot"])
    assert args.command == "pilot"


def test_run_parser_default_flags():
    """run subcommand has correct default values for all flags."""
    parser = build_cli()
    args = parser.parse_args(["run"])
    assert args.model == "all"
    assert args.limit is None
    assert args.retry_failed is False
    assert args.yes is False
    assert args.budget is None
    assert args.dry_run is False
    assert args.intervention is None
    assert args.db is None


def test_run_parser_all_flags():
    """run subcommand parses all flags correctly."""
    parser = build_cli()
    args = parser.parse_args([
        "run",
        "--model", "claude",
        "--limit", "10",
        "--retry-failed",
        "--yes",
        "--budget", "50",
        "--dry-run",
        "--intervention", "raw",
        "--db", "test.db",
    ])
    assert args.model == "claude"
    assert args.limit == 10
    assert args.retry_failed is True
    assert args.yes is True
    assert args.budget == 50.0
    assert args.dry_run is True
    assert args.intervention == "raw"
    assert args.db == "test.db"


def test_pilot_parser_default_flags():
    """pilot subcommand has correct default values."""
    parser = build_cli()
    args = parser.parse_args(["pilot"])
    assert args.yes is False
    assert args.budget is None
    assert args.dry_run is False
    assert args.db is None


def test_pilot_parser_all_flags():
    """pilot subcommand parses all flags correctly."""
    parser = build_cli()
    args = parser.parse_args([
        "pilot",
        "--yes",
        "--budget", "100",
        "--dry-run",
        "--db", "pilot.db",
    ])
    assert args.yes is True
    assert args.budget == 100.0
    assert args.dry_run is True
    assert args.db == "pilot.db"


def test_run_parser_intervention_choices():
    """run --intervention accepts valid choices and rejects invalid ones."""
    parser = build_cli()
    # Valid intervention
    args = parser.parse_args(["run", "--intervention", "pre_proc_sanitize"])
    assert args.intervention == "pre_proc_sanitize"

    # Invalid intervention
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--intervention", "invalid"])


def test_run_parser_model_choices():
    """run --model accepts valid choices and rejects invalid ones."""
    parser = build_cli()
    # Valid model
    args = parser.parse_args(["run", "--model", "openrouter"])
    assert args.model == "openrouter"

    # Invalid model
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--model", "invalid"])


def test_build_cli_has_all_subcommands_including_new():
    """build_cli parser accepts all 9 subcommands including run and pilot."""
    parser = build_cli()
    commands = [
        ("setup", ["setup"]),
        ("show-config", ["show-config"]),
        ("set-config", ["set-config", "key", "val"]),
        ("reset-config", ["reset-config", "key"]),
        ("validate", ["validate"]),
        ("diff", ["diff"]),
        ("list-models", ["list-models"]),
        ("run", ["run"]),
        ("pilot", ["pilot"]),
    ]
    for expected_cmd, argv in commands:
        args = parser.parse_args(argv)
        assert args.command == expected_cmd, f"Failed for {expected_cmd}"


def test_main_run_routes_to_handler():
    """main with 'run --yes' calls handle_run."""
    with patch("sys.argv", ["propt", "run", "--yes"]):
        with patch("src.cli.handle_run") as mock_handler:
            main()
            mock_handler.assert_called_once()


def test_main_pilot_routes_to_handler():
    """main with 'pilot --yes' calls handle_pilot."""
    with patch("sys.argv", ["propt", "pilot", "--yes"]):
        with patch("src.cli.handle_pilot") as mock_handler:
            main()
            mock_handler.assert_called_once()


# ---------------------------------------------------------------------------
# KeyboardInterrupt handling tests (260325-w6g)
# ---------------------------------------------------------------------------


def test_main_ctrl_c_exits_130(capsys):
    """Ctrl-C during main() prints 'Aborted.' to stderr and exits 130."""
    import argparse

    with patch.object(argparse.ArgumentParser, "parse_args", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 130
    captured = capsys.readouterr()
    assert "Aborted." in captured.err


def test_confirm_execution_ctrl_c_returns_no(capsys):
    """Ctrl-C at confirmation prompt returns 'no' and prints 'Aborted.'."""
    from src.execution_summary import confirm_execution

    result = confirm_execution(
        "summary",
        input_fn=lambda _: (_ for _ in ()).throw(KeyboardInterrupt),
    )
    assert result == "no"
    captured = capsys.readouterr()
    assert "Aborted." in captured.out
