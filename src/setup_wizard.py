"""Interactive setup wizard for the Linguistic Tax research toolkit.

Guides users through multi-provider selection, API key collection with .env
persistence, free-text model entry with live browser, model validation pings,
budget preview, and config file generation.
"""

import builtins
import importlib.metadata
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

import anthropic
import openai
from google import genai

from src.config import OPENROUTER_BASE_URL
from src.model_registry import ModelConfig, registry
from src.config_manager import (
    get_full_config_dict,
    save_config,
    validate_config,
    find_config_path,
)
from src.env_manager import write_env
from src.execution_summary import estimate_cost

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROVIDER_NAMES: dict[str, str] = {
    "anthropic": "Anthropic (Claude)",
    "google": "Google (Gemini)",
    "openai": "OpenAI (GPT)",
    "openrouter": "OpenRouter",
}

PROVIDER_ORDER: list[str] = ["anthropic", "google", "openai", "openrouter"]

PROVIDER_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# ---------------------------------------------------------------------------
# Default model lookup from registry
# ---------------------------------------------------------------------------

_PREFIX_MAP: dict[str, str] = {
    "anthropic": "claude",
    "google": "gemini",
    "openai": "gpt",
    "openrouter": "openrouter/",
}


def _build_default_target_models() -> dict[str, str]:
    """Build default target model mapping from registry.

    For each provider in PROVIDER_ORDER, find the first target model
    whose model_id starts with the provider prefix.

    Returns:
        Dict mapping provider key to default target model_id.
    """
    targets = registry.target_models()
    defaults: dict[str, str] = {}
    for provider in PROVIDER_ORDER:
        prefix = _PREFIX_MAP.get(provider, provider)
        for model_id in targets:
            if model_id.startswith(prefix):
                defaults[provider] = model_id
                break
    return defaults


DEFAULT_TARGET_MODELS: dict[str, str] = _build_default_target_models()

