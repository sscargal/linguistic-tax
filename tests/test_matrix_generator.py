"""Tests for the matrix generator module."""

import json
from pathlib import Path

import pytest

from src.matrix_generator import extract_noise_level, generate_matrix


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_prompts(tmp_path: Path) -> Path:
    """Create a minimal prompts JSON with 2 prompts."""
    prompts = [
        {
            "problem_id": "HumanEval/1",
            "prompt_text": "def func_1(): pass",
            "benchmark_source": "humaneval",
            "canonical_answer": "return 1",
            "test_code": "assert func_1() == 1",
            "answer_type": "code",
        },
        {
            "problem_id": "gsm8k_1",
            "prompt_text": "What is 2+2?",
            "benchmark_source": "gsm8k",
            "canonical_answer": "4",
            "test_code": "",
            "answer_type": "numeric",
        },
    ]
    path = tmp_path / "prompts.json"
    path.write_text(json.dumps(prompts))
    return path


# ---------------------------------------------------------------------------
# extract_noise_level tests
# ---------------------------------------------------------------------------

class TestExtractNoiseLevel:
    """Tests for extract_noise_level()."""

    def test_type_a_5pct(self) -> None:
        assert extract_noise_level("type_a_5pct") == "5"

    def test_type_a_10pct(self) -> None:
        assert extract_noise_level("type_a_10pct") == "10"

    def test_type_a_20pct(self) -> None:
        assert extract_noise_level("type_a_20pct") == "20"

    def test_clean_returns_none(self) -> None:
        assert extract_noise_level("clean") is None

    def test_type_b_returns_none(self) -> None:
        assert extract_noise_level("type_b_mandarin") is None


# ---------------------------------------------------------------------------
# generate_matrix tests
# ---------------------------------------------------------------------------

class TestGenerateMatrix:
    """Tests for generate_matrix()."""

    def test_returns_list_of_dicts(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        assert isinstance(matrix, list)
        assert len(matrix) > 0
        assert isinstance(matrix[0], dict)

    def test_expected_keys(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        expected_keys = {
            "prompt_id", "noise_type", "noise_level", "intervention",
            "model", "repetition_num", "status", "experiment",
        }
        for item in matrix:
            assert set(item.keys()) == expected_keys

    def test_includes_both_experiments(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        experiments = {item["experiment"] for item in matrix}
        assert "noise_recovery" in experiments
        assert "compression" in experiments

    def test_single_model_only(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        models = {item["model"] for item in matrix}
        assert models == {"model-a"}

    def test_multiple_models(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a", "model-b"])
        models = {item["model"] for item in matrix}
        assert models == {"model-a", "model-b"}

    def test_all_items_pending(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        for item in matrix:
            assert item["status"] == "pending"

    def test_compression_items_are_clean(self, tmp_prompts: Path) -> None:
        matrix = generate_matrix(str(tmp_prompts), models=["model-a"])
        compression_items = [i for i in matrix if i["experiment"] == "compression"]
        for item in compression_items:
            assert item["noise_type"] == "clean"
            assert item["intervention"] == "compress_only"
            assert item["noise_level"] is None
