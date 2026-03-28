"""Tests for the setup wizard module.

Comprehensive test suite covering multi-provider wizard flow, helper functions,
key collection, model selection, validation, budget preview, and config building.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

from src.setup_wizard import (
    _mask_key,
    _parse_provider_selection,
    _detect_existing_config,
    _handle_existing_config,
    _remove_existing_config,
    _select_providers,
    _collect_api_keys,
    _explain_model_roles,
    _select_models,
    _browse_models,
    _validate_models,
    _build_budget_preview,
    _show_confirmation,
    _build_config_dict,
    check_environment,
    run_setup_wizard,
    validate_api_key,
    MAX_TARGETS_PER_PROVIDER,
    PROVIDER_NAMES,
    PROVIDER_ORDER,
    PROVIDER_ENV_VARS,
    DEFAULT_TARGET_MODELS,
)


# ---------------------------------------------------------------------------
# Section 1: Helper function tests
# ---------------------------------------------------------------------------


class TestMaskKey:
    """Tests for _mask_key helper."""

    def test_mask_key_long_key(self):
        """Long key shows first 6 and last 4 characters."""
        result = _mask_key("sk-ant-api03-abcdef123456")
        assert result == "sk-ant...3456"

    def test_mask_key_short_key(self):
        """Short key (3 chars) returns '****'."""
        result = _mask_key("abc")
        assert result == "****"

    def test_mask_key_exactly_ten_chars(self):
        """10-char key returns '****' (boundary)."""
        result = _mask_key("1234567890")
        assert result == "****"


class TestParseProviderSelection:
    """Tests for _parse_provider_selection helper."""

    def test_parse_provider_selection_valid(self):
        """'1,3' with 4 options returns first and third."""
        result = _parse_provider_selection("1,3", ["a", "b", "c", "d"])
        assert result == ["a", "c"]

    def test_parse_provider_selection_invalid_defaults_to_first(self):
        """Out of range '99' defaults to first provider."""
        result = _parse_provider_selection("99", ["a", "b"])
        assert result == ["a"]

    def test_parse_provider_selection_empty_defaults_to_first(self):
        """Empty string defaults to first provider."""
        result = _parse_provider_selection("", ["a", "b"])
        assert result == ["a"]

    def test_parse_provider_selection_duplicate_deduplication(self):
        """Duplicate indices are deduplicated."""
        result = _parse_provider_selection("1,1,2", ["a", "b", "c"])
        assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# Section 2: Provider selection tests
# ---------------------------------------------------------------------------


class TestSelectProviders:
    """Tests for _select_providers."""

    def test_select_providers_single(self):
        """Selecting '1' returns ['anthropic']."""
        input_fn = lambda prompt="": "1"
        result = _select_providers(input_fn)
        assert result == ["anthropic"]

    def test_select_providers_multiple(self):
        """Selecting '1,2,4' returns anthropic, google, openrouter."""
        input_fn = lambda prompt="": "1,2,4"
        result = _select_providers(input_fn)
        assert result == ["anthropic", "google", "openrouter"]

    def test_select_providers_marks_existing(self, capsys):
        """Existing providers are marked '[configured]' in output."""
        input_fn = lambda prompt="": "1"
        _select_providers(input_fn, existing_providers=["anthropic"])
        captured = capsys.readouterr()
        assert "[configured]" in captured.out


# ---------------------------------------------------------------------------
# Section 3: Key collection tests (WIZ-04)
# ---------------------------------------------------------------------------


class TestCollectApiKeys:
    """Tests for _collect_api_keys."""

    def test_collect_api_keys_new_key_writes_env(self, tmp_path):
        """New key is written to .env and set in os.environ."""
        with patch.dict(os.environ, {}, clear=False):
            # Ensure no existing key
            os.environ.pop("ANTHROPIC_API_KEY", None)
            inputs = ["test-key-123"]
            input_fn = lambda prompt="": inputs.pop(0)

            with patch("src.setup_wizard.write_env") as mock_write:
                result = _collect_api_keys(
                    ["anthropic"], input_fn, env_path=tmp_path / ".env"
                )
                mock_write.assert_called_once_with(
                    "ANTHROPIC_API_KEY",
                    "test-key-123",
                    env_path=tmp_path / ".env",
                )
                assert os.environ["ANTHROPIC_API_KEY"] == "test-key-123"
                assert result["anthropic"] == "test-key-123"

    def test_collect_api_keys_keeps_existing_key(self):
        """Existing key is kept when user presses Enter (accept)."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "existing-key"}):
            inputs = [""]  # Accept existing
            input_fn = lambda prompt="": inputs.pop(0)

            with patch("src.setup_wizard.write_env") as mock_write:
                result = _collect_api_keys(["anthropic"], input_fn)
                mock_write.assert_not_called()
                assert result["anthropic"] == "existing-key"

    def test_collect_api_keys_replaces_existing_key(self, tmp_path):
        """Existing key is replaced when user says 'n' and enters new key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "old-key"}):
            inputs = ["n", "new-key-456"]
            input_fn = lambda prompt="": inputs.pop(0)

            with patch("src.setup_wizard.write_env") as mock_write:
                result = _collect_api_keys(
                    ["anthropic"], input_fn, env_path=tmp_path / ".env"
                )
                mock_write.assert_called_once_with(
                    "ANTHROPIC_API_KEY",
                    "new-key-456",
                    env_path=tmp_path / ".env",
                )
                assert result["anthropic"] == "new-key-456"


# ---------------------------------------------------------------------------
# Section 4: Model role explanation tests (WIZ-01)
# ---------------------------------------------------------------------------


class TestExplainModelRoles:
    """Tests for _explain_model_roles."""

    def test_explain_model_roles_prints_explanation(self, capsys):
        """Explanation is printed and '1' returns 'per-provider'."""
        input_fn = lambda prompt="": "1"
        result = _explain_model_roles(input_fn)
        captured = capsys.readouterr()
        assert "Target models are the LLMs" in captured.out
        assert result == "per-provider"

    def test_explain_model_roles_global_preproc(self):
        """Choosing '2' returns 'global'."""
        input_fn = lambda prompt="": "2"
        result = _explain_model_roles(input_fn)
        assert result == "global"


# ---------------------------------------------------------------------------
# Section 5: Model selection tests (WIZ-03, DSC-03)
# ---------------------------------------------------------------------------


class TestSelectModels:
    """Tests for _select_models."""

    def test_select_models_accepts_default(self):
        """Empty input accepts default target and preproc models."""
        inputs = ["", "", "d"]  # accept target, accept preproc, done with provider
        input_fn = lambda prompt="": inputs.pop(0)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == 1
        assert result[0]["target_model"] == "claude-sonnet-4-20250514"

    def test_select_models_free_text_entry(self):
        """Free text entry validates and accepts model (DSC-03)."""
        inputs = ["my-custom-model-v2", "y", "", "d"]  # custom target, keep anyway, accept preproc, done
        input_fn = lambda prompt="": inputs.pop(0)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "my-custom-model-v2"
            mock_reg._models = {}
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                with patch("src.setup_wizard._get_provider_models", return_value=[]):
                    result = _select_models(["anthropic"], "per-provider", input_fn)

        assert result[0]["target_model"] == "my-custom-model-v2"

    def test_select_models_list_triggers_browser(self):
        """Typing 'list' triggers _browse_models call."""
        # list -> browse returns None -> accept default target -> accept preproc -> done
        inputs = ["list", "", "", "d"]
        input_idx = [0]

        def input_fn(prompt=""):
            idx = input_idx[0]
            input_idx[0] += 1
            if idx < len(inputs):
                return inputs[idx]
            return ""

        with patch("src.setup_wizard._browse_models", return_value=None) as mock_browse:
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
                with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                    result = _select_models(["anthropic"], "per-provider", input_fn)

        mock_browse.assert_called_once()


# ---------------------------------------------------------------------------
# Section 5b: Multi-target selection tests
# ---------------------------------------------------------------------------


class TestMultiTargetSelection:
    """Tests for multi-model selection per provider."""

    def _make_input_fn(self, inputs: list[str]):
        """Create an input_fn from a list of responses."""
        idx = [0]
        def input_fn(prompt=""):
            i = idx[0]
            idx[0] += 1
            if i < len(inputs):
                return inputs[i]
            return ""
        return input_fn

    def test_multi_target_add_two_models(self):
        """Adding a second model results in 2 entries for the same provider."""
        inputs = [
            "",    # accept default target 1
            "",    # accept default preproc 1
            "a",   # add another model
            "",    # accept default target 2
            "",    # accept default preproc 2
            "d",   # done with provider
        ]
        input_fn = self._make_input_fn(inputs)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == 2
        assert all(r["provider"] == "anthropic" for r in result)

    def test_multi_target_remove_model(self):
        """Removing model 1 of 2 leaves only the second."""
        # _get_provider_models returns [] so _validate_model_name returns model_id
        # directly (can't validate without model list), no extra prompts consumed.
        inputs = [
            "model-a",  # target 1
            "",         # preproc 1 (accept auto)
            "a",        # add another
            "model-b",  # target 2
            "",         # preproc 2 (accept auto)
            "r1",       # remove model 1 (model-a)
            "d",        # done
        ]
        input_fn = self._make_input_fn(inputs)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            mock_reg._models = {}
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                with patch("src.setup_wizard._get_provider_models", return_value=[]):
                    result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == 1
        assert result[0]["target_model"] == "model-b"

    def test_multi_target_max_limit(self):
        """At MAX_TARGETS_PER_PROVIDER, adding shows maximum reached message."""
        # Add MAX_TARGETS_PER_PROVIDER models, then try 'a' which should print "maximum reached"
        inputs = []
        for _ in range(MAX_TARGETS_PER_PROVIDER):
            inputs.extend(["", ""])  # accept default target + preproc
            inputs.append("a")  # try to add after each
        # Last 'a' should hit the limit, then 'd' to finish
        inputs.append("d")

        input_fn = self._make_input_fn(inputs)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == MAX_TARGETS_PER_PROVIDER

    def test_multi_target_modify_model(self):
        """Modifying model 1 changes its target_model."""
        inputs = [
            "",         # accept default target 1
            "",         # accept default preproc 1
            "m1",       # modify model 1
            "new-model", # new target
            "y",        # keep anyway
            "",         # new preproc
            "d",        # done
        ]
        input_fn = self._make_input_fn(inputs)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            mock_reg._models = {}
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                with patch("src.setup_wizard._get_provider_models", return_value=[]):
                    result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == 1
        assert result[0]["target_model"] == "new-model"

    def test_multi_target_done_immediately(self):
        """Selecting one target then 'd' returns single entry (backward compatible)."""
        inputs = [
            "",   # accept default target
            "",   # accept default preproc
            "d",  # done immediately
        ]
        input_fn = self._make_input_fn(inputs)

        with patch("src.setup_wizard.registry") as mock_reg:
            mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
            with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {"anthropic": "claude-sonnet-4-20250514"}):
                result = _select_models(["anthropic"], "per-provider", input_fn)

        assert len(result) == 1
        assert result[0]["target_model"] == "claude-sonnet-4-20250514"
        assert result[0]["preproc_model"] == "claude-haiku-4-5-20250514"


# ---------------------------------------------------------------------------
# Section 6: Validation ping tests (WIZ-06)
# ---------------------------------------------------------------------------


class TestValidateApiKey:
    """Tests for validate_api_key."""

    def test_validate_api_key_uses_model_id(self):
        """validate_api_key passes model_id to client.messages.create."""
        mock_client = MagicMock()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                ok, msg = validate_api_key(
                    "anthropic", "ANTHROPIC_API_KEY", model_id="claude-test-model"
                )
                mock_client.messages.create.assert_called_once()
                call_kwargs = mock_client.messages.create.call_args
                assert call_kwargs.kwargs.get("model") == "claude-test-model" or \
                       (call_kwargs[1].get("model") == "claude-test-model")
                assert ok is True

    def test_validate_api_key_falls_back_to_default_without_model_id(self):
        """Without model_id, uses hardcoded default model."""
        mock_client = MagicMock()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
                call_kwargs = mock_client.messages.create.call_args
                model_used = call_kwargs.kwargs.get("model") or call_kwargs[1].get("model")
                assert model_used == "claude-haiku-4-5-20250514"
                assert ok is True

    def test_validate_api_key_returns_false_when_env_not_set(self):
        """Returns (False, message) when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            ok, msg = validate_api_key("anthropic", "ANTHROPIC_API_KEY")
            assert ok is False
            assert "not set" in msg


