"""Tests for the configuration module."""

import dataclasses

import pytest

from src.config import (
    ExperimentConfig, derive_seed, NOISE_TYPES, INTERVENTIONS, MODELS,
    PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS, OPENROUTER_BASE_URL,
    compute_cost,
)


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

    def test_openai_model_pinned(self, sample_config):
        """OpenAI model version is pinned."""
        assert sample_config.openai_model == "gpt-4o-2024-11-20"

    def test_openrouter_model_pinned(self, sample_config):
        """OpenRouter target model version is pinned."""
        assert sample_config.openrouter_model == "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

    def test_openrouter_preproc_model_pinned(self, sample_config):
        """OpenRouter preproc model version is pinned."""
        assert sample_config.openrouter_preproc_model == "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"


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
        """MODELS has exactly 4 entries (3 direct + 1 OpenRouter)."""
        assert len(MODELS) == 4

    def test_models_contents(self):
        """MODELS contains the pinned model versions."""
        assert "claude-sonnet-4-20250514" in MODELS
        assert "gemini-1.5-pro" in MODELS
        assert "gpt-4o-2024-11-20" in MODELS

    def test_price_table_openai(self):
        """PRICE_TABLE contains GPT-4o and GPT-4o-mini pricing entries."""
        assert PRICE_TABLE["gpt-4o-2024-11-20"] == {"input_per_1m": 2.50, "output_per_1m": 10.00}
        assert PRICE_TABLE["gpt-4o-mini-2024-07-18"] == {"input_per_1m": 0.15, "output_per_1m": 0.60}

    def test_preproc_map_openai(self):
        """PREPROC_MODEL_MAP maps GPT-4o to GPT-4o-mini."""
        assert PREPROC_MODEL_MAP["gpt-4o-2024-11-20"] == "gpt-4o-mini-2024-07-18"

    def test_rate_limit_delays_openai(self):
        """RATE_LIMIT_DELAYS contains entries for GPT-4o and GPT-4o-mini."""
        assert RATE_LIMIT_DELAYS["gpt-4o-2024-11-20"] == 0.2
        assert RATE_LIMIT_DELAYS["gpt-4o-mini-2024-07-18"] == 0.1


class TestOpenRouterConfig:
    """Tests for OpenRouter-specific configuration entries."""

    def test_openrouter_base_url_default(self):
        """OPENROUTER_BASE_URL defaults to OpenRouter API endpoint."""
        assert OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"

    def test_openrouter_model_in_models(self):
        """OpenRouter target model is in the MODELS tuple."""
        assert "openrouter/nvidia/nemotron-3-super-120b-a12b:free" in MODELS

    def test_openrouter_target_in_price_table(self):
        """OpenRouter target model has zero-cost pricing."""
        entry = PRICE_TABLE["openrouter/nvidia/nemotron-3-super-120b-a12b:free"]
        assert entry["input_per_1m"] == 0.0
        assert entry["output_per_1m"] == 0.0

    def test_openrouter_preproc_in_price_table(self):
        """OpenRouter preproc model has zero-cost pricing."""
        entry = PRICE_TABLE["openrouter/nvidia/nemotron-3-nano-30b-a3b:free"]
        assert entry["input_per_1m"] == 0.0
        assert entry["output_per_1m"] == 0.0

    def test_openrouter_preproc_map(self):
        """PREPROC_MODEL_MAP maps OpenRouter target to preproc model."""
        assert PREPROC_MODEL_MAP["openrouter/nvidia/nemotron-3-super-120b-a12b:free"] == \
            "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"

    def test_openrouter_rate_limit_target(self):
        """RATE_LIMIT_DELAYS has OpenRouter target model at 0.5s."""
        assert RATE_LIMIT_DELAYS["openrouter/nvidia/nemotron-3-super-120b-a12b:free"] == 0.5

    def test_openrouter_rate_limit_preproc(self):
        """RATE_LIMIT_DELAYS has OpenRouter preproc model at 0.5s."""
        assert RATE_LIMIT_DELAYS["openrouter/nvidia/nemotron-3-nano-30b-a3b:free"] == 0.5

    def test_compute_cost_zero_for_free_model(self):
        """compute_cost returns exactly 0.0 for free OpenRouter target model."""
        cost = compute_cost("openrouter/nvidia/nemotron-3-super-120b-a12b:free", 10000, 5000)
        assert cost == 0.0

    def test_compute_cost_zero_for_free_preproc(self):
        """compute_cost returns exactly 0.0 for free OpenRouter preproc model."""
        cost = compute_cost("openrouter/nvidia/nemotron-3-nano-30b-a3b:free", 10000, 5000)
        assert cost == 0.0
