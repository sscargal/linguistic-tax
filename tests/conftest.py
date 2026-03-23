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


@pytest.fixture
def populated_test_db(tmp_path):
    """Create a temp SQLite DB with synthetic experiment_runs for derived metric tests.

    Inserts 30 rows: 3 prompts x 2 noise_types x 1 intervention x 1 model x 5 reps.
    Pass/fail patterns are deterministic for testing CR and quadrant classification.

    Returns:
        The path to the temporary database file as a string.
    """
    from src.db import init_database, insert_run

    db_path = str(tmp_path / "test_derived.db")
    conn = init_database(db_path)

    model = "claude-sonnet-4-20250514"
    intervention = "raw"

    # Define deterministic pass/fail patterns per (prompt_id, noise_type)
    patterns = {
        ("HumanEval/1", "clean"): [1, 1, 1, 1, 1],       # CR=1.0, robust
        ("HumanEval/1", "type_a_10pct"): [1, 1, 1, 0, 0], # CR=0.4, lucky
        ("MBPP/1", "clean"): [0, 0, 0, 0, 0],             # CR=1.0, confidently_wrong
        ("MBPP/1", "type_a_10pct"): [1, 0, 1, 0, 1],      # CR=0.4, lucky
        ("GSM8K/1", "clean"): [1, 1, 0, 0, 0],            # CR=0.4, broken
        ("GSM8K/1", "type_a_10pct"): [0, 0, 0, 0, 1],     # CR=0.6, broken
    }

    for (prompt_id, noise_type), pass_fail_list in patterns.items():
        benchmark = prompt_id.split("/")[0].lower()
        for rep, pf in enumerate(pass_fail_list, start=1):
            run_id = f"{prompt_id}_{noise_type}_{intervention}_{model}_rep{rep}"
            insert_run(conn, {
                "run_id": run_id,
                "prompt_id": prompt_id,
                "benchmark": benchmark,
                "noise_type": noise_type,
                "noise_level": noise_type if noise_type != "clean" else "",
                "intervention": intervention,
                "model": model,
                "repetition": rep,
                "pass_fail": pf,
                "prompt_tokens": 100,
                "optimized_tokens": 90,
                "completion_tokens": 50,
                "total_cost_usd": 0.001,
                "preproc_cost_usd": 0.0,
                "main_model_input_cost_usd": 0.0005,
                "main_model_output_cost_usd": 0.0005,
                "status": "completed",
                "ttft_ms": 50.0,
                "ttlt_ms": 200.0,
            })

    conn.close()
    return db_path