class TestValidateModels:
    """Tests for _validate_models."""

    def test_validate_models_keeps_on_failure_if_user_says_yes(self):
        """Model kept when validation fails but user confirms."""
        models = [{"provider": "anthropic", "target_model": "test-model", "preproc_model": "haiku"}]
        input_fn = lambda prompt="": ""  # default = yes/keep

        with patch("src.setup_wizard.validate_api_key", return_value=(False, "error")):
            result = _validate_models(models, input_fn)

        assert len(result) == 1

    def test_validate_models_removes_on_failure_if_user_says_no(self):
        """Model removed when validation fails and user says no."""
        models = [{"provider": "anthropic", "target_model": "test-model", "preproc_model": "haiku"}]
        input_fn = lambda prompt="": "n"

        with patch("src.setup_wizard.validate_api_key", return_value=(False, "error")):
            result = _validate_models(models, input_fn)

        assert len(result) == 0


# ---------------------------------------------------------------------------
# Section 7: Budget preview tests (WIZ-05)
# ---------------------------------------------------------------------------


class TestBuildBudgetPreview:
    """Tests for _build_budget_preview."""

    def test_build_budget_preview_contains_pilot_and_full(self):
        """Preview contains 'Pilot run' and 'Full run' with dollar amounts."""
        models = [{"provider": "anthropic", "target_model": "claude-sonnet-4-20250514", "preproc_model": "claude-haiku-4-5-20250514"}]

        with patch("src.setup_wizard.estimate_cost", return_value={"target_cost": 1.50, "preproc_cost": 0.10}):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (3.0, 15.0)
                mock_reg._models = {"claude-sonnet-4-20250514": MagicMock()}
                result = _build_budget_preview(models)

        assert "Pilot run" in result
        assert "Full run" in result
        assert "$" in result

    def test_build_budget_preview_unknown_model_shows_pricing_unknown(self):
        """Unknown model shows 'pricing unknown' in output."""
        models = [{"provider": "anthropic", "target_model": "unknown-model-xyz", "preproc_model": "haiku"}]

        with patch("src.setup_wizard.estimate_cost", return_value={"target_cost": 0.0, "preproc_cost": 0.0}):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (0.0, 0.0)
                mock_reg._models = {}  # not in registry
                result = _build_budget_preview(models)

        assert "pricing unknown" in result

    def test_build_budget_preview_warns_over_50(self):
        """Warning shown when full run estimate exceeds $50."""
        models = [{"provider": "anthropic", "target_model": "claude-sonnet-4-20250514", "preproc_model": "claude-haiku-4-5-20250514"}]

        def mock_estimate(items):
            # Return high cost to trigger warning
            return {"target_cost": 60.0, "preproc_cost": 5.0}

        with patch("src.setup_wizard.estimate_cost", side_effect=mock_estimate):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (3.0, 15.0)
                mock_reg._models = {"claude-sonnet-4-20250514": MagicMock()}
                result = _build_budget_preview(models)

        assert "exceeds $50" in result


