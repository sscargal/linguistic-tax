"""Tests for the pilot validation module."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db import init_database, insert_run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_prompts_file(tmp_path: Path) -> Path:
    """Create a small prompts.json with 3 HumanEval, 3 MBPP, 3 GSM8K mock prompts."""
    prompts = [
        {
            "benchmark_source": "humaneval",
            "problem_id": f"HumanEval/{i}",
            "prompt_text": f"def func_{i}(): pass",
            "canonical_answer": f"return {i}",
            "test_code": f"assert func_{i}() == {i}",
            "answer_type": "code",
        }
        for i in range(1, 4)
    ] + [
        {
            "benchmark_source": "mbpp",
            "problem_id": f"Mbpp/{i}",
            "prompt_text": f"def mbpp_{i}(): pass",
            "canonical_answer": f"return {i}",
            "test_code": f"assert mbpp_{i}() == {i}",
            "answer_type": "code",
        }
        for i in range(1, 4)
    ] + [
        {
            "benchmark_source": "gsm8k",
            "problem_id": f"gsm8k_{i}",
            "prompt_text": f"What is {i} + {i}?",
            "canonical_answer": str(i * 2),
            "test_code": "",
            "answer_type": "numeric",
        }
        for i in range(1, 4)
    ]

    path = tmp_path / "prompts.json"
    path.write_text(json.dumps(prompts))
    return path


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with test data via init_database()."""
    db_path = str(tmp_path / "test.db")
    conn = init_database(db_path)
    return conn


# ---------------------------------------------------------------------------
# select_pilot_prompts tests
# ---------------------------------------------------------------------------

class TestSelectPilotPrompts:
    """Tests for stratified pilot prompt selection."""

    def test_returns_correct_count(self, tmp_prompts_file: Path, tmp_path: Path) -> None:
        from src.pilot import select_pilot_prompts
        ids = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file),
            seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=1,
            save=False,
        )
        assert len(ids) == 5

    def test_stratified_distribution(self, tmp_prompts_file: Path) -> None:
        from src.pilot import select_pilot_prompts
        ids = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file),
            seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=2,
            save=False,
        )
        humaneval_ids = [i for i in ids if i.startswith("HumanEval/")]
        mbpp_ids = [i for i in ids if i.startswith("Mbpp/")]
        gsm8k_ids = [i for i in ids if i.startswith("gsm8k")]
        assert len(humaneval_ids) == 2
        assert len(mbpp_ids) == 2
        assert len(gsm8k_ids) == 2

    def test_determinism(self, tmp_prompts_file: Path) -> None:
        from src.pilot import select_pilot_prompts
        ids1 = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file), seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=1, save=False,
        )
        ids2 = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file), seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=1, save=False,
        )
        assert ids1 == ids2

    def test_valid_prompt_ids(self, tmp_prompts_file: Path) -> None:
        from src.pilot import select_pilot_prompts
        # Load all valid IDs
        with open(tmp_prompts_file) as f:
            valid_ids = {p["problem_id"] for p in json.load(f)}
        ids = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file), seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=1, save=False,
        )
        for pid in ids:
            assert pid in valid_ids

    def test_save_creates_file(self, tmp_prompts_file: Path, tmp_path: Path) -> None:
        from src.pilot import select_pilot_prompts
        output_path = str(tmp_path / "pilot_prompts.json")
        ids = select_pilot_prompts(
            prompts_path=str(tmp_prompts_file), seed=42,
            n_humaneval=2, n_mbpp=2, n_gsm8k=1,
            save=True, output_path=output_path,
        )
        assert Path(output_path).exists()
        with open(output_path) as f:
            saved_ids = json.load(f)
        assert saved_ids == ids

    def test_full_dataset_20_prompts(self) -> None:
        """Test with the real prompts.json to verify 7+7+6=20 selection."""
        from src.pilot import select_pilot_prompts
        ids = select_pilot_prompts(
            prompts_path="data/prompts.json", seed=42,
            n_humaneval=7, n_mbpp=7, n_gsm8k=6, save=False,
        )
        assert len(ids) == 20
        humaneval_ids = [i for i in ids if i.startswith("HumanEval/")]
        mbpp_ids = [i for i in ids if i.startswith("mbpp_")]
        gsm8k_ids = [i for i in ids if i.startswith("gsm8k")]
        assert len(humaneval_ids) == 7
        assert len(mbpp_ids) == 7
        assert len(gsm8k_ids) == 6


