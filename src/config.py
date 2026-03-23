"""Configuration module for the Linguistic Tax research toolkit.

Provides pinned model versions, experiment parameters, noise settings,
file paths, and deterministic seed derivation for reproducible experiments.
"""

import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable experiment configuration with all pinned values.

    All experimental parameters are defined here as defaults.
    The frozen constraint ensures no accidental mutation during runs.
    """

    # Model versions (pinned)
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-1.5-pro"
    openai_model: str = "gpt-4o-2024-11-20"

    # Seeds
    base_seed: int = 42

    # Noise parameters
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    type_a_weights: tuple[float, ...] = (0.40, 0.25, 0.20, 0.15)

    # Experiment parameters
    repetitions: int = 5
    temperature: float = 0.0

    # Paths
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
)

MODELS: tuple[str, ...] = (
    "claude-sonnet-4-20250514",
    "gemini-1.5-pro",
    "gpt-4o-2024-11-20",
)

# ---------------------------------------------------------------------------
# Pricing, token limits, and pre-processor configuration
# ---------------------------------------------------------------------------

PRICE_TABLE: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    "claude-haiku-4-5-20250514": {"input_per_1m": 1.00, "output_per_1m": 5.00},
    "gemini-1.5-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00},
    "gemini-2.0-flash": {"input_per_1m": 0.10, "output_per_1m": 0.40},
    "gpt-4o-2024-11-20": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-4o-mini-2024-07-18": {"input_per_1m": 0.15, "output_per_1m": 0.60},
}

MAX_TOKENS_BY_BENCHMARK: dict[str, int] = {
    "humaneval": 2048,
    "mbpp": 2048,
    "gsm8k": 1024,
}

PREPROC_MODEL_MAP: dict[str, str] = {
    "claude-sonnet-4-20250514": "claude-haiku-4-5-20250514",
    "gemini-1.5-pro": "gemini-2.0-flash",
    "gpt-4o-2024-11-20": "gpt-4o-mini-2024-07-18",
}

RATE_LIMIT_DELAYS: dict[str, float] = {
    "claude-sonnet-4-20250514": 0.2,
    "claude-haiku-4-5-20250514": 0.1,
    "gemini-1.5-pro": 0.1,
    "gemini-2.0-flash": 0.05,
    "gpt-4o-2024-11-20": 0.2,
    "gpt-4o-mini-2024-07-18": 0.1,
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost from token counts and price table.

    Args:
        model: Model identifier (must be a key in PRICE_TABLE).
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Returns:
        Total cost in USD.

    Raises:
        KeyError: If model is not found in PRICE_TABLE.
    """
    prices = PRICE_TABLE[model]
    return (
        input_tokens * prices["input_per_1m"] / 1_000_000
        + output_tokens * prices["output_per_1m"] / 1_000_000
    )
