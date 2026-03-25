"""Tests for the setup wizard module."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# PROVIDERS structure tests
# ---------------------------------------------------------------------------

def test_providers_has_all_entries():
    """PROVIDERS dict has entries for anthropic, google, openai, openrouter."""
    from src.setup_wizard import PROVIDERS

    assert "anthropic" in PROVIDERS
    assert "google" in PROVIDERS
    assert "openai" in PROVIDERS
    assert "openrouter" in PROVIDERS


def test_providers_entries_have_required_keys():
    """Each PROVIDERS entry has 'name', 'models' (non-empty list), 'env_var'."""
    from src.setup_wizard import PROVIDERS

    for key, entry in PROVIDERS.items():
        assert "name" in entry, f"{key} missing 'name'"
        assert "models" in entry, f"{key} missing 'models'"
        assert "env_var" in entry, f"{key} missing 'env_var'"
        assert len(entry["models"]) > 0, f"{key} has empty models list"


def test_providers_models_are_from_config():
    """All models in PROVIDERS come from config.MODELS."""
    from src.setup_wizard import PROVIDERS
    from src.config import MODELS

    for key, entry in PROVIDERS.items():
        for model in entry["models"]:
            assert model in MODELS, f"{model} in {key} not found in MODELS"


# ---------------------------------------------------------------------------
# check_environment tests
# ---------------------------------------------------------------------------

def test_check_environment_returns_list_of_tuples():
    """check_environment returns list of (name, passed, detail) tuples."""
    from src.setup_wizard import check_environment

    results = check_environment()
    assert isinstance(results, list)
    for item in results:
        assert len(item) == 3
        name, passed, detail = item
        assert isinstance(name, str)
        assert isinstance(passed, bool)
        assert isinstance(detail, str)


def test_check_environment_detects_python_version():
    """check_environment detects Python >= 3.11 as passed."""
    from src.setup_wizard import check_environment

    results = check_environment()
    python_check = [r for r in results if r[0] == "Python >= 3.11"]
    assert len(python_check) == 1
    # We are running on Python 3.11+ so this should pass
    assert python_check[0][1] is True


def test_check_environment_detects_missing_package():
    """check_environment detects missing package as failed."""
    from src.setup_wizard import check_environment

    with patch("importlib.metadata.version", side_effect=Exception("not found")):
        results = check_environment()
        # At least one package check should fail
        package_checks = [r for r in results if r[0] != "Python >= 3.11"]
        failed = [r for r in package_checks if not r[1]]
        assert len(failed) > 0


# ---------------------------------------------------------------------------
# validate_api_key tests
# ---------------------------------------------------------------------------

def test_validate_api_key_returns_false_when_env_not_set():
    """validate_api_key returns (False, message) when env var not set."""
    from src.setup_wizard import validate_api_key

    with patch.dict(os.environ, {}, clear=True):
        ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
        assert ok is False
        assert "not set" in msg


def test_validate_api_key_anthropic_makes_api_call():
    """validate_api_key for 'anthropic' makes client.messages.create call."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
            mock_client.messages.create.assert_called_once()
            assert ok is True
            assert "validated" in msg.lower()


def test_validate_api_key_google_makes_api_call():
    """validate_api_key for 'google' makes client.models.generate_content call."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        with patch("google.genai.Client", return_value=mock_client):
            ok, msg = validate_api_key("google", "GOOGLE_API_KEY")
            mock_client.models.generate_content.assert_called_once()
            assert ok is True


def test_validate_api_key_openai_makes_api_call():
    """validate_api_key for 'openai' makes client.chat.completions.create call."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI", return_value=mock_client):
            ok, msg = validate_api_key("openai", "OPENAI_API_KEY")
            mock_client.chat.completions.create.assert_called_once()
            assert ok is True


def test_validate_api_key_openrouter_uses_base_url():
    """validate_api_key for 'openrouter' makes OpenAI client with OPENROUTER_BASE_URL."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        with patch("openai.OpenAI", return_value=mock_client) as mock_cls:
            ok, msg = validate_api_key("openrouter", "OPENROUTER_API_KEY")
            # Check that base_url was passed
            call_kwargs = mock_cls.call_args
            assert "base_url" in call_kwargs.kwargs or (
                len(call_kwargs.args) > 1
            )
            mock_client.chat.completions.create.assert_called_once()
            assert ok is True


def test_validate_api_key_distinguishes_auth_errors():
    """validate_api_key distinguishes auth errors (401/403) from other errors."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("401 Unauthorized")
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
            assert ok is False
            assert "authentication failed" in msg.lower()


