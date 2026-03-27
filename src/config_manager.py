"""Config file manager for the Linguistic Tax research toolkit.

Handles JSON config file persistence, sparse override merging with
ExperimentConfig defaults, config validation, v1-to-v2 migration,
environment loading, and registry synchronization.
"""

import json
import logging
import shutil
from dataclasses import asdict, fields
from pathlib import Path

from src.config import ExperimentConfig
from src.env_manager import load_env
from src.model_registry import ModelConfig, _load_default_models, registry

logger = logging.getLogger(__name__)

CONFIG_FILENAME: str = "experiment_config.json"

# Known providers for validation warnings
_KNOWN_PROVIDERS: set[str] = {"anthropic", "google", "openai", "openrouter"}


def find_config_path(start_dir: str = ".") -> Path | None:
    """Look for CONFIG_FILENAME in start_dir.

    Args:
        start_dir: Directory to search in. Defaults to current directory.

    Returns:
        Path to the config file if it exists, None otherwise.
    """
    path = Path(start_dir) / CONFIG_FILENAME
    if path.exists():
        return path
    return None


def _migrate_v1_to_v2(raw: dict, config_path: Path) -> dict:
    """Migrate a v1 config (flat model fields) to v2 format (models list).

    Creates a .bak backup of the original config, maps old flat fields to
    model entries using default pricing from data/default_models.json, and
    writes the migrated config back.

    Args:
        raw: The raw config dict loaded from JSON (v1 format).
        config_path: Path to the config file for backup and rewrite.

    Returns:
        The migrated config dict (v2 format).
    """
    # Create backup
    backup_path = config_path.with_suffix(".json.bak")
    shutil.copy2(config_path, backup_path)
    logger.info("Config backup saved to %s", backup_path)

    # Load default models for pricing/delay lookup
    defaults = _load_default_models()
    defaults_by_id: dict[str, ModelConfig] = {m.model_id: m for m in defaults}

    # Map old flat fields to (provider, role, default_preproc_model_id)
    OLD_FIELD_MAP: dict[str, tuple[str, str, str]] = {
        "claude_model": ("anthropic", "target", "claude-haiku-4-5-20250514"),
        "gemini_model": ("google", "target", "gemini-2.0-flash"),
        "openai_model": ("openai", "target", "gpt-4o-mini-2024-07-18"),
        "openrouter_model": ("openrouter", "target", "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"),
    }

    models_list: list[dict] = []
    removed_fields: list[str] = []
    seen_model_ids: set[str] = set()

    # Process target model fields
    for field_name, (provider, role, default_preproc) in OLD_FIELD_MAP.items():
        if field_name in raw:
            model_id = raw[field_name]
        else:
            # Use default model_id from defaults for this provider
            provider_targets = [
                m for m in defaults
                if m.provider == provider and m.role == "target"
            ]
            if provider_targets:
                model_id = provider_targets[0].model_id
            else:
                continue

        # Look up default pricing/delay
        mc = defaults_by_id.get(model_id)
        entry: dict = {
            "model_id": model_id,
            "provider": provider,
            "role": role,
            "preproc_model_id": default_preproc,
        }
        if mc:
            entry["input_price_per_1m"] = mc.input_price_per_1m
            entry["output_price_per_1m"] = mc.output_price_per_1m
            entry["rate_limit_delay"] = mc.rate_limit_delay
        else:
            entry["input_price_per_1m"] = None
            entry["output_price_per_1m"] = None
            entry["rate_limit_delay"] = None

        models_list.append(entry)
        seen_model_ids.add(model_id)

        if field_name in raw:
            removed_fields.append(field_name)

        # Also add the preproc model as a separate entry
        preproc_id = default_preproc
        if preproc_id and preproc_id not in seen_model_ids:
            pmc = defaults_by_id.get(preproc_id)
            preproc_entry: dict = {
                "model_id": preproc_id,
                "provider": provider,
                "role": "preproc",
                "preproc_model_id": None,
            }
            if pmc:
                preproc_entry["input_price_per_1m"] = pmc.input_price_per_1m
                preproc_entry["output_price_per_1m"] = pmc.output_price_per_1m
                preproc_entry["rate_limit_delay"] = pmc.rate_limit_delay
            else:
                preproc_entry["input_price_per_1m"] = None
                preproc_entry["output_price_per_1m"] = None
                preproc_entry["rate_limit_delay"] = None
            models_list.append(preproc_entry)
            seen_model_ids.add(preproc_id)

    # Handle openrouter_preproc_model separately (if present as override)
    if "openrouter_preproc_model" in raw:
        preproc_id = raw["openrouter_preproc_model"]
        if preproc_id not in seen_model_ids:
            pmc = defaults_by_id.get(preproc_id)
            preproc_entry = {
                "model_id": preproc_id,
                "provider": "openrouter",
                "role": "preproc",
                "preproc_model_id": None,
            }
            if pmc:
                preproc_entry["input_price_per_1m"] = pmc.input_price_per_1m
                preproc_entry["output_price_per_1m"] = pmc.output_price_per_1m
                preproc_entry["rate_limit_delay"] = pmc.rate_limit_delay
            else:
                preproc_entry["input_price_per_1m"] = None
                preproc_entry["output_price_per_1m"] = None
                preproc_entry["rate_limit_delay"] = None
            models_list.append(preproc_entry)
        removed_fields.append("openrouter_preproc_model")

    # Remove old flat fields from raw dict
    for field_name in list(OLD_FIELD_MAP.keys()) + ["openrouter_preproc_model"]:
        raw.pop(field_name, None)

    # Add v2 fields
    raw["models"] = models_list
    raw["config_version"] = 2

    logger.info(
        "Migrated config v1->v2: removed fields %s, added %d models",
        removed_fields, len(models_list),
    )

    # Write migrated config
    save_config(raw, config_path)

    return raw


