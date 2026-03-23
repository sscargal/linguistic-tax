"""Tests for compute_derived module -- CR, quadrant classification, cost rollups, migration."""

import sqlite3

import pytest

from src.compute_derived import (
    build_condition_string,
    classify_quadrant,
    compute_cost_rollups,
    compute_cr,
    compute_derived_metrics,
    compute_quadrant_migration,
)


# ---------------------------------------------------------------------------
# Consistency Rate (CR) tests
# ---------------------------------------------------------------------------


class TestComputeCR:
    """Tests for pairwise consistency rate computation."""

    def test_cr_all_pass(self) -> None:
        """5 passes -> CR = 1.0 (all 10 pairs agree)."""
        assert compute_cr([1, 1, 1, 1, 1]) == 1.0

    def test_cr_all_fail(self) -> None:
        """5 fails -> CR = 1.0 (all 10 pairs agree on fail)."""
        assert compute_cr([0, 0, 0, 0, 0]) == 1.0

    def test_cr_mixed_3_2(self) -> None:
        """3 pass + 2 fail -> CR = 0.4 (4 agreeing pairs out of 10)."""
        result = compute_cr([1, 1, 1, 0, 0])
        assert abs(result - 0.4) < 1e-9

    def test_cr_mixed_4_1(self) -> None:
        """4 pass + 1 fail -> CR = 0.6 (6 agreeing pairs out of 10)."""
        result = compute_cr([1, 1, 1, 1, 0])
        assert abs(result - 0.6) < 1e-9

    def test_cr_fewer_than_5(self) -> None:
        """3 runs -> CR computed with C(3,2)=3 pairs."""
        # [1, 1, 0]: 1 agreeing pair (1,1) out of 3 total -> CR = 1/3
        result = compute_cr([1, 1, 0])
        assert abs(result - 1.0 / 3.0) < 1e-9


# ---------------------------------------------------------------------------
# Quadrant classification tests
# ---------------------------------------------------------------------------


class TestClassifyQuadrant:
    """Tests for stability-correctness quadrant classification."""

    def test_quadrant_robust(self) -> None:
        """CR >= 0.8 AND majority_pass -> robust."""
        assert classify_quadrant(cr=0.9, majority_pass=True) == "robust"

    def test_quadrant_confidently_wrong(self) -> None:
        """CR >= 0.8 AND NOT majority_pass -> confidently_wrong."""
        assert classify_quadrant(cr=0.9, majority_pass=False) == "confidently_wrong"

    def test_quadrant_lucky(self) -> None:
        """CR < 0.8 AND majority_pass -> lucky."""
        assert classify_quadrant(cr=0.5, majority_pass=True) == "lucky"

    def test_quadrant_broken(self) -> None:
        """CR < 0.8 AND NOT majority_pass -> broken."""
        assert classify_quadrant(cr=0.5, majority_pass=False) == "broken"

    def test_quadrant_custom_threshold(self) -> None:
        """--cr-threshold 0.6 changes classification boundary."""
        # CR=0.7 is below default 0.8 (lucky) but above custom 0.6 (robust)
        assert classify_quadrant(cr=0.7, majority_pass=True) == "lucky"
        assert classify_quadrant(
            cr=0.7, majority_pass=True, cr_threshold=0.6
        ) == "robust"


# ---------------------------------------------------------------------------
# Condition string format test
# ---------------------------------------------------------------------------


class TestConditionString:
    """Tests for condition string formatting."""

    def test_condition_string_format(self) -> None:
        """condition = '{noise_type}_{intervention}' matches expected format."""
        assert build_condition_string("clean", "raw") == "clean_raw"
        assert (
            build_condition_string("type_a_10pct", "pre_proc_sanitize")
            == "type_a_10pct_pre_proc_sanitize"
        )


# ---------------------------------------------------------------------------
# Integration tests using populated_test_db
# ---------------------------------------------------------------------------


