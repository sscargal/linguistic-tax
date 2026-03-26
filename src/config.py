"""Configuration module for the Linguistic Tax research toolkit.

Provides experiment parameters, noise settings, file paths, and deterministic
seed derivation for reproducible experiments. Model pricing, preproc mappings,
and rate limit delays are now in src/model_registry.py.
"""

import hashlib
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL: str = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)


@dataclass
class ExperimentConfig:
    """Experiment configuration with config-driven model list.

    All experimental parameters are defined here as defaults.
    Models are configured via the ``models`` list (populated from config JSON)
    or left as None to use defaults from data/default_models.json.
    """

    models: list[dict] | None = None
    config_version: int = 2
    base_seed: int = 42
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    type_a_weights: tuple[float, ...] = (0.40, 0.25, 0.20, 0.15)
    repetitions: int = 5
    temperature: float = 0.0
    prompts_path: str = "data/prompts.json"
    matrix_path: str = "data/experiment_matrix.json"
    results_db_path: str = "results/results.db"


def derive_seed(
    base_seed: int, prompt_id: str, noise_type: str, noise_level: str
) -> int:
    """Derive a deterministic seed from experimental parameters.

    Uses SHA-256 hashing to produce a uniformly distributed seed
    from the combination of base seed and experimental condition.
    This avoids global random state contamination.

    Args:
        base_seed: The base random seed (typically 42).
        prompt_id: Unique identifier for the prompt.
        noise_type: Type of noise (e.g., "type_a", "type_b").
        noise_level: Level of noise (e.g., "5", "10", "20").

    Returns:
        A deterministic integer seed derived from the inputs.
    """
    key = f"{base_seed}:{prompt_id}:{noise_type}:{noise_level}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


# Module-level constants enumerating all experimental conditions

NOISE_TYPES: tuple[str, ...] = (
    "clean",
    "type_a_5pct",
    "type_a_10pct",
    "type_a_20pct",
    "type_b_mandarin",
    "type_b_spanish",
    "type_b_japanese",
    "type_b_mixed",
)

INTERVENTIONS: tuple[str, ...] = (
    "raw",
    "self_correct",
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "prompt_repetition",
    # Emphasis experiments (Phase 22)
    "emphasis_bold",
    "emphasis_caps",
    "emphasis_quotes",
    "emphasis_instruction_caps",
    "emphasis_instruction_bold",
    "emphasis_lowercase_initial",
    "emphasis_mixed",
    "emphasis_aggressive_caps",
)

MAX_TOKENS_BY_BENCHMARK: dict[str, int] = {
    "humaneval": 2048,
    "mbpp": 2048,
    "gsm8k": 1024,
}