def load_config(config_path: Path | None = None) -> ExperimentConfig:
    """Load config from a JSON file and merge with ExperimentConfig defaults.

    Calls load_env() first to ensure API keys are available, then loads the
    config file. Auto-migrates v1 configs to v2. If the config includes a
    models list, reloads the ModelRegistry with those models.

    If config_path is None, calls find_config_path(). If no file found,
    returns ExperimentConfig() with all defaults.

    Unknown JSON keys are silently ignored for forward compatibility.

    Args:
        config_path: Path to the JSON config file, or None to auto-discover.

    Returns:
        An ExperimentConfig instance with overrides applied.
    """
    # Load environment variables first
    load_env()

    if config_path is None:
        config_path = find_config_path()

    if config_path is None or not config_path.exists():
        logger.debug("No config file found, using defaults")
        return ExperimentConfig()

    logger.info("Loading config from %s", config_path)
    with open(config_path, "r") as f:
        raw = json.load(f)

    # Auto-migrate v1 configs
    if "config_version" not in raw:
        raw = _migrate_v1_to_v2(raw, config_path)

    # Filter to valid field names only
    valid_names = {field.name for field in fields(ExperimentConfig)}
    filtered = {k: v for k, v in raw.items() if k in valid_names}

    # Convert lists back to tuples for tuple-typed fields
    defaults = ExperimentConfig()
    for field in fields(ExperimentConfig):
        if field.name in filtered and isinstance(getattr(defaults, field.name), tuple):
            filtered[field.name] = tuple(filtered[field.name])

    config = ExperimentConfig(**filtered)

    # Reload registry if config has a models list
    if config.models is not None:
        model_configs = [
            ModelConfig(
                model_id=m["model_id"],
                provider=m.get("provider", "unknown"),
                role=m.get("role", "target"),
                preproc_model_id=m.get("preproc_model_id"),
                input_price_per_1m=m.get("input_price_per_1m"),
                output_price_per_1m=m.get("output_price_per_1m"),
                rate_limit_delay=m.get("rate_limit_delay"),
            )
            for m in config.models
        ]
        registry.reload(model_configs)

    return config


