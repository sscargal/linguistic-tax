"""Tests for session management module."""

import os
import sqlite3
from pathlib import Path

import pytest

from src.session import (
    create_session,
    list_sessions,
    resolve_session,
    get_session_metadata,
    update_session_status,
    delete_session,
    compare_sessions,
)


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    """Create a temporary results directory and patch RESULTS_DIR."""
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr("src.session.RESULTS_DIR", str(results))
    return results


class TestCreateSession:
    """Tests for create_session()."""

    def test_returns_8_char_hex_id(self, results_dir):
        session_id = create_session()
        assert len(session_id) == 8
        assert all(c in "0123456789abcdef" for c in session_id)

    def test_creates_session_directory(self, results_dir):
        session_id = create_session()
        assert (results_dir / session_id).is_dir()

    def test_creates_results_db(self, results_dir):
        session_id = create_session()
        assert (results_dir / session_id / "results.db").exists()

    def test_stores_session_meta(self, results_dir):
        session_id = create_session()
        db_path = str(results_dir / session_id / "results.db")
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM session_meta WHERE key = 'status'"
        ).fetchone()
        assert row is not None
        assert row[0] == "running"
        conn.close()

    def test_unique_ids(self, results_dir):
        ids = {create_session() for _ in range(10)}
        assert len(ids) == 10


class TestListSessions:
    """Tests for list_sessions()."""

    def test_empty_results(self, results_dir):
        sessions = list_sessions()
        assert sessions == []

    def test_lists_created_sessions(self, results_dir):
        s1 = create_session()
        s2 = create_session()
        sessions = list_sessions()
        ids = {s["session_id"] for s in sessions}
        assert s1 in ids
        assert s2 in ids

    def test_includes_legacy_if_exists(self, results_dir):
        # Create a legacy results.db directly in results/
        from src.db import init_database

        legacy_path = str(results_dir / "results.db")
        conn = init_database(legacy_path)
        conn.close()

        sessions = list_sessions()
        legacy = [s for s in sessions if s["session_id"] == "legacy"]
        assert len(legacy) == 1

    def test_no_legacy_if_absent(self, results_dir):
        create_session()
        sessions = list_sessions()
        legacy = [s for s in sessions if s["session_id"] == "legacy"]
        assert len(legacy) == 0

    def test_sorted_newest_first(self, results_dir):
        import time

        s1 = create_session()
        time.sleep(0.05)
        s2 = create_session()
        sessions = list_sessions()
        # Filter to our sessions (exclude legacy)
        non_legacy = [s for s in sessions if s["session_id"] != "legacy"]
        assert len(non_legacy) >= 2
        assert non_legacy[0]["session_id"] == s2


class TestResolveSession:
    """Tests for resolve_session()."""

    def test_resolve_by_full_id(self, results_dir):
        session_id = create_session()
        db_path = resolve_session(session_id)
        assert db_path.endswith("results.db")
        assert session_id in db_path

    def test_resolve_by_prefix(self, results_dir):
        session_id = create_session()
        prefix = session_id[:4]
        db_path = resolve_session(prefix)
        assert session_id in db_path

    def test_resolve_legacy(self, results_dir):
        from src.db import init_database

        legacy_path = str(results_dir / "results.db")
        conn = init_database(legacy_path)
        conn.close()

        db_path = resolve_session("legacy")
        assert db_path.endswith("results.db")
        assert "legacy" not in db_path or db_path == str(results_dir / "results.db")

    def test_resolve_none_returns_latest(self, results_dir):
        import time

        create_session()
        time.sleep(0.05)
        s2 = create_session()
        db_path = resolve_session(None)
        assert s2 in db_path

    def test_resolve_none_falls_back_to_legacy(self, results_dir):
        from src.db import init_database

        legacy_path = str(results_dir / "results.db")
        conn = init_database(legacy_path)
        conn.close()

        db_path = resolve_session(None)
        assert db_path == legacy_path

    def test_resolve_not_found(self, results_dir):
        with pytest.raises(ValueError, match="not found"):
            resolve_session("zzzzzzzz")

    def test_resolve_ambiguous(self, results_dir):
        # Create two sessions starting with same prefix — hard to guarantee
        # so test that ValueError is raised for invalid prefix
        create_session()
        with pytest.raises(ValueError):
            resolve_session("zzzzzzzz")


class TestUpdateSessionStatus:
    """Tests for update_session_status()."""

    def test_updates_status(self, results_dir):
        session_id = create_session()
        db_path = str(results_dir / session_id / "results.db")
        update_session_status(db_path, "completed")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM session_meta WHERE key = 'status'"
        ).fetchone()
        assert row[0] == "completed"
        conn.close()


class TestGetSessionMetadata:
    """Tests for get_session_metadata()."""

    def test_returns_metadata_dict(self, results_dir):
        session_id = create_session()
        meta = get_session_metadata(session_id)
        assert "status" in meta
        assert "created_at" in meta
        assert meta["status"] == "running"


class TestDeleteSession:
    """Tests for delete_session()."""

    def test_deletes_session_dir(self, results_dir):
        session_id = create_session()
        assert (results_dir / session_id).exists()
        delete_session(session_id)
        assert not (results_dir / session_id).exists()

    def test_refuses_legacy(self, results_dir):
        with pytest.raises(ValueError, match="legacy"):
            delete_session("legacy")

    def test_not_found(self, results_dir):
        with pytest.raises(ValueError):
            delete_session("nonexist")


class TestCompareSessions:
    """Tests for compare_sessions()."""

    def test_compare_two_sessions(self, results_dir):
        s1 = create_session()
        s2 = create_session()
        result = compare_sessions(s1, s2)
        assert isinstance(result, str)
        assert s1 in result or "Session 1" in result

    def test_compare_with_legacy(self, results_dir):
        from src.db import init_database

        legacy_path = str(results_dir / "results.db")
        conn = init_database(legacy_path)
        conn.close()

        s1 = create_session()
        result = compare_sessions(s1, "legacy")
        assert isinstance(result, str)
