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


@pytest.fixture
def analysis_test_db(tmp_path):
    """Create a richer synthetic dataset for statistical analysis tests.

    Inserts 300 rows: 10 prompts x 3 noise_types x 2 interventions x 1 model x 5 reps.
    Pass/fail patterns are designed to produce known statistical outcomes:
    - HumanEval/1: always passes clean_raw, always fails type_a_20pct_raw (fragile)
    - HumanEval/2: always fails clean_raw, always passes clean_pre_proc_sanitize (recoverable)
    - MBPP/1: passes in all conditions (robust, not fragile)
    - GSM8K/1: passes 4/5 clean, 2/5 noisy (for tau test)

    Returns:
        The path to the temporary database file as a string.
    """
    import random

    from src.db import init_database, insert_run

    db_path = str(tmp_path / "test_analysis.db")
    conn = init_database(db_path)

    model = "claude-sonnet-4-20250514"
    noise_types = ["clean", "type_a_10pct", "type_a_20pct"]
    interventions = ["raw", "pre_proc_sanitize"]

    # 10 prompts
    prompts = [
        "HumanEval/1", "HumanEval/2", "HumanEval/3", "HumanEval/4",
        "MBPP/1", "MBPP/2", "MBPP/3",
        "GSM8K/1", "GSM8K/2", "GSM8K/3",
    ]

    # Define deterministic pass/fail patterns per (prompt_id, noise_type, intervention)
    # Key is (prompt_id, noise_type, intervention) -> list of 5 pass/fail values
    rng = random.Random(42)

    patterns: dict[tuple[str, str, str], list[int]] = {}

    for prompt_id in prompts:
        for noise_type in noise_types:
            for intervention in interventions:
                # Default: random-looking but deterministic
                patterns[(prompt_id, noise_type, intervention)] = [
                    rng.randint(0, 1) for _ in range(5)
                ]

    # Override specific patterns for known test outcomes

    # HumanEval/1: always passes clean_raw, always fails type_a_20pct_raw (fragile)
    patterns[("HumanEval/1", "clean", "raw")] = [1, 1, 1, 1, 1]
    patterns[("HumanEval/1", "type_a_20pct", "raw")] = [0, 0, 0, 0, 0]
    patterns[("HumanEval/1", "type_a_10pct", "raw")] = [1, 1, 0, 0, 0]

    # HumanEval/2: always fails clean_raw, always passes clean_pre_proc_sanitize
    patterns[("HumanEval/2", "clean", "raw")] = [0, 0, 0, 0, 0]
    patterns[("HumanEval/2", "clean", "pre_proc_sanitize")] = [1, 1, 1, 1, 1]

    # MBPP/1: passes in all conditions (robust)
    for noise_type in noise_types:
        for intervention in interventions:
            patterns[("MBPP/1", noise_type, intervention)] = [1, 1, 1, 1, 1]

    # GSM8K/1: passes 4/5 clean, 2/5 noisy (for tau test)
    patterns[("GSM8K/1", "clean", "raw")] = [1, 1, 1, 1, 0]
    patterns[("GSM8K/1", "type_a_10pct", "raw")] = [1, 0, 1, 0, 0]
    patterns[("GSM8K/1", "type_a_20pct", "raw")] = [0, 1, 0, 0, 0]

    for (prompt_id, noise_type, intervention), pass_fail_list in patterns.items():
        benchmark = prompt_id.split("/")[0].lower()
        noise_level = ""
        if "10pct" in noise_type:
            noise_level = "10"
        elif "20pct" in noise_type:
            noise_level = "20"

        preproc_cost = 0.0003 if intervention == "pre_proc_sanitize" else 0.0
        for rep, pf in enumerate(pass_fail_list, start=1):
            run_id = f"{prompt_id}_{noise_type}_{intervention}_{model}_rep{rep}"
            insert_run(conn, {
                "run_id": run_id,
                "prompt_id": prompt_id,
                "benchmark": benchmark,
                "noise_type": noise_type,
                "noise_level": noise_level,
                "intervention": intervention,
                "model": model,
                "repetition": rep,
                "pass_fail": pf,
                "prompt_tokens": 100,
                "optimized_tokens": 85,
                "completion_tokens": 50,
                "total_cost_usd": 0.001,
                "preproc_cost_usd": preproc_cost,
                "main_model_input_cost_usd": 0.0005,
                "main_model_output_cost_usd": 0.0005,
                "status": "completed",
                "ttft_ms": 50.0,
                "ttlt_ms": 200.0,
            })

    conn.close()

    # Populate derived_metrics table so CR values are available for bootstrap
    from src.compute_derived import compute_derived_metrics
    compute_derived_metrics(db_path, cr_threshold=0.8)

    return db_path


@pytest.fixture
def degenerate_test_db(tmp_path):
    """Create a tiny DB with only 5 rows to force GLMM convergence failure.

    Returns:
        The path to the temporary database file as a string.
    """
    from src.db import init_database, insert_run

    db_path = str(tmp_path / "test_degenerate.db")
    conn = init_database(db_path)

    model = "claude-sonnet-4-20250514"
    for rep in range(1, 6):
        insert_run(conn, {
            "run_id": f"degen_rep{rep}",
            "prompt_id": "HumanEval/1",
            "benchmark": "humaneval",
            "noise_type": "clean",
            "noise_level": "",
            "intervention": "raw",
            "model": model,
            "repetition": rep,
            "pass_fail": 1,
            "prompt_tokens": 100,
            "optimized_tokens": 85,
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
