"""Model registry providing config-driven pricing, preproc mappings, and rate limit delays.

Replaces the hardcoded PRICE_TABLE, PREPROC_MODEL_MAP, and RATE_LIMIT_DELAYS
module-level constants from config.py with a centralized ModelRegistry class.

The module-level ``registry`` singleton is initialized from
``data/default_models.json`` at import time. Callers that load a user config
should call ``registry.reload(models)`` to replace the defaults.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Provider-to-API-key mapping (hardcoded per user decision)
_PROVIDER_KEY_MAP: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


@dataclass
class ModelConfig:
    """Configuration for a single LLM model.

    Attributes:
        model_id: Unique model identifier (e.g. "claude-sonnet-4-20250514").
        provider: API provider name ("anthropic", "google", "openai", "openrouter").
        role: Model role -- "target" for experiment models, "preproc" for preprocessor models.
        preproc_model_id: Associated preprocessor model_id (only for role="target").
        input_price_per_1m: Cost per 1M input tokens in USD. None = unknown, 0.0 = free.
        output_price_per_1m: Cost per 1M output tokens in USD. None = unknown, 0.0 = free.
        rate_limit_delay: Seconds to wait between API calls. None = unknown (default 0.5s).
    """

    model_id: str
    provider: str
    role: str
    preproc_model_id: str | None = None
    input_price_per_1m: float | None = None
    output_price_per_1m: float | None = None
    rate_limit_delay: float | None = None


def _load_default_models() -> list[ModelConfig]:
    """Load curated default model configurations from data/default_models.json.

    Returns:
        List of ModelConfig instances for all default models.
    """
    json_path = Path(__file__).resolve().parent.parent / "data" / "default_models.json"
    with open(json_path) as f:
        data = json.load(f)

    models: list[ModelConfig] = []
    for entry in data["models"]:
        models.append(
            ModelConfig(
                model_id=entry["model_id"],
                provider=entry["provider"],
                role=entry["role"],
                preproc_model_id=entry.get("preproc_model_id"),
                input_price_per_1m=entry.get("input_price_per_1m"),
                output_price_per_1m=entry.get("output_price_per_1m"),
                rate_limit_delay=entry.get("rate_limit_delay"),
            )
        )
    return models


class ModelRegistry:
    """Registry of configured models with pricing, preproc mapping, and delays.

    Provides centralized access to model configuration data. Unknown models
    are handled defensively -- returning safe defaults instead of raising errors.
    """

    def __init__(self, models: list[ModelConfig]) -> None:
        """Initialize the registry from a list of model configurations.

        Args:
            models: List of ModelConfig instances to register.
        """
        self._models: dict[str, ModelConfig] = {m.model_id: m for m in models}
        self._warned_unknown: set[str] = set()

    def get_price(self, model_id: str) -> tuple[float, float]:
        """Return (input_per_1m, output_per_1m) pricing for a model.

        For unknown models, returns (0.0, 0.0). For known models with None
        pricing fields, returns 0.0 for the None field.

        Args:
            model_id: The model identifier to look up.

        Returns:
            Tuple of (input_price_per_1m, output_price_per_1m) in USD.
        """
        mc = self._models.get(model_id)
        if mc is None:
            return (0.0, 0.0)
        inp = mc.input_price_per_1m if mc.input_price_per_1m is not None else 0.0
        out = mc.output_price_per_1m if mc.output_price_per_1m is not None else 0.0
        return (inp, out)

    def get_preproc(self, model_id: str) -> str | None:
        """Return the preprocessor model_id for a target model.

        Args:
            model_id: The model identifier to look up.

        Returns:
            The preproc_model_id if the model is known and has one, else None.
        """
        mc = self._models.get(model_id)
        if mc is None:
            return None
        return mc.preproc_model_id

    def get_delay(self, model_id: str) -> float:
        """Return the rate limit delay for a model.

        Args:
            model_id: The model identifier to look up.

        Returns:
            Delay in seconds. Defaults to 0.5 for unknown models or models
            with None delay.
        """
        mc = self._models.get(model_id)
        if mc is None:
            return 0.5
        return mc.rate_limit_delay if mc.rate_limit_delay is not None else 0.5

    def target_models(self) -> list[str]:
        """Return model_ids for all models with role='target'.

        Returns:
            List of target model identifiers.
        """
        return [m.model_id for m in self._models.values() if m.role == "target"]

    def compute_cost(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Compute cost in USD from token counts.

        For unknown models, logs a warning once per model_id and returns 0.0.

        Args:
            model_id: The model identifier.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.

        Returns:
            Total cost in USD.
        """
        if model_id not in self._models:
            if model_id not in self._warned_unknown:
                logger.warning(
                    "Unknown model '%s': using $0.00 pricing. "
                    "Run 'propt list-models' to see configured models.",
                    model_id,
                )
                self._warned_unknown.add(model_id)
            return 0.0
        inp, out = self.get_price(model_id)
        return input_tokens * inp / 1_000_000 + output_tokens * out / 1_000_000

    def reload(self, models: list[ModelConfig]) -> None:
        """Replace internal model data with a new set of models.

        Clears the warned-unknown set so warnings can fire again for
        previously unknown models.

        Args:
            models: New list of ModelConfig instances.
        """
        self._models = {m.model_id: m for m in models}
        self._warned_unknown.clear()

    def check_provider(self, provider: str) -> dict[str, bool]:
        """Check if an API key exists in the environment for a provider.

        Args:
            provider: Provider name (e.g. "anthropic", "google").

        Returns:
            Dict with "key_name" (str) and "exists" (bool) keys.
        """
        key_name = _PROVIDER_KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")
        return {
            "key_name": key_name,
            "exists": bool(os.environ.get(key_name, "")),
        }


def _build_registry() -> ModelRegistry:
    """Build the default ModelRegistry from data/default_models.json.

    Returns:
        A ModelRegistry initialized with all default models.
    """
    models = _load_default_models()
    return ModelRegistry(models)


registry: ModelRegistry = _build_registry()
