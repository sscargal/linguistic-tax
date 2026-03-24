"""Config file manager for the Linguistic Tax research toolkit.

Handles JSON config file persistence, sparse override merging with
ExperimentConfig defaults, and config validation. Foundation for the
setup wizard and CLI config subcommands.
"""

import json
import logging
from dataclasses import asdict, fields
from pathlib import Path

from src.config import ExperimentConfig, PRICE_TABLE

logger = logging.getLogger(__name__)

CONFIG_FILENAME: str = "experiment_config.json"


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


def load_config(config_path: Path | None = None) -> ExperimentConfig:
    """Load config from a JSON file and merge with ExperimentConfig defaults.

    If config_path is None, calls find_config_path(). If no file found,
    returns ExperimentConfig() with all defaults. If file found, reads JSON,
    filters to valid ExperimentConfig field names, converts list values to
    tuples for tuple-typed fields, and returns a new ExperimentConfig.

    Unknown JSON keys are silently ignored for forward compatibility.

    Args:
        config_path: Path to the JSON config file, or None to auto-discover.

    Returns:
        An ExperimentConfig instance with overrides applied.
    """
    if config_path is None:
        config_path = find_config_path()

    if config_path is None or not config_path.exists():
        logger.debug("No config file found, using defaults")
        return ExperimentConfig()

    logger.info("Loading config from %s", config_path)
    with open(config_path, "r") as f:
        raw = json.load(f)

    # Filter to valid field names only
    valid_names = {field.name for field in fields(ExperimentConfig)}
    filtered = {k: v for k, v in raw.items() if k in valid_names}

    # Convert lists back to tuples for tuple-typed fields
    defaults = ExperimentConfig()
    for field in fields(ExperimentConfig):
        if field.name in filtered and isinstance(getattr(defaults, field.name), tuple):
            filtered[field.name] = tuple(filtered[field.name])

    return ExperimentConfig(**filtered)


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
    is considered valid (no fields to validate). An empty return list
    means the config is valid.

    Args:
        config_dict: Dictionary of config key-value pairs to validate.

    Returns:
        List of error message strings. Empty list means valid.
    """
    errors: list[str] = []

    # Model fields: must be in PRICE_TABLE
    model_fields = [
        "claude_model",
        "gemini_model",
        "openai_model",
        "openrouter_model",
        "openrouter_preproc_model",
    ]
    for field_name in model_fields:
        if field_name in config_dict:
            value = config_dict[field_name]
            if value not in PRICE_TABLE:
                errors.append(
                    f"{field_name}: unknown model '{value}'. "
                    f"Must be one of: {', '.join(sorted(PRICE_TABLE.keys()))}"
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
