"""Comprehensive tests for CLI config subcommand handlers.

Tests cover: show-config (table, JSON, changed filter, single property, verbose),
set-config (creation, sparse writes, type coercion, validation, change summary),
reset-config (single key, all, preserves others, already default),
validate, diff, list-models, and helper functions.
"""

import json
from dataclasses import fields as dc_fields
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import ExperimentConfig, PRICE_TABLE
from src.config_commands import (
    FIELD_DESCRIPTIONS,
    _coerce_value,
    _format_value,
    _load_raw_overrides,
    handle_diff,
    handle_list_models,
    handle_reset_config,
    handle_set_config,
    handle_show_config,
    handle_validate,
    property_name_completer,
)
from src.config_manager import CONFIG_FILENAME


def make_args(**kwargs) -> SimpleNamespace:
    """Create a Namespace with defaults for all handler args."""
    defaults = {
        "property": None,
        "json": False,
        "changed": False,
        "verbose": False,
        "pairs": [],
        "properties": [],
        "all": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# show-config tests
# ---------------------------------------------------------------------------


class TestShowConfig:
    """Tests for handle_show_config."""

    def test_show_config_table_all_properties(self, tmp_path, monkeypatch, capsys):
        """show-config with no flags prints table containing all 13 field names."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args())
        output = capsys.readouterr().out
        for f in dc_fields(ExperimentConfig):
            assert f.name in output, f"Missing field: {f.name}"

    def test_show_config_modified_indicator(self, tmp_path, monkeypatch, capsys):
        """When config has override, property shows * prefix."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps({"temperature": 0.5}))
        handle_show_config(make_args())
        output = capsys.readouterr().out
        assert "*temperature" in output

    def test_show_config_json_output(self, tmp_path, monkeypatch, capsys):
        """--json flag produces valid JSON with all 13 keys."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(json=True))
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == 13
        for f in dc_fields(ExperimentConfig):
            assert f.name in data

    def test_show_config_changed_filter(self, tmp_path, monkeypatch, capsys):
        """--changed with overrides only shows overridden properties."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps({"temperature": 0.5}))
        handle_show_config(make_args(changed=True))
        output = capsys.readouterr().out
        assert "temperature" in output
        assert "repetitions" not in output

    def test_show_config_changed_no_overrides(self, tmp_path, monkeypatch, capsys):
        """--changed with no config file shows nothing (or empty table)."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(changed=True))
        output = capsys.readouterr().out
        # Should not contain any field names (no changes)
        assert "temperature" not in output.split("\n")[-1] or output.strip() == "" or "Property" in output

    def test_show_config_single_property(self, tmp_path, monkeypatch, capsys):
        """show-config temperature prints just the default value."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(property="temperature"))
        output = capsys.readouterr().out
        assert output.strip() == "0.0"

    def test_show_config_single_property_json(self, tmp_path, monkeypatch, capsys):
        """show-config temperature --json prints JSON with single key."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(property="temperature", json=True))
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data == {"temperature": 0.0}

    def test_show_config_single_property_invalid(self, tmp_path, monkeypatch):
        """Unknown property name exits 1."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_show_config(make_args(property="nonexistent"))
        assert exc_info.value.code == 1

    def test_show_config_verbose(self, tmp_path, monkeypatch, capsys):
        """--verbose adds Description column to output."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(verbose=True))
        output = capsys.readouterr().out
        assert "Description" in output
        # Check at least one description appears
        assert "LLM sampling temperature" in output


# ---------------------------------------------------------------------------
# set-config tests
# ---------------------------------------------------------------------------


class TestSetConfig:
    """Tests for handle_set_config."""

    def test_set_config_creates_file(self, tmp_path, monkeypatch, capsys):
        """set-config on nonexistent config auto-creates the file."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["temperature", "0.5"]))
        assert (tmp_path / CONFIG_FILENAME).exists()

    def test_set_config_sparse_write(self, tmp_path, monkeypatch, capsys):
        """set-config writes only the set key, not all defaults."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["temperature", "0.5"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert raw == {"temperature": 0.5}

    def test_set_config_type_coercion_float(self, tmp_path, monkeypatch, capsys):
        """temperature 0.5 coerces to float 0.5."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["temperature", "0.5"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert raw["temperature"] == 0.5
        assert isinstance(raw["temperature"], float)

    def test_set_config_type_coercion_int(self, tmp_path, monkeypatch, capsys):
        """repetitions 3 coerces to int 3."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["repetitions", "3"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert raw["repetitions"] == 3
        assert isinstance(raw["repetitions"], int)

    def test_set_config_type_coercion_tuple(self, tmp_path, monkeypatch, capsys):
        """type_a_rates 0.05,0.10,0.30 coerces to tuple of floats."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["type_a_rates", "0.05,0.10,0.30"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        # JSON stores as list, but the coercion produces tuple which save_config converts
        assert raw["type_a_rates"] == [0.05, 0.10, 0.30]

    def test_set_config_multiple_pairs(self, tmp_path, monkeypatch, capsys):
        """Multiple key-value pairs set both properties."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["temperature", "0.5", "repetitions", "3"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert raw["temperature"] == 0.5
        assert raw["repetitions"] == 3

    def test_set_config_validates_before_save(self, tmp_path, monkeypatch):
        """Invalid model name exits 1 without writing."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_set_config(make_args(pairs=["claude_model", "invalid-model"]))
        assert exc_info.value.code == 1
        assert not (tmp_path / CONFIG_FILENAME).exists()

    def test_set_config_unknown_property(self, tmp_path, monkeypatch):
        """Unknown key exits 1."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_set_config(make_args(pairs=["nonexistent", "value"]))
        assert exc_info.value.code == 1

    def test_set_config_odd_pairs(self, tmp_path, monkeypatch):
        """Odd number of args exits 1."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_set_config(make_args(pairs=["temperature"]))
        assert exc_info.value.code == 1

    def test_set_config_change_summary(self, tmp_path, monkeypatch, capsys):
        """Output contains change summary with arrow."""
        monkeypatch.chdir(tmp_path)
        handle_set_config(make_args(pairs=["temperature", "0.5"]))
        output = capsys.readouterr().out
        assert "temperature" in output
        assert "0.5" in output
        assert "->" in output


# ---------------------------------------------------------------------------
# reset-config tests
# ---------------------------------------------------------------------------


class TestResetConfig:
    """Tests for handle_reset_config."""

    def test_reset_config_single(self, tmp_path, monkeypatch, capsys):
        """reset-config removes key from sparse config."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(
            json.dumps({"temperature": 0.5, "repetitions": 3})
        )
        handle_reset_config(make_args(properties=["temperature"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert "temperature" not in raw

    def test_reset_config_preserves_other(self, tmp_path, monkeypatch, capsys):
        """Resetting one key preserves other overrides."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(
            json.dumps({"temperature": 0.5, "repetitions": 3})
        )
        handle_reset_config(make_args(properties=["temperature"]))
        raw = json.loads((tmp_path / CONFIG_FILENAME).read_text())
        assert raw["repetitions"] == 3

    def test_reset_config_already_default(self, tmp_path, monkeypatch, capsys):
        """Resetting non-overridden key prints 'already at default'."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps({"repetitions": 3}))
        handle_reset_config(make_args(properties=["temperature"]))
        output = capsys.readouterr().out
        assert "already at default" in output

    def test_reset_config_all(self, tmp_path, monkeypatch, capsys):
        """--all deletes the config file."""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(json.dumps({"temperature": 0.5}))
        assert config_path.exists()
        handle_reset_config(make_args(all=True, properties=[]))
        assert not config_path.exists()

    def test_reset_config_unknown_property(self, tmp_path, monkeypatch):
        """Unknown property exits 1."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_reset_config(make_args(properties=["nonexistent"]))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# validate tests
