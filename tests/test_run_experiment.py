"""Tests for the execution engine: intervention router, run_id, ordering, and engine loop."""

import argparse
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch, call

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

    def test_apply_intervention_compress_only(self) -> None:
        from src.run_experiment import apply_intervention
        with patch("src.run_experiment.sanitize_and_compress", return_value=("compressed", {"preproc_model": "haiku"})) as mock_sc:
            text, meta = apply_intervention("test prompt", "compress_only", "claude-sonnet-4-20250514", mock_call_fn)
            mock_sc.assert_called_once_with("test prompt", "claude-sonnet-4-20250514", mock_call_fn)
            assert isinstance(text, str)
            assert "preproc_model" in meta

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


# ---------------------------------------------------------------------------
# Test fixtures for engine tests
# ---------------------------------------------------------------------------

SAMPLE_PROMPT_RECORD = {
    "benchmark_source": "gsm8k",
    "problem_id": "gsm8k_1",
    "prompt_text": "What is 2 + 2?",
    "canonical_answer": "4",
    "answer_type": "numeric",
}

SAMPLE_MATRIX_ITEM = {
    "prompt_id": "gsm8k_1",
    "noise_type": "clean",
    "noise_level": None,
    "intervention": "raw",
    "model": "claude-sonnet-4-20250514",
    "repetition_num": 1,
    "status": "pending",
    "experiment": "noise_recovery",
}


def _make_test_args(
    model: str = "all",
    limit: int | None = None,
    retry_failed: bool = False,
    dry_run: bool = False,
    db: str | None = None,
    yes: bool = True,
    budget: float | None = None,
) -> argparse.Namespace:
    """Build a mock args namespace for run_engine."""
    return argparse.Namespace(
        model=model,
        limit=limit,
        retry_failed=retry_failed,
        dry_run=dry_run,
        db=db,
        yes=yes,
        budget=budget,
    )


def _setup_test_env(tmp_path, matrix_items=None, prompts=None):
    """Create temporary matrix and prompts files, return config."""
    from src.config import ExperimentConfig
    from src.db import init_database

    if prompts is None:
        prompts = [SAMPLE_PROMPT_RECORD]
    if matrix_items is None:
        matrix_items = [SAMPLE_MATRIX_ITEM]

    prompts_path = str(tmp_path / "prompts.json")
    matrix_path = str(tmp_path / "matrix.json")
    db_path = str(tmp_path / "test.db")

    with open(prompts_path, "w") as f:
        json.dump(prompts, f)
    with open(matrix_path, "w") as f:
        json.dump(matrix_items, f)

    config = ExperimentConfig(
        prompts_path=prompts_path,
        matrix_path=matrix_path,
        results_db_path=db_path,
    )

    conn = init_database(db_path)
    return config, conn, db_path


# ---------------------------------------------------------------------------
# _process_item tests
# ---------------------------------------------------------------------------

class TestProcessItem:
    """Tests for the single-item processing pipeline."""

    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_process_item_calls_pipeline(self, mock_grade, mock_call, tmp_path) -> None:
        """_process_item calls apply_intervention, call_model, grade_run, insert_run, save_grade_result."""
        from src.run_experiment import _process_item
        from src.grade_results import GradeResult

        config, conn, _ = _setup_test_env(tmp_path)

        mock_call.return_value = MockAPIResponse(
            text="The answer is 4",
            model="claude-sonnet-4-20250514",
            input_tokens=20,
            output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="Extracted: 4.0 (canonical: 4.0)",
            stderr="", execution_time_ms=5.0, extraction_method="integer",
        )

        prompts_by_id = {"gsm8k_1": SAMPLE_PROMPT_RECORD}
        _process_item(SAMPLE_MATRIX_ITEM, conn, prompts_by_id, config, 0, 1)

        # Verify call_model was called
        mock_call.assert_called_once()
        # Verify grade_run was called
        mock_grade.assert_called_once()
        # Verify run was inserted in DB
        from src.db import query_runs
        runs = query_runs(conn, status="completed")
        assert len(runs) == 1
        assert runs[0]["run_id"] == "gsm8k_1|clean|none|raw|claude-sonnet-4-20250514|1"

    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_process_item_builds_full_run_data(self, mock_grade, mock_call, tmp_path) -> None:
        """_process_item populates all required DB columns."""
        from src.run_experiment import _process_item
        from src.grade_results import GradeResult

        config, conn, _ = _setup_test_env(tmp_path)

        mock_call.return_value = MockAPIResponse(
            text="4", model="claude-sonnet-4-20250514",
            input_tokens=20, output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method="integer",
        )

        prompts_by_id = {"gsm8k_1": SAMPLE_PROMPT_RECORD}
        _process_item(SAMPLE_MATRIX_ITEM, conn, prompts_by_id, config, 0, 1)

        from src.db import query_runs
        runs = query_runs(conn, status="completed")
        r = runs[0]
        # Check key fields are populated
        assert r["prompt_id"] == "gsm8k_1"
        assert r["benchmark"] == "gsm8k"
        assert r["noise_type"] == "clean"
        assert r["intervention"] == "raw"
        assert r["model"] == "claude-sonnet-4-20250514"
        assert r["repetition"] == 1
        assert r["prompt_tokens"] == 20
        assert r["completion_tokens"] == 10
        assert r["ttft_ms"] == 50.0
        assert r["ttlt_ms"] == 100.0
        assert r["temperature"] == 0.0
        assert r["status"] == "completed"
        assert r["total_cost_usd"] is not None

    @patch("src.run_experiment.call_model")
    def test_process_item_handles_api_exception(self, mock_call, tmp_path) -> None:
        """_process_item catches API exceptions and marks status='failed'."""
        from src.run_experiment import _process_item

        config, conn, _ = _setup_test_env(tmp_path)
        mock_call.side_effect = RuntimeError("API exploded")

        prompts_by_id = {"gsm8k_1": SAMPLE_PROMPT_RECORD}
        _process_item(SAMPLE_MATRIX_ITEM, conn, prompts_by_id, config, 0, 1)

        from src.db import query_runs
        runs = query_runs(conn, status="failed")
        assert len(runs) == 1
        assert runs[0]["status"] == "failed"


