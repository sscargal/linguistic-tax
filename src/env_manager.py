"""Environment variable manager for the Linguistic Tax research toolkit.

Provides .env file loading, writing, and API key checking using python-dotenv.
The .env file is always at the project root (not configurable by default).
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv, set_key

logger = logging.getLogger(__name__)

PROVIDER_KEY_MAP: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_ENV_PATH = Path(".env")


def load_env(env_path: Path | None = None) -> bool:
    """Load .env file from project root into os.environ.

    Does not override existing environment variables.

    Args:
        env_path: Path to .env file. Defaults to project root .env.

    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    path = env_path or _ENV_PATH
    if path.exists():
        load_dotenv(dotenv_path=path, override=False)
        logger.debug("Loaded environment from %s", path)
        return True
    logger.debug("No .env file found at %s", path)
    return False


def write_env(key: str, value: str, env_path: Path | None = None) -> None:
    """Write a key-value pair to .env file. Creates file if needed.

    Sets chmod 600 (owner-only read/write) on the .env file after writing.

    Args:
        key: Environment variable name (e.g., "ANTHROPIC_API_KEY").
        value: Environment variable value.
        env_path: Path to .env file. Defaults to project root .env.
    """
    path = env_path or _ENV_PATH
    set_key(str(path), key, value)
    os.chmod(path, 0o600)
    logger.info("Wrote %s to %s", key, path)


def check_keys(providers: list[str]) -> dict[str, bool]:
    """Check which providers have API keys set in the environment.

    Args:
        providers: List of provider names (e.g., ["anthropic", "google"]).

    Returns:
        Dict mapping provider name to True/False for key presence.
    """
    result: dict[str, bool] = {}
    for provider in providers:
        env_var = PROVIDER_KEY_MAP.get(provider, "")
        result[provider] = bool(os.environ.get(env_var, "")) if env_var else False
    return result