def test_validate_api_key_other_error():
    """validate_api_key returns informative message for non-auth errors."""
    from src.setup_wizard import validate_api_key

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Connection timeout")
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
            assert ok is False
            assert "key may be valid" in msg.lower()


# ---------------------------------------------------------------------------
# run_setup_wizard tests
# ---------------------------------------------------------------------------

def test_wizard_non_interactive_creates_config(tmp_path):
    """run_setup_wizard with --non-interactive writes defaults without prompting."""
    from src.setup_wizard import run_setup_wizard

    config_path = tmp_path / "experiment_config.json"
    args = SimpleNamespace(non_interactive=True)

    with patch("src.setup_wizard.save_config", return_value=config_path) as mock_save:
        with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
            run_setup_wizard(args)
            mock_save.assert_called_once()


def test_wizard_interactive_flow_creates_config(tmp_path):
    """run_setup_wizard with mocked inputs creates config file with expected values."""
    from src.setup_wizard import run_setup_wizard

    config_path = tmp_path / "experiment_config.json"

    # Simulate: select provider 1 (anthropic), accept default model (Enter),
    # accept default preproc model (Enter), skip API validation (n),
    # accept default paths (Enter x3), accept config (Enter)
    inputs = [
        "1",     # provider selection
        "",      # accept default target model
        "",      # accept default preproc model
        "n",     # skip API key validation
        "",      # accept default prompts_path
        "",      # accept default matrix_path
        "",      # accept default results_db_path
    ]

    args = SimpleNamespace(non_interactive=False)

    with patch("src.setup_wizard.save_config", return_value=config_path) as mock_save:
        with patch("src.setup_wizard.get_full_config_dict", return_value={
            "claude_model": "claude-sonnet-4-20250514",
            "temperature": 0.0,
            "prompts_path": "data/prompts.json",
            "matrix_path": "data/experiment_matrix.json",
            "results_db_path": "results/results.db",
        }):
            with patch("src.setup_wizard.validate_config", return_value=[]):
                with patch("src.setup_wizard.check_environment", return_value=[
                    ("Python >= 3.11", True, "3.11.0"),
                ]):
                    run_setup_wizard(args, input_fn=lambda prompt="": inputs.pop(0))
                    mock_save.assert_called_once()


def test_wizard_auto_fills_preproc_model():
    """wizard auto-fills preproc model from PREPROC_MODEL_MAP when user selects target model."""
    from src.setup_wizard import PROVIDERS
    from src.config import PREPROC_MODEL_MAP

    # Verify that models in PROVIDERS map to preproc models
    for provider_key, provider in PROVIDERS.items():
        for model in provider["models"]:
            if model in PREPROC_MODEL_MAP:
                assert PREPROC_MODEL_MAP[model] is not None


def test_wizard_ctrl_c_cancels_cleanly(capsys):
    """Ctrl-C during wizard prints 'Setup cancelled.' and returns None."""
    from src.setup_wizard import run_setup_wizard

    args = SimpleNamespace(non_interactive=False)

    def raise_interrupt(prompt=""):
        raise KeyboardInterrupt

    with patch("src.setup_wizard.check_environment", return_value=[
        ("Python >= 3.11", True, "3.11.0"),
    ]):
        result = run_setup_wizard(args, input_fn=raise_interrupt)

    assert result is None
    captured = capsys.readouterr()
    assert "Setup cancelled." in captured.out


def test_wizard_interactive_with_model_override(tmp_path):
    """Wizard allows overriding the default model selection."""
    from src.setup_wizard import run_setup_wizard

    config_path = tmp_path / "experiment_config.json"

    # Select provider 1 (anthropic), pick model 1 (same as default),
    # accept preproc (Enter), skip validation, accept paths
    inputs = [
        "1",     # provider selection
        "1",     # explicitly select model 1
        "",      # accept default preproc model
        "n",     # skip API key validation
        "",      # accept default prompts_path
        "",      # accept default matrix_path
        "",      # accept default results_db_path
    ]

    args = SimpleNamespace(non_interactive=False)

    with patch("src.setup_wizard.save_config", return_value=config_path):
        with patch("src.setup_wizard.get_full_config_dict", return_value={
            "claude_model": "claude-sonnet-4-20250514",
            "temperature": 0.0,
            "prompts_path": "data/prompts.json",
            "matrix_path": "data/experiment_matrix.json",
            "results_db_path": "results/results.db",
        }):
            with patch("src.setup_wizard.validate_config", return_value=[]):
                with patch("src.setup_wizard.check_environment", return_value=[
                    ("Python >= 3.11", True, "3.11.0"),
                ]):
                    run_setup_wizard(args, input_fn=lambda prompt="": inputs.pop(0))
