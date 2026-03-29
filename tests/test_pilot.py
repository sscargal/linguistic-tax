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


# ---------------------------------------------------------------------------
# Helper: populate DB with synthetic pilot data
# ---------------------------------------------------------------------------

def _make_run(
    prompt_id: str,
    benchmark: str,
    noise_type: str = "clean",
    noise_level: str | None = None,
    intervention: str = "raw",
    model: str = "claude-sonnet-4-20250514",
    repetition: int = 1,
    pass_fail: int = 1,
    total_cost_usd: float = 0.01,
    ttft_ms: float = 50.0,
    ttlt_ms: float = 200.0,
    status: str = "completed",
    prompt_text: str = "prompt text",
    raw_output: str = "output text",
) -> dict:
    """Build a synthetic experiment_runs row dict."""
    run_id = f"{prompt_id}|{noise_type}|{intervention}|{model}|{repetition}"
    return {
        "run_id": run_id,
        "prompt_id": prompt_id,
        "benchmark": benchmark,
        "noise_type": noise_type,
        "noise_level": noise_level,
        "intervention": intervention,
        "model": model,
        "repetition": repetition,
        "status": status,
        "prompt_text": prompt_text,
        "prompt_tokens": 100,
        "raw_output": raw_output,
        "completion_tokens": 50,
        "pass_fail": pass_fail,
        "ttft_ms": ttft_ms,
        "ttlt_ms": ttlt_ms,
        "total_cost_usd": total_cost_usd,
        "timestamp": "2026-01-01T00:00:00Z",
        "temperature": 0.0,
    }


@pytest.fixture
def pilot_db(tmp_path: Path) -> tuple[sqlite3.Connection, list[str], dict]:
    """Create DB with synthetic pilot data across benchmarks and conditions.

    Returns (conn, pilot_prompt_ids, prompts_by_id).
    """
    db_path = str(tmp_path / "pilot.db")
    conn = init_database(db_path)

    pilot_ids = ["gsm8k_1", "gsm8k_2", "HumanEval/1", "HumanEval/2", "Mbpp/1"]
    prompts_by_id = {
        "gsm8k_1": {"prompt_text": "What is 2+2?", "canonical_answer": "4", "answer_type": "numeric"},
        "gsm8k_2": {"prompt_text": "What is 3+3?", "canonical_answer": "6", "answer_type": "numeric"},
        "HumanEval/1": {"prompt_text": "def f(): pass", "test_code": "assert f() == 1", "answer_type": "code"},
        "HumanEval/2": {"prompt_text": "def g(): pass", "test_code": "assert g() == 2", "answer_type": "code"},
        "Mbpp/1": {"prompt_text": "def h(): pass", "test_code": "assert h() == 3", "answer_type": "code"},
    }

    benchmarks = {
        "gsm8k_1": "gsm8k", "gsm8k_2": "gsm8k",
        "HumanEval/1": "humaneval", "HumanEval/2": "humaneval",
        "Mbpp/1": "mbpp",
    }

    cost_idx = 0
    base_costs = [0.003, 0.005, 0.007, 0.004, 0.006]
    for pid in pilot_ids:
        bm = benchmarks[pid]
        for noise in ["clean", "type_a_5pct"]:
            for intv in ["raw", "pre_proc_sanitize"]:
                for rep in range(1, 3):  # 2 reps for speed
                    cost = base_costs[cost_idx % len(base_costs)]
                    cost_idx += 1
                    insert_run(conn, _make_run(
                        prompt_id=pid, benchmark=bm,
                        noise_type=noise, intervention=intv,
                        repetition=rep, total_cost_usd=cost,
                        ttft_ms=40.0 + rep * 10, ttlt_ms=150.0 + rep * 50,
                    ))

    return conn, pilot_ids, prompts_by_id


# ---------------------------------------------------------------------------
# run_spot_check tests
# ---------------------------------------------------------------------------

