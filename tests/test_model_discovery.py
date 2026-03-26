"""Tests for the model discovery module.

Covers all 4 provider query functions, parallel orchestration,
timeout handling, missing API keys, pagination, and fallback.
"""

import os
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from src.model_discovery import (
    DiscoveredModel,
    DiscoveryResult,
    _get_fallback_models,
    _query_anthropic,
    _query_google,
    _query_openai,
    _query_openrouter,
    discover_all_models,
)


# ---------------------------------------------------------------------------
# Anthropic tests
# ---------------------------------------------------------------------------

class TestQueryAnthropic:
    """Tests for _query_anthropic."""

    @patch("src.model_discovery.anthropic")
    def test_query_anthropic_returns_discovered_models(self, mock_anthropic_mod):
        """Basic Anthropic query returns DiscoveredModel with correct fields."""
        mock_model = MagicMock()
        mock_model.id = "claude-sonnet-4-20250514"
        mock_model.max_input_tokens = 200000

        mock_page = MagicMock()
        mock_page.data = [mock_model]
        mock_page.has_more = False

        mock_client = MagicMock()
        mock_client.models.list.return_value = mock_page
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = _query_anthropic(timeout=5.0)

        assert len(result) == 1
        m = result[0]
        assert isinstance(m, DiscoveredModel)
        assert m.model_id == "claude-sonnet-4-20250514"
        assert m.provider == "anthropic"
        assert m.context_window == 200000
        assert m.input_price_per_1m is None
        assert m.output_price_per_1m is None

    @patch("src.model_discovery.anthropic")
    def test_query_anthropic_pagination(self, mock_anthropic_mod):
        """Anthropic pagination: when has_more=True, fetches additional pages."""
        model_a = MagicMock()
        model_a.id = "claude-sonnet-4-20250514"
        model_a.max_input_tokens = 200000

        model_b = MagicMock()
        model_b.id = "claude-haiku-35-20241022"
        model_b.max_input_tokens = 100000

        page1 = MagicMock()
        page1.data = [model_a]
        page1.has_more = True
        page1.last_id = "claude-sonnet-4-20250514"

        page2 = MagicMock()
        page2.data = [model_b]
        page2.has_more = False

        mock_client = MagicMock()
        mock_client.models.list.side_effect = [page1, page2]
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = _query_anthropic(timeout=5.0)

        assert len(result) == 2
        assert result[0].model_id == "claude-sonnet-4-20250514"
        assert result[1].model_id == "claude-haiku-35-20241022"
        # Verify second call used after_id
        calls = mock_client.models.list.call_args_list
        assert len(calls) == 2
        assert calls[1][1].get("after_id") == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Google tests
# ---------------------------------------------------------------------------

class TestQueryGoogle:
    """Tests for _query_google."""

    @patch("src.model_discovery.genai")
    def test_query_google_strips_models_prefix(self, mock_genai_mod):
        """Google model names have 'models/' prefix stripped."""
        mock_model = MagicMock()
        mock_model.name = "models/gemini-1.5-pro"
        mock_model.input_token_limit = 1048576

        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model]
        mock_genai_mod.Client.return_value = mock_client

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = _query_google(timeout=5.0)

        assert len(result) == 1
        assert result[0].model_id == "gemini-1.5-pro"
        assert result[0].provider == "google"
        assert result[0].context_window == 1048576
        assert result[0].input_price_per_1m is None
        assert result[0].output_price_per_1m is None

    @patch("src.model_discovery.genai")
    def test_query_google_skips_empty_model_id(self, mock_genai_mod):
        """Google models with empty name after prefix strip are skipped."""
        mock_model = MagicMock()
        mock_model.name = "models/"
        mock_model.input_token_limit = None

        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model]
        mock_genai_mod.Client.return_value = mock_client

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = _query_google(timeout=5.0)

        assert len(result) == 0


# ---------------------------------------------------------------------------
# OpenAI tests
# ---------------------------------------------------------------------------

class TestQueryOpenAI:
    """Tests for _query_openai."""

    @patch("src.model_discovery.openai")
    def test_query_openai_returns_discovered_models(self, mock_openai_mod):
        """OpenAI query returns DiscoveredModel with no context window or pricing."""
        mock_model = MagicMock()
        mock_model.id = "gpt-4o"

        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model]
        mock_openai_mod.OpenAI.return_value = mock_client

        result = _query_openai(timeout=5.0)

        assert len(result) == 1
        m = result[0]
        assert m.model_id == "gpt-4o"
        assert m.provider == "openai"
        assert m.context_window is None
        assert m.input_price_per_1m is None
        assert m.output_price_per_1m is None


