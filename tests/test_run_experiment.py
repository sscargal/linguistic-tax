"""Tests for the execution engine: intervention router, run_id generation, and model ordering."""

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MockAPIResponse:
    """Minimal mock matching APIResponse shape."""

    text: str = "fixed text"
    input_tokens: int = 10
    output_tokens: int = 5
    ttft_ms: float = 50.0
    ttlt_ms: float = 100.0
    model: str = "claude-haiku-4-5-20250514"


def mock_call_fn(**kwargs: Any) -> MockAPIResponse:
    """Mock call_model that returns a canned response."""
    return MockAPIResponse(model=kwargs.get("model", "mock"))


SAMPLE_ITEM = {
    "prompt_id": "HumanEval/1",
    "noise_type": "clean",
    "noise_level": None,
    "intervention": "raw",
    "model": "claude-sonnet-4-20250514",
    "repetition_num": 1,
    "status": "pending",
    "experiment": "noise_recovery",
}


# ---------------------------------------------------------------------------
# make_run_id tests
# ---------------------------------------------------------------------------

class TestMakeRunId:
    """Tests for deterministic run_id generation."""

    def test_basic_run_id(self) -> None:
        from src.run_experiment import make_run_id
        result = make_run_id(SAMPLE_ITEM)
        assert result == "HumanEval/1|clean|none|raw|claude-sonnet-4-20250514|1"

    def test_deterministic(self) -> None:
        from src.run_experiment import make_run_id
        assert make_run_id(SAMPLE_ITEM) == make_run_id(SAMPLE_ITEM)

    def test_none_noise_level(self) -> None:
        from src.run_experiment import make_run_id
        item = dict(SAMPLE_ITEM, noise_level=None)
        result = make_run_id(item)
        assert "|none|" in result

    def test_numeric_noise_level(self) -> None:
        from src.run_experiment import make_run_id
        item = dict(SAMPLE_ITEM, noise_level="5")
        result = make_run_id(item)
        assert "|5|" in result

    def test_different_items_different_ids(self) -> None:
        from src.run_experiment import make_run_id
        item2 = dict(SAMPLE_ITEM, repetition_num=2)
        assert make_run_id(SAMPLE_ITEM) != make_run_id(item2)


# ---------------------------------------------------------------------------
# apply_intervention tests
# ---------------------------------------------------------------------------

class TestApplyIntervention:
    """Tests for the intervention router."""

    def test_raw_passthrough(self) -> None:
        from src.run_experiment import apply_intervention
        text, meta = apply_intervention("hello", "raw", "claude-sonnet-4-20250514", mock_call_fn)
        assert text == "hello"
        assert meta == {}

    def test_self_correct(self) -> None:
        from src.run_experiment import apply_intervention
        from src.prompt_compressor import SELF_CORRECT_PREFIX
        text, meta = apply_intervention("hello", "self_correct", "claude-sonnet-4-20250514", mock_call_fn)
        assert text.startswith(SELF_CORRECT_PREFIX)
        assert meta == {}

    def test_prompt_repetition(self) -> None:
        from src.run_experiment import apply_intervention
        text, meta = apply_intervention("hello", "prompt_repetition", "claude-sonnet-4-20250514", mock_call_fn)
        assert text == "hello\n\nhello"
        assert meta == {}

    def test_pre_proc_sanitize_calls_sanitize(self) -> None:
        from src.run_experiment import apply_intervention
        with patch("src.run_experiment.sanitize", return_value=("sanitized", {"preproc_model": "haiku"})) as mock_san:
            text, meta = apply_intervention("hello", "pre_proc_sanitize", "claude-sonnet-4-20250514", mock_call_fn)
            mock_san.assert_called_once_with("hello", "claude-sonnet-4-20250514", mock_call_fn)
            assert text == "sanitized"
            assert meta == {"preproc_model": "haiku"}

    def test_pre_proc_sanitize_compress_calls_sanitize_and_compress(self) -> None:
        from src.run_experiment import apply_intervention
        with patch("src.run_experiment.sanitize_and_compress", return_value=("compressed", {"preproc_model": "haiku"})) as mock_sc:
            text, meta = apply_intervention("hello", "pre_proc_sanitize_compress", "claude-sonnet-4-20250514", mock_call_fn)
            mock_sc.assert_called_once_with("hello", "claude-sonnet-4-20250514", mock_call_fn)
            assert text == "compressed"
            assert meta == {"preproc_model": "haiku"}

    def test_unknown_raises_value_error(self) -> None:
        from src.run_experiment import apply_intervention
        with pytest.raises(ValueError, match="Unknown intervention"):
            apply_intervention("hello", "unknown", "claude-sonnet-4-20250514", mock_call_fn)


# ---------------------------------------------------------------------------
# _order_by_model tests
# ---------------------------------------------------------------------------

class TestOrderByModel:
    """Tests for model-based ordering with deterministic shuffle."""

    def test_claude_first_gemini_second(self) -> None:
        from src.run_experiment import _order_by_model
        items = [
            {"model": "gemini-1.5-pro", "id": "g1"},
            {"model": "claude-sonnet-4-20250514", "id": "c1"},
            {"model": "gemini-1.5-pro", "id": "g2"},
            {"model": "claude-sonnet-4-20250514", "id": "c2"},
        ]
        ordered = _order_by_model(items, seed=42)
        # All claude items should come before gemini items
        claude_ids = [x["id"] for x in ordered if x["model"].startswith("claude")]
        gemini_ids = [x["id"] for x in ordered if x["model"].startswith("gemini")]
        claude_positions = [i for i, x in enumerate(ordered) if x["model"].startswith("claude")]
        gemini_positions = [i for i, x in enumerate(ordered) if x["model"].startswith("gemini")]
        assert max(claude_positions) < min(gemini_positions)

    def test_deterministic_with_same_seed(self) -> None:
        from src.run_experiment import _order_by_model
        items = [
            {"model": "gemini-1.5-pro", "id": f"g{i}"} for i in range(10)
        ] + [
            {"model": "claude-sonnet-4-20250514", "id": f"c{i}"} for i in range(10)
        ]
        r1 = _order_by_model(items, seed=42)
        r2 = _order_by_model(items, seed=42)
        assert [x["id"] for x in r1] == [x["id"] for x in r2]

    def test_different_seed_different_order(self) -> None:
        from src.run_experiment import _order_by_model
        items = [
            {"model": "claude-sonnet-4-20250514", "id": f"c{i}"} for i in range(20)
        ]
        r1 = _order_by_model(items, seed=42)
        r2 = _order_by_model(items, seed=99)
        # Very unlikely same order with different seeds for 20 items
        assert [x["id"] for x in r1] != [x["id"] for x in r2]

    def test_preserves_all_items(self) -> None:
        from src.run_experiment import _order_by_model
        items = [
            {"model": "gemini-1.5-pro", "id": "g1"},
            {"model": "claude-sonnet-4-20250514", "id": "c1"},
        ]
        ordered = _order_by_model(items, seed=42)
        assert len(ordered) == 2
        assert set(x["id"] for x in ordered) == {"g1", "c1"}