class TestDerivedMetricsDB:
    """Integration tests for derived metric computation against a populated DB."""

    def test_derived_metrics_written_to_db(self, populated_test_db: str) -> None:
        """After compute, derived_metrics table has rows with correct values."""
        summary = compute_derived_metrics(populated_test_db)

        conn = sqlite3.connect(populated_test_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM derived_metrics").fetchall()
        conn.close()

        # 3 prompts x 2 noise_types x 1 model = 6 rows
        assert len(rows) == 6

        # Check specific known values
        row_map = {(r["prompt_id"], r["condition"]): dict(r) for r in rows}

        # HumanEval/1 clean_raw: CR=1.0, quadrant=robust, pass_count=5
        he_clean = row_map[("HumanEval/1", "clean_raw")]
        assert abs(he_clean["consistency_rate"] - 1.0) < 1e-9
        assert he_clean["quadrant"] == "robust"
        assert he_clean["pass_count"] == 5
        assert he_clean["majority_pass"] == 1

        # MBPP/1 clean_raw: CR=1.0, quadrant=confidently_wrong, pass_count=0
        mbpp_clean = row_map[("MBPP/1", "clean_raw")]
        assert abs(mbpp_clean["consistency_rate"] - 1.0) < 1e-9
        assert mbpp_clean["quadrant"] == "confidently_wrong"
        assert mbpp_clean["pass_count"] == 0

        # GSM8K/1 clean_raw: CR=0.4, quadrant=broken, pass_count=2
        gsm_clean = row_map[("GSM8K/1", "clean_raw")]
        assert abs(gsm_clean["consistency_rate"] - 0.4) < 1e-9
        assert gsm_clean["quadrant"] == "broken"
        assert gsm_clean["pass_count"] == 2

        # HumanEval/1 type_a_10pct_raw: CR=0.4, quadrant=lucky, pass_count=3
        he_noisy = row_map[("HumanEval/1", "type_a_10pct_raw")]
        assert abs(he_noisy["consistency_rate"] - 0.4) < 1e-9
        assert he_noisy["quadrant"] == "lucky"
        assert he_noisy["pass_count"] == 3

        # GSM8K/1 type_a_10pct_raw: CR=0.6, quadrant=broken, pass_count=1
        gsm_noisy = row_map[("GSM8K/1", "type_a_10pct_raw")]
        assert abs(gsm_noisy["consistency_rate"] - 0.6) < 1e-9
        assert gsm_noisy["quadrant"] == "broken"
        assert gsm_noisy["pass_count"] == 1

    def test_cost_rollup_per_condition(self, populated_test_db: str) -> None:
        """Aggregates total_cost_usd, preproc_cost_usd by (model, noise_type, intervention)."""
        rollups = compute_cost_rollups(populated_test_db)

        # 2 noise types x 1 intervention x 1 model = 2 rollup rows
        assert len(rollups) == 2

        for rollup in rollups:
            assert "model" in rollup
            assert "noise_type" in rollup
            assert "intervention" in rollup
            assert "mean_total_cost_usd" in rollup
            assert "sum_total_cost_usd" in rollup
            assert "mean_preproc_cost_usd" in rollup

            # Each group has 15 runs (3 prompts x 5 reps), each costing 0.001
            assert rollup["n_runs"] == 15
            assert abs(rollup["sum_total_cost_usd"] - 0.015) < 1e-9
            assert abs(rollup["mean_total_cost_usd"] - 0.001) < 1e-9

    def test_quadrant_migration_matrix(self, populated_test_db: str) -> None:
        """clean->noisy transition matrix counts are correct."""
        # First compute derived metrics to populate the table
        compute_derived_metrics(populated_test_db)

        model = "claude-sonnet-4-20250514"
        migration = compute_quadrant_migration(
            populated_test_db,
            model=model,
            from_condition="clean_raw",
            to_condition="type_a_10pct_raw",
        )

        assert migration["n_prompts"] == 3
        tm = migration["transition_matrix"]

        # HumanEval/1: robust -> lucky
        assert tm["robust"]["lucky"] == 1

        # MBPP/1: confidently_wrong -> lucky
        assert tm["confidently_wrong"]["lucky"] == 1

        # GSM8K/1: broken -> broken
        assert tm["broken"]["broken"] == 1
