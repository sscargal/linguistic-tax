---
created: 2026-03-27T03:05:58.859Z
title: "Results management: per-session tracking, list, delete, compare"
area: general
files:
  - src/cli.py
  - src/db.py
  - src/run_experiment.py
  - src/execution_summary.py
---

## Problem

Currently all experiment runs go into a single `results/results.db` with no concept of "sessions" or "runs". Users can't:
- See a list of past experiment sessions with their status
- Delete a partial/failed session to start clean (beyond `propt clean` which deletes everything)
- Compare results across separate experiment sessions
- Know which sessions are complete vs partial vs canceled

When iterating on the experiment (changing models, tweaking noise parameters), old and new results mix in the same database, making it hard to isolate and compare.

## Solution

Introduce per-session result tracking. Key components:

### Schema changes
- Add a `sessions` table: `session_id` (UUID or date-based), `started_at`, `config_snapshot` (JSON), `status` (running/completed/partial/canceled), `total_items`, `completed_items`, `failed_items`
- Add `session_id` foreign key to `experiment_runs`

### New CLI subcommands
- `propt list-results` — show all sessions with status rollup
  - Columns: #, Session ID, Date, Models, Status, Items (done/total), Cost
  - Filter: `--status complete|partial|failed|canceled`
- `propt delete-results` — delete a session by # or ID (with confirmation)
  - Support partial ID matching
  - Warn if session is the only one with data for a model
- `propt compare-results` — diff two sessions (pass rates, costs, timing)

### Execution changes
- Each `propt run` or `propt pilot` creates a new session
- Session ID format: `YYMMDD-HHMM` (human-readable) or UUID
- Results directory: `results/{session_id}/results.db` OR keep single DB with session_id column
- On interruption or quota exhaustion, mark session as `partial` or `canceled`

### Status logic
- `completed`: all items done, zero failures
- `partial`: some items done, some failed or skipped (quota, errors)
- `canceled`: user interrupted (Ctrl-C)
- `running`: session in progress (detect stale sessions)

### Display example
```
# propt list-results
  #  Session      Date        Models                    Status     Items        Cost
---  -----------  ----------  ------------------------  ---------  -----------  ------
  1  260327-0854  2026-03-27  nemotron-super (OR)       partial    40/4100      $0.00
  2  260327-1430  2026-03-27  claude-sonnet, gemini-pro completed  8200/8200    $25.66
  3  260328-0900  2026-03-28  nemotron-super (OR)       completed  4100/4100    $0.00

# propt delete-results 1
Delete session 260327-0854 (partial, 40/4100 items)? (y/N): y
Deleted 40 rows from session 260327-0854.
```

### Considerations
- Backward compatibility: existing `results.db` without session_id should be treated as session "legacy"
- The analysis pipeline needs to filter by session_id (or default to latest complete session)
- `propt report` should accept `--session` to report on a specific session
- Consider whether `results/{session_id}/` directories are better than a single DB with session_id column (single DB is simpler for SQL queries, directories are cleaner for disk management)
