"""SQLite database module for the Linguistic Tax research toolkit.

Provides schema creation, insert, and query helpers for experiment
results storage following the RDD Section 9.2 specification.
"""

import logging
import pathlib
import sqlite3

logger = logging.getLogger(__name__)

CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    noise_type TEXT NOT NULL,
    noise_level TEXT,
    intervention TEXT NOT NULL,
    model TEXT NOT NULL,
    repetition INTEGER NOT NULL,

    -- Prompt data
    prompt_text TEXT,
    prompt_tokens INTEGER,
    optimized_tokens INTEGER,

    -- Response data
    raw_output TEXT,
    cot_trace TEXT,
    completion_tokens INTEGER,

    -- Grading
    pass_fail INTEGER,

    -- Timing
    ttft_ms REAL,
    ttlt_ms REAL,
    generation_ms REAL,

    -- Pre-processor tracking
    preproc_model TEXT,
    preproc_input_tokens INTEGER,
    preproc_output_tokens INTEGER,
    preproc_ttft_ms REAL,
    preproc_ttlt_ms REAL,

    -- Cost tracking
    main_model_input_cost_usd REAL,
    main_model_output_cost_usd REAL,
    preproc_cost_usd REAL,
    total_cost_usd REAL,

    -- Metadata
    temperature REAL DEFAULT 0.0,
    timestamp TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_runs_prompt ON experiment_runs(prompt_id);
CREATE INDEX IF NOT EXISTS idx_runs_condition ON experiment_runs(noise_type, intervention, model);
CREATE INDEX IF NOT EXISTS idx_runs_status ON experiment_runs(status);

CREATE TABLE IF NOT EXISTS derived_metrics (
    prompt_id TEXT NOT NULL,
    condition TEXT NOT NULL,
    model TEXT NOT NULL,
    consistency_rate REAL,
    majority_pass INTEGER,
    pass_count INTEGER,
    quadrant TEXT,
    mean_ttft_ms REAL,
    mean_ttlt_ms REAL,
    mean_total_latency_ms REAL,
    mean_total_cost_usd REAL,
    token_savings INTEGER,
    net_token_cost INTEGER,
    std_latency_ms REAL,
    PRIMARY KEY (prompt_id, condition, model)
);
"""

# Column names for experiment_runs, used by insert_run
_EXPERIMENT_RUNS_COLUMNS = [
    "run_id", "prompt_id", "benchmark", "noise_type", "noise_level",
    "intervention", "model", "repetition", "prompt_text", "prompt_tokens",
    "optimized_tokens", "raw_output", "cot_trace", "completion_tokens",
    "pass_fail", "ttft_ms", "ttlt_ms", "generation_ms", "preproc_model",
    "preproc_input_tokens", "preproc_output_tokens", "preproc_ttft_ms",
    "preproc_ttlt_ms", "main_model_input_cost_usd", "main_model_output_cost_usd",
    "preproc_cost_usd", "total_cost_usd", "temperature", "timestamp", "status",
]


def init_database(db_path: str) -> sqlite3.Connection:
    """Create the results database with the full RDD schema.

    Creates parent directories if needed, executes the schema DDL,
    and enables WAL journal mode for better concurrent read performance.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        An open sqlite3.Connection with WAL mode enabled.
    """
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(CREATE_SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    logger.info("Database initialized at %s", db_path)
    return conn


def insert_run(conn: sqlite3.Connection, run_data: dict) -> None:
    """Insert a single experiment run into the database.

    Uses parameterized queries to prevent SQL injection.
    Only inserts columns present in run_data; others get defaults.

    Args:
        conn: An open database connection.
        run_data: Dictionary with column names as keys.

    Raises:
        sqlite3.IntegrityError: If run_id already exists.
    """
    columns = [c for c in _EXPERIMENT_RUNS_COLUMNS if c in run_data]
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    values = [run_data[c] for c in columns]

    conn.execute(
        f"INSERT INTO experiment_runs ({col_names}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    logger.debug("Inserted run %s", run_data.get("run_id", "unknown"))


def query_runs(conn: sqlite3.Connection, **filters: object) -> list[dict]:
    """Query experiment runs with optional filters.

    Builds a WHERE clause from keyword arguments. Each keyword
    corresponds to a column name in experiment_runs.

    Args:
        conn: An open database connection.
        **filters: Column name/value pairs for filtering.

    Returns:
        List of matching rows as dictionaries. Empty list if no matches.
    """
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM experiment_runs"
    params: list[object] = []

    if filters:
        clauses = []
        for col, val in filters.items():
            clauses.append(f"{col} = ?")
            params.append(val)
        query += " WHERE " + " AND ".join(clauses)

    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
