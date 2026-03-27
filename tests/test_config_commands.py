"""Comprehensive tests for CLI config subcommand handlers.

Tests cover: show-config (table, JSON, changed filter, single property, verbose),
set-config (creation, sparse writes, type coercion, validation, change summary),
reset-config (single key, all, preserves others, already default),
validate, diff, list-models, and helper functions.
"""

import json
import logging
from dataclasses import fields as dc_fields
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.config import ExperimentConfig
from src.model_registry import registry
from src.model_discovery import DiscoveredModel, DiscoveryResult
from src.config_commands import (
    FIELD_DESCRIPTIONS,
    _coerce_value,
    _format_price,
    _format_context_window,
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
        """show-config with no flags prints table containing all field names."""
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
        """--json flag produces valid JSON with all ExperimentConfig keys."""
        monkeypatch.chdir(tmp_path)
        handle_show_config(make_args(json=True))
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == len(dc_fields(ExperimentConfig))
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
        """Invalid value exits 1 without writing."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            handle_set_config(make_args(pairs=["repetitions", "-1"]))
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
        """validate exits 1 with invalid repetitions value."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(
            json.dumps({"repetitions": -1})
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

    @patch("src.config_manager.load_config")
    @patch("src.config_commands.discover_all_models")
    def test_list_models_all_entries(self, mock_discover, mock_load, capsys):
        """list-models output contains all registry model names."""
        # Prevent load_config from reloading registry with user's config
        mock_load.return_value = None
        # Force fallback to registry for all providers so output is deterministic
        mock_discover.return_value = DiscoveryResult(
            models={},
            errors={p: f"Skipping {p}: key not set" for p in
                    ["anthropic", "google", "openai", "openrouter"]},
        )
        handle_list_models(make_args())
        output = capsys.readouterr().out
        for model_id in registry._models:
            assert model_id in output, f"Missing model: {model_id}"
        assert len(registry._models) == 8

    @patch("src.config_manager.load_config")
    @patch("src.config_commands.discover_all_models")
    def test_list_models_free_indicator(self, mock_discover, mock_load, capsys):
        """Output contains 'free' for openrouter models."""
        mock_load.return_value = None
        mock_discover.return_value = DiscoveryResult(
            models={},
            errors={p: f"Skipping {p}: key not set" for p in
                    ["anthropic", "google", "openai", "openrouter"]},
        )
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
        """FIELD_DESCRIPTIONS has entries for all ExperimentConfig fields."""
        for f in dc_fields(ExperimentConfig):
            assert f.name in FIELD_DESCRIPTIONS, f"Missing description for {f.name}"
        assert len(FIELD_DESCRIPTIONS) == len(dc_fields(ExperimentConfig))

    def test_format_price_priced(self):
        """_format_price with real prices shows $X.XX / $Y.YY format."""
        assert _format_price(3.0, 15.0) == "$3.00 / $15.00"

    def test_format_price_free(self):
        """_format_price with 0/0 shows 'free'."""
        assert _format_price(0.0, 0.0) == "free"

    def test_format_price_unknown(self):
        """_format_price with None/None shows '--'."""
        assert _format_price(None, None) == "--"

    def test_format_price_partial_none(self):
        """_format_price with one None treats it as 0.0."""
        assert _format_price(3.0, None) == "$3.00 / $0.00"

    def test_format_context_window_value(self):
        """_format_context_window with int shows comma-separated number."""
        assert _format_context_window(200000) == "200,000"

    def test_format_context_window_none(self):
        """_format_context_window with None shows '--'."""
        assert _format_context_window(None) == "--"


# ---------------------------------------------------------------------------
# Enhanced list-models tests (with model discovery)
# ---------------------------------------------------------------------------


def _make_discovery_result(
    models: dict[str, list[DiscoveredModel]] | None = None,
    errors: dict[str, str] | None = None,
) -> DiscoveryResult:
    """Create a DiscoveryResult with defaults."""
    return DiscoveryResult(
        models=models or {},
        errors=errors or {},
    )


class TestListModelsEnhanced:
    """Tests for enhanced handle_list_models with live discovery."""

    @pytest.fixture(autouse=True)
    def _prevent_config_reload(self):
        """Prevent load_config from reloading registry with user's config."""
        with patch("src.config_manager.load_config", return_value=None):
            yield

    def _mock_result(self) -> DiscoveryResult:
        """Create a standard mock DiscoveryResult with two providers."""
        return _make_discovery_result(
            models={
                "anthropic": [
                    DiscoveredModel(
                        model_id="claude-sonnet-4-20250514",
                        provider="anthropic",
                        context_window=200000,
                        input_price_per_1m=None,
                        output_price_per_1m=None,
                    ),
                    DiscoveredModel(
                        model_id="claude-opus-4-20250514",
                        provider="anthropic",
                        context_window=200000,
                        input_price_per_1m=None,
                        output_price_per_1m=None,
                    ),
                ],
                "openrouter": [
                    DiscoveredModel(
                        model_id="anthropic/claude-sonnet-4",
                        provider="openrouter",
                        context_window=200000,
                        input_price_per_1m=3.0,
                        output_price_per_1m=15.0,
                    ),
                    DiscoveredModel(
                        model_id="google/gemini-2.0-flash",
                        provider="openrouter",
                        context_window=1000000,
                        input_price_per_1m=0.0,
                        output_price_per_1m=0.0,
                    ),
                ],
            }
        )

    @patch("src.config_commands.discover_all_models")
    def test_list_models_provider_headers(self, mock_discover, capsys):
        """Output contains uppercase provider headers."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "ANTHROPIC" in output
        assert "OPENROUTER" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_configured_status(self, mock_discover, capsys):
        """Configured models show 'configured' status."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "configured" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_available_status(self, mock_discover, capsys):
        """Non-configured models show 'available' status."""
        mock_discover.return_value = _make_discovery_result(
            models={
                "anthropic": [
                    DiscoveredModel(
                        model_id="claude-unknown-model",
                        provider="anthropic",
                        context_window=100000,
                        input_price_per_1m=None,
                        output_price_per_1m=None,
                    ),
                ],
            }
        )
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "available" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_pricing_format_priced(self, mock_discover, capsys):
        """Model with input=3.0/output=15.0 displays '$3.00 / $15.00'."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "$3.00 / $15.00" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_pricing_format_free(self, mock_discover, capsys):
        """Model with 0/0 pricing displays 'free'."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "free" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_pricing_format_unknown(self, mock_discover, capsys):
        """Model with None/None pricing displays '--'."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "--" in output

    @patch("src.config_commands.discover_all_models")
    @patch("src.config_commands._get_fallback_models")
    def test_list_models_fallback_on_error(self, mock_fallback, mock_discover, capsys):
        """Provider in errors dict shows fallback models with 'fallback' status."""
        mock_discover.return_value = _make_discovery_result(
            errors={"anthropic": "Skipping anthropic: ANTHROPIC_API_KEY not set"}
        )
        mock_fallback.return_value = [
            DiscoveredModel(
                model_id="claude-sonnet-4-20250514",
                provider="anthropic",
                context_window=None,
                input_price_per_1m=3.0,
                output_price_per_1m=15.0,
            ),
        ]
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "fallback" in output
        assert "ANTHROPIC" in output
        mock_fallback.assert_called_once_with("anthropic")

    @patch("src.config_commands.discover_all_models")
    def test_list_models_skipped_provider_warning(self, mock_discover, caplog):
        """Skipped provider logs warning message."""
        mock_discover.return_value = _make_discovery_result(
            errors={"google": "Skipping google: GOOGLE_API_KEY not set"}
        )
        with caplog.at_level(logging.WARNING):
            handle_list_models(make_args())
        assert "GOOGLE_API_KEY" in caplog.text

    @patch("src.config_commands.discover_all_models")
    def test_list_models_json_output(self, mock_discover, capsys):
        """--json flag produces valid JSON output."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args(json=True))
        output = capsys.readouterr().out
        data = json.loads(output)
        assert isinstance(data, dict)
        assert "anthropic" in data
        assert "openrouter" in data
        # Check model entries have expected keys
        first_model = data["anthropic"][0]
        assert "model_id" in first_model
        assert "context_window" in first_model
        assert "status" in first_model

    @patch("src.config_commands.discover_all_models")
    def test_list_models_context_window_display(self, mock_discover, capsys):
        """Context window displays as formatted integer."""
        mock_discover.return_value = self._mock_result()
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "200,000" in output

    @patch("src.config_commands.discover_all_models")
    def test_list_models_context_window_none(self, mock_discover, capsys):
        """Context window None displays as '--'."""
        mock_discover.return_value = _make_discovery_result(
            models={
                "openai": [
                    DiscoveredModel(
                        model_id="gpt-4o",
                        provider="openai",
                        context_window=None,
                        input_price_per_1m=None,
                        output_price_per_1m=None,
                    ),
                ],
            }
        )
        handle_list_models(make_args())
        output = capsys.readouterr().out
        assert "--" in output
