"""Tests for the ModelConfig dataclass, ModelRegistry class, and default model loading."""

import json
import logging
from pathlib import Path

import pytest

from src.model_registry import ModelConfig, ModelRegistry, _load_default_models, registry


class TestModelConfig:
    """Tests for the ModelConfig dataclass."""

    def test_instantiation_with_required_fields(self) -> None:
        """ModelConfig can be instantiated with model_id, provider, role."""
        mc = ModelConfig(model_id="test-model", provider="anthropic", role="target")
        assert mc.model_id == "test-model"
        assert mc.provider == "anthropic"
        assert mc.role == "target"

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        mc = ModelConfig(model_id="test-model", provider="anthropic", role="target")
        assert mc.preproc_model_id is None
        assert mc.input_price_per_1m is None
        assert mc.output_price_per_1m is None
        assert mc.rate_limit_delay is None


class TestModelRegistry:
    """Tests for the ModelRegistry class."""

    @pytest.fixture()
    def sample_models(self) -> list[ModelConfig]:
        """Create a sample list of models for testing."""
        return [
            ModelConfig(
                model_id="claude-sonnet-4-20250514",
                provider="anthropic",
                role="target",
                preproc_model_id="claude-haiku-4-5-20250514",
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                rate_limit_delay=0.2,
            ),
            ModelConfig(
                model_id="claude-haiku-4-5-20250514",
                provider="anthropic",
                role="preproc",
                preproc_model_id=None,
                input_price_per_1m=1.00,
                output_price_per_1m=5.00,
                rate_limit_delay=0.1,
            ),
            ModelConfig(
                model_id="gemini-1.5-pro",
                provider="google",
                role="target",
                preproc_model_id="gemini-2.0-flash",
                input_price_per_1m=1.25,
                output_price_per_1m=5.00,
                rate_limit_delay=0.1,
            ),
            ModelConfig(
                model_id="free-model",
                provider="openrouter",
                role="target",
                preproc_model_id=None,
                input_price_per_1m=0.0,
                output_price_per_1m=0.0,
                rate_limit_delay=0.5,
            ),
        ]

    @pytest.fixture()
    def reg(self, sample_models: list[ModelConfig]) -> ModelRegistry:
        """Create a ModelRegistry from sample models."""
        return ModelRegistry(sample_models)

    def test_constructed_from_model_list(self, reg: ModelRegistry) -> None:
        """ModelRegistry can be constructed from a list of ModelConfig instances."""
        assert reg is not None

    def test_get_price_known_model(self, reg: ModelRegistry) -> None:
        """get_price returns correct (input, output) tuple for known model."""
        assert reg.get_price("claude-sonnet-4-20250514") == (3.00, 15.00)

    def test_get_price_unknown_model(self, reg: ModelRegistry) -> None:
        """get_price returns (0.0, 0.0) for unknown model."""
        assert reg.get_price("unknown-model") == (0.0, 0.0)

    def test_get_preproc_target_model(self, reg: ModelRegistry) -> None:
        """get_preproc returns preproc_model_id for target model."""
        assert reg.get_preproc("claude-sonnet-4-20250514") == "claude-haiku-4-5-20250514"

    def test_get_preproc_preproc_model(self, reg: ModelRegistry) -> None:
        """get_preproc returns None for a preproc model (no nested preproc)."""
        assert reg.get_preproc("claude-haiku-4-5-20250514") is None

    def test_get_preproc_unknown_model(self, reg: ModelRegistry) -> None:
        """get_preproc returns None for unknown model."""
        assert reg.get_preproc("unknown-model") is None

    def test_get_delay_known_model(self, reg: ModelRegistry) -> None:
        """get_delay returns configured delay for known model."""
        assert reg.get_delay("claude-sonnet-4-20250514") == 0.2

    def test_get_delay_unknown_model(self, reg: ModelRegistry) -> None:
        """get_delay returns 0.1 default for unknown model."""
        assert reg.get_delay("unknown-model") == 0.1

    def test_target_models(self, reg: ModelRegistry) -> None:
        """target_models returns only model_ids with role='target'."""
        targets = reg.target_models()
        assert "claude-sonnet-4-20250514" in targets
        assert "gemini-1.5-pro" in targets
        assert "free-model" in targets
        assert "claude-haiku-4-5-20250514" not in targets
        assert len(targets) == 3

    def test_compute_cost_known_model(self, reg: ModelRegistry) -> None:
        """compute_cost calculates correct USD amount for known model."""
        cost = reg.compute_cost("claude-sonnet-4-20250514", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.00)

    def test_compute_cost_unknown_model(self, reg: ModelRegistry) -> None:
        """compute_cost returns 0.0 for unknown model."""
        cost = reg.compute_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_compute_cost_unknown_logs_warning_once(
        self, reg: ModelRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """compute_cost logs warning for unknown model exactly once."""
        with caplog.at_level(logging.WARNING, logger="src.model_registry"):
            reg.compute_cost("brand-new-unknown", 100, 100)
            reg.compute_cost("brand-new-unknown", 200, 200)

        warning_records = [
            r for r in caplog.records
            if "brand-new-unknown" in r.message and r.levelno == logging.WARNING
        ]
        assert len(warning_records) == 1

    def test_reload_replaces_models(self, reg: ModelRegistry) -> None:
        """reload() replaces internal model data."""
        new_models = [
            ModelConfig(
                model_id="new-model",
                provider="test",
                role="target",
                input_price_per_1m=99.0,
                output_price_per_1m=99.0,
                rate_limit_delay=1.0,
            ),
        ]
        reg.reload(new_models)
        assert reg.get_price("new-model") == (99.0, 99.0)
        # Old model should no longer be found
        assert reg.get_price("claude-sonnet-4-20250514") == (0.0, 0.0)

    def test_reload_clears_warned_set(
        self, reg: ModelRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """reload() clears the warned-unknown set so warnings fire again."""
        with caplog.at_level(logging.WARNING, logger="src.model_registry"):
            reg.compute_cost("temp-unknown", 100, 100)
        assert len([r for r in caplog.records if "temp-unknown" in r.message]) == 1

        reg.reload([])
        caplog.clear()

        with caplog.at_level(logging.WARNING, logger="src.model_registry"):
            reg.compute_cost("temp-unknown", 100, 100)
        assert len([r for r in caplog.records if "temp-unknown" in r.message]) == 1

    def test_check_provider_known(self, reg: ModelRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_provider returns correct key_name and exists status."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
        result = reg.check_provider("anthropic")
        assert result["key_name"] == "ANTHROPIC_API_KEY"
        assert result["exists"] is True

    def test_check_provider_missing_key(self, reg: ModelRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_provider returns exists=False when key is not set."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = reg.check_provider("google")
        assert result["key_name"] == "GOOGLE_API_KEY"
        assert result["exists"] is False

    def test_check_provider_unknown(self, reg: ModelRegistry) -> None:
        """check_provider returns constructed key_name for unknown provider."""
        result = reg.check_provider("azure")
        assert result["key_name"] == "AZURE_API_KEY"
        assert result["exists"] is False


class TestNoneVsZero:
    """Tests for the None vs 0.0 distinction."""

    def test_none_pricing_returns_zero(self) -> None:
        """Model with None pricing returns (0.0, 0.0) from get_price."""
        mc = ModelConfig(
            model_id="null-price",
            provider="test",
            role="target",
            input_price_per_1m=None,
            output_price_per_1m=None,
        )
        reg = ModelRegistry([mc])
        assert reg.get_price("null-price") == (0.0, 0.0)

    def test_zero_pricing_returns_zero(self) -> None:
        """Model with 0.0 pricing returns (0.0, 0.0) from get_price."""
        mc = ModelConfig(
            model_id="free-price",
            provider="test",
            role="target",
            input_price_per_1m=0.0,
            output_price_per_1m=0.0,
        )
        reg = ModelRegistry([mc])
        assert reg.get_price("free-price") == (0.0, 0.0)

    def test_internal_distinction_preserved(self) -> None:
        """ModelConfig preserves None vs 0.0 internally."""
        mc_none = ModelConfig(model_id="a", provider="t", role="target", input_price_per_1m=None)
        mc_zero = ModelConfig(model_id="b", provider="t", role="target", input_price_per_1m=0.0)
        assert mc_none.input_price_per_1m is None
        assert mc_zero.input_price_per_1m == 0.0
        assert mc_none.input_price_per_1m != mc_zero.input_price_per_1m


class TestDefaultModels:
    """Tests for the default models loading."""

    def test_load_default_models_returns_8(self) -> None:
        """_load_default_models loads all 8 models from default_models.json."""
        models = _load_default_models()
        assert len(models) == 8

    def test_default_models_json_has_8_entries(self) -> None:
        """data/default_models.json contains exactly 8 model entries."""
        json_path = Path(__file__).resolve().parent.parent / "data" / "default_models.json"
        with open(json_path) as f:
            data = json.load(f)
        assert len(data["models"]) == 8

    def test_default_models_have_required_fields(self) -> None:
        """Each default model has all required fields."""
        models = _load_default_models()
        required_fields = {"model_id", "provider", "role", "input_price_per_1m", "output_price_per_1m", "rate_limit_delay"}
        for mc in models:
            for field in required_fields:
                assert getattr(mc, field) is not None, f"Model {mc.model_id} missing {field}"

    def test_default_models_4_targets_4_preproc(self) -> None:
        """Default models contain exactly 4 targets and 4 preproc models."""
        models = _load_default_models()
        targets = [m for m in models if m.role == "target"]
        preprocs = [m for m in models if m.role == "preproc"]
        assert len(targets) == 4
        assert len(preprocs) == 4

    def test_default_contains_claude_sonnet(self) -> None:
        """Default models include claude-sonnet-4-20250514."""
        models = _load_default_models()
        ids = [m.model_id for m in models]
        assert "claude-sonnet-4-20250514" in ids


class TestModuleSingleton:
    """Tests for the module-level registry singleton."""

    def test_registry_is_model_registry_instance(self) -> None:
        """Module-level registry variable is a ModelRegistry instance."""
        assert isinstance(registry, ModelRegistry)

    def test_registry_has_target_models(self) -> None:
        """Module-level registry has 4 target models loaded from defaults."""
        assert len(registry.target_models()) == 4

    def test_registry_get_price_works(self) -> None:
        """Module-level registry can look up prices."""
        price = registry.get_price("claude-sonnet-4-20250514")
        assert price == (3.0, 15.0)
