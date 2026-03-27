---
phase: quick
plan: 260327-r3e
subsystem: preproc-pipeline
tags: [preproc, debugging, cli, token-optimization]
dependency_graph:
  requires: []
  provides: [preproc-raw-output-storage, inspect-command, fallback-rate-reporting]
  affects: [prompt_compressor, db, run_experiment, cli, execution_summary]
tech_stack:
  added: []
  patterns: [db-migration-via-alter-table]
key_files:
  created: []
  modified:
    - src/prompt_compressor.py
    - src/db.py
    - src/run_experiment.py
    - src/cli.py
    - src/execution_summary.py
    - tests/test_prompt_compressor.py
    - tests/test_db.py
decisions:
  - max_tokens capped at max(256, int(len*1.3)) to constrain chatty preproc output
  - preproc_raw_output captured before fallback logic to always store what model returned
  - ALTER TABLE migration for backward compatibility with existing databases
  - Fallback rate shown only when preproc_raw_output data exists to avoid confusing old-data output
metrics:
  duration: 3min
  completed: 2026-03-27
  tasks_completed: 2
  tasks_total: 2
---

# Quick Task 260327-r3e: Inspect Pre-processor Output and Fix Chatty Responses Summary

Tightened sanitization prompts with explicit "Output ONLY" constraints, reduced max_tokens from max(512, len*2) to max(256, int(len*1.3)), added DB storage of raw preproc output with migration support, inspect CLI command, and fallback rate reporting.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Tighten preproc prompts, reduce max_tokens, store raw output | 139c2b2 | prompt_compressor.py, db.py, run_experiment.py, tests |
| 2 | Add inspect command and fallback rate to report | 0f09d36 | cli.py, execution_summary.py |

## Key Changes

### Prompt Tightening (prompt_compressor.py)
- `_SANITIZE_INSTRUCTION` now includes "Do not explain. Do not add commentary. Output ONLY the corrected text, nothing else."
- `_COMPRESS_INSTRUCTION` similarly tightened
- `max_tokens` reduced from `max(512, len(text) * 2)` to `max(256, int(len(text) * 1.3))` for both sanitize and sanitize_and_compress
- `preproc_raw_output` added to metadata dict before fallback check (always captured)

### DB Schema (db.py)
- `preproc_raw_output TEXT` column added to CREATE_SCHEMA
- Column added to `_EXPERIMENT_RUNS_COLUMNS` whitelist
- Migration via `ALTER TABLE` in `init_database()` for existing databases

### Inspect Command (cli.py)
- `propt inspect {run_id}` shows complete run details across 7 sections: Run Info, Prompt, Pre-processor, Pre-processor Output, Model Response, Grading, Timing, Cost
- Detects fallback triggers and labels them explicitly
- Long outputs truncated at 2000 chars

### Fallback Rate (execution_summary.py)
- Post-run report shows "Pre-processor fallback rate: X/Y (Z%) -- N bloated, M empty"
- Only displayed when preproc_raw_output data exists (skipped for pre-migration runs)

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- 58 tests passing (37 compressor+db, rest matching broader filter)
- `propt inspect --help` shows correct usage
- Sanitization prompts contain "Output ONLY" wording
- max_tokens uses `max(256, int(len(text) * 1.3))` formula
- preproc_raw_output in both CREATE_SCHEMA and _EXPERIMENT_RUNS_COLUMNS