# ---------------------------------------------------------------------------
# Section 8: Wizard flow integration tests (WIZ-02)
# ---------------------------------------------------------------------------


class TestWizardFlow:
    """Tests for run_setup_wizard integration."""

    def test_wizard_non_interactive_creates_config(self, tmp_path):
        """Non-interactive mode writes defaults without prompting."""
        config_path = tmp_path / "experiment_config.json"
        args = SimpleNamespace(non_interactive=True)

        with patch("src.setup_wizard.save_config", return_value=config_path) as mock_save:
            with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
                run_setup_wizard(args)
                mock_save.assert_called_once()

    def test_wizard_ctrl_c_cancels_cleanly(self, capsys):
        """Ctrl-C during wizard prints 'Setup cancelled.' and returns."""
        args = SimpleNamespace(non_interactive=False)

        def raise_interrupt(prompt=""):
            raise KeyboardInterrupt

        with patch("src.setup_wizard.check_environment", return_value=[
            ("Python >= 3.11", True, "3.11.0"),
        ]):
            with patch("src.setup_wizard._detect_existing_config", return_value=None):
                result = run_setup_wizard(args, input_fn=raise_interrupt)

        assert result is None
        captured = capsys.readouterr()
        assert "Setup cancelled." in captured.out

    def test_wizard_interactive_full_flow(self, tmp_path):
        """Full interactive flow with 2 providers creates config with models."""
        config_path = tmp_path / "experiment_config.json"
        args = SimpleNamespace(non_interactive=False)

        # Flow: select providers 1,2 -> key for anthropic -> key for google ->
        # explain roles (per-provider) -> target anthropic -> preproc anthropic ->
        # done anthropic -> target google -> preproc google -> done google -> confirm
        inputs = [
            "1,2",           # provider selection
            "test-ant-key",  # anthropic key (no existing)
            "test-goo-key",  # google key (no existing)
            "1",             # per-provider preproc
            "",              # accept default anthropic target
            "",              # accept default anthropic preproc
            "d",             # done with anthropic
            "",              # accept default google target
            "",              # accept default google preproc
            "d",             # done with google
            "",              # keep validated model (anthropic)
            "",              # keep validated model (google)
            "y",             # confirm save
        ]
        input_idx = [0]

        def input_fn(prompt=""):
            idx = input_idx[0]
            input_idx[0] += 1
            if idx < len(inputs):
                return inputs[idx]
            return ""

        with patch("src.setup_wizard.check_environment", return_value=[
            ("Python >= 3.11", True, "3.11.0"),
        ]):
            with patch("src.setup_wizard._detect_existing_config", return_value=None):
                with patch.dict(os.environ, {}, clear=False):
                    # Clear any existing keys
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                    os.environ.pop("GOOGLE_API_KEY", None)

                    with patch("src.setup_wizard.write_env"):
                        with patch("src.setup_wizard.validate_api_key", return_value=(True, "ok")):
                            with patch("src.setup_wizard.save_config", return_value=config_path) as mock_save:
                                with patch("src.setup_wizard.validate_config", return_value=[]):
                                    with patch("src.setup_wizard.registry") as mock_reg:
                                        mock_reg.get_preproc.return_value = "claude-haiku-4-5-20250514"
                                        mock_reg.get_price.return_value = (3.0, 15.0)
                                        mock_reg._models = {}
                                        with patch("src.setup_wizard.DEFAULT_TARGET_MODELS", {
                                            "anthropic": "claude-sonnet-4-20250514",
                                            "google": "gemini-2.0-flash",
                                        }):
                                            with patch("src.setup_wizard.estimate_cost", return_value={"target_cost": 1.0, "preproc_cost": 0.1}):
                                                with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
                                                    with patch("src.setup_wizard.ModelConfig"):
                                                        run_setup_wizard(args, input_fn=input_fn)

                                mock_save.assert_called_once()
                                saved_config = mock_save.call_args[0][0]
                                assert "models" in saved_config
                                # Should have target entries for both providers
                                target_entries = [m for m in saved_config["models"] if m.get("role") == "target"]
                                assert len(target_entries) >= 2