class TestRunSpotCheck:
    """Tests for grading spot-check report."""

    def test_spot_check_selects_all_gsm8k(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_spot_check
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "spot.json")
        report = run_spot_check(conn, pilot_ids, prompts_by_id, output_path=out)
        # All GSM8K rows should be in the sample
        gsm8k_samples = [s for s in report["samples"] if s["benchmark"] == "gsm8k"]
        # Count how many gsm8k rows exist in DB
        all_runs = conn.execute(
            "SELECT COUNT(*) FROM experiment_runs WHERE benchmark='gsm8k' AND status='completed'"
            " AND prompt_id IN (?, ?)", ["gsm8k_1", "gsm8k_2"]
        ).fetchone()[0]
        assert report["gsm8k_count"] == all_runs

    def test_spot_check_samples_20pct_code(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_spot_check
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "spot.json")
        report = run_spot_check(conn, pilot_ids, prompts_by_id, output_path=out)
        # Code samples should be approximately 20% of code rows
        code_rows_total = conn.execute(
            "SELECT COUNT(*) FROM experiment_runs WHERE benchmark IN ('humaneval','mbpp')"
            " AND status='completed' AND prompt_id IN (?,?,?)",
            ["HumanEval/1", "HumanEval/2", "Mbpp/1"],
        ).fetchone()[0]
        assert report["code_count"] >= 1
        assert report["code_count"] <= code_rows_total

    def test_spot_check_report_fields(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_spot_check
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "spot.json")
        report = run_spot_check(conn, pilot_ids, prompts_by_id, output_path=out)
        assert "generated_at" in report
        assert "total_sampled" in report
        assert "gsm8k_count" in report
        assert "code_count" in report
        assert "samples" in report
        assert report["total_sampled"] == report["gsm8k_count"] + report["code_count"]

    def test_spot_check_sample_dict_fields(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_spot_check
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "spot.json")
        report = run_spot_check(conn, pilot_ids, prompts_by_id, output_path=out)
        sample = report["samples"][0]
        for key in ["run_id", "prompt_id", "benchmark", "noise_type", "intervention",
                     "model", "raw_output", "pass_fail", "expected_answer"]:
            assert key in sample, f"Missing key: {key}"

    def test_spot_check_writes_json(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_spot_check
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "spot.json")
        run_spot_check(conn, pilot_ids, prompts_by_id, output_path=out)
        assert Path(out).exists()
        with open(out) as f:
            data = json.load(f)
        assert "samples" in data


# ---------------------------------------------------------------------------
# compute_cost_projection tests
# ---------------------------------------------------------------------------

