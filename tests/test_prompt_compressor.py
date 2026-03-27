"""Tests for prompt_compressor module with mocked API calls.

Covers:
- INTV-01: sanitize() and sanitize_and_compress() via cheap model
- INTV-03: SELF_CORRECT_PREFIX exact wording and build_self_correct_prompt()
- INTV-04: Pre-processor fallback on empty and bloated output
- Pre-processor model mapping (_get_preproc_model)
"""

import sys
from dataclasses import dataclass
from typing import Any

import pytest

from src.prompt_compressor import (
    SELF_CORRECT_PREFIX,
    _COMPRESS_INSTRUCTION,
    _COMPRESS_SYSTEM,
    _SANITIZE_INSTRUCTION,
    _SANITIZE_SYSTEM,
    _get_preproc_model,
    build_self_correct_prompt,
    sanitize,
    sanitize_and_compress,
)


# ---------------------------------------------------------------------------
# Mock API response
# ---------------------------------------------------------------------------
@dataclass
class MockAPIResponse:
    """Simulates an API response object with the fields prompt_compressor expects."""

    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float
    ttlt_ms: float
    model: str


def make_mock_call_fn(
    response_text: str = "Fixed text here",
    input_tokens: int = 50,
    output_tokens: int = 30,
    ttft_ms: float = 100.0,
    ttlt_ms: float = 300.0,
    model: str = "claude-haiku-4-5-20250514",
) -> tuple[Any, list[dict[str, Any]]]:
    """Create a mock call_fn that returns a preset response and records calls.

    Returns:
        A tuple of (mock_call_fn, call_log) where call_log is a list
        of dicts recording each call's keyword arguments.
    """
    call_log: list[dict[str, Any]] = []

    def mock_call_fn(**kwargs: Any) -> MockAPIResponse:
        call_log.append(kwargs)
        return MockAPIResponse(
            text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            ttft_ms=ttft_ms,
            ttlt_ms=ttlt_ms,
            model=kwargs.get("model", model),
        )

    return mock_call_fn, call_log


# ---------------------------------------------------------------------------
# SELF_CORRECT_PREFIX tests
# ---------------------------------------------------------------------------
class TestSelfCorrectPrefix:
    """Tests for SELF_CORRECT_PREFIX constant."""

    def test_exact_wording(self) -> None:
        expected = (
            "Note: my prompt below may contain spelling or grammar errors. "
            "First, correct any errors you find, then execute the corrected "
            "version of my request."
        )
        assert SELF_CORRECT_PREFIX == expected

    def test_starts_with_note(self) -> None:
        assert SELF_CORRECT_PREFIX.startswith("Note: my prompt below may contain")


# ---------------------------------------------------------------------------
# build_self_correct_prompt tests
# ---------------------------------------------------------------------------
class TestBuildSelfCorrectPrompt:
    """Tests for build_self_correct_prompt function."""

    def test_output_format(self) -> None:
        result = build_self_correct_prompt("test")
        assert result == f"{SELF_CORRECT_PREFIX}\n---\ntest"

    def test_preserves_input_text(self) -> None:
        noisy = "Wrte a functin taht sorts"
        result = build_self_correct_prompt(noisy)
        assert result.endswith(noisy)
        assert "---" in result


# ---------------------------------------------------------------------------
# _get_preproc_model tests
# ---------------------------------------------------------------------------
class TestGetPreprocModel:
    """Tests for pre-processor model lookup."""

    def test_claude_maps_to_haiku(self) -> None:
        assert _get_preproc_model("claude-sonnet-4-20250514") == "claude-haiku-4-5-20250514"

    def test_gemini_maps_to_flash(self) -> None:
        assert _get_preproc_model("gemini-1.5-pro") == "gemini-2.0-flash"

    def test_unknown_model_falls_back_to_self(self) -> None:
        """Unknown model returns itself as fallback instead of raising."""
        result = _get_preproc_model("unknown-model-123")
        assert result == "unknown-model-123"


