---
phase: 260327-rhk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/session.py
  - src/db.py
  - src/cli.py
  - src/run_experiment.py
  - src/pilot.py
  - src/execution_summary.py
  - tests/test_session.py
autonomous: true
requirements: [results-management]
must_haves:
  truths:
    - "Each propt run/pilot creates a new session directory under results/{session_id}/"
    - "propt list shows all sessions with date, models, status, item counts, cost"
    - "propt list-runs <session> shows individual runs within a session"
    - "propt delete-results <session> removes the session directory after confirmation"
    - "propt compare-results <s1> <s2> shows side-by-side metrics for two sessions"
    - "Existing results/results.db is accessible as session 'legacy'"
    - "propt report and propt inspect default to latest session, accept --session"
  artifacts:
    - path: "src/session.py"
      provides: "Session management: create, list, resolve, metadata"
    - path: "tests/test_session.py"
      provides: "Unit tests for session lifecycle"
  key_links:
    - from: "src/run_experiment.py"
      to: "src/session.py"
      via: "create_session() at start of run_engine"
      pattern: "create_session"
    - from: "src/cli.py"
      to: "src/session.py"
      via: "list/delete/compare subcommand handlers"
      pattern: "handle_list|handle_list_runs|handle_delete_results|handle_compare_results"
---

<objective>
Add per-session result tracking so each experiment run gets its own isolated directory and database, with CLI commands to list, inspect, delete, and compare sessions.

Purpose: Currently all results go into a single results/results.db which makes it impossible to compare across experiment runs, selectively delete old runs, or track session-level metadata (status, timestamps). This adds proper session management.

Output: New src/session.py module, updated CLI with 4 new subcommands, run_engine/pilot wired to auto-create sessions, backward compat for existing results.db as "legacy" session.
</objective>

<execution_context>
@/home/steve/linguistic-tax/.claude/get-shit-done/workflows/execute-plan.md
@/home/steve/linguistic-tax/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/cli.py
@src/db.py
@src/run_experiment.py
@src/pilot.py
@src/execution_summary.py
@src/config.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create session management module with tests</name>
  <files>src/session.py, tests/test_session.py</files>
  <behavior>
    - create_session() returns an 8-char hex session ID and creates results/{session_id}/ directory
    - list_sessions() returns list of session metadata dicts sorted by date (newest first), each with session_id, created_at, status, models, item_count, cost, db_path
    - list_sessions() includes a "legacy" entry if results/results.db exists (not inside a session dir)
    - resolve_session(session_id) returns the db_path for a session; supports prefix matching (e.g., "a3f7" matches "a3f7c2e1"); raises ValueError if ambiguous or not found
    - resolve_session("legacy") returns "results/results.db"
    - resolve_session(None) returns the most recent session's db_path (or "legacy" if no sessions exist)
    - get_session_metadata(session_id) reads metadata from the session's DB
    - update_session_status(session_id, status) updates status in session metadata (running/completed/partial/canceled)
    - delete_session(session_id) removes results/{session_id}/ directory entirely; raises ValueError for "legacy"
    - compare_sessions(s1, s2) returns a comparison dict with per-model pass rates, costs, timing for each session
  </behavior>
  <action>
Create src/session.py with:

1. **Session ID generation**: `create_session() -> str` generates 8-char hex ID from `uuid.uuid4().hex[:8]`. Creates `results/{session_id}/` directory. Stores a `session_meta` table in the session's `results.db` with columns: session_id, created_at (ISO timestamp), status (default "running"), description (optional). Returns the session_id.

2. **Session metadata table**: Add a `CREATE TABLE IF NOT EXISTS session_meta` to db.py's schema (or have session.py create it separately in the session DB). Columns: key TEXT PRIMARY KEY, value TEXT. Store created_at, status, description as key-value pairs. This is simpler than a structured table and easy to extend.

3. **list_sessions() -> list[dict]**: Scan `results/` for directories containing `results.db`. For each, open the DB, read session_meta for created_at/status, query experiment_runs for aggregate stats (COUNT, SUM(total_cost_usd), distinct models). Also check if `results/results.db` exists (the legacy flat file) and include it as session_id="legacy" with metadata derived from querying that DB.

4. **resolve_session(session_id: str | None) -> str**: If None, return most recent session's db_path. If "legacy", return "results/results.db". Otherwise, find matching session dir by prefix. Raise ValueError if 0 or 2+ matches.

5. **update_session_status(db_path: str, status: str)**: INSERT OR REPLACE into session_meta.

