---
phase: quick-260327-4az
plan: 01
subsystem: cli
tags: [clean, results-management, todo]
---

# Quick Task 260327-4az: Add propt clean command and results management todo

## Changes

1. **Added `propt clean` CLI subcommand** — deletes results.db, execution plans, and pilot prompts with confirmation prompt and file size display
2. **Created detailed todo** for full results management system (per-session tracking, list-results, delete-results, compare-results)

## propt clean behavior
- Lists files to delete with sizes
- Requires confirmation (or `--yes` to skip)
- Supports `--db` override
- Deletes: results.db, execution_plan.json, pilot_plan.json, pilot_prompts.json

## Result
660 tests pass. Clean command tested with existing results.