# ---------------------------------------------------------------------------
# Required packages for environment check
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES: list[str] = [
    "anthropic",
    "google-genai",
    "openai",
    "scipy",
    "statsmodels",
    "pandas",
    "matplotlib",
    "pytest",
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _mask_key(key: str) -> str:
    """Mask an API key for safe display.

    Shows first 6 and last 4 characters for keys longer than 10 chars,
    otherwise returns '****'.

    Args:
        key: The API key string to mask.

    Returns:
        Masked key string.
    """
    if len(key) <= 10:
        return "****"
    return f"{key[:6]}...{key[-4:]}"


def _parse_provider_selection(raw: str, available: list[str]) -> list[str]:
    """Parse comma-separated provider numbers into provider keys.

    Numbers are 1-indexed. Invalid entries are skipped. If result is
    empty, defaults to [available[0]].

    Args:
        raw: User input string (e.g., "1,3").
        available: Ordered list of provider keys.

    Returns:
        List of selected provider keys.
    """
    selected: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < len(available):
                provider = available[idx]
                if provider not in selected:
                    selected.append(provider)
        except ValueError:
            continue
    if not selected:
        selected = [available[0]]
    return selected


def _detect_existing_config() -> dict | None:
    """Detect and parse an existing config file.

    Calls find_config_path(). If found, extracts the models list and
    groups by provider.

    Returns:
        Dict with 'providers' list and 'models' dict mapping provider
        to {'target': model_id, 'preproc': model_id}, or None if no config.
    """
    config_path = find_config_path()
    if config_path is None:
        return None

    try:
        with open(config_path) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    models_list = raw.get("models")
    if not models_list:
        return None

    providers: list[str] = []
    models: dict[str, dict[str, str]] = {}

    for entry in models_list:
        provider = entry.get("provider", "")
        role = entry.get("role", "")
        model_id = entry.get("model_id", "")

        if provider not in models:
            models[provider] = {}
        if provider not in providers and role == "target":
            providers.append(provider)

        if role == "target":
            models[provider]["target"] = model_id
            preproc = entry.get("preproc_model_id")
            if preproc:
                models[provider]["preproc"] = preproc

    return {"providers": providers, "models": models}


def _handle_existing_config(
    existing: dict, input_fn: Callable[..., str]
) -> str:
    """Show existing config and ask user what to do.

    Args:
        existing: Dict from _detect_existing_config().
        input_fn: Callable for reading user input.

    Returns:
        One of 'add', 'reconfigure', or 'fresh'.
    """
    print("\nExisting configuration found:")
    for provider in existing["providers"]:
        model_info = existing["models"].get(provider, {})
        target = model_info.get("target", "unknown")
        preproc = model_info.get("preproc", "none")
        name = PROVIDER_NAMES.get(provider, provider)
        print(f"  {name}: target={target}, preproc={preproc}")

    print("\nWhat would you like to do?")
    print("  1. Add a provider")
    print("  2. Reconfigure everything")
    print("  3. Start fresh")
    choice = input_fn("Choice [2]: ").strip()

    if choice == "1":
        return "add"
    elif choice == "3":
        return "fresh"
    return "reconfigure"


def _select_providers(
    input_fn: Callable[..., str],
    existing_providers: list[str] | None = None,
) -> list[str]:
    """Show provider list and let user multi-select.

    Args:
        input_fn: Callable for reading user input.
        existing_providers: List of already-configured providers to mark.

    Returns:
        List of selected provider keys.
    """
    print("\nAvailable providers:")
    for i, key in enumerate(PROVIDER_ORDER, 1):
        name = PROVIDER_NAMES[key]
        marker = " (configured)" if existing_providers and key in existing_providers else ""
        print(f"  {i}. {name}{marker}")

    raw = input_fn("Enter numbers separated by commas (e.g., 1,3): ")
    return _parse_provider_selection(raw, PROVIDER_ORDER)


def _collect_api_keys(
    providers: list[str],
    input_fn: Callable[..., str],
    env_path: Path | None = None,
) -> dict[str, str]:
    """Collect API keys for selected providers.

    Checks existing keys in os.environ. Offers to keep existing keys
    or prompt for new ones. Writes new keys to .env immediately and
    loads them into os.environ.

    Args:
        providers: List of provider keys to collect keys for.
        input_fn: Callable for reading user input.
        env_path: Optional .env file path for testing.

    Returns:
        Dict mapping provider key to API key value.
    """
    keys: dict[str, str] = {}

    for provider in providers:
        env_var = PROVIDER_ENV_VARS[provider]
        name = PROVIDER_NAMES[provider]
        existing_key = os.environ.get(env_var, "")

        if existing_key:
            masked = _mask_key(existing_key)
            print(f"\n{name}: {env_var} = {masked}")
            keep = input_fn("Keep this? (Y/n): ").strip().lower()
            if keep in ("", "y", "yes"):
                keys[provider] = existing_key
                continue

        new_key = input_fn(f"\nEnter {env_var}: ").strip()
        if new_key:
            write_env(env_var, new_key, env_path=env_path)
            os.environ[env_var] = new_key
            keys[provider] = new_key
        else:
            print(f"  Warning: No key provided for {name}")
            keys[provider] = ""

    return keys


def _explain_model_roles(input_fn: Callable[..., str]) -> str:
    """Explain target vs pre-processor models and ask about preproc scope.

    Args:
        input_fn: Callable for reading user input.

    Returns:
        'per-provider' or 'global'.
    """
    print("\n--- Model Roles ---")
    print(
        "Target models are the LLMs being tested in the experiment. These are the\n"
        "models whose accuracy under noisy prompts you want to measure.\n"
    )
    print(
        "Pre-processor models are cheap, fast models (like Haiku or Flash) that\n"
        "clean up prompts before they reach the target model. They run on every\n"
        "prompt, so cost matters."
    )
    print()
    print("Use a separate pre-processor per provider, or one global pre-processor?")
    print("  1. Per-provider (default)")
    print("  2. Global")
    choice = input_fn("Choice [1]: ").strip()

    if choice == "2":
        return "global"
    return "per-provider"


def _select_models(
    providers: list[str],
    preproc_scope: str,
    input_fn: Callable[..., str],
    existing_models: dict | None = None,
) -> list[dict]:
    """Select target and preproc models for each provider.

    Supports free-text entry and 'list' command to browse available models.

    Args:
        providers: List of provider keys to configure.
        preproc_scope: 'per-provider' or 'global'.
        input_fn: Callable for reading user input.
        existing_models: Dict from _detect_existing_config() models field.

    Returns:
        List of dicts with 'provider', 'target_model', 'preproc_model' keys.
    """
    models: list[dict] = []
    global_preproc: str | None = None

    print("\n--- Model Selection ---")
    print("For each provider, choose the target model (the LLM being tested)")
    print("and then the pre-processor model (the cheap model that cleans prompts).\n")

    for provider in providers:
        name = PROVIDER_NAMES[provider]

        # Determine default target model
        default_target = DEFAULT_TARGET_MODELS.get(provider, "")
        if existing_models and provider in existing_models:
            default_target = existing_models[provider].get("target", default_target)

        # Target model selection
        while True:
            prompt = f"{name} target model (the LLM being tested) [{default_target}]: "
            raw = input_fn(prompt).strip()
            if raw.lower() == "list":
                selected = _browse_models(provider, input_fn)
                if selected:
                    target_model = selected
                    break
                # If browse returned None, loop back
                continue
            elif raw == "":
                target_model = default_target
                break
            else:
                target_model = raw
                break

        # Preproc model selection
        if preproc_scope == "global" and global_preproc is not None:
            preproc_model = global_preproc
            print(f"  Pre-processor: {preproc_model} (global)")
        else:
            # Auto-assign from registry
            auto_preproc = registry.get_preproc(target_model)
            if auto_preproc is None:
                auto_preproc = target_model

            raw_preproc = input_fn(f"  Pre-processor (auto-assigned) [{auto_preproc}]: ").strip()
            if raw_preproc.lower() == "list":
                selected = _browse_models(provider, input_fn)
                preproc_model = selected if selected else auto_preproc
            elif raw_preproc == "":
                preproc_model = auto_preproc
            else:
                preproc_model = raw_preproc

            if preproc_scope == "global" and global_preproc is None:
                global_preproc = preproc_model

        models.append({
            "provider": provider,
            "target_model": target_model,
            "preproc_model": preproc_model,
        })

    return models


def _browse_models(
    provider: str,
    input_fn: Callable[..., str],
    timeout: float = 5.0,
) -> str | None:
    """Browse available models from a provider's live API.

    Paginates 20 per page with search, navigation, and selection.

    Args:
        provider: Provider key to query.
        input_fn: Callable for reading user input.
        timeout: Timeout for the API query.

    Returns:
        Selected model_id, or None if user quits.
    """
    from src.model_discovery import (
        _query_anthropic,
        _query_google,
        _query_openai,
        _query_openrouter,
        _get_fallback_models,
    )

    query_map = {
        "anthropic": _query_anthropic,
        "google": _query_google,
        "openai": _query_openai,
        "openrouter": _query_openrouter,
    }

    query_fn = query_map.get(provider)
    if query_fn is None:
        print(f"  No model browser available for {provider}")
        return None

    # Try live query, fall back to registry
    try:
        all_models = query_fn(timeout=timeout)
        if not all_models:
            raise ValueError("Empty model list")
    except Exception:
        all_models = _get_fallback_models(provider)
        print("  (Using cached model list -- live API unreachable)")

    if not all_models:
        print("  No models available.")
        return None

    # Sort by model_id descending
    all_models.sort(key=lambda m: m.model_id, reverse=True)

    page_size = 20
    search_filter: str = ""
    page = 0

    while True:
        # Apply filter
        if search_filter:
            filtered = [m for m in all_models if search_filter.lower() in m.model_id.lower()]
        else:
            filtered = all_models

        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page = min(page, total_pages - 1)
        start = page * page_size
        end = min(start + page_size, len(filtered))
        page_models = filtered[start:end]

        print(f"\n  Models for {PROVIDER_NAMES.get(provider, provider)}:")
        if search_filter:
            print(f"  Filter: '{search_filter}'")
        for i, m in enumerate(page_models, start + 1):
            ctx = f" ({m.context_window:,} tokens)" if m.context_window else ""
            print(f"  {i}. {m.model_id}{ctx}")

        print(f"\n  Page {page + 1}/{total_pages} | n=next p=prev #=select /text=search q=quit")
        cmd = input_fn("  > ").strip()

        if cmd.lower() == "n":
            if page < total_pages - 1:
                page += 1
        elif cmd.lower() == "p":
            if page > 0:
                page -= 1
        elif cmd.lower() == "q":
            return None
        elif cmd.startswith("/"):
            search_filter = cmd[1:]
            page = 0
        else:
            try:
                idx = int(cmd) - 1
                if 0 <= idx < len(filtered):
                    return filtered[idx].model_id
                else:
                    print("  Invalid selection.")
            except ValueError:
                print("  Invalid command.")


def validate_api_key(
    provider: str, env_var: str, model_id: str | None = None
) -> tuple[bool, str]:
    """Validate an API key by making a minimal test call.

    Uses the provided model_id if given, otherwise falls back to
    hardcoded cheap defaults per provider.

    Args:
        provider: Provider key (anthropic, google, openai, openrouter).
        env_var: Environment variable name holding the API key.
        model_id: Optional model ID to use for the validation call.

    Returns:
        Tuple of (success, message).
    """
    key = os.environ.get(env_var)
    if not key:
        return (False, f"Environment variable {env_var} is not set")

    try:
        if provider == "anthropic":
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model=model_id or "claude-haiku-4-5-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "google":
            client = genai.Client(api_key=key)
            client.models.generate_content(
                model=model_id or "gemini-2.0-flash",
                contents="Hi",
                config={"max_output_tokens": 1},
            )
        elif provider == "openai":
            client = openai.OpenAI(api_key=key)
            client.chat.completions.create(
                model=model_id or "gpt-4o-mini-2024-07-18",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "openrouter":
            # Strip openrouter/ prefix — internal convention, not used by the API
            api_model = (model_id or "nvidia/nemotron-3-nano-30b-a3b:free")
            if api_model.startswith("openrouter/"):
                api_model = api_model.removeprefix("openrouter/")
            client = openai.OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)
            client.chat.completions.create(
                model=api_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        else:
            return (False, f"Unknown provider: {provider}")

        return (True, "API key validated successfully")

    except Exception as e:
        err_str = str(e).lower()
        if any(token in err_str for token in ("401", "403", "invalid", "auth")):
            return (False, f"Authentication failed: {e}")
        return (False, f"API call failed (key may be valid, but got error): {e}")


def _validate_models(
    models: list[dict], input_fn: Callable[..., str]
) -> list[dict]:
    """Validate each model by pinging the API with the actual target model.

    When validation fails, offers the user choices: keep anyway, enter a
    different model ID, list available models, or skip the provider.

    Args:
        models: List of model config dicts with 'provider', 'target_model'.
        input_fn: Callable for reading user input.

    Returns:
        Filtered list with only validated or user-accepted models.
    """
    validated: list[dict] = []

    for entry in models:
        provider = entry["provider"]
        target = entry["target_model"]
        env_var = PROVIDER_ENV_VARS[provider]

        print(f"\nValidating {target}... ", end="", flush=True)
        ok, msg = validate_api_key(provider, env_var, model_id=target)

        if ok:
            print("OK")
            validated.append(entry)
        else:
            print(f"FAILED: {msg}")
            while True:
                print("  Options:")
                print("    y    - Keep this model anyway")
                print("    n    - Skip this provider")
                print("    list - Browse available models")
                print("    Or type a different model ID")
                choice = input_fn("Choice: ").strip()

                if choice.lower() in ("y", "yes", ""):
                    validated.append(entry)
                    break
                elif choice.lower() == "n":
                    break
                elif choice.lower() == "list":
                    selected = _browse_models(provider, input_fn)
                    if selected:
                        entry["target_model"] = selected
                        # Re-validate the new selection
                        print(f"\nValidating {selected}... ", end="", flush=True)
                        ok2, msg2 = validate_api_key(provider, env_var, model_id=selected)
                        if ok2:
                            print("OK")
                            validated.append(entry)
                            break
                        else:
                            print(f"FAILED: {msg2}")
                            # Loop back to options
                    # If browse returned None, loop back
                else:
                    # Treat as a model ID
                    entry["target_model"] = choice
                    print(f"\nValidating {choice}... ", end="", flush=True)
                    ok2, msg2 = validate_api_key(provider, env_var, model_id=choice)
                    if ok2:
                        print("OK")
                        validated.append(entry)
                        break
                    else:
                        print(f"FAILED: {msg2}")
                        # Loop back to options

    return validated


def _build_budget_preview(models: list[dict]) -> str:
    """Build budget preview string for pilot and full experiment runs.

    Creates synthetic experiment items and calls estimate_cost() for
    both pilot (20 prompts) and full (200 prompts) runs.

    Args:
        models: List of model config dicts with 'provider', 'target_model',
                'preproc_model'.

    Returns:
        Formatted multi-line budget preview string.
    """
    interventions = ["raw", "self_correct", "pre_proc_sanitize",
                     "pre_proc_sanitize_compress", "prompt_repetition"]
    repetitions = 5

    def _make_items(prompt_count: int) -> list[dict[str, Any]]:
        """Build synthetic experiment items for cost estimation."""
        items: list[dict[str, Any]] = []
        # Distribute prompts: 40% HumanEval, 40% Mbpp, 20% GSM8K
        humaneval_count = int(prompt_count * 0.4)
        mbpp_count = int(prompt_count * 0.4)
        gsm8k_count = prompt_count - humaneval_count - mbpp_count

        prompt_ids: list[str] = []
        for i in range(humaneval_count):
            prompt_ids.append(f"HumanEval/{i}")
        for i in range(mbpp_count):
            prompt_ids.append(f"Mbpp/{i}")
        for i in range(gsm8k_count):
            prompt_ids.append(f"gsm8k_{i}")

        for entry in models:
            target = entry["target_model"]
            for prompt_id in prompt_ids:
                for intervention in interventions:
                    for rep in range(1, repetitions + 1):
                        items.append({
                            "prompt_id": prompt_id,
                            "model": target,
                            "intervention": intervention,
                            "repetition_num": rep,
                        })
        return items

    # Build per-model cost breakdown
    def _per_model_costs(prompt_count: int) -> dict[str, dict[str, float]]:
        """Get per-model cost estimates."""
        per_model: dict[str, dict[str, float]] = {}
        for entry in models:
            target = entry["target_model"]
            single_model_items = _make_items(prompt_count)
            # Filter to just this model
            model_items = [it for it in single_model_items if it["model"] == target]
            cost = estimate_cost(model_items)
            per_model[target] = cost
        return per_model

    lines: list[str] = []
    lines.append("\nBudget Estimate")
    lines.append("---------------")

    # Check for unknown pricing
    unknown_models: set[str] = set()
    for entry in models:
        target = entry["target_model"]
        price = registry.get_price(target)
        if price == (0.0, 0.0) and target not in registry._models:
            unknown_models.add(target)

    for label, count in [("Pilot run (20 prompts)", 20), ("Full run (200 prompts)", 200)]:
        per_model = _per_model_costs(count)
        total_target = sum(c["target_cost"] for c in per_model.values())
        total_preproc = sum(c["preproc_cost"] for c in per_model.values())
        total = total_target + total_preproc

        lines.append(f"\n{label}:")
        known_total = 0.0
        for target_model, cost in per_model.items():
            model_total = cost["target_cost"]
            if target_model in unknown_models:
                lines.append(f"  {target_model}: pricing unknown")
            else:
                lines.append(f"  {target_model}: ~${model_total:.2f}")
                known_total += model_total

        lines.append(f"  Pre-processing: ~${total_preproc:.2f}")
        known_total += total_preproc

        if unknown_models:
            lines.append(f"  Total (excluding unknown): ~${known_total:.2f}")
        else:
            lines.append(f"  Total: ~${total:.2f}")

        if label.startswith("Full") and total > 50:
            lines.append("  WARNING: Full run estimate exceeds $50.00")

    return "\n".join(lines)


def _show_confirmation(
    models: list[dict],
    keys: dict[str, str],
    input_fn: Callable[..., str],
) -> bool:
    """Show configuration summary and ask for confirmation.

    Args:
        models: List of model config dicts.
        keys: Dict mapping provider to API key value.
        input_fn: Callable for reading user input.

    Returns:
        True if user confirms, False otherwise.
    """
    print("\n=== Configuration Summary ===\n")

    # Model table
    print(f"{'Provider':<20} {'Target Model':<40} {'Preproc Model':<35} {'Key':<10}")
    print("-" * 105)
    for entry in models:
        provider = entry["provider"]
        name = PROVIDER_NAMES.get(provider, provider)
        target = entry["target_model"]
        preproc = entry["preproc_model"]
        key_status = "set" if keys.get(provider) else "not set"
        print(f"{name:<20} {target:<40} {preproc:<35} {key_status:<10}")

    # Config validation warnings
    config_dict = _build_config_dict(models)
    errors = validate_config(config_dict)
    if errors:
        print("\nValidation warnings:")
        for err in errors:
            print(f"  - {err}")

    # Budget preview
    preview = _build_budget_preview(models)
    print(preview)

    print()
    choice = input_fn("Save this configuration? (Y/n): ").strip().lower()
    return choice in ("", "y", "yes")


def _build_config_dict(models: list[dict]) -> dict:
    """Build a config dict suitable for save_config().

    Starts with get_full_config_dict() defaults, sets config_version=2,
    and builds the models list from the wizard selections.

    Args:
        models: List of model config dicts with 'provider', 'target_model',
                'preproc_model'.

    Returns:
        Complete config dict ready for save_config().
    """
    config = get_full_config_dict()
    config["config_version"] = 2

    models_list: list[dict] = []
    seen_preproc: set[str] = set()

    for entry in models:
        provider = entry["provider"]
        target = entry["target_model"]
        preproc = entry["preproc_model"]

        # Look up pricing from registry for known models
        target_price = registry.get_price(target)
        target_in_registry = target in registry._models
        target_mc = registry._models.get(target)

        target_entry: dict[str, Any] = {
            "model_id": target,
            "provider": provider,
            "role": "target",
            "preproc_model_id": preproc,
            "input_price_per_1m": target_price[0] if target_in_registry else None,
            "output_price_per_1m": target_price[1] if target_in_registry else None,
            "rate_limit_delay": target_mc.rate_limit_delay if target_mc else None,
        }
        models_list.append(target_entry)

        # Preproc entry (deduplicated)
        if preproc not in seen_preproc:
            seen_preproc.add(preproc)
            preproc_price = registry.get_price(preproc)
            preproc_in_registry = preproc in registry._models
            preproc_mc = registry._models.get(preproc)

            preproc_entry: dict[str, Any] = {
                "model_id": preproc,
                "provider": provider,
                "role": "preproc",
                "preproc_model_id": None,
                "input_price_per_1m": preproc_price[0] if preproc_in_registry else None,
                "output_price_per_1m": preproc_price[1] if preproc_in_registry else None,
                "rate_limit_delay": preproc_mc.rate_limit_delay if preproc_mc else None,
            }
            models_list.append(preproc_entry)

    config["models"] = models_list
    return config


# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------

def check_environment() -> list[tuple[str, bool, str]]:
    """Check Python version and required package availability.

    Returns:
        List of (check_name, passed, detail_string) tuples.
    """
    results: list[tuple[str, bool, str]] = []

    # Python version check
    vi = sys.version_info
    passed = vi >= (3, 11)
    detail = f"{vi.major}.{vi.minor}.{vi.micro}"
    results.append(("Python >= 3.11", passed, detail))

    # Package checks
    for pkg in REQUIRED_PACKAGES:
        try:
            version = importlib.metadata.version(pkg)
            results.append((f"Package: {pkg}", True, version))
        except Exception:
            results.append((f"Package: {pkg}", False, "not installed"))

    return results


# ---------------------------------------------------------------------------
# Main wizard entry point
# ---------------------------------------------------------------------------

def run_setup_wizard(
    args: Any,
    input_fn: Callable[..., str] | None = None,
) -> None:
    """Run the interactive setup wizard or write defaults in non-interactive mode.

    Implements the full multi-provider wizard flow: environment check,
    existing config detection, provider selection, API key collection,
    model role explanation, model selection with live browser support,
    validation pings, budget preview, and confirmation.

    Args:
        args: Parsed argparse Namespace with at least 'non_interactive' attribute.
        input_fn: Optional callable replacing builtins.input for testability.
    """
    if input_fn is None:
        input_fn = builtins.input

    # Non-interactive mode: write defaults and exit
    if args.non_interactive:
        config = get_full_config_dict()
        path = save_config(config)
        print(f"Config saved to {path}")
        return

    # Interactive flow
    try:
        print("\nWelcome to the Linguistic Tax research toolkit setup!\n")

        # Step 1: Environment check
        print("Checking environment...")
        env_results = check_environment()
        for name, passed, detail in env_results:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}: {detail}")
        print()

        # Step 2: Detect existing config
        existing = _detect_existing_config()
        existing_providers: list[str] | None = None
        existing_models: dict | None = None

        if existing:
            action = _handle_existing_config(existing, input_fn)
            if action == "add":
                existing_providers = existing["providers"]
                existing_models = existing["models"]
            elif action == "fresh":
                existing = None
            else:  # reconfigure
                existing_providers = existing["providers"]
                existing_models = existing["models"]

        # Step 3: Provider selection
        providers = _select_providers(input_fn, existing_providers=existing_providers)

        # Step 4: API key collection
        print("\nAPI Key Configuration\n")
        keys = _collect_api_keys(providers, input_fn)

        # Step 5: Model role explanation and preproc scope
        preproc_scope = _explain_model_roles(input_fn)

        # Step 6: Model selection
        selected_models = _select_models(
            providers, preproc_scope, input_fn, existing_models=existing_models
        )

        # Step 7: Validate models
        selected_models = _validate_models(selected_models, input_fn)

        if not selected_models:
            print("No valid models configured. Exiting.")
            return

        # Step 8: Confirmation
        if not _show_confirmation(selected_models, keys, input_fn):
            print("Configuration not saved.")
            return

        # Step 9: Save config and reload registry
        config = _build_config_dict(selected_models)
        saved_path = save_config(config)

        # Reload registry with new models
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
            for m in config["models"]
        ]
        registry.reload(model_configs)

        print(f"\nConfig saved to {saved_path}")
        print("\nNext steps:")
        print("  Run 'propt pilot' to test with 20 prompts")
        print("  Run 'propt list-models' to see available models")
        print("  Run 'propt config show' to review your configuration")

    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        return