# ---------------------------------------------------------------------------
# OpenRouter tests
# ---------------------------------------------------------------------------

class TestQueryOpenRouter:
    """Tests for _query_openrouter."""

    @patch("src.model_discovery.requests")
    def test_query_openrouter_parses_pricing(self, mock_requests):
        """OpenRouter pricing strings are parsed to per-1M floats."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "anthropic/claude-3-opus",
                    "context_length": 200000,
                    "pricing": {
                        "prompt": "0.000003",
                        "completion": "0.000004",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = _query_openrouter(timeout=5.0)

        assert len(result) == 1
        m = result[0]
        assert m.model_id == "anthropic/claude-3-opus"
        assert m.provider == "openrouter"
        assert m.context_window == 200000
        assert m.input_price_per_1m == pytest.approx(3.0)
        assert m.output_price_per_1m == pytest.approx(4.0)

    @patch("src.model_discovery.requests")
    def test_query_openrouter_free_models(self, mock_requests):
        """OpenRouter free models (pricing '0') parse as 0.0."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "free/model",
                    "context_length": 4096,
                    "pricing": {
                        "prompt": "0",
                        "completion": "0",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = _query_openrouter(timeout=5.0)

        assert len(result) == 1
        assert result[0].input_price_per_1m == 0.0
        assert result[0].output_price_per_1m == 0.0


# ---------------------------------------------------------------------------
# discover_all_models tests
# ---------------------------------------------------------------------------

class TestDiscoverAllModels:
    """Tests for discover_all_models orchestrator."""

    @patch("src.model_discovery._PROVIDER_QUERY_MAP")
    def test_skips_providers_with_missing_api_keys(self, mock_query_map):
        """Missing API keys cause skip warning, not crash."""
        mock_query_map.items.return_value = [("anthropic", MagicMock())]

        with patch.dict(os.environ, {}, clear=True):
            result = discover_all_models(timeout=5.0)

        assert "anthropic" in result.errors
        assert "ANTHROPIC_API_KEY" in result.errors["anthropic"]
        assert "anthropic" not in result.models

    @patch("src.model_discovery._PROVIDER_QUERY_MAP")
    def test_catches_provider_exceptions(self, mock_query_map):
        """Provider API failures populate errors dict."""
        def failing_query(timeout: float = 5.0) -> list:
            raise ConnectionError("API unreachable")

        mock_query_map.items.return_value = [("anthropic", failing_query)]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = discover_all_models(timeout=5.0)

        assert "anthropic" in result.errors
        assert "API unreachable" in result.errors["anthropic"]

    @patch("src.model_discovery._PROVIDER_QUERY_MAP")
    def test_timeout_produces_error(self, mock_query_map):
        """Provider that sleeps >5s produces error, not hang."""
        def slow_query(timeout: float = 5.0) -> list:
            time.sleep(10)
            return []

        mock_query_map.items.return_value = [("anthropic", slow_query)]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = discover_all_models(timeout=0.1)  # short timeout for test speed

        assert "anthropic" in result.errors


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------

class TestGetFallbackModels:
    """Tests for _get_fallback_models."""

    @patch("src.model_discovery.registry")
    def test_fallback_returns_registry_models(self, mock_registry):
        """Fallback returns DiscoveredModel instances from registry."""
        mock_mc = MagicMock()
        mock_mc.model_id = "claude-sonnet-4-20250514"
        mock_mc.provider = "anthropic"
        mock_mc.input_price_per_1m = 3.0
        mock_mc.output_price_per_1m = 15.0

        mock_other = MagicMock()
        mock_other.model_id = "gpt-4o"
        mock_other.provider = "openai"

        mock_registry._models = {
            "claude-sonnet-4-20250514": mock_mc,
            "gpt-4o": mock_other,
        }

        result = _get_fallback_models("anthropic")

        assert len(result) == 1
        m = result[0]
        assert isinstance(m, DiscoveredModel)
        assert m.model_id == "claude-sonnet-4-20250514"
        assert m.provider == "anthropic"
        assert m.context_window is None
        assert m.input_price_per_1m == 3.0
        assert m.output_price_per_1m == 15.0