# ---------------------------------------------------------------------------
# sanitize() tests
# ---------------------------------------------------------------------------
class TestSanitize:
    """Tests for sanitize function with mocked API."""

    def test_calls_with_correct_system_prompt(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Fixed text")
        sanitize("noisy text", "claude-sonnet-4-20250514", call_fn)
        assert log[0]["system"] == "You are a text corrector."

    def test_calls_with_correct_user_message(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Fixed text")
        sanitize("noisy input here", "claude-sonnet-4-20250514", call_fn)
        user_msg = log[0]["user_message"]
        assert user_msg.startswith("Fix all spelling and grammar errors")
        assert "---" in user_msg
        assert user_msg.endswith("noisy input here")

    def test_calls_preproc_model(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Fixed text")
        sanitize("noisy text", "claude-sonnet-4-20250514", call_fn)
        assert log[0]["model"] == "claude-haiku-4-5-20250514"

    def test_returns_corrected_text_and_metadata(self) -> None:
        call_fn, _ = make_mock_call_fn(
            response_text="Fixed text",
            input_tokens=50,
            output_tokens=30,
            ttft_ms=100.0,
            ttlt_ms=300.0,
        )
        result_text, metadata = sanitize("noisy text", "claude-sonnet-4-20250514", call_fn)
        assert result_text == "Fixed text"
        assert metadata["preproc_model"] == "claude-haiku-4-5-20250514"
        assert metadata["preproc_input_tokens"] == 50
        assert metadata["preproc_output_tokens"] == 30
        assert metadata["preproc_ttft_ms"] == 100.0
        assert metadata["preproc_ttlt_ms"] == 300.0
        assert metadata["preproc_raw_output"] == "Fixed text"
        assert "preproc_failed" not in metadata

    def test_max_tokens_formula(self) -> None:
        """max_tokens uses max(256, int(len*1.3)) formula."""
        call_fn, log = make_mock_call_fn(response_text="Fixed text")
        text = "x" * 500
        sanitize(text, "claude-sonnet-4-20250514", call_fn)
        assert log[0]["max_tokens"] == max(256, int(len(text) * 1.3))

    def test_fallback_on_empty_response(self) -> None:
        call_fn, _ = make_mock_call_fn(response_text="")
        result_text, metadata = sanitize("original noisy text", "claude-sonnet-4-20250514", call_fn)
        assert result_text == "original noisy text"
        assert metadata["preproc_failed"] is True

    def test_fallback_on_whitespace_only_response(self) -> None:
        call_fn, _ = make_mock_call_fn(response_text="   \n  ")
        result_text, metadata = sanitize("original noisy text", "claude-sonnet-4-20250514", call_fn)
        assert result_text == "original noisy text"
        assert metadata["preproc_failed"] is True

    def test_fallback_on_bloated_response(self) -> None:
        """Response longer than 1.5x original should trigger fallback."""
        original = "short text"  # 10 chars
        bloated = "x" * 20  # 20 chars > 10 * 1.5 = 15
        call_fn, _ = make_mock_call_fn(response_text=bloated)
        result_text, metadata = sanitize(original, "claude-sonnet-4-20250514", call_fn)
        assert result_text == original
        assert metadata["preproc_failed"] is True

    def test_preproc_raw_output_captured_on_fallback(self) -> None:
        """preproc_raw_output is stored even when fallback triggers."""
        original = "short text"  # 10 chars
        bloated = "x" * 20  # bloated output triggers fallback
        call_fn, _ = make_mock_call_fn(response_text=bloated)
        result_text, metadata = sanitize(original, "claude-sonnet-4-20250514", call_fn)
        assert result_text == original  # fallback to original
        assert metadata["preproc_raw_output"] == bloated  # raw output still captured
        assert metadata["preproc_failed"] is True

    def test_no_fallback_at_boundary(self) -> None:
        """Response exactly at 1.5x should not trigger fallback."""
        original = "short text"  # 10 chars
        at_boundary = "x" * 15  # 15 chars == 10 * 1.5, NOT greater
        call_fn, _ = make_mock_call_fn(response_text=at_boundary)
        result_text, metadata = sanitize(original, "claude-sonnet-4-20250514", call_fn)
        assert result_text == at_boundary
        assert "preproc_failed" not in metadata

    def test_uses_gemini_preproc_model(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Fixed text")
        sanitize("noisy text", "gemini-1.5-pro", call_fn)
        assert log[0]["model"] == "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# sanitize_and_compress() tests
# ---------------------------------------------------------------------------
class TestSanitizeAndCompress:
    """Tests for sanitize_and_compress function with mocked API."""

    def test_calls_with_correct_system_prompt(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Compressed text")
        sanitize_and_compress("verbose noisy text", "claude-sonnet-4-20250514", call_fn)
        assert log[0]["system"] == "You are a prompt optimizer."

    def test_calls_with_correct_user_message(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Compressed text")
        sanitize_and_compress("verbose noisy input", "claude-sonnet-4-20250514", call_fn)
        user_msg = log[0]["user_message"]
        assert "Fix all spelling and grammar errors" in user_msg
        assert "remove redundancy and condense" in user_msg
        assert "---" in user_msg
        assert user_msg.endswith("verbose noisy input")

    def test_returns_compressed_text_and_metadata(self) -> None:
        call_fn, _ = make_mock_call_fn(
            response_text="Short text",
            input_tokens=80,
            output_tokens=20,
            ttft_ms=90.0,
            ttlt_ms=250.0,
        )
        result_text, metadata = sanitize_and_compress(
            "verbose noisy text here", "claude-sonnet-4-20250514", call_fn
        )
        assert result_text == "Short text"
        assert metadata["preproc_model"] == "claude-haiku-4-5-20250514"
        assert metadata["preproc_input_tokens"] == 80
        assert metadata["preproc_output_tokens"] == 20

    def test_fallback_on_empty_response(self) -> None:
        call_fn, _ = make_mock_call_fn(response_text="")
        result_text, metadata = sanitize_and_compress(
            "original text", "claude-sonnet-4-20250514", call_fn
        )
        assert result_text == "original text"
        assert metadata["preproc_failed"] is True

    def test_fallback_on_bloated_response(self) -> None:
        original = "short"  # 5 chars
        bloated = "x" * 10  # 10 > 5 * 1.5 = 7.5
        call_fn, _ = make_mock_call_fn(response_text=bloated)
        result_text, metadata = sanitize_and_compress(
            original, "claude-sonnet-4-20250514", call_fn
        )
        assert result_text == original
        assert metadata["preproc_failed"] is True

    def test_calls_preproc_model_not_main_model(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Compressed")
        sanitize_and_compress("text", "gemini-1.5-pro", call_fn)
        assert log[0]["model"] == "gemini-2.0-flash"

    def test_temperature_is_zero(self) -> None:
        call_fn, log = make_mock_call_fn(response_text="Compressed")
        sanitize_and_compress("text", "claude-sonnet-4-20250514", call_fn)
        assert log[0]["temperature"] == 0.0

    def test_max_tokens_formula(self) -> None:
        """max_tokens uses max(256, int(len*1.3)) formula."""
        call_fn, log = make_mock_call_fn(response_text="Compressed")
        text = "y" * 400
        sanitize_and_compress(text, "claude-sonnet-4-20250514", call_fn)
        assert log[0]["max_tokens"] == max(256, int(len(text) * 1.3))
