"""Integration tests for multi-module flows in the Linguistic Tax research toolkit.

These tests verify that modules work together correctly across boundaries,
not just in isolation. They cover three key pipelines:

1. Noise injection -> intervention -> grading
2. DB experiment data -> derived metrics -> quadrant classification
3. Config -> seed derivation -> DB init -> insert -> query roundtrip
"""

import pytest
from unittest.mock import MagicMock


class TestNoiseToGradingPipeline:
    """Tests the flow: clean prompt -> noise injection -> (optional intervention) -> grading."""

    def test_type_a_noise_preserves_gradeable_code(self, tmp_path):
        """Noise generator output feeds into grader; clean code grades correctly."""
        from src.noise_generator import inject_type_a_noise
        from src.grade_results import grade_code

        # A simple HumanEval-style prompt with function + test
        clean_code = "def add(a, b):\n    return a + b\n"
        test_code = (
            "def check(candidate):\n"
            "    assert candidate(1, 2) == 3\n"
            "    assert candidate(0, 0) == 0\n"
        )

        # Apply Type A noise at 5% to the prompt text (not the code itself)
        prompt_text = "Write a function that adds two numbers.\ndef add(a, b):"
        noisy_prompt = inject_type_a_noise(prompt_text, error_rate=0.05, seed=42)

        # Verify noise was actually applied (text differs)
        assert noisy_prompt != prompt_text, "Noise should modify the prompt text"

        # Grade the CLEAN code against the test harness to verify grading pipeline works
        prompt_record = {
            "benchmark_source": "humaneval",
            "prompt_text": "def add(a, b):",
            "test_code": test_code,
        }
        result = grade_code(clean_code, prompt_record)
        assert result.passed is True, f"Clean code should pass grading: {result.fail_reason}"

    def test_type_b_noise_then_sanitize(self):
        """Type B noise -> sanitize flow completes without error."""
        from src.noise_generator import inject_type_b_noise
        from src.prompt_compressor import sanitize

        clean_text = "Write a function that returns the sorted list of elements."
        noisy_text = inject_type_b_noise(clean_text, l1_source="mandarin", seed=42)

        # Verify noise was applied
        assert noisy_text != clean_text, "Type B noise should modify the text"

        # Mock the API call_fn for sanitize
        mock_response = MagicMock()
        mock_response.text = "Write a function that returns the sorted list of elements."
        mock_response.input_tokens = 50
        mock_response.output_tokens = 30
        mock_response.ttft_ms = 10.0
        mock_response.ttlt_ms = 50.0

        def mock_call_fn(**kwargs):
            return mock_response

        sanitized, metadata = sanitize(
            noisy_text,
            main_model="claude-sonnet-4-20250514",
            call_fn=mock_call_fn,
        )

        # The sanitized text should be the mock return value
        assert sanitized == "Write a function that returns the sorted list of elements."
        assert "preproc_model" in metadata
        assert metadata["preproc_model"] == "claude-haiku-4-5-20250514"

    def test_prompt_repeater_doubles_content(self):
        """Prompt repeater doubles the content with separator."""
        from src.prompt_repeater import repeat_prompt

        original = "What is the sum of 2 and 3?"
        repeated = repeat_prompt(original)

        assert len(repeated) > len(original), "Repeated prompt should be longer"
        assert repeated.count(original) == 2, "Original text should appear twice"
        assert "\n\n" in repeated, "Copies should be separated by double newline"
        assert repeated == f"{original}\n\n{original}"