def save_config(config: dict, config_path: Path | None = None) -> Path:
    """Write a config dict to JSON.

    Converts tuple values to lists before serializing.

    Args:
        config: Dictionary of config values to save.
        config_path: Path to write to. If None, uses CWD / CONFIG_FILENAME.

    Returns:
        The path written to.
    """
    if config_path is None:
        config_path = Path(".") / CONFIG_FILENAME

    # Convert tuples to lists for JSON serialization
    serializable = {}
    for k, v in config.items():
        if isinstance(v, tuple):
            serializable[k] = list(v)
        else:
            serializable[k] = v

    logger.info("Saving config to %s", config_path)
    with open(config_path, "w") as f:
        json.dump(serializable, f, indent=2)
        f.write("\n")

    return config_path


def get_full_config_dict() -> dict:
    """Return all ExperimentConfig fields with defaults, tuples as lists.

    Creates a default ExperimentConfig, converts to dict, and replaces
    tuple values with lists for JSON compatibility.

    Returns:
        Complete config dict with all default values.
    """
    d = asdict(ExperimentConfig())
    for k, v in d.items():
        if isinstance(v, tuple):
            d[k] = list(v)
    return d


def validate_config(config_dict: dict) -> list[str]:
    """Validate config values and return a list of error messages.

    Only validates keys that are present in the dict. An empty dict
    is considered valid (no fields to validate). Unknown model IDs
    produce warnings (not errors) for forward compatibility.

    Args:
        config_dict: Dictionary of config key-value pairs to validate.

    Returns:
        List of error message strings. Empty list means valid.
    """
    errors: list[str] = []

    # Models list: warn on unknown providers (not model IDs — users can configure any model)
    if "models" in config_dict and config_dict["models"] is not None:
        for model_entry in config_dict["models"]:
            provider = model_entry.get("provider", "")
            model_id = model_entry.get("model_id", "")
            if provider and provider not in _KNOWN_PROVIDERS:
                logger.warning(
                    "Unknown provider '%s' for model '%s'. "
                    "Known providers: %s",
                    provider, model_id, ", ".join(sorted(_KNOWN_PROVIDERS)),
                )

    # type_a_rates: each must be in [0, 1]
    if "type_a_rates" in config_dict:
        rates = config_dict["type_a_rates"]
        if isinstance(rates, (list, tuple)):
            for i, rate in enumerate(rates):
                if not (0 <= rate <= 1):
                    errors.append(
                        f"type_a_rates[{i}]: {rate} is outside valid range [0, 1]"
                    )

    # type_a_weights: each must be in [0, 1]
    if "type_a_weights" in config_dict:
        weights = config_dict["type_a_weights"]
        if isinstance(weights, (list, tuple)):
            for i, weight in enumerate(weights):
                if not (0 <= weight <= 1):
                    errors.append(
                        f"type_a_weights[{i}]: {weight} is outside valid range [0, 1]"
                    )

    # repetitions: must be >= 1
    if "repetitions" in config_dict:
        if config_dict["repetitions"] < 1:
            errors.append(
                f"repetitions: {config_dict['repetitions']} must be >= 1"
            )

    # temperature: must be >= 0
    if "temperature" in config_dict:
        if config_dict["temperature"] < 0:
            errors.append(
                f"temperature: {config_dict['temperature']} must be >= 0"
            )

    # prompts_path: file must exist if specified
    if "prompts_path" in config_dict:
        if not Path(config_dict["prompts_path"]).exists():
            errors.append(
                f"prompts_path: file not found: {config_dict['prompts_path']}"
            )

    # matrix_path: file must exist if specified
    if "matrix_path" in config_dict:
        if not Path(config_dict["matrix_path"]).exists():
            errors.append(
                f"matrix_path: file not found: {config_dict['matrix_path']}"
            )

    # results_db_path: parent directory must exist or be creatable (no error)
    # Intentionally not validated -- it gets created at runtime

    return errors