# ---------------------------------------------------------------------------
# run_engine tests
# ---------------------------------------------------------------------------

class TestRunEngine:
    """Tests for the main engine loop."""

    @patch("src.run_experiment._validate_api_keys")
    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_engine_skips_completed(self, mock_grade, mock_call, mock_keys, tmp_path) -> None:
        """Engine skips items whose run_id is already completed in DB."""
        from src.run_experiment import run_engine, make_run_id
        from src.grade_results import GradeResult
        from src.db import insert_run

        config, conn, db_path = _setup_test_env(tmp_path)

        # Pre-insert a completed run
        run_id = make_run_id(SAMPLE_MATRIX_ITEM)
        insert_run(conn, {
            "run_id": run_id,
            "prompt_id": "gsm8k_1",
            "benchmark": "gsm8k",
            "noise_type": "clean",
            "intervention": "raw",
            "model": "claude-sonnet-4-20250514",
            "repetition": 1,
            "status": "completed",
        })
        conn.close()

        args = _make_test_args(db=db_path)
        run_engine(args, config=config)

        # call_model should NOT have been called (item was skipped)
        mock_call.assert_not_called()

    @patch("src.run_experiment._validate_api_keys")
    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_engine_retry_failed(self, mock_grade, mock_call, mock_keys, tmp_path) -> None:
        """Engine with --retry-failed reprocesses failed items."""
        from src.run_experiment import run_engine, make_run_id
        from src.grade_results import GradeResult
        from src.db import insert_run

        config, conn, db_path = _setup_test_env(tmp_path)

        # Pre-insert a failed run
        run_id = make_run_id(SAMPLE_MATRIX_ITEM)
        insert_run(conn, {
            "run_id": run_id,
            "prompt_id": "gsm8k_1",
            "benchmark": "gsm8k",
            "noise_type": "clean",
            "intervention": "raw",
            "model": "claude-sonnet-4-20250514",
            "repetition": 1,
            "status": "failed",
        })
        conn.close()

        mock_call.return_value = MockAPIResponse(
            text="4", model="claude-sonnet-4-20250514",
            input_tokens=20, output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method="integer",
        )

        args = _make_test_args(retry_failed=True, db=db_path)
        run_engine(args, config=config)

        # call_model should have been called (failed item reprocessed)
        mock_call.assert_called_once()

    @patch("src.run_experiment._validate_api_keys")
    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_engine_limit(self, mock_grade, mock_call, mock_keys, tmp_path) -> None:
        """Engine with --limit 1 processes only 1 item."""
        from src.run_experiment import run_engine
        from src.grade_results import GradeResult

        items = [
            dict(SAMPLE_MATRIX_ITEM, repetition_num=i) for i in range(1, 6)
        ]
        config, conn, db_path = _setup_test_env(tmp_path, matrix_items=items)
        conn.close()

        mock_call.return_value = MockAPIResponse(
            text="4", model="claude-sonnet-4-20250514",
            input_tokens=20, output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method="integer",
        )

        args = _make_test_args(limit=1, db=db_path)
        run_engine(args, config=config)

        # Only 1 call
        assert mock_call.call_count == 1

    def test_engine_dry_run(self, tmp_path) -> None:
        """Engine with --dry-run does not call any API or insert any runs."""
        from src.run_experiment import run_engine

        items = [SAMPLE_MATRIX_ITEM]
        config, conn, db_path = _setup_test_env(tmp_path, matrix_items=items)
        conn.close()

        with patch("src.run_experiment.call_model") as mock_call:
            args = _make_test_args(dry_run=True, db=db_path)
            run_engine(args, config=config)
            mock_call.assert_not_called()

        # No runs in DB
        from src.db import init_database, query_runs
        conn2 = init_database(db_path)
        assert len(query_runs(conn2)) == 0
        conn2.close()

    @patch("src.run_experiment._validate_api_keys")
    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_engine_model_filter_claude(self, mock_grade, mock_call, mock_keys, tmp_path) -> None:
        """Engine with --model claude filters to claude items only."""
        from src.run_experiment import run_engine
        from src.grade_results import GradeResult

        items = [
            dict(SAMPLE_MATRIX_ITEM, model="claude-sonnet-4-20250514", repetition_num=1),
            dict(SAMPLE_MATRIX_ITEM, model="gemini-1.5-pro", repetition_num=1),
        ]
        config, conn, db_path = _setup_test_env(tmp_path, matrix_items=items)
        conn.close()

        mock_call.return_value = MockAPIResponse(
            text="4", model="claude-sonnet-4-20250514",
            input_tokens=20, output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method="integer",
        )

        args = _make_test_args(model="claude", db=db_path)
        run_engine(args, config=config)

        # Only 1 call (claude only)
        assert mock_call.call_count == 1

    @patch("src.run_experiment._validate_api_keys")
    @patch("src.run_experiment.call_model")
    @patch("src.run_experiment.grade_run")
    def test_progress_logging_format(self, mock_grade, mock_call, mock_keys, tmp_path, caplog) -> None:
        """Progress logging matches the specified format."""
        import logging
        from src.run_experiment import run_engine
        from src.grade_results import GradeResult

        config, conn, db_path = _setup_test_env(tmp_path)
        conn.close()

        mock_call.return_value = MockAPIResponse(
            text="4", model="claude-sonnet-4-20250514",
            input_tokens=20, output_tokens=10,
        )
        mock_grade.return_value = GradeResult(
            passed=True, fail_reason=None,
            stdout="ok", stderr="", execution_time_ms=5.0,
            extraction_method="integer",
        )

        args = _make_test_args(db=db_path)
        with caplog.at_level(logging.INFO, logger="src.run_experiment"):
            run_engine(args, config=config)

        # Check log contains expected format elements
        progress_logs = [r for r in caplog.records if "[1/1]" in r.message]
        assert len(progress_logs) == 1
        msg = progress_logs[0].message
        assert "gsm8k_1" in msg
        assert "clean" in msg
        assert "raw" in msg
        assert ("PASS" in msg or "FAIL" in msg)
        assert "$" in msg


