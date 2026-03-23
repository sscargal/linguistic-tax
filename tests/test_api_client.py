"""Tests for src/api_client.py — unified API client with streaming TTFT/TTLT.

All tests use mocked SDKs. No real API calls are made.
"""

import dataclasses
import os
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.api_client import APIResponse, call_model, _call_anthropic, _call_google, _call_openai, _rate_delays


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_anthropic_stream_mock(text_chunks: list[str], input_tokens: int, output_tokens: int):
    """Create a mock Anthropic streaming context manager."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    final_message = MagicMock()
    final_message.usage = usage

    stream_cm = MagicMock()
    stream_cm.text_stream = iter(text_chunks)
    stream_cm.get_final_message.return_value = final_message
    stream_cm.__enter__ = MagicMock(return_value=stream_cm)
    stream_cm.__exit__ = MagicMock(return_value=False)

    return stream_cm, final_message


def _make_google_chunks(text_chunks: list[str], prompt_tokens: int, candidate_tokens: int):
    """Create mock Google GenAI streaming chunks."""
    chunks = []
    for i, text in enumerate(text_chunks):
        chunk = MagicMock()
        chunk.text = text
        # Only the last chunk has usage_metadata
        if i == len(text_chunks) - 1:
            usage = MagicMock()
            usage.prompt_token_count = prompt_tokens
            usage.candidates_token_count = candidate_tokens
            chunk.usage_metadata = usage
        else:
            chunk.usage_metadata = None
        chunks.append(chunk)
    return chunks


def _make_openai_stream_chunks(
    text_chunks: list[str], prompt_tokens: int, completion_tokens: int
):
    """Create mock OpenAI streaming chunks.

    Each text chunk has choices[0].delta.content = text and usage = None.
    The final chunk has choices = [] and usage populated.
    """
    chunks = []
    for text in text_chunks:
        chunk = MagicMock()
        chunk.usage = None
        delta = MagicMock()
        delta.content = text
        choice = MagicMock()
        choice.delta = delta
        chunk.choices = [choice]
        chunks.append(chunk)

    # Final usage chunk with empty choices
    final = MagicMock()
    final.choices = []
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    final.usage = usage
    chunks.append(final)

    return chunks


# ---------------------------------------------------------------------------
# APIResponse dataclass tests
# ---------------------------------------------------------------------------

class TestAPIResponse:
    def test_is_frozen_dataclass(self):
        """APIResponse is a frozen dataclass with all required fields."""
        resp = APIResponse(
            text="hello", input_tokens=10, output_tokens=5,
            ttft_ms=1.0, ttlt_ms=2.0, model="test",
        )
        assert resp.text == "hello"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5
        assert resp.ttft_ms == 1.0
        assert resp.ttlt_ms == 2.0
        assert resp.model == "test"

    def test_frozen_immutability(self):
        """APIResponse cannot be mutated."""
        resp = APIResponse(
            text="hello", input_tokens=10, output_tokens=5,
            ttft_ms=1.0, ttlt_ms=2.0, model="test",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            resp.text = "modified"

    def test_has_all_required_fields(self):
        """APIResponse has exactly the documented fields."""
        fields = {f.name for f in dataclasses.fields(APIResponse)}
        expected = {"text", "input_tokens", "output_tokens", "ttft_ms", "ttlt_ms", "model"}
        assert fields == expected


# ---------------------------------------------------------------------------
# call_model routing tests
# ---------------------------------------------------------------------------

class TestCallModelRouting:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("src.api_client._call_anthropic")
    @patch("src.api_client._apply_rate_limit")
    def test_routes_claude_to_anthropic(self, mock_rate, mock_anthropic):
        """call_model with claude model name routes to _call_anthropic."""
        mock_anthropic.return_value = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="claude-sonnet-4-20250514",
        )
        result = call_model("claude-sonnet-4-20250514", None, "hello", 100)
        mock_anthropic.assert_called_once()
        assert result.model == "claude-sonnet-4-20250514"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("src.api_client._call_google")
    @patch("src.api_client._apply_rate_limit")
    def test_routes_gemini_to_google(self, mock_rate, mock_google):
        """call_model with gemini model name routes to _call_google."""
        mock_google.return_value = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="gemini-1.5-pro",
        )
        result = call_model("gemini-1.5-pro", None, "hello", 100)
        mock_google.assert_called_once()
        assert result.model == "gemini-1.5-pro"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x", "GOOGLE_API_KEY": "y", "OPENAI_API_KEY": "z"})
    def test_unknown_model_raises_value_error(self):
        """call_model with unknown model raises ValueError."""
        with pytest.raises(ValueError, match="Unknown model"):
            call_model("llama-3-70b", None, "hello", 100)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.api_client._call_openai")
    @patch("src.api_client._apply_rate_limit")
    def test_routes_gpt_to_openai(self, mock_rate, mock_openai):
        """call_model with gpt model name routes to _call_openai."""
        mock_openai.return_value = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="gpt-4o-2024-11-20",
        )
        result = call_model("gpt-4o-2024-11-20", None, "hello", 100)
        mock_openai.assert_called_once()
        assert result.model == "gpt-4o-2024-11-20"


# ---------------------------------------------------------------------------
# Anthropic streaming tests
# ---------------------------------------------------------------------------

class TestCallAnthropic:
    @patch("src.api_client.anthropic.Anthropic")
    def test_uses_stream_context_manager(self, mock_cls):
        """_call_anthropic uses client.messages.stream() context manager."""
        stream_cm, _ = _make_anthropic_stream_mock(["hello ", "world"], 10, 5)
        client = MagicMock()
        client.messages.stream.return_value = stream_cm
        mock_cls.return_value = client

        result = _call_anthropic("claude-sonnet-4-20250514", None, "test", 100, 0.0)

        client.messages.stream.assert_called_once()
        assert result.text == "hello world"

    @patch("src.api_client.anthropic.Anthropic")
    def test_returns_token_counts_from_usage(self, mock_cls):
        """_call_anthropic returns token counts from final_message.usage."""
        stream_cm, _ = _make_anthropic_stream_mock(["hi"], 42, 17)
        client = MagicMock()
        client.messages.stream.return_value = stream_cm
        mock_cls.return_value = client

        result = _call_anthropic("claude-sonnet-4-20250514", None, "test", 100, 0.0)

        assert result.input_tokens == 42
        assert result.output_tokens == 17

    @patch("src.api_client.anthropic.Anthropic")
    def test_passes_system_only_when_not_none(self, mock_cls):
        """_call_anthropic passes system parameter only when system is not None."""
        stream_cm, _ = _make_anthropic_stream_mock(["hi"], 10, 5)
        client = MagicMock()
        client.messages.stream.return_value = stream_cm
        mock_cls.return_value = client

        # Without system
        _call_anthropic("claude-sonnet-4-20250514", None, "test", 100, 0.0)
        kwargs_no_sys = client.messages.stream.call_args[1]
        assert "system" not in kwargs_no_sys

        # With system
        client.messages.stream.return_value = _make_anthropic_stream_mock(["hi"], 10, 5)[0]
        _call_anthropic("claude-sonnet-4-20250514", "Be helpful", "test", 100, 0.0)
        kwargs_with_sys = client.messages.stream.call_args[1]
        assert kwargs_with_sys["system"] == "Be helpful"


# ---------------------------------------------------------------------------
# Google GenAI streaming tests
# ---------------------------------------------------------------------------

class TestCallGoogle:
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("src.api_client.genai.Client")
    def test_uses_generate_content_stream(self, mock_cls):
        """_call_google uses client.models.generate_content_stream()."""
        chunks = _make_google_chunks(["hello ", "world"], 15, 8)
        client = MagicMock()
        client.models.generate_content_stream.return_value = iter(chunks)
        mock_cls.return_value = client

        result = _call_google("gemini-1.5-pro", None, "test", 100, 0.0)

        client.models.generate_content_stream.assert_called_once()
        assert result.text == "hello world"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("src.api_client.genai.Client")
    def test_returns_token_counts_from_usage_metadata(self, mock_cls):
        """_call_google returns token counts from last_chunk.usage_metadata."""
        chunks = _make_google_chunks(["hi"], 33, 12)
        client = MagicMock()
        client.models.generate_content_stream.return_value = iter(chunks)
        mock_cls.return_value = client

        result = _call_google("gemini-1.5-pro", None, "test", 100, 0.0)

        assert result.input_tokens == 33
        assert result.output_tokens == 12

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    @patch("src.api_client.genai.Client")
    def test_handles_none_last_chunk_gracefully(self, mock_cls):
        """_call_google returns 0 tokens when no chunks are received."""
        client = MagicMock()
        client.models.generate_content_stream.return_value = iter([])
        mock_cls.return_value = client

        result = _call_google("gemini-1.5-pro", None, "test", 100, 0.0)

        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.text == ""


# ---------------------------------------------------------------------------
# OpenAI streaming tests
# ---------------------------------------------------------------------------

class TestCallOpenAI:
    @patch("src.api_client.openai.OpenAI")
    def test_streams_and_assembles_text(self, mock_cls):
        """_call_openai streams chunks and assembles text correctly."""
        chunks = _make_openai_stream_chunks(["hello ", "world"], 10, 5)
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        mock_cls.return_value = client

        result = _call_openai("gpt-4o-2024-11-20", None, "test", 100, 0.0)

        assert result.text == "hello world"

    @patch("src.api_client.openai.OpenAI")
    def test_returns_token_counts_from_usage(self, mock_cls):
        """_call_openai returns token counts from the usage chunk."""
        chunks = _make_openai_stream_chunks(["hi"], 25, 10)
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        mock_cls.return_value = client

        result = _call_openai("gpt-4o-2024-11-20", None, "test", 100, 0.0)

        assert result.input_tokens == 25
        assert result.output_tokens == 10

    @patch("src.api_client.openai.OpenAI")
    def test_system_message_prepended(self, mock_cls):
        """_call_openai prepends system message when provided."""
        chunks = _make_openai_stream_chunks(["hi"], 10, 5)
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        mock_cls.return_value = client

        _call_openai("gpt-4o-2024-11-20", "Be helpful", "test", 100, 0.0)

        call_kwargs = client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be helpful"}
        assert messages[1] == {"role": "user", "content": "test"}

    @patch("src.api_client.openai.OpenAI")
    def test_no_system_message_when_none(self, mock_cls):
        """_call_openai sends only user message when system is None."""
        chunks = _make_openai_stream_chunks(["hi"], 10, 5)
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        mock_cls.return_value = client

        _call_openai("gpt-4o-2024-11-20", None, "test", 100, 0.0)

        call_kwargs = client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @patch("src.api_client.openai.OpenAI")
    def test_handles_none_delta_content(self, mock_cls):
        """_call_openai handles chunks where delta.content is None."""
        # Create a chunk with None content (role-only delta)
        role_chunk = MagicMock()
        role_chunk.usage = None
        delta = MagicMock()
        delta.content = None
        choice = MagicMock()
        choice.delta = delta
        role_chunk.choices = [choice]

        text_chunks = _make_openai_stream_chunks(["hello"], 10, 5)
        all_chunks = [role_chunk] + text_chunks
        client = MagicMock()
        client.chat.completions.create.return_value = iter(all_chunks)
        mock_cls.return_value = client

        result = _call_openai("gpt-4o-2024-11-20", None, "test", 100, 0.0)

        assert result.text == "hello"


# ---------------------------------------------------------------------------
# Timing tests
# ---------------------------------------------------------------------------

class TestTiming:
    @patch("src.api_client.anthropic.Anthropic")
    @patch("src.api_client.time.monotonic")
    def test_ttft_is_positive_with_chunks(self, mock_mono, mock_cls):
        """ttft_ms is > 0 when streaming returns text chunks."""
        # Simulate: start=0.0, first chunk at 0.050, end at 0.100
        mock_mono.side_effect = [0.0, 0.050, 0.100]
        stream_cm, _ = _make_anthropic_stream_mock(["hello"], 10, 5)
        client = MagicMock()
        client.messages.stream.return_value = stream_cm
        mock_cls.return_value = client

        result = _call_anthropic("claude-sonnet-4-20250514", None, "test", 100, 0.0)

        assert result.ttft_ms > 0
        assert result.ttft_ms == pytest.approx(50.0)

    @patch("src.api_client.anthropic.Anthropic")
    @patch("src.api_client.time.monotonic")
    def test_ttlt_gte_ttft(self, mock_mono, mock_cls):
        """ttlt_ms >= ttft_ms."""
        # Simulate: start=0.0, first chunk at 0.050, end at 0.150
        mock_mono.side_effect = [0.0, 0.050, 0.150]
        stream_cm, _ = _make_anthropic_stream_mock(["hello"], 10, 5)
        client = MagicMock()
        client.messages.stream.return_value = stream_cm
        mock_cls.return_value = client

        result = _call_anthropic("claude-sonnet-4-20250514", None, "test", 100, 0.0)

        assert result.ttlt_ms >= result.ttft_ms
        assert result.ttlt_ms == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# Retry / rate limiting tests
# ---------------------------------------------------------------------------

class TestRetryAndRateLimiting:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("src.api_client.time.sleep")
    @patch("src.api_client._call_anthropic")
    @patch("src.api_client._apply_rate_limit")
    def test_retries_on_rate_limit_up_to_3_times(self, mock_rate, mock_call, mock_sleep):
        """Retry logic retries on RateLimitError up to 3 times with exponential backoff."""
        import anthropic as anth

        # Create a proper RateLimitError mock
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.headers = {}
        error_response.json.return_value = {"error": {"message": "rate limited"}}
        rate_error = anth.RateLimitError(
            message="rate limited",
            response=error_response,
            body={"error": {"message": "rate limited"}},
        )

        success = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="claude-sonnet-4-20250514",
        )
        mock_call.side_effect = [rate_error, rate_error, success]

        # Reset rate delays before test
        _rate_delays.update({"claude-sonnet-4-20250514": 0.2})

        result = call_model("claude-sonnet-4-20250514", None, "hello", 100)

        assert result.text == "ok"
        assert mock_call.call_count == 3
        # Should have slept for backoff delays (1s, 4s)
        assert mock_sleep.call_count >= 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("src.api_client.time.sleep")
    @patch("src.api_client._call_anthropic")
    @patch("src.api_client._apply_rate_limit")
    def test_raises_after_4_total_failures(self, mock_rate, mock_call, mock_sleep):
        """After 4 total failures, raises the exception."""
        import anthropic as anth

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.headers = {}
        error_response.json.return_value = {"error": {"message": "rate limited"}}
        rate_error = anth.RateLimitError(
            message="rate limited",
            response=error_response,
            body={"error": {"message": "rate limited"}},
        )

        mock_call.side_effect = [rate_error, rate_error, rate_error, rate_error]

        _rate_delays.update({"claude-sonnet-4-20250514": 0.2})

        with pytest.raises(anth.RateLimitError):
            call_model("claude-sonnet-4-20250514", None, "hello", 100)

        assert mock_call.call_count == 4

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.api_client.time.sleep")
    @patch("src.api_client._call_openai")
    @patch("src.api_client._apply_rate_limit")
    def test_retries_on_openai_rate_limit(self, mock_rate, mock_call, mock_sleep):
        """Retry logic retries on openai.RateLimitError."""
        import openai as oai

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.headers = {}
        error_response.json.return_value = {"error": {"message": "rate limited"}}
        rate_error = oai.RateLimitError(
            message="rate limited",
            response=error_response,
            body={"error": {"message": "rate limited"}},
        )

        success = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="gpt-4o-2024-11-20",
        )
        mock_call.side_effect = [rate_error, rate_error, success]

        _rate_delays.update({"gpt-4o-2024-11-20": 0.2})

        result = call_model("gpt-4o-2024-11-20", None, "hello", 100)

        assert result.text == "ok"
        assert mock_call.call_count == 3
        assert mock_sleep.call_count >= 2

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("src.api_client.time.sleep")
    @patch("src.api_client._call_openai")
    @patch("src.api_client._apply_rate_limit")
    def test_openai_429_doubles_rate_delay(self, mock_rate, mock_call, mock_sleep):
        """On OpenAI 429, rate limit delay doubles."""
        import openai as oai

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.headers = {}
        error_response.json.return_value = {"error": {"message": "rate limited"}}
        rate_error = oai.RateLimitError(
            message="rate limited",
            response=error_response,
            body={"error": {"message": "rate limited"}},
        )

        success = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="gpt-4o-2024-11-20",
        )
        mock_call.side_effect = [rate_error, success]

        original_delay = 0.2
        _rate_delays.update({"gpt-4o-2024-11-20": original_delay})

        call_model("gpt-4o-2024-11-20", None, "hello", 100)

        assert _rate_delays["gpt-4o-2024-11-20"] == original_delay * 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("src.api_client.time.sleep")
    @patch("src.api_client._call_anthropic")
    @patch("src.api_client._apply_rate_limit")
    def test_429_doubles_rate_delay(self, mock_rate, mock_call, mock_sleep):
        """On 429 response, rate limit delay doubles for subsequent calls."""
        import anthropic as anth

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.headers = {}
        error_response.json.return_value = {"error": {"message": "rate limited"}}
        rate_error = anth.RateLimitError(
            message="rate limited",
            response=error_response,
            body={"error": {"message": "rate limited"}},
        )

        success = APIResponse(
            text="ok", input_tokens=1, output_tokens=1,
            ttft_ms=1.0, ttlt_ms=2.0, model="claude-sonnet-4-20250514",
        )
        mock_call.side_effect = [rate_error, success]

        original_delay = 0.2
        _rate_delays.update({"claude-sonnet-4-20250514": original_delay})

        call_model("claude-sonnet-4-20250514", None, "hello", 100)

        assert _rate_delays["claude-sonnet-4-20250514"] == original_delay * 2


# ---------------------------------------------------------------------------
# API key validation tests
# ---------------------------------------------------------------------------

class TestAPIKeyValidation:
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_anthropic_key_raises(self):
        """API keys validated via os.environ.get with EnvironmentError if missing."""
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            call_model("claude-sonnet-4-20250514", None, "test", 100)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_google_key_raises(self):
        """API keys validated via os.environ.get with EnvironmentError if missing."""
        with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY"):
            call_model("gemini-1.5-pro", None, "test", 100)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_openai_key_raises(self):
        """Missing OPENAI_API_KEY raises EnvironmentError."""
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            call_model("gpt-4o-2024-11-20", None, "test", 100)
