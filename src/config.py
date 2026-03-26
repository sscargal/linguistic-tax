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
)

MAX_TOKENS_BY_BENCHMARK: dict[str, int] = {
    "humaneval": 2048,
    "mbpp": 2048,
    "gsm8k": 1024,
}


# ---------------------------------------------------------------------------
# Backward-compatibility aliases (delegate to ModelRegistry)
#
# These provide the same names that consumer modules currently import.
# Phase 17 will update consumers to use the registry directly, after which
# these aliases will be removed.
# ---------------------------------------------------------------------------

def _lazy_registry():
    """Import registry on first use to avoid circular imports."""
    from src.model_registry import registry
    return registry


class _RegistryBackedDict(dict):
    """A dict-like shim that rebuilds itself from the live registry on each access."""

    def __init__(self, builder):
        self._builder = builder
        super().__init__(builder())

    def _refresh(self):
        super().clear()
        super().update(self._builder())

    def __getitem__(self, key):
        self._refresh()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._refresh()
        return super().__contains__(key)

    def __iter__(self):
        self._refresh()
        return super().__iter__()

    def keys(self):
        self._refresh()
        return super().keys()

    def values(self):
        self._refresh()
        return super().values()

    def items(self):
        self._refresh()
        return super().items()

    def __len__(self):
        self._refresh()
        return super().__len__()

    def __repr__(self):
        self._refresh()
        return super().__repr__()

    def get(self, key, default=None):
        self._refresh()
        return super().get(key, default)


def _build_models_tuple():
    r = _lazy_registry()
    return tuple(r.target_models())


def _build_price_table():
    r = _lazy_registry()
    result = {}
    for mid, mc in r._models.items():
        inp = mc.input_price_per_1m if mc.input_price_per_1m is not None else 0.0
        out = mc.output_price_per_1m if mc.output_price_per_1m is not None else 0.0
        result[mid] = {"input_per_1m": inp, "output_per_1m": out}
    return result


def _build_preproc_map():
    r = _lazy_registry()
    result = {}
    for mid, mc in r._models.items():
        if mc.preproc_model_id is not None:
            result[mid] = mc.preproc_model_id
    return result


def _build_rate_limit_delays():
    r = _lazy_registry()
    result = {}
    for mid, mc in r._models.items():
        result[mid] = mc.rate_limit_delay if mc.rate_limit_delay is not None else 0.5
    return result


class _LazyModels:
    """Lazy tuple-like that rebuilds from registry on access."""

    def __contains__(self, item):
        return item in _build_models_tuple()

    def __iter__(self):
        return iter(_build_models_tuple())

    def __len__(self):
        return len(_build_models_tuple())

    def __repr__(self):
        return repr(_build_models_tuple())

    def __str__(self):
        return str(_build_models_tuple())

    def __eq__(self, other):
        return _build_models_tuple() == other

    def __getitem__(self, index):
        return _build_models_tuple()[index]


MODELS = _LazyModels()

PRICE_TABLE = _RegistryBackedDict(_build_price_table)

PREPROC_MODEL_MAP = _RegistryBackedDict(_build_preproc_map)

RATE_LIMIT_DELAYS = _RegistryBackedDict(_build_rate_limit_delays)


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost from token counts via the ModelRegistry.

    Backward-compatibility wrapper. Phase 17 will migrate callers to
    registry.compute_cost() directly.

    Args:
        model: Model identifier.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Returns:
        Total cost in USD.
    """
    return _lazy_registry().compute_cost(model, input_tokens, output_tokens)
