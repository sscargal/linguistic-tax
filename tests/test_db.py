"""Tests for the SQLite database module."""

import sqlite3
import uuid

import pytest

from src.db import init_database, insert_run, query_runs


class TestInitDatabase:
    """Tests for database initialization."""

    def test_creates_sqlite_file(self, tmp_db_path):
        """init_database creates a SQLite file at the given path."""
        import os
        conn = init_database(tmp_db_path)
        conn.close()
        assert os.path.exists(tmp_db_path)

    def test_experiment_runs_table_exists(self, tmp_db_path):
        """experiment_runs table is created with expected columns."""
        conn = init_database(tmp_db_path)
        cursor = conn.execute("PRAGMA table_info(experiment_runs)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "run_id", "prompt_id", "benchmark", "noise_type", "noise_level",
            "intervention", "model", "repetition", "prompt_text", "prompt_tokens",
            "optimized_tokens", "raw_output", "cot_trace", "completion_tokens",
            "pass_fail", "ttft_ms", "ttlt_ms", "generation_ms", "preproc_model",
            "preproc_input_tokens", "preproc_output_tokens", "preproc_ttft_ms",
            "preproc_ttlt_ms", "main_model_input_cost_usd", "main_model_output_cost_usd",
            "preproc_cost_usd", "total_cost_usd", "temperature", "timestamp", "status",
        }
        assert expected_columns.issubset(columns)
        conn.close()

    def test_derived_metrics_table_exists(self, tmp_db_path):
        """derived_metrics table is created with expected columns."""
        conn = init_database(tmp_db_path)
        cursor = conn.execute("PRAGMA table_info(derived_metrics)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "prompt_id", "condition", "model", "consistency_rate", "majority_pass",
            "pass_count", "quadrant", "mean_ttft_ms", "mean_ttlt_ms",
            "mean_total_latency_ms", "mean_total_cost_usd", "token_savings",
            "net_token_cost", "std_latency_ms",
        }
        assert expected_columns.issubset(columns)
        conn.close()

    def test_indexes_exist(self, tmp_db_path):
        """Required indexes are created."""
        conn = init_database(tmp_db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = {row[0] for row in cursor.fetchall()}
        assert "idx_runs_prompt" in index_names
        assert "idx_runs_condition" in index_names
        assert "idx_runs_status" in index_names
        conn.close()

    def test_wal_journal_mode(self, tmp_db_path):
        """WAL journal mode is enabled after init."""
        conn = init_database(tmp_db_path)
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_idempotent(self, tmp_db_path):
        """Calling init_database twice does not raise an error."""
        conn1 = init_database(tmp_db_path)
        conn1.close()
        conn2 = init_database(tmp_db_path)
        conn2.close()


def _make_run_data(run_id: str | None = None) -> dict:
    """Create a minimal valid run data dict for testing."""
    return {
        "run_id": run_id or str(uuid.uuid4()),
        "prompt_id": "humaneval_042",
        "benchmark": "humaneval",
        "noise_type": "type_a_10pct",
        "noise_level": "10",
        "intervention": "raw",
        "model": "claude-sonnet-4-20250514",
        "repetition": 1,
        "prompt_text": "def is_prime(n):",
        "prompt_tokens": 50,
        "status": "complete",
    }


class TestInsertRun:
    """Tests for inserting experiment runs."""

    def test_insert_and_query_back(self, tmp_db_path):
        """insert_run inserts a row that can be queried back."""
        conn = init_database(tmp_db_path)
        run_data = _make_run_data()
        insert_run(conn, run_data)

        cursor = conn.execute(
            "SELECT * FROM experiment_runs WHERE run_id = ?",
            (run_data["run_id"],),
        )
        row = cursor.fetchone()
        assert row is not None
        conn.close()

    def test_duplicate_run_id_raises(self, tmp_db_path):
        """Inserting a duplicate run_id raises IntegrityError."""
        conn = init_database(tmp_db_path)
        run_data = _make_run_data(run_id="duplicate-id")
        insert_run(conn, run_data)

        with pytest.raises(sqlite3.IntegrityError):
            insert_run(conn, run_data)
        conn.close()


class TestQueryRuns:
    """Tests for querying experiment runs."""

    def test_query_with_filters(self, tmp_db_path):
        """query_runs with filters returns only matching rows."""
        conn = init_database(tmp_db_path)

        run1 = _make_run_data()
        run1["prompt_id"] = "humaneval_001"
        insert_run(conn, run1)

        run2 = _make_run_data()
        run2["prompt_id"] = "humaneval_002"
        insert_run(conn, run2)

        results = query_runs(conn, prompt_id="humaneval_001")
        assert len(results) == 1
        assert results[0]["prompt_id"] == "humaneval_001"
        conn.close()

    def test_query_no_matches(self, tmp_db_path):
        """query_runs returns empty list when no rows match."""
        conn = init_database(tmp_db_path)
        results = query_runs(conn, prompt_id="nonexistent")
        assert results == []
        conn.close()

    def test_query_returns_dicts(self, tmp_db_path):
        """query_runs returns list of dicts."""
        conn = init_database(tmp_db_path)
        run_data = _make_run_data()
        insert_run(conn, run_data)

        results = query_runs(conn, prompt_id=run_data["prompt_id"])
        assert isinstance(results, list)
        assert isinstance(results[0], dict)
        conn.close()
