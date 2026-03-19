"""Tests for the configuration module."""

import dataclasses

import pytest

from src.config import ExperimentConfig, derive_seed, NOISE_TYPES, INTERVENTIONS, MODELS


class TestExperimentConfig:
    """Tests for ExperimentConfig frozen dataclass."""

    def test_config_is_frozen(self, sample_config):
        """ExperimentConfig is frozen -- assigning attribute raises FrozenInstanceError."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_config.base_seed = 99

    def test_claude_model_pinned(self, sample_config):
        """Claude model version is pinned."""
        assert sample_config.claude_model == "claude-sonnet-4-20250514"

    def test_gemini_model_pinned(self, sample_config):
        """Gemini model version is pinned."""
        assert sample_config.gemini_model == "gemini-1.5-pro"

    def test_base_seed(self, sample_config):
        """Base seed is 42."""
        assert sample_config.base_seed == 42

    def test_type_a_rates(self, sample_config):
        """Type A noise rates are (0.05, 0.10, 0.20)."""
        assert sample_config.type_a_rates == (0.05, 0.10, 0.20)

    def test_type_a_weights(self, sample_config):
        """Type A mutation weights: adj_swap, omission, doubling, transposition."""
        assert sample_config.type_a_weights == (0.40, 0.25, 0.20, 0.15)

    def test_repetitions(self, sample_config):
        """Repetitions per condition is 5."""
        assert sample_config.repetitions == 5

    def test_temperature(self, sample_config):
        """Temperature is 0.0."""
        assert sample_config.temperature == 0.0

    def test_prompts_path(self, sample_config):
        """Prompts path is data/prompts.json."""
        assert sample_config.prompts_path == "data/prompts.json"

    def test_matrix_path(self, sample_config):
        """Matrix path is data/experiment_matrix.json."""
        assert sample_config.matrix_path == "data/experiment_matrix.json"

    def test_results_db_path(self, sample_config):
        """Results DB path is results/results.db."""
        assert sample_config.results_db_path == "results/results.db"


class TestDeriveSeed:
    """Tests for deterministic seed derivation."""

    def test_derive_seed_returns_int(self):
        """derive_seed returns an integer."""
        result = derive_seed(42, "humaneval_042", "type_a", "10")
        assert isinstance(result, int)

    def test_derive_seed_deterministic(self):
        """Calling derive_seed twice with same args returns same value."""
        seed1 = derive_seed(42, "humaneval_042", "type_a", "10")
        seed2 = derive_seed(42, "humaneval_042", "type_a", "10")
        assert seed1 == seed2

    def test_derive_seed_different_args(self):
        """Different args produce different seeds."""
        seed1 = derive_seed(42, "humaneval_042", "type_a", "10")
        seed2 = derive_seed(42, "humaneval_042", "type_a", "20")
        assert seed1 != seed2

    def test_derive_seed_uses_hashlib(self):
        """derive_seed uses hashlib.sha256, not global random state."""
        import hashlib
        key = "42:humaneval_042:type_a:10"
        expected = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        result = derive_seed(42, "humaneval_042", "type_a", "10")
        assert result == expected


class TestConstants:
    """Tests for module-level constants."""

    def test_noise_types_count(self):
        """NOISE_TYPES has exactly 8 entries."""
        assert len(NOISE_TYPES) == 8

    def test_noise_types_contents(self):
        """NOISE_TYPES contains all expected noise conditions."""
        expected = {
            "clean", "type_a_5pct", "type_a_10pct", "type_a_20pct",
            "type_b_mandarin", "type_b_spanish", "type_b_japanese", "type_b_mixed",
        }
        assert set(NOISE_TYPES) == expected

    def test_interventions_count(self):
        """INTERVENTIONS has exactly 5 entries."""
        assert len(INTERVENTIONS) == 5

    def test_interventions_contents(self):
        """INTERVENTIONS contains all expected intervention types."""
        expected = {
            "raw", "self_correct", "pre_proc_sanitize",
            "pre_proc_sanitize_compress", "prompt_repetition",
        }
        assert set(INTERVENTIONS) == expected

    def test_models_count(self):
        """MODELS has exactly 2 entries."""
        assert len(MODELS) == 2

    def test_models_contents(self):
        """MODELS contains the pinned model versions."""
        assert "claude-sonnet-4-20250514" in MODELS
        assert "gemini-1.5-pro" in MODELS
