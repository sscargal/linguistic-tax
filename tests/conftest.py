"""Shared test fixtures for the Linguistic Tax research toolkit."""

import pytest


@pytest.fixture
def sample_config():
    """Return a default ExperimentConfig instance."""
    from src.config import ExperimentConfig
    return ExperimentConfig()


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a temporary database path for testing."""
    return str(tmp_path / "test_results.db")


@pytest.fixture
def sample_prompt_record():
    """Return a sample prompt record dict with all required keys."""
    return {
        "benchmark_source": "humaneval",
        "problem_id": "HumanEval/42",
        "prompt_text": "def is_prime(n: int) -> bool:\n    \"\"\"Return True if n is prime.\"\"\"",
        "canonical_answer": "    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
        "test_code": "assert is_prime(2) == True\nassert is_prime(4) == False",
        "answer_type": "code",
    }


@pytest.fixture
def sample_run_record():
    """Return a sample experiment run record for grading tests."""
    return {
        "run_id": "test-run-001",
        "prompt_id": "HumanEval/1",
        "benchmark": "humaneval",
        "noise_type": "clean",
        "intervention": "raw",
        "model": "test-model",
        "repetition": 1,
        "raw_output": "def separate_paren_groups(paren_string):\n    ...",
        "status": "completed",
    }
