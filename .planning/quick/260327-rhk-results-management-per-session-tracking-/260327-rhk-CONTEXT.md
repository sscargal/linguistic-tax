# Quick Task 260327-rhk: Results management — per-session tracking, list, delete, compare - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Task Boundary

Add per-session result tracking to the experiment pipeline. Each `propt run` or `propt pilot` creates a new session with its own results DB. New CLI subcommands: `propt list` (sessions), `propt list-runs` (runs within a session), `propt delete-results` (delete session), `propt compare-results` (diff two sessions). Track session status (running/completed/partial/canceled). Backward compat: existing `results/results.db` treated as session "legacy".

</domain>

<decisions>
## Implementation Decisions

### Storage Model
- **Separate DB per session.** Each session gets its own `results/{session_id}/results.db`. Clean isolation, easy delete (`rm -rf` the directory). Cross-session queries handled by loading multiple DBs or using ATTACH when needed (compare command).

### Session ID Format
- **Short hash (8 chars).** E.g., `a3f7c2e1`. Compact for CLI use. Generated from UUID or timestamp hash. Users rely on `propt list` to see dates/details.

### Run Listing Scope
- **Two-level navigation.** `propt list` shows sessions (session_id, date, models, status, item counts, cost). `propt list-runs <session>` shows individual runs within a session with filters (`--model`, `--benchmark`, `--intervention`, `--failed`). This keeps the top-level list clean and gives users a path to find run_ids for `propt inspect`.

### Claude's Discretion
- Session metadata storage format (JSON file vs SQLite table within session DB)
- `propt compare-results` output format and metrics
- How `propt report` and `propt inspect` integrate with sessions (default to latest? require `--session`?)
- Ctrl-C / interruption handling for marking sessions as canceled

</decisions>

<specifics>
## Specific Ideas

- `propt list` columns: #, Session ID, Date, Models, Status, Items (done/total), Cost
- `propt list-runs <session>` columns: Run ID, Prompt, Benchmark, Noise, Intervention, Model, Pass/Fail
- `propt delete-results <session>` with confirmation prompt
- `propt report` defaults to latest completed session, `--session <id>` for specific
- `propt inspect` auto-detects which session a run_id belongs to
- Session directory: `results/{session_id}/` containing `results.db` + optional `execution_plan.json`

</specifics>

<canonical_refs>
## Canonical References

- RDD Section 9.2: Database schema specification
- Existing todo: `.planning/todos/pending/2026-03-27-results-management-per-session-tracking-list-delete-compare.md`

</canonical_refs>