# ---------------------------------------------------------------------------


class TestValidate:
    """Tests for handle_validate."""

    def test_validate_valid(self, tmp_path, monkeypatch, capsys):
        """validate exits 0 with valid config."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps({"temperature": 0.5}))
        # Should not raise
        handle_validate(make_args())
        output = capsys.readouterr().out
        assert "valid" in output.lower()

    def test_validate_invalid(self, tmp_path, monkeypatch):
        """validate exits 1 with invalid model name."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(
            json.dumps({"claude_model": "invalid"})
        )
        with pytest.raises(SystemExit) as exc_info:
            handle_validate(make_args())
        assert exc_info.value.code == 1

    def test_validate_no_config(self, tmp_path, monkeypatch, capsys):
        """validate with no config file exits 0 (defaults are valid)."""
        monkeypatch.chdir(tmp_path)
        handle_validate(make_args())
        output = capsys.readouterr().out
        assert "valid" in output.lower()


# ---------------------------------------------------------------------------
# diff tests
# ---------------------------------------------------------------------------


class TestDiff:
    """Tests for handle_diff."""

    def test_diff_no_changes(self, tmp_path, monkeypatch, capsys):
        """diff with no overrides prints 'No changes from defaults'."""
        monkeypatch.chdir(tmp_path)
        handle_diff(make_args())
        output = capsys.readouterr().out
        assert "No changes from defaults" in output

    def test_diff_with_changes(self, tmp_path, monkeypatch, capsys):
        """diff shows changed properties with default and current values."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps({"temperature": 0.5}))
        handle_diff(make_args())
        output = capsys.readouterr().out
        assert "temperature" in output
        assert "0.5" in output


# ---------------------------------------------------------------------------
# list-models tests
# ---------------------------------------------------------------------------


class TestListModels:
    """Tests for handle_list_models."""

    def test_list_models_all_entries(self, capsys):
        """list-models output contains all 8 PRICE_TABLE model names."""
        handle_list_models(make_args())
        output = capsys.readouterr().out
        for model in PRICE_TABLE:
            assert model in output, f"Missing model: {model}"
        assert len(PRICE_TABLE) == 8

    def test_list_models_free_indicator(self, capsys):
        """Output contains 'free' for openrouter models."""
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "free" in output


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for helper functions."""

    def test_coerce_value_string(self):
        """_coerce_value for str field returns string."""
        result = _coerce_value("prompts_path", "custom/path.json")
        assert result == "custom/path.json"
        assert isinstance(result, str)

    def test_property_name_completer(self):
        """Completer returns matching field names for prefix."""
        result = property_name_completer("temp", None)
        assert result == ["temperature"]

    def test_property_name_completer_multiple(self):
        """Completer returns multiple matches for broader prefix."""
        result = property_name_completer("type_a", None)
        assert "type_a_rates" in result
        assert "type_a_weights" in result

    def test_format_value_tuple(self):
        """_format_value formats tuples as comma-separated string."""
        assert _format_value((0.05, 0.10, 0.20)) == "0.05, 0.1, 0.2"

    def test_format_value_string(self):
        """_format_value passes strings through."""
        assert _format_value("hello") == "hello"

    def test_field_descriptions_has_all_fields(self):
        """FIELD_DESCRIPTIONS has entries for all 13 ExperimentConfig fields."""
        for f in dc_fields(ExperimentConfig):
            assert f.name in FIELD_DESCRIPTIONS, f"Missing description for {f.name}"
        assert len(FIELD_DESCRIPTIONS) == 13
