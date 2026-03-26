"""Tests for the env_manager module."""

import os
import stat

import pytest

from src.env_manager import PROVIDER_KEY_MAP, check_keys, load_env, write_env


class TestProviderKeyMap:
    """Tests for the PROVIDER_KEY_MAP constant."""

    def test_contains_exactly_four_entries(self) -> None:
        assert len(PROVIDER_KEY_MAP) == 4

    def test_contains_expected_providers(self) -> None:
        assert set(PROVIDER_KEY_MAP.keys()) == {
            "anthropic",
            "google",
            "openai",
            "openrouter",
        }

    def test_maps_to_correct_env_vars(self) -> None:
        assert PROVIDER_KEY_MAP["anthropic"] == "ANTHROPIC_API_KEY"
        assert PROVIDER_KEY_MAP["google"] == "GOOGLE_API_KEY"
        assert PROVIDER_KEY_MAP["openai"] == "OPENAI_API_KEY"
        assert PROVIDER_KEY_MAP["openrouter"] == "OPENROUTER_API_KEY"


class TestLoadEnv:
    """Tests for the load_env function."""

    def test_returns_false_when_no_env_file(self, tmp_path: object) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        result = load_env(env_path=env_path)
        assert result is False

    def test_returns_true_and_loads_vars(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        env_path.write_text("TEST_LOAD_VAR=hello_world\n")  # type: ignore[union-attr]
        # Ensure the var is not already set
        monkeypatch.delenv("TEST_LOAD_VAR", raising=False)

        result = load_env(env_path=env_path)

        assert result is True
        assert os.environ.get("TEST_LOAD_VAR") == "hello_world"

    def test_does_not_override_existing_env_vars(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        env_path.write_text("TEST_OVERRIDE_VAR=from_file\n")  # type: ignore[union-attr]
        monkeypatch.setenv("TEST_OVERRIDE_VAR", "original_value")

        load_env(env_path=env_path)

        assert os.environ["TEST_OVERRIDE_VAR"] == "original_value"


class TestWriteEnv:
    """Tests for the write_env function."""

    def test_creates_env_file_if_not_exists(self, tmp_path: object) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        write_env("MY_KEY", "my_value", env_path=env_path)
        assert env_path.exists()  # type: ignore[union-attr]
        content = env_path.read_text()  # type: ignore[union-attr]
        assert "MY_KEY" in content
        assert "my_value" in content

    def test_adds_key_to_existing_file(self, tmp_path: object) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        env_path.write_text("EXISTING_KEY=existing_value\n")  # type: ignore[union-attr]
        write_env("NEW_KEY", "new_value", env_path=env_path)
        content = env_path.read_text()  # type: ignore[union-attr]
        assert "EXISTING_KEY" in content
        assert "NEW_KEY" in content
        assert "new_value" in content

    def test_sets_permissions_to_600(self, tmp_path: object) -> None:
        env_path = tmp_path / ".env"  # type: ignore[operator]
        write_env("PERM_KEY", "perm_value", env_path=env_path)
        file_mode = os.stat(env_path).st_mode & 0o777  # type: ignore[arg-type]
        assert file_mode == 0o600


class TestCheckKeys:
    """Tests for the check_keys function."""

    def test_returns_true_when_key_is_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        result = check_keys(["anthropic"])
        assert result == {"anthropic": True}

    def test_returns_false_when_key_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = check_keys(["anthropic"])
        assert result == {"anthropic": False}

    def test_checks_multiple_providers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = check_keys(["anthropic", "google"])
        assert result == {"anthropic": True, "google": False}

    def test_unknown_provider_returns_false(self) -> None:
        result = check_keys(["unknown_provider"])
        assert result == {"unknown_provider": False}
