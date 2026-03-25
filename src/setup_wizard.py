"""Interactive setup wizard for the Linguistic Tax research toolkit.

Guides users through provider selection, model configuration,
API key validation, environment checks, and config file generation.
"""

import builtins
import importlib.metadata
import logging
import os
import sys
from typing import Any, Callable

import anthropic
import openai
from google import genai

from src.config import MODELS, OPENROUTER_BASE_URL, PREPROC_MODEL_MAP
from src.config_manager import get_full_config_dict, save_config, validate_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": [m for m in MODELS if m.startswith("claude")],
        "env_var": "ANTHROPIC_API_KEY",
    },
    "google": {
        "name": "Google (Gemini)",
        "models": [m for m in MODELS if m.startswith("gemini")],
        "env_var": "GOOGLE_API_KEY",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "models": [m for m in MODELS if m.startswith("gpt")],
        "env_var": "OPENAI_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter (free models)",
        "models": [m for m in MODELS if m.startswith("openrouter/")],
        "env_var": "OPENROUTER_API_KEY",
    },
}

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
# API key validation
# ---------------------------------------------------------------------------

def validate_api_key(provider: str, env_var: str) -> tuple[bool, str]:
    """Validate an API key by making a minimal test call.

    Args:
        provider: Provider key (anthropic, google, openai, openrouter).
        env_var: Environment variable name holding the API key.

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
                model="claude-haiku-4-5-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "google":
            client = genai.Client(api_key=key)
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Hi",
                config={"max_output_tokens": 1},
            )
        elif provider == "openai":
            client = openai.OpenAI(api_key=key)
            client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "openrouter":
            client = openai.OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)
            client.chat.completions.create(
                model="nvidia/nemotron-3-nano-30b-a3b:free",
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


# ---------------------------------------------------------------------------
# Model field mapping
# ---------------------------------------------------------------------------

_MODEL_FIELD_MAP: dict[str, str] = {
    "anthropic": "claude_model",
    "google": "gemini_model",
    "openai": "openai_model",
    "openrouter": "openrouter_model",
}

_PREPROC_FIELD_MAP: dict[str, str] = {
    "anthropic": "claude_model",
    "google": "gemini_model",
    "openai": "openai_model",
    "openrouter": "openrouter_preproc_model",
}


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

def run_setup_wizard(
    args: Any,
    input_fn: Callable[..., str] | None = None,
) -> None:
    """Run the interactive setup wizard or write defaults in non-interactive mode.

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
        print("\nWelcome to the Linguistic Tax slicer setup wizard!\n")

        # Step 1: Environment check
        print("Checking environment...")
        env_results = check_environment()
        for name, passed, detail in env_results:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}: {detail}")
        print()

        # Step 2: Provider selection
        provider_keys = list(PROVIDERS.keys())
        print("Select your LLM provider:")
        for i, key in enumerate(provider_keys, 1):
            print(f"  {i}. {PROVIDERS[key]['name']}")

        choice = input_fn("Enter choice (1-4): ")
        try:
            provider_idx = int(choice) - 1
            provider_key = provider_keys[provider_idx]
        except (ValueError, IndexError):
            provider_key = provider_keys[0]
            print(f"Invalid choice, defaulting to {PROVIDERS[provider_key]['name']}")

        provider = PROVIDERS[provider_key]
        env_var = provider["env_var"]

        # Step 3: Target model
        models = provider["models"]
        print(f"\nTarget model (default: {models[0]}):")
        for i, m in enumerate(models, 1):
            print(f"  {i}. {m}")

        model_choice = input_fn("Enter choice or press Enter for default: ")
        if model_choice.strip() == "":
            target_model = models[0]
        else:
            try:
                target_model = models[int(model_choice) - 1]
            except (ValueError, IndexError):
                target_model = models[0]
                print(f"Invalid choice, defaulting to {target_model}")

        # Step 4: Preproc model
        preproc_model = PREPROC_MODEL_MAP.get(target_model, "")
        if preproc_model:
            print(f"\nPre-processor model (auto-filled): {preproc_model}")
            preproc_choice = input_fn("Press Enter to accept or type model name: ")
            if preproc_choice.strip():
                preproc_model = preproc_choice.strip()

        # Step 5: API key check
        key_value = os.environ.get(env_var)
        if key_value:
            print(f"\n{env_var} is set.")
            do_validate = input_fn("Validate API key with a test call? (y/n): ")
            if do_validate.strip().lower() in ("y", "yes", ""):
                ok, msg = validate_api_key(provider_key, env_var)
                print(f"  {'PASS' if ok else 'FAIL'}: {msg}")
        else:
            print(f"\n{env_var} is not set.")
            print(f"Set {env_var} in your environment before running experiments.")

        # Step 6: Paths
        config = get_full_config_dict()
        default_paths = {
            "prompts_path": config.get("prompts_path", "data/prompts.json"),
            "matrix_path": config.get("matrix_path", "data/experiment_matrix.json"),
            "results_db_path": config.get("results_db_path", "results/results.db"),
        }

        print("\nFile paths:")
        for path_key, default_val in default_paths.items():
            user_val = input_fn(f"  {path_key} [{default_val}]: ")
            if user_val.strip():
                config[path_key] = user_val.strip()
            else:
                config[path_key] = default_val

        # Step 7: Build config with user selections
        model_field = _MODEL_FIELD_MAP.get(provider_key)
        if model_field:
            config[model_field] = target_model
        if preproc_model and provider_key == "openrouter":
            config["openrouter_preproc_model"] = preproc_model

        # Step 8: Validate
        errors = validate_config(config)
        if errors:
            print("\nValidation warnings:")
            for err in errors:
                print(f"  - {err}")

        # Step 9: Save
        path = save_config(config)
        print(f"\nConfig saved to {path}")
        print("Setup complete! Run experiments with: python src/run_experiment.py")
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        return
