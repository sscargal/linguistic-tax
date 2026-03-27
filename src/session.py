"""Session management module for the Linguistic Tax research toolkit.

Provides per-session result isolation so each experiment run gets its own
directory and database. Supports listing, resolving, deleting, and
comparing sessions, with backward compatibility for legacy results.db.
"""

import logging
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Base directory for all results (overridable for testing)
RESULTS_DIR: str = "results"

# SQL for session metadata key-value table
_SESSION_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _ensure_session_meta(conn: sqlite3.Connection) -> None:
    """Create session_meta table if it doesn't exist.

    Args:
        conn: An open SQLite database connection.
    """
    conn.executescript(_SESSION_META_SCHEMA)


def create_session(description: str = "") -> str:
    """Create a new session with its own results directory and database.

    Generates an 8-character hex session ID, creates the directory
    results/{session_id}/, initializes a results.db inside it with
    the session_meta table, and stores initial metadata.

    Args:
        description: Optional description for the session.

    Returns:
        The 8-character hex session ID.
    """
    from src.db import init_database

    session_id = uuid.uuid4().hex[:8]
    session_dir = Path(RESULTS_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    db_path = str(session_dir / "results.db")
    conn = init_database(db_path)

    _ensure_session_meta(conn)

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?, ?)",
        ("created_at", now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?, ?)",
        ("status", "running"),
    )
    conn.execute(
        "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?, ?)",
        ("session_id", session_id),
    )
    if description:
        conn.execute(
            "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?, ?)",
            ("description", description),
        )
    conn.commit()
    conn.close()

    logger.info("Created session %s at %s", session_id, session_dir)
    return session_id


def _get_session_dirs() -> list[Path]:
    """Return all session directories (directories containing results.db).

    Returns:
        List of Path objects for session directories, sorted by name.
    """
    results = Path(RESULTS_DIR)
    if not results.exists():
        return []

    dirs = []
    for d in results.iterdir():
        if d.is_dir() and (d / "results.db").exists():
            dirs.append(d)

    return sorted(dirs, key=lambda p: p.name)


def list_sessions() -> list[dict[str, Any]]:
    """List all sessions with metadata, sorted newest first.

    Scans results/ for session directories. Also checks for a legacy
    results/results.db (not inside a session directory).

    Returns:
        List of session metadata dicts with keys: session_id, created_at,
        status, models, item_count, cost, db_path.
    """
    sessions: list[dict[str, Any]] = []

    for session_dir in _get_session_dirs():
        db_path = str(session_dir / "results.db")
        try:
            meta = _read_session_info(db_path, session_dir.name)
            sessions.append(meta)
        except Exception:
            logger.warning("Could not read session %s", session_dir.name)

    # Check for legacy results.db
    legacy_path = Path(RESULTS_DIR) / "results.db"
    if legacy_path.exists():
        try:
            meta = _read_session_info(str(legacy_path), "legacy")
            sessions.append(meta)
        except Exception:
            logger.warning("Could not read legacy results.db")

    # Sort by created_at descending (newest first)
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)

    return sessions