class TestDerivedMetricsPipeline:
    """Tests the flow: DB with results -> derived metrics -> quadrant classification."""

    def test_full_derived_pipeline(self, populated_test_db):
        """Compute derived metrics from populated DB and verify quadrant assignments."""
        import sqlite3
        from src.compute_derived import compute_derived_metrics

        summary = compute_derived_metrics(populated_test_db, cr_threshold=0.8)

        # Should have processed all groups
        assert summary["total"] > 0, "Should have computed metrics for at least one group"

        # Query the derived_metrics table
        conn = sqlite3.connect(populated_test_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM derived_metrics").fetchall()
        conn.close()

        assert len(rows) > 0, "derived_metrics table should have rows"

        # Convert to dicts for easier inspection
        metrics = [dict(r) for r in rows]
        quadrants = {m["quadrant"] for m in metrics}

        # Based on conftest patterns:
        # ("HumanEval/1", "clean"): [1,1,1,1,1] -> CR=1.0, majority_pass=True -> robust
        # ("MBPP/1", "clean"): [0,0,0,0,0] -> CR=1.0, majority_pass=False -> confidently_wrong
        assert "robust" in quadrants, "Should have at least one robust quadrant"
        assert "confidently_wrong" in quadrants, "Should have at least one confidently_wrong quadrant"

        # Verify expected columns exist
        required_columns = {
            "prompt_id", "condition", "model", "consistency_rate",
            "majority_pass", "pass_count", "quadrant",
        }
        actual_columns = set(metrics[0].keys())
        assert required_columns.issubset(actual_columns), (
            f"Missing columns: {required_columns - actual_columns}"
        )

    def test_cr_then_quadrant_classification(self):
        """Compute CR for known patterns and verify quadrant classification."""
        from src.compute_derived import compute_cr, classify_quadrant

        # All pass -> CR=1.0, mean=1.0 -> robust
        cr_all_pass = compute_cr([1, 1, 1, 1, 1])
        assert cr_all_pass == 1.0
        q1 = classify_quadrant(cr_all_pass, majority_pass=True, cr_threshold=0.8)
        assert q1 == "robust"

        # All fail -> CR=1.0, mean=0.0 -> confidently_wrong
        cr_all_fail = compute_cr([0, 0, 0, 0, 0])
        assert cr_all_fail == 1.0
        q2 = classify_quadrant(cr_all_fail, majority_pass=False, cr_threshold=0.8)
        assert q2 == "confidently_wrong"

        # Mixed: [1,0,1,0,1] -> CR=0.4 (4 agreeing out of 10 pairs), mean=0.6 -> lucky
        cr_mixed = compute_cr([1, 0, 1, 0, 1])
        assert abs(cr_mixed - 0.4) < 1e-9
        mean_pass = sum([1, 0, 1, 0, 1]) / 5
        majority_pass = mean_pass >= 0.5
        q3 = classify_quadrant(cr_mixed, majority_pass=majority_pass, cr_threshold=0.8)
        assert q3 == "lucky"


class TestOpenRouterLifecycle:
    """Integration test: config -> MODELS -> call_model routing -> _call_openrouter -> APIResponse."""

    def test_openrouter_full_lifecycle(self):
        """Full lifecycle: OpenRouter model in MODELS, routes through call_model, returns APIResponse."""
        import os
        from unittest.mock import patch, MagicMock

        from src.config import MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, compute_cost
        from src.api_client import call_model, APIResponse

        target = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
        preproc = "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"

        # Step 1: Verify config entries exist
        assert target in MODELS, "Target model not in MODELS"
        assert target in PRICE_TABLE, "Target model not in PRICE_TABLE"
        assert preproc in PRICE_TABLE, "Preproc model not in PRICE_TABLE"
        assert PREPROC_MODEL_MAP[target] == preproc, "Preproc mapping wrong"

        # Step 2: Verify zero-cost pricing
        cost = compute_cost(target, 1000, 500)
        assert cost == 0.0, f"Expected 0.0, got {cost}"

        # Step 3: Mock the OpenAI client and verify call_model routes correctly
        mock_client_instance = MagicMock()

        # Create streaming chunks (content chunk + usage chunk)
        content_chunk = MagicMock()
        content_chunk.choices = [MagicMock()]
        content_chunk.choices[0].delta.content = "Hello from Nemotron"
        content_chunk.usage = None

        usage_chunk = MagicMock()
        usage_chunk.choices = []
        usage_chunk.usage = MagicMock()
        usage_chunk.usage.prompt_tokens = 50
        usage_chunk.usage.completion_tokens = 25

        mock_client_instance.chat.completions.create.return_value = iter(
            [content_chunk, usage_chunk]
        )

        with patch("src.api_client.openai.OpenAI", return_value=mock_client_instance), \
             patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), \
             patch("src.api_client.time.sleep"):  # skip rate limit delay

            result = call_model(target, None, "test prompt", 1024, 0.0)

        # Step 4: Verify full APIResponse
        assert isinstance(result, APIResponse)
        assert result.text == "Hello from Nemotron"
        assert result.input_tokens == 50
        assert result.output_tokens == 25
        assert result.model == target  # Full prefixed ID preserved

        # Step 5: Verify prefix was stripped for the API call
        create_call = mock_client_instance.chat.completions.create
        call_kwargs = create_call.call_args
        assert call_kwargs.kwargs.get("model") == "nvidia/nemotron-3-super-120b-a12b:free", \
            "Model prefix was not stripped for API call"


class TestConfigToDatabasePipeline:
    """Tests the flow: config -> seed derivation -> DB init -> insert -> query."""

    def test_config_seed_to_db_roundtrip(self, tmp_path):
        """Config seed derivation -> DB init -> insert -> query roundtrip."""
        from src.config import ExperimentConfig, derive_seed
        from src.db import init_database, insert_run, query_runs

        config = ExperimentConfig()

        # Derive a deterministic seed
        seed = derive_seed(
            base_seed=config.base_seed,
            prompt_id="HumanEval/42",
            noise_type="type_a",
            noise_level="10",
        )
        assert isinstance(seed, int)
        assert seed > 0

        # Verify determinism: same inputs -> same seed
        seed2 = derive_seed(
            base_seed=config.base_seed,
            prompt_id="HumanEval/42",
            noise_type="type_a",
            noise_level="10",
        )
        assert seed == seed2

        # Init temp DB
        db_path = str(tmp_path / "roundtrip_test.db")
        conn = init_database(db_path)

        # Insert a run using the derived seed info
        run_data = {
            "run_id": f"test-seed-{seed}",
            "prompt_id": "HumanEval/42",
            "benchmark": "humaneval",
            "noise_type": "type_a_10pct",
            "noise_level": "10",
            "intervention": "raw",
            "model": config.claude_model,
            "repetition": 1,
            "status": "completed",
            "pass_fail": 1,
            "prompt_tokens": 100,
            "total_cost_usd": 0.001,
            "ttft_ms": 50.0,
            "ttlt_ms": 200.0,
        }
        insert_run(conn, run_data)

        # Query back and verify
        results = query_runs(conn, prompt_id="HumanEval/42")
        assert len(results) == 1
        row = results[0]
        assert row["run_id"] == f"test-seed-{seed}"
        assert row["model"] == "claude-sonnet-4-20250514"
        assert row["noise_type"] == "type_a_10pct"
        assert row["status"] == "completed"
        assert row["pass_fail"] == 1

        conn.close()