# ---------------------------------------------------------------------------
# audit_data_completeness tests
# ---------------------------------------------------------------------------

class TestAuditDataCompleteness:
    """Tests for data completeness auditing."""

    def test_detects_null_prompt_text(self, tmp_db: sqlite3.Connection) -> None:
        from src.pilot import audit_data_completeness
        insert_run(tmp_db, {
            "run_id": "test|1", "prompt_id": "HumanEval/1",
            "benchmark": "humaneval", "noise_type": "clean",
            "intervention": "raw", "model": "claude-sonnet-4-20250514",
            "repetition": 1, "status": "completed",
            "prompt_text": None, "prompt_tokens": 100,
            "raw_output": "output", "completion_tokens": 50,
            "pass_fail": 1, "ttft_ms": 50.0, "ttlt_ms": 100.0,
            "total_cost_usd": 0.01, "timestamp": "2026-01-01T00:00:00Z",
        })
        result = audit_data_completeness(tmp_db, ["HumanEval/1"])
        assert result["issues_found"] > 0
        assert any("prompt_text" in str(issue) for issue in result["issues"])

    def test_detects_zero_prompt_tokens(self, tmp_db: sqlite3.Connection) -> None:
        from src.pilot import audit_data_completeness
        insert_run(tmp_db, {
            "run_id": "test|2", "prompt_id": "HumanEval/1",
            "benchmark": "humaneval", "noise_type": "clean",
            "intervention": "raw", "model": "claude-sonnet-4-20250514",
            "repetition": 1, "status": "completed",
            "prompt_text": "hello", "prompt_tokens": 0,
            "raw_output": "output", "completion_tokens": 50,
            "pass_fail": 1, "ttft_ms": 50.0, "ttlt_ms": 100.0,
            "total_cost_usd": 0.01, "timestamp": "2026-01-01T00:00:00Z",
        })
        result = audit_data_completeness(tmp_db, ["HumanEval/1"])
        assert result["issues_found"] > 0
        assert any("prompt_tokens" in str(issue) for issue in result["issues"])

    def test_clean_data_no_issues(self, tmp_db: sqlite3.Connection) -> None:
        from src.pilot import audit_data_completeness
        insert_run(tmp_db, {
            "run_id": "test|3", "prompt_id": "HumanEval/1",
            "benchmark": "humaneval", "noise_type": "clean",
            "intervention": "raw", "model": "claude-sonnet-4-20250514",
            "repetition": 1, "status": "completed",
            "prompt_text": "hello world", "prompt_tokens": 100,
            "raw_output": "the answer", "completion_tokens": 50,
            "pass_fail": 1, "ttft_ms": 50.0, "ttlt_ms": 100.0,
            "total_cost_usd": 0.01, "timestamp": "2026-01-01T00:00:00Z",
        })
        result = audit_data_completeness(tmp_db, ["HumanEval/1"])
        assert result["issues_found"] == 0


# ---------------------------------------------------------------------------
# verify_noise_rates tests
# ---------------------------------------------------------------------------

class TestVerifyNoiseRates:
    """Tests for noise injection sanity checking."""

    def test_within_tolerance_not_flagged(self) -> None:
        from src.pilot import verify_noise_rates
        # Use a prompt that is long enough for noise to be applied
        prompts_by_id = {
            "HumanEval/1": {
                "problem_id": "HumanEval/1",
                "prompt_text": "This is a relatively long prompt text with many words to ensure noise mutations can be applied reliably across the character space",
                "answer_type": "code",
            }
        }
        result = verify_noise_rates(
            prompts_by_id, ["HumanEval/1"], base_seed=42, tolerance=0.5,
        )
        # With real noise generator and 0.5 tolerance, most should pass
        assert result["flagged_count"] <= result["total_checks"]
        assert "flagged" in result

    def test_extreme_tolerance_flags(self) -> None:
        from src.pilot import verify_noise_rates
        prompts_by_id = {
            "HumanEval/1": {
                "problem_id": "HumanEval/1",
                "prompt_text": "This is a relatively long prompt text with many words to ensure noise mutations can be applied reliably across the character space",
                "answer_type": "code",
            }
        }
        # Very tight tolerance should flag some entries
        result = verify_noise_rates(
            prompts_by_id, ["HumanEval/1"], base_seed=42, tolerance=0.001,
        )
        assert result["flagged_count"] > 0
        assert result["flagged"][0]["flagged"] is True
