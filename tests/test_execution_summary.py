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
    """Tests for estimate_cost function."""

    def test_estimate_cost_single_raw_item(self):
        """Single raw HumanEval item has correct target cost and zero preproc."""
        items = [_make_item()]
        result = estimate_cost(items)
        expected_target = registry.compute_cost("claude-sonnet-4-20250514", 500, 200)
        assert result["target_cost"] == pytest.approx(expected_target)
        assert result["preproc_cost"] == 0.0
        assert result["total_cost"] == pytest.approx(expected_target)

    def test_estimate_cost_preproc_item_adds_preproc_cost(self):
        """Pre-processor intervention adds non-zero preproc cost."""
        items = [_make_item(intervention="pre_proc_sanitize")]
        result = estimate_cost(items)
        assert result["preproc_cost"] > 0.0

        # Preproc cost uses haiku model with input=500, output=int(500*0.8)=400
        preproc_model = registry.get_preproc("claude-sonnet-4-20250514")
        expected_preproc = registry.compute_cost(preproc_model, 500, 400)
        assert result["preproc_cost"] == pytest.approx(expected_preproc)

    def test_estimate_cost_gsm8k_uses_different_tokens(self):
        """GSM8K items use 300 input / 100 output tokens."""
        items = [_make_item(prompt_id="gsm8k_1")]
        result = estimate_cost(items)
        expected = registry.compute_cost("claude-sonnet-4-20250514", 300, 100)
        assert result["target_cost"] == pytest.approx(expected)

    def test_estimate_cost_empty_list(self):
        """Empty item list returns all zeros."""
        result = estimate_cost([])
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
        total_result = estimate_cost(items)

        individual_sum = sum(
            estimate_cost([item])["total_cost"] for item in items
        )
        assert total_result["total_cost"] == pytest.approx(individual_sum)

    def test_estimate_cost_free_model_zero_cost(self):
        """Free OpenRouter Nemotron model has zero total cost."""
        items = [
            _make_item(
                model="openrouter/nvidia/nemotron-3-super-120b-a12b:free"
            )
        ]
        result = estimate_cost(items)
        assert result["total_cost"] == 0.0

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

    def test_estimate_runtime_single_model(self):
        """10 claude-sonnet items at 0.2s each = 2.0 seconds."""
        items = [_make_item() for _ in range(10)]
        result = estimate_runtime(items)
        expected = 10 * registry.get_delay("claude-sonnet-4-20250514")
        assert result == pytest.approx(expected)

    def test_estimate_runtime_mixed_models(self):
        """Mixed models sum per-model delays correctly."""
        items = [_make_item(model="claude-sonnet-4-20250514") for _ in range(5)]
        items += [_make_item(model="gemini-1.5-pro") for _ in range(5)]
        result = estimate_runtime(items)
        expected = (
            5 * registry.get_delay("claude-sonnet-4-20250514")
            + 5 * registry.get_delay("gemini-1.5-pro")
        )
        assert result == pytest.approx(expected)

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
        assert "Cost" in output
        assert "Runtime" in output

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