# ---------------------------------------------------------------------------
# _get_benchmark tests
# ---------------------------------------------------------------------------

class TestGetBenchmark:
    """Tests for benchmark detection from prompt_id."""

    def test_humaneval(self) -> None:
        from src.run_experiment import _get_benchmark
        assert _get_benchmark("HumanEval/1") == "humaneval"

    def test_mbpp(self) -> None:
        from src.run_experiment import _get_benchmark
        assert _get_benchmark("Mbpp/1") == "mbpp"

    def test_gsm8k(self) -> None:
        from src.run_experiment import _get_benchmark
        assert _get_benchmark("gsm8k_1") == "gsm8k"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    """Tests for the argument parser."""

    def test_parser_defaults(self) -> None:
        from src.run_experiment import _build_parser
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.model == "all"
        assert args.limit is None
        assert args.retry_failed is False
        assert args.dry_run is False
        assert args.db is None

    def test_parser_all_flags(self) -> None:
        from src.run_experiment import _build_parser
        parser = _build_parser()
        args = parser.parse_args([
            "--model", "claude",
            "--limit", "10",
            "--retry-failed",
            "--dry-run",
            "--db", "/tmp/test.db",
        ])
        assert args.model == "claude"
        assert args.limit == 10
        assert args.retry_failed is True
        assert args.dry_run is True
        assert args.db == "/tmp/test.db"