# ---------------------------------------------------------------------------
# Section 9: Existing config re-entry tests
# ---------------------------------------------------------------------------


class TestExistingConfig:
    """Tests for _detect_existing_config and _handle_existing_config."""

    def test_detect_existing_config_returns_none_when_no_file(self):
        """Returns None when find_config_path returns None."""
        with patch("src.setup_wizard.find_config_path", return_value=None):
            result = _detect_existing_config()
        assert result is None

    def test_handle_existing_config_default_is_modify(self):
        """Empty input defaults to 'modify'."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [{"target": "claude-sonnet-4-20250514", "preproc": "haiku"}]}},
        }
        input_fn = lambda prompt="": ""
        result = _handle_existing_config(existing, input_fn)
        assert result == "modify"

    def test_handle_existing_config_modify(self):
        """Choosing '1' returns 'modify'."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [{"target": "claude-sonnet-4-20250514", "preproc": "haiku"}]}},
        }
        input_fn = lambda prompt="": "1"
        result = _handle_existing_config(existing, input_fn)
        assert result == "modify"

    def test_handle_existing_config_remove(self):
        """Choosing '2' returns 'remove'."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [{"target": "claude-sonnet-4-20250514", "preproc": "haiku"}]}},
        }
        input_fn = lambda prompt="": "2"
        result = _handle_existing_config(existing, input_fn)
        assert result == "remove"

    def test_handle_existing_config_add(self):
        """Choosing '3' returns 'add'."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [{"target": "claude-sonnet-4-20250514", "preproc": "haiku"}]}},
        }
        input_fn = lambda prompt="": "3"
        result = _handle_existing_config(existing, input_fn)
        assert result == "add"

    def test_handle_existing_config_reconfigure(self):
        """Choosing '4' returns 'reconfigure'."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [{"target": "claude-sonnet-4-20250514", "preproc": "haiku"}]}},
        }
        input_fn = lambda prompt="": "4"
        result = _handle_existing_config(existing, input_fn)
        assert result == "reconfigure"

    def test_handle_existing_config_shows_numbered_targets(self, capsys):
        """Multiple targets per provider are displayed with numbers."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [
                {"target": "claude-sonnet-4-20250514", "preproc": "haiku"},
                {"target": "claude-opus-4-20250514", "preproc": "haiku"},
            ]}},
        }
        input_fn = lambda prompt="": "4"
        _handle_existing_config(existing, input_fn)
        captured = capsys.readouterr()
        assert "1." in captured.out
        assert "2." in captured.out
        assert "claude-sonnet-4-20250514" in captured.out
        assert "claude-opus-4-20250514" in captured.out


    def test_remove_existing_config_removes_entry(self):
        """Removing entry 1 from a 2-entry config leaves 1 entry."""
        existing = {
            "providers": ["anthropic"],
            "models": {"anthropic": {"targets": [
                {"target": "claude-sonnet-4-20250514", "preproc": "haiku"},
                {"target": "claude-opus-4-20250514", "preproc": "haiku"},
            ]}},
        }
        responses = iter(["1", "d"])
        input_fn = lambda prompt="": next(responses)
        result = _remove_existing_config(existing, input_fn)
        assert result is not None
        assert len(result) == 1
        assert result[0]["target_model"] == "claude-opus-4-20250514"

    def test_remove_existing_config_all_returns_none(self):
        """Removing all entries returns None."""
        existing = {
            "providers": ["openai"],
            "models": {"openai": {"targets": [
                {"target": "gpt-5.1", "preproc": "gpt-5-nano"},
            ]}},
        }
        input_fn = lambda prompt="": "1"
        result = _remove_existing_config(existing, input_fn)
        assert result is None