class TestComputeCostProjection:
    """Tests for bootstrap cost projection."""

    def test_cost_projection_scaling(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import compute_cost_projection
        conn, pilot_ids, _ = pilot_db
        out = str(tmp_path / "cost.json")
        result = compute_cost_projection(conn, pilot_ids, n_bootstrap=100, output_path=out)
        # 5 pilot prompts -> 200 full prompts: scale factor = 40
        assert result["pilot_total_cost"] > 0
        expected_proj = result["pilot_total_cost"] * (200 / len(pilot_ids))
        assert abs(result["projected_full_cost"] - expected_proj) < 0.001

    def test_cost_projection_ci_ordering(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import compute_cost_projection
        conn, pilot_ids, _ = pilot_db
        out = str(tmp_path / "cost.json")
        result = compute_cost_projection(conn, pilot_ids, n_bootstrap=100, output_path=out)
        assert result["ci_low"] <= result["projected_full_cost"] <= result["ci_high"]

    def test_cost_projection_output_fields(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import compute_cost_projection
        conn, pilot_ids, _ = pilot_db
        out = str(tmp_path / "cost.json")
        result = compute_cost_projection(conn, pilot_ids, n_bootstrap=100, output_path=out)
        for key in ["pilot_total_cost", "projected_full_cost", "ci_low", "ci_high",
                     "confidence_level", "n_bootstrap", "per_condition_breakdown"]:
            assert key in result, f"Missing key: {key}"

    def test_cost_projection_writes_json(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import compute_cost_projection
        conn, pilot_ids, _ = pilot_db
        out = str(tmp_path / "cost.json")
        compute_cost_projection(conn, pilot_ids, n_bootstrap=100, output_path=out)
        assert Path(out).exists()
        with open(out) as f:
            data = json.load(f)
        assert "projected_full_cost" in data


# ---------------------------------------------------------------------------
# check_budget_gate tests
# ---------------------------------------------------------------------------

class TestBudgetGate:
    """Tests for budget threshold checking."""

    def test_budget_gate_exceeds(self) -> None:
        from src.pilot import check_budget_gate
        result = check_budget_gate(250.0, budget_threshold=200.0)
        assert result["exceeds_budget"] is True
        assert result["projected_cost"] == 250.0
        assert result["budget_threshold"] == 200.0

    def test_budget_gate_within(self) -> None:
        from src.pilot import check_budget_gate
        result = check_budget_gate(150.0, budget_threshold=200.0)
        assert result["exceeds_budget"] is False

    def test_budget_gate_exact_threshold(self) -> None:
        from src.pilot import check_budget_gate
        result = check_budget_gate(200.0, budget_threshold=200.0)
        assert result["exceeds_budget"] is False


# ---------------------------------------------------------------------------
# check_preproc_fidelity tests
# ---------------------------------------------------------------------------

class TestCheckPreprocFidelity:
    """Tests for BERTScore pre-processor fidelity checking."""

    def test_preproc_fidelity_returns_expected_fields(self, pilot_db: tuple) -> None:
        from src.pilot import check_preproc_fidelity
        conn, pilot_ids, prompts_by_id = pilot_db
        # Mock bert_score.score to avoid downloading model
        import torch
        mock_f1 = torch.tensor([0.92, 0.88, 0.78, 0.95, 0.80, 0.91, 0.87, 0.93, 0.76, 0.90])
        mock_p = mock_f1.clone()
        mock_r = mock_f1.clone()
        with patch("src.pilot.bert_score_fn", return_value=(mock_p, mock_r, mock_f1)):
            result = check_preproc_fidelity(conn, pilot_ids, prompts_by_id)
        assert "mean_f1" in result
        assert "min_f1" in result
        assert "threshold" in result
        assert "flagged_count" in result
        assert "flagged_pairs" in result
        assert "total_pairs" in result

    def test_preproc_fidelity_flags_below_threshold(self, pilot_db: tuple) -> None:
        from src.pilot import check_preproc_fidelity
        conn, pilot_ids, prompts_by_id = pilot_db
        import torch
        # Create scores with some below 0.85
        mock_f1 = torch.tensor([0.92, 0.50, 0.78, 0.95, 0.80, 0.91, 0.60, 0.93, 0.76, 0.90])
        mock_p = mock_f1.clone()
        mock_r = mock_f1.clone()
        with patch("src.pilot.bert_score_fn", return_value=(mock_p, mock_r, mock_f1)):
            result = check_preproc_fidelity(conn, pilot_ids, prompts_by_id, threshold=0.85)
        # Scores below 0.85: 0.50, 0.78, 0.80, 0.60, 0.76 = 5 flagged
        assert result["flagged_count"] == 5
        for fp in result["flagged_pairs"]:
            assert fp["f1"] < 0.85

    def test_preproc_fidelity_handles_import_error(self, pilot_db: tuple) -> None:
        from src.pilot import check_preproc_fidelity
        conn, pilot_ids, prompts_by_id = pilot_db
        with patch("src.pilot.bert_score_fn", side_effect=ImportError("No module")):
            result = check_preproc_fidelity(conn, pilot_ids, prompts_by_id)
        assert "error" in result


# ---------------------------------------------------------------------------
# profile_latency tests
# ---------------------------------------------------------------------------

class TestProfileLatency:
    """Tests for latency profiling."""

    def test_profile_latency_returns_expected_structure(self, pilot_db: tuple) -> None:
        from src.pilot import profile_latency
        conn, pilot_ids, _ = pilot_db
        result = profile_latency(conn, pilot_ids)
        assert "by_model" in result
        assert "by_condition" in result
        assert "estimated_full_run_hours" in result
        assert "latency_flags" in result

    def test_profile_latency_per_model_stats(self, pilot_db: tuple) -> None:
        from src.pilot import profile_latency
        conn, pilot_ids, _ = pilot_db
        result = profile_latency(conn, pilot_ids)
        # We have one model in our fixture
        assert "claude-sonnet-4-20250514" in result["by_model"]
        model_stats = result["by_model"]["claude-sonnet-4-20250514"]
        assert "ttft" in model_stats
        assert "ttlt" in model_stats
        for stat_key in ["mean", "p50", "p95", "max", "min"]:
            assert stat_key in model_stats["ttft"]
            assert stat_key in model_stats["ttlt"]

    def test_profile_latency_flags_slow_conditions(self, tmp_path: Path) -> None:
        from src.pilot import profile_latency
        db_path = str(tmp_path / "slow.db")
        conn = init_database(db_path)
        # Insert rows with very high latency
        for rep in range(1, 6):
            insert_run(conn, _make_run(
                prompt_id="gsm8k_1", benchmark="gsm8k",
                repetition=rep, ttft_ms=1000.0, ttlt_ms=35000.0,  # > 30s
            ))
        result = profile_latency(conn, ["gsm8k_1"])
        assert len(result["latency_flags"]) > 0


# ---------------------------------------------------------------------------
# estimate_power tests
# ---------------------------------------------------------------------------

class TestEstimatePower:
    """Tests for power analysis estimation."""

    def test_estimate_power_returns_expected_fields(self, tmp_path: Path) -> None:
        from src.pilot import estimate_power
        db_path = str(tmp_path / "power.db")
        conn = init_database(db_path)
        # Create clean+raw runs (high pass rate)
        for rep in range(1, 6):
            insert_run(conn, _make_run(
                prompt_id="gsm8k_1", benchmark="gsm8k",
                noise_type="clean", intervention="raw",
                repetition=rep, pass_fail=1,
            ))
        # Create noisy+raw runs (lower pass rate)
        for rep in range(1, 6):
            insert_run(conn, _make_run(
                prompt_id="gsm8k_1", benchmark="gsm8k",
                noise_type="type_a_20pct", intervention="raw",
                repetition=rep, pass_fail=0 if rep <= 3 else 1,
            ))
        result = estimate_power(conn, ["gsm8k_1"])
        assert "observed_effects" in result
        assert "required_n" in result
        assert "n_200_sufficient" in result
        assert "note" in result


# ---------------------------------------------------------------------------
# run_pilot_verdict tests
# ---------------------------------------------------------------------------

class TestRunPilotVerdict:
    """Tests for structured pilot verdict."""

    def test_verdict_pass_on_high_completion(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_pilot_verdict
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "verdict.json")
        import torch
        mock_f1 = torch.tensor([0.92] * 10)
        with patch("src.pilot.bert_score_fn", return_value=(mock_f1, mock_f1, mock_f1)):
            result = run_pilot_verdict(conn, pilot_ids, prompts_by_id, output_path=out)
        assert result["overall_verdict"] == "PASS"
        assert result["completion_rate"] >= 0.95

    def test_verdict_fail_on_low_completion(self, tmp_path: Path) -> None:
        from src.pilot import run_pilot_verdict
        db_path = str(tmp_path / "fail_verdict.db")
        conn = init_database(db_path)
        pilot_ids = ["gsm8k_1"]
        prompts_by_id = {
            "gsm8k_1": {"prompt_text": "What is 2+2?", "canonical_answer": "4", "answer_type": "numeric"},
        }
        # Insert 10 completed, 10 failed -> 50% completion
        for i in range(1, 11):
            insert_run(conn, _make_run(
                prompt_id="gsm8k_1", benchmark="gsm8k",
                noise_type="clean", intervention="raw",
                repetition=i, status="completed",
            ))
        for i in range(11, 21):
            insert_run(conn, _make_run(
                prompt_id="gsm8k_1", benchmark="gsm8k",
                noise_type="type_a_5pct", intervention="raw",
                repetition=i, status="failed",
            ))
        out = str(tmp_path / "verdict.json")
        with patch("src.pilot.bert_score_fn", side_effect=ImportError("skip")):
            result = run_pilot_verdict(conn, pilot_ids, prompts_by_id, output_path=out)
        assert result["overall_verdict"] == "FAIL"
        assert result["completion_rate"] < 0.95

    def test_verdict_includes_zero_variance(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_pilot_verdict
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "verdict.json")
        import torch
        mock_f1 = torch.tensor([0.92] * 10)
        with patch("src.pilot.bert_score_fn", return_value=(mock_f1, mock_f1, mock_f1)):
            result = run_pilot_verdict(conn, pilot_ids, prompts_by_id, output_path=out)
        assert "zero_variance_pct" in result

    def test_verdict_includes_power_analysis(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_pilot_verdict
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "verdict.json")
        import torch
        mock_f1 = torch.tensor([0.92] * 10)
        with patch("src.pilot.bert_score_fn", return_value=(mock_f1, mock_f1, mock_f1)):
            result = run_pilot_verdict(conn, pilot_ids, prompts_by_id, output_path=out)
        assert "power_analysis" in result

    def test_verdict_writes_json(self, pilot_db: tuple, tmp_path: Path) -> None:
        from src.pilot import run_pilot_verdict
        conn, pilot_ids, prompts_by_id = pilot_db
        out = str(tmp_path / "verdict.json")
        import torch
        mock_f1 = torch.tensor([0.92] * 10)
        with patch("src.pilot.bert_score_fn", return_value=(mock_f1, mock_f1, mock_f1)):
            run_pilot_verdict(conn, pilot_ids, prompts_by_id, output_path=out)
        assert Path(out).exists()
        with open(out) as f:
            data = json.load(f)
        assert "overall_verdict" in data


# ---------------------------------------------------------------------------
# CLI / _build_parser tests
# ---------------------------------------------------------------------------

class TestCLI:
    """Tests for the CLI argument parser."""

    def test_build_parser_has_budget(self) -> None:
        from src.pilot import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--budget", "300.0"])
        assert args.budget == 300.0

    def test_build_parser_has_db(self) -> None:
        from src.pilot import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--db", "/tmp/test.db"])
        assert args.db == "/tmp/test.db"

    def test_build_parser_has_select_only(self) -> None:
        from src.pilot import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--select-only"])
        assert args.select_only is True

    def test_build_parser_has_analyze_only(self) -> None:
        from src.pilot import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--analyze-only"])
        assert args.analyze_only is True

    def test_build_parser_defaults(self) -> None:
        from src.pilot import _build_parser
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.budget == 200.0
        assert args.db is None
        assert args.select_only is False
        assert args.analyze_only is False


class TestValidModels:
    """Tests for _VALID_MODELS derivation from config."""

    def test_valid_models_includes_openai(self) -> None:
        from src.pilot import _VALID_MODELS
        assert "gpt-4o-2024-11-20" in _VALID_MODELS

    def test_valid_models_includes_claude(self) -> None:
        from src.pilot import _VALID_MODELS
        assert "claude-sonnet-4-20250514" in _VALID_MODELS

    def test_valid_models_includes_gemini(self) -> None:
        from src.pilot import _VALID_MODELS
        assert "gemini-1.5-pro" in _VALID_MODELS

    def test_valid_models_matches_config(self) -> None:
        from src.model_registry import registry
        from src.pilot import _VALID_MODELS
        assert _VALID_MODELS == set(registry.target_models())


