"""Unit tests for the config_manager module.

Tests cover: save/load config persistence, sparse override merging,
tuple/list round-trip, validation of all configurable fields,
find_config_path, and get_full_config_dict.
"""

import json
from pathlib import Path

import pytest

from src.config import ExperimentConfig
from src.config_manager import (
    CONFIG_FILENAME,
    find_config_path,
    get_full_config_dict,
    load_config,
    save_config,
    validate_config,
)


class TestSaveConfig:
    """Tests for save_config."""

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """save_config writes JSON to given path, file contains valid JSON."""
        config_dict = {"claude_model": "claude-sonnet-4-20250514", "repetitions": 5}
        out_path = tmp_path / CONFIG_FILENAME
        result = save_config(config_dict, out_path)
        assert result == out_path
        data = json.loads(out_path.read_text())
        assert data["claude_model"] == "claude-sonnet-4-20250514"
        assert data["repetitions"] == 5

    def test_save_converts_tuples_to_lists(self, tmp_path: Path) -> None:
        """save_config converts tuple values to lists before serializing."""
        config_dict = {"type_a_rates": (0.05, 0.10, 0.20)}
        out_path = tmp_path / CONFIG_FILENAME
        save_config(config_dict, out_path)
        data = json.loads(out_path.read_text())
        assert isinstance(data["type_a_rates"], list)
        assert data["type_a_rates"] == [0.05, 0.10, 0.20]

    def test_save_uses_default_path_when_none(self, tmp_path: Path, monkeypatch) -> None:
        """save_config uses CWD / CONFIG_FILENAME when config_path is None."""
        monkeypatch.chdir(tmp_path)
        save_config({"repetitions": 3})
        assert (tmp_path / CONFIG_FILENAME).exists()


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_no_file_returns_defaults(self, tmp_path: Path) -> None:
        """load_config with no file returns default ExperimentConfig()."""
        config = load_config(tmp_path / "nonexistent.json")
        assert config == ExperimentConfig()

    def test_load_sparse_override(self, tmp_path: Path) -> None:
        """load_config with sparse override applies overrides, keeps defaults."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(json.dumps({"repetitions": 10}))
        config = load_config(config_path)
        assert config.repetitions == 10
        assert config.claude_model == ExperimentConfig().claude_model
        assert config.base_seed == 42

    def test_load_converts_lists_to_tuples(self, tmp_path: Path) -> None:
        """load_config converts JSON lists back to tuples for tuple-typed fields."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(json.dumps({
            "type_a_rates": [0.01, 0.02],
            "type_a_weights": [0.5, 0.5],
        }))
        config = load_config(config_path)
        assert isinstance(config.type_a_rates, tuple)
        assert config.type_a_rates == (0.01, 0.02)
        assert isinstance(config.type_a_weights, tuple)
        assert config.type_a_weights == (0.5, 0.5)

    def test_load_ignores_unknown_keys(self, tmp_path: Path) -> None:
        """load_config ignores unknown keys in config file (forward-compatible)."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(json.dumps({
            "repetitions": 7,
            "unknown_future_key": "some_value",
            "another_unknown": 999,
        }))
        config = load_config(config_path)
        assert config.repetitions == 7
        assert not hasattr(config, "unknown_future_key")


class TestGetFullConfigDict:
    """Tests for get_full_config_dict."""

    def test_returns_all_fields(self) -> None:
        """get_full_config_dict returns all ExperimentConfig fields with defaults."""
        d = get_full_config_dict()
        assert "claude_model" in d
        assert "gemini_model" in d
        assert "type_a_rates" in d
        assert "repetitions" in d

    def test_tuples_as_lists(self) -> None:
        """get_full_config_dict converts tuples to lists."""
        d = get_full_config_dict()
        assert isinstance(d["type_a_rates"], list)
        assert isinstance(d["type_a_weights"], list)


class TestFindConfigPath:
    """Tests for find_config_path."""

    def test_returns_path_when_exists(self, tmp_path: Path) -> None:
        """find_config_path returns Path when file exists."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("{}")
        result = find_config_path(str(tmp_path))
        assert result is not None
        assert result == config_file

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        """find_config_path returns None when missing."""
        result = find_config_path(str(tmp_path))
        assert result is None


class TestValidateConfig:
    """Tests for validate_config."""

    def test_valid_default_config(self) -> None:
        """validate_config returns empty list for valid default config."""
        from dataclasses import asdict
        d = asdict(ExperimentConfig())
        errors = validate_config(d)
        assert errors == []

    def test_unknown_model_string(self) -> None:
        """validate_config returns error for unknown model string in claude_model."""
        errors = validate_config({"claude_model": "not-a-real-model"})
        assert len(errors) >= 1
        assert any("claude_model" in e for e in errors)

    def test_noise_rate_outside_range(self) -> None:
        """validate_config returns error for noise rate outside [0, 1]."""
        errors = validate_config({"type_a_rates": [0.05, 1.5, -0.1]})
        assert len(errors) >= 1
        assert any("type_a_rates" in e for e in errors)

    def test_repetitions_less_than_one(self) -> None:
        """validate_config returns error for repetitions < 1."""
        errors = validate_config({"repetitions": 0})
        assert len(errors) >= 1
        assert any("repetitions" in e for e in errors)

    def test_negative_temperature(self) -> None:
        """validate_config returns error for temperature < 0."""
        errors = validate_config({"temperature": -0.5})
        assert len(errors) >= 1
        assert any("temperature" in e for e in errors)

    def test_nonexistent_prompts_path(self) -> None:
        """validate_config returns error for nonexistent prompts_path."""
        errors = validate_config({"prompts_path": "/nonexistent/path/prompts.json"})
        assert len(errors) >= 1
        assert any("prompts_path" in e for e in errors)

    def test_multiple_errors(self) -> None:
        """validate_config returns multiple errors when multiple fields invalid."""
        errors = validate_config({
            "claude_model": "bad-model",
            "repetitions": -1,
            "temperature": -5.0,
        })
        assert len(errors) >= 3

    def test_valid_empty_dict(self) -> None:
        """validate_config returns empty list for empty dict (no fields to validate)."""
        errors = validate_config({})
        assert errors == []


class TestRoundTrip:
    """Tests for save then load round-trip."""

    def test_round_trip_produces_equivalent_config(self, tmp_path: Path) -> None:
        """Round-trip save then load produces equivalent ExperimentConfig."""
        original = ExperimentConfig()
        full_dict = get_full_config_dict()
        config_path = tmp_path / CONFIG_FILENAME
        save_config(full_dict, config_path)
        loaded = load_config(config_path)
        assert loaded == original
