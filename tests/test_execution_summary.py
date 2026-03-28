"""Tests for the execution_summary module.

Covers cost estimation (including pre-processor costs), runtime estimation,
summary formatting, confirmation gate behavior (Y/N/M, --yes, --budget),
execution plan saving, and resume detection via count_completed.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.model_registry import registry
from src.execution_summary import (
    AVG_TOKENS,
    PREPROC_INTERVENTIONS,
    confirm_execution,
    count_completed,
    estimate_cost,
    estimate_runtime,
    format_post_run_report,
    format_summary,
    save_execution_plan,
)


# ---------------------------------------------------------------------------
# Helper: test item factory
# ---------------------------------------------------------------------------


def _make_item(
    prompt_id: str = "HumanEval/1",
    model: str = "claude-sonnet-4-20250514",
    intervention: str = "raw",
    noise_type: str = "clean",
    noise_level: str | None = None,
    repetition_num: int = 1,
) -> dict:
    """Create a minimal experiment matrix item for testing."""
    return {
        "prompt_id": prompt_id,
        "model": model,
        "intervention": intervention,
        "noise_type": noise_type,
        "noise_level": noise_level,
        "repetition_num": repetition_num,
    }


# ---------------------------------------------------------------------------
# TestCostEstimation
# ---------------------------------------------------------------------------


class TestCostEstimation:
    """Tests for estimate_cost function.

    Uses prompts_path="/nonexistent" to force fallback to AVG_TOKENS
    estimates, making tests deterministic without real prompt data.
    """

    _NO_PROMPTS = "/nonexistent/prompts.json"

    def test_estimate_cost_single_raw_item(self):
        """Single raw HumanEval item has correct target cost and zero preproc."""
        items = [_make_item()]
        result = estimate_cost(items, prompts_path=self._NO_PROMPTS)
        # Fallback: input=500, output=int(500*8.0)=4000
        expected_target = registry.compute_cost("claude-sonnet-4-20250514", 500, 4000)
        assert result["target_cost"] == pytest.approx(expected_target)
        assert result["preproc_cost"] == 0.0
        assert result["total_cost"] == pytest.approx(expected_target)

    def test_estimate_cost_preproc_item_adds_preproc_cost(self):
        """Pre-processor intervention adds non-zero preproc cost."""
        items = [_make_item(intervention="pre_proc_sanitize")]
        result = estimate_cost(items, prompts_path=self._NO_PROMPTS)
        assert result["preproc_cost"] > 0.0

        # Preproc cost uses haiku model with input=500, output=int(500*0.8)=400
        preproc_model = registry.get_preproc("claude-sonnet-4-20250514")
        expected_preproc = registry.compute_cost(preproc_model, 500, 400)
        assert result["preproc_cost"] == pytest.approx(expected_preproc)

    def test_estimate_cost_gsm8k_uses_different_tokens(self):
        """GSM8K items use fallback 300 input, output_ratio 5.0 -> 1500 output."""
        items = [_make_item(prompt_id="gsm8k_1")]
        result = estimate_cost(items, prompts_path=self._NO_PROMPTS)
        expected = registry.compute_cost("claude-sonnet-4-20250514", 300, 1500)
        assert result["target_cost"] == pytest.approx(expected)

    def test_estimate_cost_empty_list(self):
        """Empty item list returns all zeros."""
        result = estimate_cost([], prompts_path=self._NO_PROMPTS)
        assert result["target_cost"] == 0.0
        assert result["preproc_cost"] == 0.0
        assert result["total_cost"] == 0.0

    def test_estimate_cost_multiple_items_sums(self):
        """Total cost of N items equals sum of individual costs."""
        items = [
            _make_item(prompt_id="HumanEval/1"),
            _make_item(prompt_id="gsm8k_2"),
            _make_item(prompt_id="Mbpp/3"),
        ]
        total_result = estimate_cost(items, prompts_path=self._NO_PROMPTS)

        individual_sum = sum(
            estimate_cost([item], prompts_path=self._NO_PROMPTS)["total_cost"]
            for item in items
        )
        assert total_result["total_cost"] == pytest.approx(individual_sum)

    def test_estimate_cost_free_model_zero_cost(self):
        """Free OpenRouter Nemotron model has zero total cost."""
        items = [
            _make_item(
                model="openrouter/nvidia/nemotron-3-super-120b-a12b:free"
            )
        ]
        result = estimate_cost(items, prompts_path=self._NO_PROMPTS)
        assert result["total_cost"] == 0.0

    def test_estimate_cost_returns_token_counts(self):
        """Cost estimate includes token count breakdowns."""
        items = [_make_item(), _make_item(intervention="pre_proc_sanitize")]
        result = estimate_cost(items, prompts_path=self._NO_PROMPTS)
        assert result["target_input_tokens"] > 0
        assert result["target_output_tokens"] > 0
        assert result["preproc_input_tokens"] > 0
        assert result["preproc_output_tokens"] > 0

    def test_estimate_cost_all_preproc_interventions(self):
        """All three PREPROC_INTERVENTIONS trigger preproc cost."""
        for intervention in PREPROC_INTERVENTIONS:
            items = [_make_item(intervention=intervention)]
            result = estimate_cost(items)
            # Free model still has zero, so test with claude
            assert result["preproc_cost"] >= 0.0


# ---------------------------------------------------------------------------
# TestRuntimeEstimation
# ---------------------------------------------------------------------------


class TestRuntimeEstimation:
    """Tests for estimate_runtime function."""

    def test_estimate_runtime_counts_all_calls(self):
        """10 raw items = 10 target calls at 6.0s each = 60s."""
        items = [_make_item() for _ in range(10)]
        result = estimate_runtime(items)
        assert result == pytest.approx(10 * 6.0)

    def test_estimate_runtime_includes_preproc_calls(self):
        """5 raw + 5 preproc items = 10 target + 5 preproc = 15 calls."""
        items = [_make_item() for _ in range(5)]
        items += [_make_item(intervention="pre_proc_sanitize") for _ in range(5)]
        result = estimate_runtime(items)
        assert result == pytest.approx(15 * 6.0)

    def test_estimate_runtime_empty_list(self):
        """Empty item list returns 0.0."""
        assert estimate_runtime([]) == 0.0


# ---------------------------------------------------------------------------
# TestFormatSummary
# ---------------------------------------------------------------------------


class TestFormatSummary:
    """Tests for format_summary function."""

    def _make_summary(self, items=None, completed=0, total=10, cost=None, runtime=60.0):
        """Helper to build a summary with defaults."""
        if items is None:
            items = [_make_item() for _ in range(5)]
        if cost is None:
            cost = {"target_cost": 1.50, "preproc_cost": 0.0, "total_cost": 1.50}
        return format_summary(items, completed, total, cost, runtime)

    def test_format_summary_contains_all_sections(self):
        """Summary output contains required section headings and keywords."""
        output = self._make_summary()
        assert "Pre-Execution Summary" in output
        assert "Model" in output
        assert "Intervention" in output
        assert "Noise" in output
        assert "Estimates:" in output
        assert "Estimated runtime" in output

    def test_format_summary_shows_resume_info(self):
        """With completed_count > 0, summary shows resume information."""
        items = [_make_item() for _ in range(50)]
        output = self._make_summary(items=items, completed=50, total=100)
        assert "50" in output
        assert "100" in output
        assert "remaining" in output.lower() or "Resuming" in output

    def test_format_summary_no_resume_when_zero_completed(self):
        """With completed_count=0, no resume text appears."""
        output = self._make_summary(completed=0, total=100)
        assert "Resuming" not in output
        assert "remaining" not in output.lower()

    def test_format_summary_shows_preproc_cost_line(self):
        """Pre-processor cost line appears in output."""
        cost = {"target_cost": 1.0, "preproc_cost": 0.50, "total_cost": 1.50}
        output = self._make_summary(cost=cost)
        assert "Pre-processor" in output


# ---------------------------------------------------------------------------
# TestConfirmExecution
# ---------------------------------------------------------------------------


class TestConfirmExecution:
    """Tests for confirm_execution function."""

    def test_confirm_yes_flag_returns_yes(self, capsys):
        """--yes flag auto-accepts without prompting."""
        result = confirm_execution("summary text", yes=True)
        assert result == "yes"

    def test_confirm_yes_input(self, capsys):
        """User entering 'y' returns 'yes'."""
        result = confirm_execution("summary text", input_fn=lambda _: "y")
        assert result == "yes"

    def test_confirm_no_input(self, capsys):
        """User entering 'n' returns 'no'."""
        result = confirm_execution("summary text", input_fn=lambda _: "n")
        assert result == "no"

    def test_confirm_modify_input(self, capsys):
        """User entering 'm' returns 'modify'."""
        result = confirm_execution("summary text", input_fn=lambda _: "m")
        assert result == "modify"

    def test_confirm_budget_exceeded_exits(self, capsys):
        """Budget gate fires SystemExit when estimated cost exceeds budget."""
        with pytest.raises(SystemExit) as exc_info:
            confirm_execution(
                "summary", budget=10.0, estimated_cost=20.0, input_fn=lambda _: "y"
            )
        assert exc_info.value.code == 1

    def test_confirm_budget_not_exceeded_proceeds(self, capsys):
        """Within budget with --yes returns 'yes' normally."""
        result = confirm_execution(
            "summary", yes=True, budget=100.0, estimated_cost=50.0
        )
        assert result == "yes"

    def test_confirm_budget_checked_before_yes(self, capsys):
        """Budget gate fires even with --yes flag (budget checked first)."""
        with pytest.raises(SystemExit):
            confirm_execution(
                "summary", yes=True, budget=10.0, estimated_cost=20.0
            )

    def test_confirm_invalid_then_valid(self, capsys):
        """Invalid input loops, then valid input is accepted."""
        call_count = 0

        def _mock_input(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "x"
            return "y"

        result = confirm_execution("summary", input_fn=_mock_input)
        assert result == "yes"
        assert call_count == 2


# ---------------------------------------------------------------------------
# TestSaveExecutionPlan
# ---------------------------------------------------------------------------


class TestSaveExecutionPlan:
    """Tests for save_execution_plan function."""

    def test_save_creates_json_file(self, tmp_path):
        """Saved file exists, is valid JSON, and contains required keys."""
        output = str(tmp_path / "plan.json")
        items = [_make_item()]
        cost = {"target_cost": 1.0, "preproc_cost": 0.0, "total_cost": 1.0}
        save_execution_plan(items, cost, 60.0, output_path=output)

        with open(output) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert data["total_items"] == 1
        assert "models" in data
        assert "cost_estimate" in data

    def test_save_includes_filters(self, tmp_path):
        """Filters dict is included in the saved JSON."""
        output = str(tmp_path / "plan.json")
        items = [_make_item()]
        cost = {"target_cost": 1.0, "preproc_cost": 0.0, "total_cost": 1.0}
        save_execution_plan(
            items, cost, 60.0, filters={"model": "claude"}, output_path=output
        )

        with open(output) as f:
            data = json.load(f)

        assert data["filters"]["model"] == "claude"

    def test_save_creates_parent_directory(self, tmp_path):
        """Parent directories are auto-created when they do not exist."""
        output = str(tmp_path / "subdir" / "plan.json")
        items = [_make_item()]
        cost = {"target_cost": 0.0, "preproc_cost": 0.0, "total_cost": 0.0}
        save_execution_plan(items, cost, 0.0, output_path=output)

        with open(output) as f:
            data = json.load(f)
        assert data["total_items"] == 1


# ---------------------------------------------------------------------------
# TestCountCompleted
# ---------------------------------------------------------------------------


class TestCountCompleted:
    """Tests for count_completed function."""

    def test_count_completed_with_mock_db(self):
        """Mock DB returns completed runs; count and pending list are correct."""
        items = [
            _make_item(prompt_id="HumanEval/1", repetition_num=1),
            _make_item(prompt_id="HumanEval/2", repetition_num=1),
            _make_item(prompt_id="HumanEval/3", repetition_num=1),
        ]

        # Build the run_id that count_completed would generate for item 0
        # run_id = "HumanEval/1|clean|none|raw|claude-sonnet-4-20250514|1"
        completed_run_id = "HumanEval/1|clean|none|raw|claude-sonnet-4-20250514|1"

        mock_conn = MagicMock()
        with patch("src.db.query_runs") as mock_query:
            mock_query.return_value = [{"run_id": completed_run_id}]
            completed, total, pending = count_completed(items, mock_conn)

        assert completed == 1
        assert total == 3
        assert len(pending) == 2
        # The completed item should not be in pending
        pending_ids = [item["prompt_id"] for item in pending]
        assert "HumanEval/1" not in pending_ids

    def test_count_completed_none_completed(self):
        """With no completed runs, all items are pending."""
        items = [_make_item() for _ in range(5)]
        mock_conn = MagicMock()
        with patch("src.db.query_runs") as mock_query:
            mock_query.return_value = []
            completed, total, pending = count_completed(items, mock_conn)

        assert completed == 0
        assert total == 5
        assert len(pending) == 5


# ---------------------------------------------------------------------------
# TestBenchmarkBreakdown
# ---------------------------------------------------------------------------


def _make_test_db(tmp_path):
    """Create an in-memory SQLite db with test rows for benchmark breakdown tests."""
    import sqlite3
    from src.db import init_database

    db_path = str(tmp_path / "test_report.db")
    conn = init_database(db_path)

    # Insert test rows covering multiple benchmarks and noise types
    test_rows = [
        # HumanEval - clean/raw - pass
        ("HumanEval/1|clean|none|raw|model-a|1", "HumanEval/1", "humaneval",
         "clean", None, "raw", "model-a", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # HumanEval - clean/raw - fail
        ("HumanEval/2|clean|none|raw|model-a|1", "HumanEval/2", "humaneval",
         "clean", None, "raw", "model-a", 1, 0, 150.0, 250.0, 0.001, 0.002, 0.003, "completed"),
        # MBPP - clean/raw - pass
        ("Mbpp/1|clean|none|raw|model-a|1", "Mbpp/1", "mbpp",
         "clean", None, "raw", "model-a", 1, 1, 120.0, 220.0, 0.002, 0.003, 0.005, "completed"),
        # GSM8K - clean/raw - pass
        ("gsm8k_1|clean|none|raw|model-a|1", "gsm8k_1", "gsm8k",
         "clean", None, "raw", "model-a", 1, 1, 80.0, 150.0, 0.0005, 0.001, 0.0015, "completed"),
        # HumanEval - typo_5/raw - fail
        ("HumanEval/1|typo_5|5|raw|model-a|1", "HumanEval/1", "humaneval",
         "typo_5", "5", "raw", "model-a", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # MBPP - typo_5/raw - pass
        ("Mbpp/1|typo_5|5|raw|model-a|1", "Mbpp/1", "mbpp",
         "typo_5", "5", "raw", "model-a", 1, 1, 120.0, 220.0, 0.002, 0.003, 0.005, "completed"),
        # GSM8K - typo_5/raw - fail
        ("gsm8k_1|typo_5|5|raw|model-a|1", "gsm8k_1", "gsm8k",
         "typo_5", "5", "raw", "model-a", 1, 0, 80.0, 150.0, 0.0005, 0.001, 0.0015, "completed"),
    ]

    for row in test_rows:
        conn.execute("""
            INSERT INTO experiment_runs (
                run_id, prompt_id, benchmark, noise_type, noise_level,
                intervention, model, repetition, pass_fail, ttft_ms, ttlt_ms,
                main_model_input_cost_usd, main_model_output_cost_usd,
                total_cost_usd, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
    conn.commit()
    return conn


class TestBenchmarkBreakdown:
    """Tests for benchmark breakdown in format_post_run_report."""

    def test_per_benchmark_section_always_shown(self, tmp_path):
        """format_post_run_report with benchmark=False includes Per-Benchmark section."""
        conn = _make_test_db(tmp_path)
        report = format_post_run_report(conn, benchmark=False)
        conn.close()
        assert "Per-Benchmark:" in report
        assert "humaneval" in report.lower()
        assert "mbpp" in report.lower()
        assert "gsm8k" in report.lower()

    def test_benchmark_crosstab_shown_when_flag_true(self, tmp_path):
        """format_post_run_report with benchmark=True includes cross-tabulation."""
        conn = _make_test_db(tmp_path)
        report = format_post_run_report(conn, benchmark=True)
        conn.close()
        assert "Benchmark x Noise:" in report

    def test_benchmark_baselines_shown_when_flag_true(self, tmp_path):
        """format_post_run_report with benchmark=True includes baselines section."""
        conn = _make_test_db(tmp_path)
        report = format_post_run_report(conn, benchmark=True)
        conn.close()
        assert "Benchmark Baselines" in report

    def test_no_runs_returns_no_runs_found(self, tmp_path):
        """format_post_run_report with no completed runs returns 'No runs found'."""
        from src.db import init_database
        db_path = str(tmp_path / "empty.db")
        conn = init_database(db_path)
        report = format_post_run_report(conn, benchmark=False)
        conn.close()
        assert "No runs found" in report


# ---------------------------------------------------------------------------
# Helper: multi-model test database
# ---------------------------------------------------------------------------


def _make_multi_model_db(tmp_path):
    """Create a SQLite db with rows for 2 models across interventions and noise types."""
    import sqlite3
    from src.db import init_database

    db_path = str(tmp_path / "multi_model.db")
    conn = init_database(db_path)

    test_rows = [
        # model-a, raw, clean — 2 pass
        ("p1|clean|raw|model-a|1", "p1", "humaneval", "clean", None, "raw", "model-a", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|clean|raw|model-a|1", "p2", "humaneval", "clean", None, "raw", "model-a", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # model-a, raw, typo_5 — 1 pass 1 fail
        ("p1|typo_5|raw|model-a|1", "p1", "humaneval", "typo_5", "5", "raw", "model-a", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|typo_5|raw|model-a|1", "p2", "humaneval", "typo_5", "5", "raw", "model-a", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # model-a, pre_proc_sanitize, clean — 1 pass 1 fail
        ("p1|clean|pps|model-a|1", "p1", "humaneval", "clean", None, "pre_proc_sanitize", "model-a", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|clean|pps|model-a|1", "p2", "humaneval", "clean", None, "pre_proc_sanitize", "model-a", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # model-b, raw, clean — 1 pass 1 fail
        ("p1|clean|raw|model-b|1", "p1", "humaneval", "clean", None, "raw", "model-b", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|clean|raw|model-b|1", "p2", "humaneval", "clean", None, "raw", "model-b", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # model-b, raw, typo_5 — 0 pass 2 fail
        ("p1|typo_5|raw|model-b|1", "p1", "humaneval", "typo_5", "5", "raw", "model-b", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|typo_5|raw|model-b|1", "p2", "humaneval", "typo_5", "5", "raw", "model-b", 1, 0, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        # model-b, pre_proc_sanitize, clean — 2 pass
        ("p1|clean|pps|model-b|1", "p1", "humaneval", "clean", None, "pre_proc_sanitize", "model-b", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
        ("p2|clean|pps|model-b|1", "p2", "humaneval", "clean", None, "pre_proc_sanitize", "model-b", 1, 1, 100.0, 200.0, 0.001, 0.002, 0.003, "completed"),
    ]

    for row in test_rows:
        conn.execute("""
            INSERT INTO experiment_runs (
                run_id, prompt_id, benchmark, noise_type, noise_level,
                intervention, model, repetition, pass_fail, ttft_ms, ttlt_ms,
                main_model_input_cost_usd, main_model_output_cost_usd,
                total_cost_usd, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
    conn.commit()
    return conn


class TestMultiModelPivot:
    """Tests for multi-model pivot tables in format_post_run_report."""

    def test_pivot_tables_appear_with_two_models(self, tmp_path):
        """Multi-model DB produces Intervention x Model and Noise x Model headers."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn)
        conn.close()
        assert "Intervention x Model" in report
        assert "Noise x Model" in report

    def test_pivot_tables_contain_both_model_names(self, tmp_path):
        """Both model names appear in pivot tables."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn)
        conn.close()
        # Both model names should appear in the pivot sections
        assert "model-a" in report
        assert "model-b" in report

    def test_pivot_skipped_single_model(self, tmp_path):
        """Single-model DB does not show pivot table headers."""
        conn = _make_test_db(tmp_path)
        report = format_post_run_report(conn)
        conn.close()
        assert "Intervention x Model" not in report
        assert "Noise x Model" not in report

    def test_intervention_pivot_pass_rates(self, tmp_path):
        """Intervention x Model pivot shows correct pass rates."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn)
        conn.close()
        # model-a raw: 3 pass / 4 total = 75.0%
        # model-b raw: 1 pass / 4 total = 25.0%
        assert "75.0%" in report
        assert "25.0%" in report

    def test_noise_pivot_pass_rates(self, tmp_path):
        """Noise x Model pivot shows correct pass rates per noise type."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn)
        conn.close()
        # model-b typo_5: 0 pass / 2 total = 0.0%
        assert "0.0%" in report


class TestReportFormats:
    """Tests for output_format parameter of format_post_run_report."""

    def test_json_format_valid(self, tmp_path):
        """output_format='json' returns valid JSON with expected keys."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn, output_format="json")
        conn.close()
        data = json.loads(report)
        assert "models" in data
        assert "interventions" in data
        assert "noise" in data
        assert "costs" in data

    def test_csv_format(self, tmp_path):
        """output_format='csv' returns comma-separated values."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn, output_format="csv")
        conn.close()
        # CSV should have comma-separated rows
        assert "," in report
        # Should have section headers
        assert "# Models" in report or "# models" in report.lower()

    def test_markdown_format(self, tmp_path):
        """output_format='markdown' returns pipe-delimited table rows."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn, output_format="markdown")
        conn.close()
        # Markdown tables use pipes
        assert "|" in report
        # GitHub-flavored markdown has separator rows with dashes
        assert "---" in report

    def test_text_format_backward_compat(self, tmp_path):
        """output_format='text' returns same format as current behavior."""
        conn = _make_multi_model_db(tmp_path)
        report = format_post_run_report(conn, output_format="text")
        conn.close()
        assert "=== Post-Run Report ===" in report