def _read_session_info(db_path: str, session_id: str) -> dict[str, Any]:
    """Read session info from a database file.

    Args:
        db_path: Path to the SQLite database.
        session_id: The session identifier.

    Returns:
        Dict with session metadata.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Read session_meta if it exists
    created_at = ""
    status = "unknown"
    try:
        rows = conn.execute("SELECT key, value FROM session_meta").fetchall()
        meta_map = {r["key"]: r["value"] for r in rows}
        created_at = meta_map.get("created_at", "")
        status = meta_map.get("status", "unknown")
    except sqlite3.OperationalError:
        # No session_meta table (legacy DB)
        pass

    # Aggregate stats from experiment_runs
    item_count = 0
    cost = 0.0
    models: list[str] = []
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(total_cost_usd), 0) as cost "
            "FROM experiment_runs WHERE status = 'completed'"
        ).fetchone()
        item_count = row["cnt"]
        cost = row["cost"]

        model_rows = conn.execute(
            "SELECT DISTINCT model FROM experiment_runs"
        ).fetchall()
        models = sorted(r["model"] for r in model_rows)
    except sqlite3.OperationalError:
        pass

    conn.close()

    return {
        "session_id": session_id,
        "created_at": created_at,
        "status": status,
        "models": models,
        "item_count": item_count,
        "cost": cost,
        "db_path": db_path,
    }


def resolve_session(session_id: str | None) -> str:
    """Resolve a session identifier to a database path.

    Supports full IDs, prefix matching, "legacy", and None (latest session).

    Args:
        session_id: Full or partial session ID, "legacy", or None for latest.

    Returns:
        Path to the session's results.db.

    Raises:
        ValueError: If session not found or prefix is ambiguous.
    """
    results = Path(RESULTS_DIR)

    if session_id is None:
        # Return most recent session
        sessions = list_sessions()
        non_legacy = [s for s in sessions if s["session_id"] != "legacy"]
        if non_legacy:
            return non_legacy[0]["db_path"]
        # Fall back to legacy
        legacy_path = str(results / "results.db")
        if Path(legacy_path).exists():
            return legacy_path
        raise ValueError("No sessions found")

    if session_id == "legacy":
        legacy_path = str(results / "results.db")
        if Path(legacy_path).exists():
            return legacy_path
        raise ValueError("Legacy results.db not found")

    # Try exact match first
    exact_dir = results / session_id
    if exact_dir.is_dir() and (exact_dir / "results.db").exists():
        return str(exact_dir / "results.db")

    # Try prefix match
    matches = []
    for d in _get_session_dirs():
        if d.name.startswith(session_id):
            matches.append(d)

    if len(matches) == 1:
        return str(matches[0] / "results.db")
    elif len(matches) > 1:
        ids = ", ".join(m.name for m in matches)
        raise ValueError(
            f"Ambiguous session prefix '{session_id}' matches: {ids}"
        )
    else:
        raise ValueError(f"Session '{session_id}' not found")


def get_session_metadata(session_id: str) -> dict[str, str]:
    """Read metadata from a session's database.

    Args:
        session_id: The session identifier.

    Returns:
        Dict of key-value metadata pairs.

    Raises:
        ValueError: If session not found.
    """
    db_path = resolve_session(session_id)
    conn = sqlite3.connect(db_path)

    try:
        rows = conn.execute("SELECT key, value FROM session_meta").fetchall()
        return {row[0]: row[1] for row in rows}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def update_session_status(db_path: str, status: str) -> None:
    """Update the status in a session's metadata.

    Args:
        db_path: Path to the session's results.db.
        status: New status (running/completed/partial/canceled).
    """
    conn = sqlite3.connect(db_path)
    _ensure_session_meta(conn)
    conn.execute(
        "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?, ?)",
        ("status", status),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str) -> None:
    """Delete a session's directory and all its data.

    Args:
        session_id: The session identifier. Cannot be "legacy".

    Raises:
        ValueError: If session_id is "legacy" or session not found.
    """
    if session_id == "legacy":
        raise ValueError(
            "Cannot delete the legacy session. Use `propt clean` instead."
        )

    results = Path(RESULTS_DIR)
    session_dir = results / session_id

    if not session_dir.exists():
        # Try prefix match
        matches = [d for d in _get_session_dirs() if d.name.startswith(session_id)]
        if len(matches) == 1:
            session_dir = matches[0]
        elif len(matches) > 1:
            ids = ", ".join(m.name for m in matches)
            raise ValueError(f"Ambiguous prefix '{session_id}' matches: {ids}")
        else:
            raise ValueError(f"Session '{session_id}' not found")

    shutil.rmtree(session_dir)
    logger.info("Deleted session %s", session_id)


def compare_sessions(id1: str, id2: str) -> str:
    """Compare two sessions side by side.

    Resolves both session IDs, queries per-model pass rates, costs,
    and timing from each, and formats as a comparison table.

    Args:
        id1: First session identifier.
        id2: Second session identifier.

    Returns:
        Formatted comparison string.
    """
    from tabulate import tabulate

    db1 = resolve_session(id1)
    db2 = resolve_session(id2)

    def _query_stats(db_path: str) -> dict[str, Any]:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        overall = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed,
                COALESCE(SUM(total_cost_usd), 0) as cost,
                AVG(ttlt_ms) as avg_ttlt
            FROM experiment_runs WHERE status='completed'
        """).fetchone()

        models_rows = conn.execute("""
            SELECT
                model,
                COUNT(*) as total,
                SUM(CASE WHEN pass_fail=1 THEN 1 ELSE 0 END) as passed,
                COALESCE(SUM(total_cost_usd), 0) as cost,
                AVG(ttlt_ms) as avg_ttlt
            FROM experiment_runs WHERE status='completed'
            GROUP BY model ORDER BY model
        """).fetchall()

        conn.close()

        return {
            "total": overall["total"],
            "passed": overall["passed"],
            "cost": overall["cost"],
            "avg_ttlt": overall["avg_ttlt"],
            "models": [dict(r) for r in models_rows],
        }

    s1_stats = _query_stats(db1)
    s2_stats = _query_stats(db2)

    lines: list[str] = []
    lines.append(f"=== Session Comparison ===")
    lines.append(f"")
    lines.append(f"  Session 1: {id1}")
    lines.append(f"  Session 2: {id2}")
    lines.append(f"")

    # Overall comparison
    s1_rate = (s1_stats["passed"] / s1_stats["total"] * 100) if s1_stats["total"] > 0 else 0
    s2_rate = (s2_stats["passed"] / s2_stats["total"] * 100) if s2_stats["total"] > 0 else 0

    overall_table = [
        ["Items", s1_stats["total"], s2_stats["total"]],
        ["Pass Rate", f"{s1_rate:.1f}%", f"{s2_rate:.1f}%"],
        ["Cost", f"${s1_stats['cost']:.4f}", f"${s2_stats['cost']:.4f}"],
        [
            "Avg TTLT",
            f"{s1_stats['avg_ttlt']:.0f}ms" if s1_stats["avg_ttlt"] else "--",
            f"{s2_stats['avg_ttlt']:.0f}ms" if s2_stats["avg_ttlt"] else "--",
        ],
    ]
    lines.append(tabulate(
        overall_table,
        headers=["Metric", f"Session 1", f"Session 2"],
        tablefmt="simple",
    ))
    lines.append("")

    # Per-model comparison
    all_models = sorted(set(
        [m["model"] for m in s1_stats["models"]] +
        [m["model"] for m in s2_stats["models"]]
    ))

    if all_models:
        s1_by_model = {m["model"]: m for m in s1_stats["models"]}
        s2_by_model = {m["model"]: m for m in s2_stats["models"]}

        model_table = []
        for model in all_models:
            m1 = s1_by_model.get(model, {})
            m2 = s2_by_model.get(model, {})

            r1 = (m1["passed"] / m1["total"] * 100) if m1.get("total", 0) > 0 else 0
            r2 = (m2["passed"] / m2["total"] * 100) if m2.get("total", 0) > 0 else 0

            model_table.append([
                model,
                f"{r1:.1f}%" if m1 else "--",
                f"{r2:.1f}%" if m2 else "--",
                f"${m1.get('cost', 0):.4f}" if m1 else "--",
                f"${m2.get('cost', 0):.4f}" if m2 else "--",
            ])

        lines.append("Per-Model:")
        lines.append(tabulate(
            model_table,
            headers=["Model", "S1 Pass", "S2 Pass", "S1 Cost", "S2 Cost"],
            tablefmt="simple",
        ))

    return "\n".join(lines)
