"""Tests for prompt_repeater module and config additions.

Covers:
- INTV-02: Prompt repetition (repeat_prompt pure function)
- INTV-03: Self-correct prefix and build_self_correct_prompt
- Config: PRICE_TABLE, MAX_TOKENS_BY_BENCHMARK, PREPROC_MODEL_MAP, compute_cost
"""

import sys

import pytest

# imports use src. prefix


# ---------------------------------------------------------------------------
# repeat_prompt tests (INTV-02)
# ---------------------------------------------------------------------------
class TestRepeatPrompt:
    """Tests for the repeat_prompt function."""

    def test_basic_duplication(self) -> None:
        from src.prompt_repeater import repeat_prompt

        result = repeat_prompt("hello world")
        assert result == "hello world\n\nhello world"

    def test_empty_string(self) -> None:
        from src.prompt_repeater import repeat_prompt

        result = repeat_prompt("")
        assert result == "\n\n"

    def test_preserves_noisy_text_verbatim(self) -> None:
        """Noisy text is repeated as-is, no cleaning."""
        from src.prompt_repeater import repeat_prompt

        noisy = "Wrte a functin taht sorts teh lsit"
        result = repeat_prompt(noisy)
        assert result == f"{noisy}\n\n{noisy}"

    def test_multiline_text(self) -> None:
        from src.prompt_repeater import repeat_prompt

        text = "line one\nline two\nline three"
        result = repeat_prompt(text)
        assert result == f"{text}\n\n{text}"


# ---------------------------------------------------------------------------
# SELF_CORRECT_PREFIX and build_self_correct_prompt tests (INTV-03)
# ---------------------------------------------------------------------------
class TestSelfCorrect:
    """Tests for self-correct prefix and builder."""

    def test_prefix_starts_correctly(self) -> None:
        from src.prompt_compressor import SELF_CORRECT_PREFIX

        assert SELF_CORRECT_PREFIX.startswith(
            "Note: my prompt below may contain"
        )

    def test_prefix_exact_wording(self) -> None:
        from src.prompt_compressor import SELF_CORRECT_PREFIX

        expected = (
            "Note: my prompt below may contain spelling or grammar errors. "
            "First, correct any errors you find, then execute the corrected "
            "version of my request."
        )
        assert SELF_CORRECT_PREFIX == expected

    def test_build_self_correct_prompt(self) -> None:
        from src.prompt_compressor import SELF_CORRECT_PREFIX, build_self_correct_prompt

        result = build_self_correct_prompt("test prompt")
        assert result == f"{SELF_CORRECT_PREFIX}\n---\ntest prompt"


# ---------------------------------------------------------------------------
# Config additions tests
# ---------------------------------------------------------------------------
class TestPriceTable:
    """Tests for PRICE_TABLE config constant."""

    def test_contains_all_eight_models(self) -> None:
        from src.config import PRICE_TABLE

        expected_models = {
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20250514",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gpt-4o-2024-11-20",
            "gpt-4o-mini-2024-07-18",
            "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
            "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
        }
        assert set(PRICE_TABLE.keys()) == expected_models

    def test_claude_sonnet_input_price(self) -> None:
        from src.config import PRICE_TABLE

        assert PRICE_TABLE["claude-sonnet-4-20250514"]["input_per_1m"] == 3.00

    def test_claude_sonnet_output_price(self) -> None:
        from src.config import PRICE_TABLE

        assert PRICE_TABLE["claude-sonnet-4-20250514"]["output_per_1m"] == 15.00

    def test_all_models_have_input_and_output(self) -> None:
        from src.config import PRICE_TABLE

        for model, prices in PRICE_TABLE.items():
            assert "input_per_1m" in prices, f"{model} missing input_per_1m"
            assert "output_per_1m" in prices, f"{model} missing output_per_1m"


class TestMaxTokens:
    """Tests for MAX_TOKENS_BY_BENCHMARK config constant."""

    def test_humaneval_max_tokens(self) -> None:
        from src.config import MAX_TOKENS_BY_BENCHMARK

        assert MAX_TOKENS_BY_BENCHMARK["humaneval"] == 2048

    def test_mbpp_max_tokens(self) -> None:
        from src.config import MAX_TOKENS_BY_BENCHMARK

        assert MAX_TOKENS_BY_BENCHMARK["mbpp"] == 2048

    def test_gsm8k_max_tokens(self) -> None:
        from src.config import MAX_TOKENS_BY_BENCHMARK

        assert MAX_TOKENS_BY_BENCHMARK["gsm8k"] == 1024


class TestPreprocModelMap:
    """Tests for PREPROC_MODEL_MAP config constant."""

    def test_claude_maps_to_haiku(self) -> None:
        from src.config import PREPROC_MODEL_MAP

        assert PREPROC_MODEL_MAP["claude-sonnet-4-20250514"] == "claude-haiku-4-5-20250514"

    def test_gemini_maps_to_flash(self) -> None:
        from src.config import PREPROC_MODEL_MAP

        assert PREPROC_MODEL_MAP["gemini-1.5-pro"] == "gemini-2.0-flash"


class TestComputeCost:
    """Tests for compute_cost function."""

    def test_claude_sonnet_cost(self) -> None:
        from src.config import compute_cost

        # 1000 input tokens * 3.00/1M + 500 output tokens * 15.00/1M
        # = 0.003 + 0.0075 = 0.0105
        result = compute_cost("claude-sonnet-4-20250514", 1000, 500)
        assert abs(result - 0.0105) < 1e-10

    def test_zero_tokens(self) -> None:
        from src.config import compute_cost

        result = compute_cost("claude-sonnet-4-20250514", 0, 0)
        assert result == 0.0

    def test_gemini_flash_cost(self) -> None:
        from src.config import compute_cost

        # 1000 input * 0.10/1M + 1000 output * 0.40/1M
        # = 0.0001 + 0.0004 = 0.0005
        result = compute_cost("gemini-2.0-flash", 1000, 1000)
        assert abs(result - 0.0005) < 1e-10

    def test_unknown_model_returns_zero(self) -> None:
        from src.config import compute_cost

        result = compute_cost("unknown-model", 100, 100)
        assert result == 0.0
