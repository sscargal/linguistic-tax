"""CLI config subcommand handlers for the Linguistic Tax research toolkit.

Provides handler functions for show-config, set-config, reset-config,
validate, diff, and list-models subcommands. All config writes use the
sparse override pattern -- only user-changed values are persisted.
"""

import json
import logging
import sys
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any

from tabulate import tabulate

from src.config import ExperimentConfig
from src.model_discovery import DiscoveredModel, discover_all_models, _get_fallback_models
from src.model_registry import registry
from src.config_manager import (
    find_config_path,
    load_config,
    save_config,
    validate_config,
    CONFIG_FILENAME,
)

logger = logging.getLogger(__name__)

FIELD_DESCRIPTIONS: dict[str, str] = {
    "models": "List of model configurations (None = use defaults)",
    "config_version": "Configuration format version",
    "base_seed": "Base random seed for reproducibility",
    "type_a_rates": "Character-level noise error rates",
    "type_a_weights": "Character mutation type weights (swap, delete, insert, substitute)",
    "repetitions": "Number of repetitions per experimental condition",
    "temperature": "LLM sampling temperature (0.0 = deterministic)",
    "prompts_path": "Path to benchmark prompts JSON file",
    "matrix_path": "Path to experiment matrix JSON file",
    "results_db_path": "Path to SQLite results database",
}


def _load_raw_overrides(config_path: Path | None = None) -> tuple[dict, Path]:
    """Load the sparse override dict from the config file.

    Reads only the raw JSON overrides, NOT the merged config. If no file
    exists, returns an empty dict with the default config path.

    Args:
        config_path: Explicit path to the config file, or None to auto-discover.

    Returns:
        Tuple of (raw overrides dict, config file path).
    """
    if config_path is None:
        config_path = find_config_path()

    if config_path is not None and config_path.exists():
        with open(config_path, "r") as f:
            raw = json.load(f)
        return raw, config_path

    return {}, Path(".") / CONFIG_FILENAME


