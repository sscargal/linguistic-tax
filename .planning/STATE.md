---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Configurable Models and Dynamic Pricing
status: unknown
stopped_at: Completed 21-03-PLAN.md
last_updated: "2026-03-26T18:20:39.312Z"
last_activity: 2026-03-26
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 16
  completed_plans: 15
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it
**Current focus:** Phase 21 — update-all-documentation

## Current Position

Phase: 21 (update-all-documentation) — EXECUTING
Plan: 4 of 4 (Plans 1-3 complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v2.0)
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend (from v1.0):**

- Last 5 plans: 4min, 6min, 3min, 4min, 4min
- Trend: Stable (~4min/plan)

*Updated after each plan completion*
| Phase 16 P02 | 2min | 2 tasks | 4 files |
| Phase 16 P01 | 2min | 1 tasks | 3 files |
| Phase 16 P03 | 6min | 2 tasks | 8 files |
| Phase 17 P01 | 4min | 2 tasks | 7 files |
| Phase 17-02 P02 | 4min | 2 tasks | 8 files |
| Phase 17-03 P03 | 3min | 2 tasks | 4 files |
| Phase 18 P01 | 4min | 1 tasks | 2 files |
| Phase 18 P02 | 3min | 1 tasks | 3 files |
| Phase 19 P01 | 2min | 2 tasks | 1 files |
| Phase 19 P02 | 3min | 2 tasks | 1 files |
| Phase 20 P01 | 2min | 2 tasks | 8 files |
| Phase 20 P02 | 5min | 2 tasks | 14 files |
| Phase 21 P02 | 2min | 1 tasks | 1 files |
| Phase 21 P01 | 3min | 2 tasks | 2 files |
| Phase 21 P03 | 5min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 13]: isinstance check on defaults for tuple detection (more robust than string type parsing)
- [Phase 13]: input_fn parameter injection for wizard testability instead of monkeypatching builtins.input
- [Phase 14]: print() for CLI output instead of logging for user-facing commands
- [Phase 15]: Budget gate checks before --yes auto-accept for scripted safety
- [Phase 16]: env_path parameter on all env_manager functions for test isolation via tmp_path
- [Phase 16]: Registry initialized from default_models.json at import time; reload() used after config load
- [Phase 16]: Added registry-backed backward-compat shims for MODELS/PRICE_TABLE/etc. to bridge Phase 16-17 transition
- [Phase 17]: Unknown preproc models warn and return model-itself as fallback instead of raising ValueError
- [Phase 17-02]: setup_wizard PROVIDERS built via _build_providers() function for registry evaluation
- [Phase 17-03]: All backward-compat shims removed from config.py; model_registry is sole source of truth for model data
- [Phase 18]: Used as_completed(timeout=) for outer timeout enforcement in parallel provider queries
- [Phase 18]: Provider display order hardcoded as anthropic/google/openai/openrouter for consistent CLI output
- [Phase 19]: All 16 wizard functions in single module; budget preview via synthetic experiment items
- [Phase 19]: Class-based test organization matching wizard sections for maintainability
- [Phase 20]: Workspace evaluation output files left untouched as historical artifacts
- [Phase 20]: skill-creator unavailable; manually wrote v2.0 eval cases following existing JSON format
- [Phase 21]: Wizard-first config approach: propt setup leads Configuration section, manual set-config is secondary
- [Phase 21]: ExperimentConfig field names for set-config examples (base_seed, repetitions, temperature) based on config_commands.py source
- [Phase 21]: Environment and Discovery Layer in architecture module reference (separate from Configuration Layer)

### Pending Todos

- Investigate fine-tuned small LM as pre-processor (general)
- Experiment with provider prompt best practices as preprocessing (general)

### Roadmap Evolution

- v2.0 roadmap: 4 phases (16-19) derived from 21 requirements at standard granularity
- Dropped proposed Phase 20 (cross-cutting tests) — verification absorbed into each phase's success criteria
- Phases 17 and 18 can execute in parallel after Phase 16
- Phase 20 added: Update skills and agents in .claude using the skill-creator skill and re-run all optimizations and evaluations
- Phase 21 added: Update all documentation
- Phase 22 added: Experiment: All-caps and emphasis formatting effects on LLM attention

### Blockers/Concerns

- Research flag (Phase 18): OpenRouter /api/v1/models pricing schema is MEDIUM confidence — verify live before writing parser
- Research flag (Phase 19): python-dotenv set_key() behavior on missing .env file — resolved in Phase 19 wizard rewrite (write_env handles creation)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260325-w6g | Support Ctrl-C in the wizard and scripts | 2026-03-25 | d7e40b4 | [260325-w6g-support-ctrl-c-in-the-wizard-and-scripts](./quick/260325-w6g-support-ctrl-c-in-the-wizard-and-scripts/) |
| 260326-n2y | Git status triage — commit untracked files | 2026-03-26 | 8b08e67 | [260326-n2y-run-git-status-and-decide-what-needs-to-](./quick/260326-n2y-run-git-status-and-decide-what-needs-to-/) |

## Session Continuity

Last activity: 2026-03-26
Last session: 2026-03-26T18:20:39.310Z
Stopped at: Completed 21-03-PLAN.md
Resume file: None