6. **delete_session(session_id: str)**: Refuse "legacy" with clear message. Otherwise `shutil.rmtree(results/{session_id})`.

7. **compare_sessions(id1: str, id2: str) -> str**: Resolve both sessions, open both DBs, query per-model pass rates / costs / timing from each, format as side-by-side tabulate table. Show total items, pass rate, cost, avg TTLT for each model in each session.

Create tests/test_session.py with tests for all the above behaviors using tmp_path for isolation. Mock the results directory.
  </action>
  <verify>
    <automated>cd /home/steve/linguistic-tax && python -m pytest tests/test_session.py -x -v</automated>
  </verify>
  <done>All session module tests pass. create/list/resolve/delete/compare all work correctly. Legacy detection works.</done>
</task>

<task type="auto">
  <name>Task 2: Wire sessions into run_engine, pilot, and CLI</name>
  <files>src/run_experiment.py, src/pilot.py, src/cli.py, src/execution_summary.py</files>
  <action>
**run_experiment.py changes:**
1. At the top of `run_engine()`, if `args.db` is not specified (user didn't override), call `create_session()` to get a new session_id. Set `db_path = f"results/{session_id}/results.db"`. Print the session ID: `print(f"Session: {session_id}")`.
2. After the processing loop completes normally, call `update_session_status(db_path, "completed")`.
3. In the KeyboardInterrupt handler, call `update_session_status(db_path, "canceled")`.
4. If some items failed but others completed, set status to "partial" (check failed_count > 0).
5. Save execution_plan.json inside the session directory: `results/{session_id}/execution_plan.json`.

**pilot.py changes:**
1. Same session creation pattern in `run_pilot()` when db_path is not overridden.
2. Save pilot_plan.json inside session directory.
3. Update status on completion/interruption.

**execution_summary.py changes:**
1. `save_execution_plan()` — change default output_path parameter or pass session-aware path from callers.

**cli.py changes:**
1. Add `--session` argument to `report`, `inspect`, `regrade`, `clean` subcommands. When provided, resolve the session and use its db_path instead of the default.
2. For `report` and `inspect`, if no `--session` and no `--db`, default to latest session via `resolve_session(None)`.

3. Add 4 new subcommands:

   **`propt list`** (handle_list): Call `list_sessions()`, format as table with columns: #, Session ID, Date, Models, Status, Items, Cost. Use tabulate.

   **`propt list-runs <session>`** (handle_list_runs): Resolve session, open DB, query experiment_runs. Show table: Run ID (truncated), Prompt, Benchmark, Noise, Intervention, Model, Pass/Fail. Support filters: `--model`, `--benchmark`, `--intervention`, `--failed`.

   **`propt delete-results <session>`** (handle_delete_results): Resolve session, show what will be deleted (session dir size), confirm, call `delete_session()`. Support `--yes` to skip confirmation.

   **`propt compare-results <session1> <session2>`** (handle_compare_results): Resolve both sessions, call `compare_sessions()`, print formatted output.

4. Update `handle_clean` to be session-aware: if `--session` provided, delete that session. If no session specified, clean the legacy DB (backward compat).

Note: The existing `--db` flag on run/pilot should still work and bypass session creation entirely (for backward compat and testing).
  </action>
  <verify>
    <automated>cd /home/steve/linguistic-tax && python -m pytest tests/test_session.py tests/test_cli.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    - `propt run` creates a new session and prints the session ID
    - `propt list` shows all sessions including legacy
    - `propt list-runs <session>` shows runs with filters
    - `propt delete-results <session>` deletes with confirmation
    - `propt compare-results <s1> <s2>` shows side-by-side comparison
    - `propt report` defaults to latest session
    - `propt inspect` auto-detects which session a run_id belongs to
    - Existing --db flag bypasses session system entirely
    - All existing tests still pass
  </done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/ -x -v` — all tests pass
2. `python -m propt list` — shows legacy session if results/results.db exists
3. `python -m propt run --dry-run` — shows session ID in output
</verification>

<success_criteria>
- Session isolation: each run gets its own DB in results/{session_id}/
- Session lifecycle: running -> completed/partial/canceled
- CLI navigation: list -> list-runs -> inspect flow works
- Backward compat: existing results.db accessible as "legacy"
- All existing tests pass without modification
</success_criteria>

<output>
After completion, create `.planning/quick/260327-rhk-results-management-per-session-tracking-/260327-rhk-SUMMARY.md`
</output>