def _format_value(value: Any) -> str:
    """Format a config value for human-readable display.

    Tuples and lists are formatted as comma-separated strings.

    Args:
        value: The config value to format.

    Returns:
        Human-readable string representation.
    """
    if isinstance(value, (tuple, list)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _json_default(obj: Any) -> Any:
    """JSON serializer for types not supported by default.

    Converts tuples to lists for JSON compatibility.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-compatible representation.

    Raises:
        TypeError: If the object type is not supported.
    """
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _coerce_value(field_name: str, raw_value: str) -> Any:
    """Coerce a string value to the correct type based on ExperimentConfig defaults.

    Uses isinstance checks on the default value to determine the target type.

    Args:
        field_name: The config field name.
        raw_value: The string value from the command line.

    Returns:
        The coerced value matching the field's default type.
    """
    default_val = getattr(ExperimentConfig(), field_name)

    try:
        if isinstance(default_val, bool):
            return raw_value.lower() in ("true", "1", "yes")
        if isinstance(default_val, int):
            return int(raw_value)
        if isinstance(default_val, float):
            return float(raw_value)
        if isinstance(default_val, tuple):
            parts = [p.strip() for p in raw_value.split(",")]
            if all(isinstance(v, float) for v in default_val):
                return tuple(float(p) for p in parts)
            return tuple(parts)
        return raw_value
    except ValueError as exc:
        print(f"Error: cannot convert '{raw_value}' for {field_name}: {exc}")
        sys.exit(1)


def handle_show_config(args: Any) -> None:
    """Display current configuration as a table or JSON.

    Shows all properties with current values, defaults, and modification
    indicators. Supports single-property queries, JSON output, and
    filtering to changed-only properties.

    Args:
        args: Parsed argparse namespace with optional property, json,
              changed, and verbose attributes.
    """
    current = load_config()
    defaults = ExperimentConfig()

    # Single property query
    if getattr(args, "property", None) is not None:
        valid_names = {f.name for f in dc_fields(ExperimentConfig)}
        if args.property not in valid_names:
            print(f"Error: unknown property '{args.property}'")
            sys.exit(1)
        value = getattr(current, args.property)
        if getattr(args, "json", False):
            print(json.dumps({args.property: value}, default=_json_default))
        else:
            print(_format_value(value))
        return

    # Build rows for table display
    rows = []
    for f in dc_fields(ExperimentConfig):
        cur_val = getattr(current, f.name)
        def_val = getattr(defaults, f.name)
        modified = "*" if cur_val != def_val else ""
        row = [f"{modified}{f.name}", _format_value(cur_val), _format_value(def_val)]
        if getattr(args, "verbose", False):
            row.append(FIELD_DESCRIPTIONS.get(f.name, ""))
        rows.append(row)

    # Filter to changed-only if requested
    if getattr(args, "changed", False):
        rows = [r for r in rows if r[0].startswith("*")]

    if getattr(args, "json", False):
        config_dict = {}
        for f in dc_fields(ExperimentConfig):
            cur_val = getattr(current, f.name)
            def_val = getattr(defaults, f.name)
            if getattr(args, "changed", False) and cur_val == def_val:
                continue
            config_dict[f.name] = cur_val
        print(json.dumps(config_dict, indent=2, default=_json_default))
    else:
        headers = ["Property", "Value", "Default"]
        if getattr(args, "verbose", False):
            headers.append("Description")
        print(tabulate(rows, headers=headers, tablefmt="simple"))


def handle_set_config(args: Any) -> None:
    """Set one or more configuration properties.

    Accepts key-value pairs, coerces types, validates, and saves to the
    sparse override config file.

    Args:
        args: Parsed argparse namespace with pairs attribute (list of strings).
    """
    pairs = getattr(args, "pairs", []) or []
    if len(pairs) % 2 != 0:
        print("Error: set-config requires key-value pairs (even number of arguments)")
        sys.exit(1)

    raw, config_path = _load_raw_overrides()
    valid_names = {f.name for f in dc_fields(ExperimentConfig)}
    defaults = ExperimentConfig()
    changes: dict[str, Any] = {}

    for i in range(0, len(pairs), 2):
        key = pairs[i]
        value_str = pairs[i + 1]

        if key not in valid_names:
            print(f"Error: unknown property '{key}'")
            sys.exit(1)

        coerced = _coerce_value(key, value_str)
        changes[key] = coerced

    # Merge changes into raw overrides
    merged = {**raw, **changes}

    # Validate before saving
    errors = validate_config(merged)
    if errors:
        for err in errors:
            print(f"Error: {err}")
        sys.exit(1)

    # Print change summary
    for key, new_val in changes.items():
        old_val = raw.get(key, getattr(defaults, key))
        print(f"{key}: {_format_value(old_val)} -> {_format_value(new_val)}")

    save_config(merged, config_path)


def handle_reset_config(args: Any) -> None:
    """Reset configuration properties to their defaults.

    Removes specified keys from the sparse override file, or deletes
    the entire config file if --all is specified.

    Args:
        args: Parsed argparse namespace with properties list and all flag.
    """
    raw, config_path = _load_raw_overrides()

    if getattr(args, "all", False):
        if config_path.exists():
            config_path.unlink()
            print("Config reset to defaults")
        else:
            print("No config file found, already using defaults")
        return

    properties = getattr(args, "properties", []) or []
    valid_names = {f.name for f in dc_fields(ExperimentConfig)}

    for prop in properties:
        if prop not in valid_names:
            print(f"Error: unknown property '{prop}'")
            sys.exit(1)
        if prop in raw:
            del raw[prop]
            print(f"{prop}: reset to default")
        else:
            print(f"{prop}: already at default")

    save_config(raw, config_path)


def handle_validate(args: Any) -> None:
    """Validate the current configuration.

    Runs validate_config on the raw overrides and reports errors.
    Exits with code 0 for valid config, 1 for invalid.

    Args:
        args: Parsed argparse namespace (no specific attributes needed).
    """
    raw, _config_path = _load_raw_overrides()
    errors = validate_config(raw)

    if errors:
        for err in errors:
            print(f"Error: {err}")
        sys.exit(1)
    else:
        print("Configuration is valid")


def handle_diff(args: Any) -> None:
    """Show properties that differ from defaults.

    Displays a table of only the properties where the current value
    differs from the ExperimentConfig default.

    Args:
        args: Parsed argparse namespace (no specific attributes needed).
    """
    current = load_config()
    defaults = ExperimentConfig()

    rows = []
    for f in dc_fields(ExperimentConfig):
        cur_val = getattr(current, f.name)
        def_val = getattr(defaults, f.name)
        if cur_val != def_val:
            rows.append([f.name, _format_value(def_val), _format_value(cur_val)])

    if not rows:
        print("No changes from defaults")
    else:
        print(tabulate(rows, headers=["Property", "Default", "Current"], tablefmt="simple"))


def _format_price(input_per_1m: float | None, output_per_1m: float | None) -> str:
    """Format pricing for display.

    Args:
        input_per_1m: Input cost per 1M tokens, or None if unknown.
        output_per_1m: Output cost per 1M tokens, or None if unknown.

    Returns:
        Formatted price string: "$X.XX / $Y.YY", "free", or "--".
    """
    if input_per_1m is None and output_per_1m is None:
        return "--"
    inp = input_per_1m if input_per_1m is not None else 0.0
    out = output_per_1m if output_per_1m is not None else 0.0
    if inp == 0.0 and out == 0.0:
        return "free"
    return f"${inp:.2f} / ${out:.2f}"


def _format_context_window(ctx: int | None) -> str:
    """Format context window size for display.

    Args:
        ctx: Context window token count, or None if unknown.

    Returns:
        Comma-separated integer string or "--" for None.
    """
    if ctx is None:
        return "--"
    return f"{ctx:,}"


def handle_list_models(args: Any) -> None:
    """List all available models with live provider discovery and pricing.

    Loads user config first so the registry reflects configured models.
    Only queries providers that have models in the registry (i.e., ones
    the user configured). Falls back to registry data when provider
    queries fail.

    Args:
        args: Parsed argparse namespace with optional json flag.
    """
    from src.config_manager import load_config

    load_config()

    # Determine which providers the user has configured
    configured_providers = {m.provider for m in registry._models.values()}
    configured_ids = set(registry._models.keys())
    provider_order = [p for p in ["anthropic", "google", "openai", "openrouter"]
                      if p in configured_providers]

    if not provider_order:
        print("No models configured. Run `propt setup` to configure providers.")
        return

    result = discover_all_models(timeout=5.0)

    all_provider_data: dict[str, list[tuple[DiscoveredModel, str]]] = {}

    for provider in provider_order:
        if provider in result.errors:
            logger.warning("%s", result.errors[provider])
            fallback_models = _get_fallback_models(provider)
            if fallback_models:
                all_provider_data[provider] = [
                    (m, "fallback") for m in fallback_models
                ]
        elif provider in result.models:
            all_provider_data[provider] = [
                (m, "configured" if m.model_id in configured_ids else "available")
                for m in result.models[provider]
            ]

    if getattr(args, "json", False):
        output_dict: dict[str, list[dict[str, Any]]] = {}
        for provider, model_entries in all_provider_data.items():
            output_dict[provider] = [
                {
                    "model_id": m.model_id,
                    "context_window": m.context_window,
                    "input_price_per_1m": m.input_price_per_1m,
                    "output_price_per_1m": m.output_price_per_1m,
                    "status": status,
                }
                for m, status in model_entries
            ]
        print(json.dumps(output_dict, indent=2))
    else:
        for provider, model_entries in all_provider_data.items():
            rows = []
            for m, status in model_entries:
                rows.append([
                    m.model_id,
                    _format_context_window(m.context_window),
                    _format_price(m.input_price_per_1m, m.output_price_per_1m),
                    status,
                ])
            print(f"\n{provider.upper()}")
            print(tabulate(
                rows,
                headers=["Model ID", "Context Window", "Pricing (per 1M tokens)", "Status"],
                tablefmt="simple",
            ))


def property_name_completer(prefix: str, parsed_args: Any, **kwargs: Any) -> list[str]:
    """Provide tab completion for ExperimentConfig property names.

    Used by argcomplete for shell tab completion of property names
    in show-config, set-config, and reset-config subcommands.

    Args:
        prefix: The current prefix typed by the user.
        parsed_args: The partially parsed argparse namespace.
        **kwargs: Additional keyword arguments from argcomplete.

    Returns:
        List of matching property names.
    """
    return [f.name for f in dc_fields(ExperimentConfig) if f.name.startswith(prefix)]