# ---------------------------------------------------------------------------
# Section 10: Config dict building
# ---------------------------------------------------------------------------


class TestBuildConfigDict:
    """Tests for _build_config_dict."""

    def test_build_config_dict_has_models_list(self):
        """Config dict has 'models' key with target and preproc entries."""
        models = [
            {"provider": "anthropic", "target_model": "claude-sonnet-4-20250514", "preproc_model": "claude-haiku-4-5-20250514"},
            {"provider": "google", "target_model": "gemini-2.0-flash", "preproc_model": "gemini-2.0-flash"},
        ]

        with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (3.0, 15.0)
                mock_reg._models = {
                    "claude-sonnet-4-20250514": MagicMock(),
                    "claude-haiku-4-5-20250514": MagicMock(),
                    "gemini-2.0-flash": MagicMock(),
                }
                result = _build_config_dict(models)

        assert "models" in result
        assert isinstance(result["models"], list)
        target_entries = [m for m in result["models"] if m["role"] == "target"]
        preproc_entries = [m for m in result["models"] if m["role"] == "preproc"]
        assert len(target_entries) == 2
        assert len(preproc_entries) >= 1

    def test_build_config_dict_multi_target_per_provider(self):
        """Multiple targets from same provider produce multiple target entries."""
        models = [
            {"provider": "anthropic", "target_model": "claude-sonnet-4-20250514", "preproc_model": "claude-haiku-4-5-20250514"},
            {"provider": "anthropic", "target_model": "claude-opus-4-20250514", "preproc_model": "claude-haiku-4-5-20250514"},
        ]

        with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (3.0, 15.0)
                mock_reg._models = {
                    "claude-sonnet-4-20250514": MagicMock(),
                    "claude-opus-4-20250514": MagicMock(),
                    "claude-haiku-4-5-20250514": MagicMock(),
                }
                result = _build_config_dict(models)

        target_entries = [m for m in result["models"] if m["role"] == "target"]
        preproc_entries = [m for m in result["models"] if m["role"] == "preproc"]
        assert len(target_entries) == 2
        target_ids = {m["model_id"] for m in target_entries}
        assert "claude-sonnet-4-20250514" in target_ids
        assert "claude-opus-4-20250514" in target_ids
        # Shared preproc should be deduplicated
        assert len(preproc_entries) == 1
        assert preproc_entries[0]["model_id"] == "claude-haiku-4-5-20250514"

    def test_build_config_dict_deduplicates_preproc(self):
        """Shared preproc model appears only once in models list."""
        models = [
            {"provider": "anthropic", "target_model": "claude-sonnet-4-20250514", "preproc_model": "shared-preproc"},
            {"provider": "google", "target_model": "gemini-2.0-flash", "preproc_model": "shared-preproc"},
        ]

        with patch("src.setup_wizard.get_full_config_dict", return_value={"temperature": 0.0}):
            with patch("src.setup_wizard.registry") as mock_reg:
                mock_reg.get_price.return_value = (0.0, 0.0)
                mock_reg._models = {}
                result = _build_config_dict(models)

        preproc_entries = [m for m in result["models"] if m["role"] == "preproc"]
        preproc_ids = [m["model_id"] for m in preproc_entries]
        assert preproc_ids.count("shared-preproc") == 1


# ---------------------------------------------------------------------------
# Section 11: check_environment tests
# ---------------------------------------------------------------------------


class TestCheckEnvironment:
    """Tests for check_environment."""

    def test_check_environment_returns_list_of_tuples(self):
        """Returns list of (name, passed, detail) tuples."""
        results = check_environment()
        assert isinstance(results, list)
        for item in results:
            assert len(item) == 3
            name, passed, detail = item
            assert isinstance(name, str)
            assert isinstance(passed, bool)
            assert isinstance(detail, str)

    def test_check_environment_detects_python_version(self):
        """Detects Python >= 3.11 as passed."""
        results = check_environment()
        python_check = [r for r in results if r[0] == "Python >= 3.11"]
        assert len(python_check) == 1
        assert python_check[0][1] is True

    def test_check_environment_detects_missing_package(self):
        """Detects missing packages as failed."""
        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            results = check_environment()
            package_checks = [r for r in results if r[0] != "Python >= 3.11"]
            failed = [r for r in package_checks if not r[1]]
            assert len(failed) > 0
