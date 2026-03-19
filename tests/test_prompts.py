"""Validation tests for curated benchmark prompts in data/prompts.json."""

import json
from pathlib import Path

import pytest

PROMPTS_PATH = Path(__file__).parent.parent / "data" / "prompts.json"


@pytest.fixture(scope="module")
def prompts() -> list[dict]:
    """Load the curated prompts from data/prompts.json."""
    assert PROMPTS_PATH.exists(), f"Prompts file not found: {PROMPTS_PATH}"
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "prompts.json must be a JSON array"
    return data


def test_file_exists_and_valid_json() -> None:
    """Test that data/prompts.json exists and contains valid JSON."""
    assert PROMPTS_PATH.exists(), f"Prompts file not found: {PROMPTS_PATH}"
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)


def test_exactly_200_prompts(prompts: list[dict]) -> None:
    """Test that exactly 200 prompts are curated."""
    assert len(prompts) == 200, f"Expected 200 prompts, got {len(prompts)}"


def test_benchmark_distribution(prompts: list[dict]) -> None:
    """Test that prompts have ~67 HumanEval, ~67 MBPP, ~66 GSM8K."""
    counts = {}
    for p in prompts:
        src = p["benchmark_source"]
        counts[src] = counts.get(src, 0) + 1

    assert counts.get("humaneval", 0) == 67, f"HumanEval: {counts.get('humaneval', 0)}"
    assert counts.get("mbpp", 0) == 67, f"MBPP: {counts.get('mbpp', 0)}"
    assert counts.get("gsm8k", 0) == 66, f"GSM8K: {counts.get('gsm8k', 0)}"


def test_required_keys(prompts: list[dict]) -> None:
    """Test that every record has all required keys."""
    required_keys = {
        "benchmark_source",
        "problem_id",
        "prompt_text",
        "canonical_answer",
        "answer_type",
    }
    for i, p in enumerate(prompts):
        missing = required_keys - set(p.keys())
        assert not missing, f"Prompt {i} ({p.get('problem_id', '?')}) missing keys: {missing}"


def test_humaneval_entries(prompts: list[dict]) -> None:
    """Test that all HumanEval entries have code answer_type and test_code."""
    he_prompts = [p for p in prompts if p["benchmark_source"] == "humaneval"]
    for p in he_prompts:
        assert p["answer_type"] == "code", (
            f"HumanEval {p['problem_id']} has answer_type={p['answer_type']}"
        )
        assert p.get("test_code") is not None, (
            f"HumanEval {p['problem_id']} has no test_code"
        )


def test_mbpp_entries(prompts: list[dict]) -> None:
    """Test that all MBPP entries have code answer_type and test_code."""
    mbpp_prompts = [p for p in prompts if p["benchmark_source"] == "mbpp"]
    for p in mbpp_prompts:
        assert p["answer_type"] == "code", (
            f"MBPP {p['problem_id']} has answer_type={p['answer_type']}"
        )
        assert p.get("test_code") is not None, (
            f"MBPP {p['problem_id']} has no test_code"
        )


def test_gsm8k_entries(prompts: list[dict]) -> None:
    """Test that all GSM8K entries have numeric answer_type and no test_code."""
    gsm_prompts = [p for p in prompts if p["benchmark_source"] == "gsm8k"]
    for p in gsm_prompts:
        assert p["answer_type"] == "numeric", (
            f"GSM8K {p['problem_id']} has answer_type={p['answer_type']}"
        )
        assert p.get("test_code") is None, (
            f"GSM8K {p['problem_id']} should have test_code=None"
        )


def test_unique_problem_ids(prompts: list[dict]) -> None:
    """Test that all problem_ids are unique."""
    ids = [p["problem_id"] for p in prompts]
    assert len(ids) == len(set(ids)), (
        f"Duplicate problem_ids found: {len(ids)} total, {len(set(ids))} unique"
    )


def test_nonempty_prompt_text(prompts: list[dict]) -> None:
    """Test that all prompt_text values are non-empty strings."""
    for p in prompts:
        assert isinstance(p["prompt_text"], str), (
            f"{p['problem_id']} prompt_text is not a string"
        )
        assert len(p["prompt_text"].strip()) > 0, (
            f"{p['problem_id']} has empty prompt_text"
        )


def test_nonempty_canonical_answer(prompts: list[dict]) -> None:
    """Test that all canonical_answer values are non-empty."""
    for p in prompts:
        assert p["canonical_answer"] is not None, (
            f"{p['problem_id']} has None canonical_answer"
        )
        if isinstance(p["canonical_answer"], str):
            assert len(p["canonical_answer"].strip()) > 0, (
                f"{p['problem_id']} has empty canonical_answer"
            )


def test_gsm8k_numeric_answers(prompts: list[dict]) -> None:
    """Test that GSM8K canonical_answers can be parsed as numbers."""
    gsm_prompts = [p for p in prompts if p["benchmark_source"] == "gsm8k"]
    for p in gsm_prompts:
        answer = p["canonical_answer"].replace(",", "")
        try:
            float(answer)
        except ValueError:
            pytest.fail(
                f"GSM8K {p['problem_id']} canonical_answer '{p['canonical_answer']}' "
                f"is not numeric"
            )
