---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Configurable Models and Dynamic Pricing
status: unknown
stopped_at: Completed 23-02-PLAN.md
last_updated: "2026-03-27T21:27:58.389Z"
last_activity: 2026-03-27
progress:
  total_phases: 8
  completed_phases: 8
  total_plans: 21
  completed_plans: 21
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it
**Current focus:** Phase 23 — fix-pre-processor-output-quality-and-performance

## Current Position

Phase: 23 (fix-pre-processor-output-quality-and-performance) — EXECUTING
Plan: 2 of 2

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
| Phase 21 P04 | 3min | 2 tasks | 1 files |
| Phase 22 P01 | 3min | 2 tasks | 6 files |
| Phase 22 P02 | 5min | 2 tasks | 6 files |
| Phase 22 P03 | 7min | 2 tasks | 10 files |
| Phase 23 P01 | 3min | 2 tasks | 4 files |
| Phase 23 P02 | 1min | 2 tasks | 2 files |

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
- [Phase 21]: Architecture.md Design Decisions historical references to old constants are legitimate, not stale
- [Phase 22]: Sentinel replacement strategy for key-term matching prevents double-replacement
- [Phase 22]: prompt_id param added to apply_intervention with backward-compatible default
- [Phase 22]: Natural-language key terms instead of function identifiers to avoid breaking code in def lines
- [Phase 22]: Direct _replace_terms bypasses code-block protection for HumanEval indented docstrings
- [Phase 22]: Docstring content treated as natural language, not code, for emphasis conversion
- [Phase 23]: noise_type parameter backward-compatible: empty string default preserves old caller behavior
- [Phase 23]: Token-ratio warning is informational only, does not trigger fallback
- [Phase 23]: Anti-reasoning directives added to system prompts, not user messages
- [Phase 23]: Guidance placed after model table in getting-started.md for natural reading flow

### Pending Todos

- Investigate fine-tuned small LM as pre-processor (general)
- Experiment with provider prompt best practices as preprocessing (general)
- Add benchmark breakdown to propt report (general)
- Support multiple target models per provider in setup wizard (general)
- Investigate pre-processor performance anomaly — slow TTFT, high output (general)
- Investigate why pre_proc_sanitize hurts accuracy vs raw (general)


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
- [Phase 21]: All 7 target docs verified stale-reference-free; cross-document sweep found zero remaining v1.0 constants

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260325-w6g | Support Ctrl-C in the wizard and scripts | 2026-03-25 | d7e40b4 | [260325-w6g-support-ctrl-c-in-the-wizard-and-scripts](./quick/260325-w6g-support-ctrl-c-in-the-wizard-and-scripts/) |
| 260326-n2y | Git status triage — commit untracked files | 2026-03-26 | 8b08e67 | [260326-n2y-run-git-status-and-decide-what-needs-to-](./quick/260326-n2y-run-git-status-and-decide-what-needs-to-/) |
| 260326-vzd | Fix slicer references and QA script failures | 2026-03-26 | 1dcef07 | [260326-vzd-fix-slicer-references-and-qa-script-fail](./quick/260326-vzd-fix-slicer-references-and-qa-script-fail/) |
| 260326-w5r | Fix pytest warnings and test failures | 2026-03-26 | 3732002 | [260326-w5r-fix-pytest-failures](./quick/260326-w5r-fix-pytest-failures/) |
| 260327-19a | Add post-run report command | 2026-03-27 | c267936 | [260327-19a-add-post-run-report-comparing-projected-](./quick/260327-19a-add-post-run-report-comparing-projected-/) |
| 260327-3tc | Add OpenRouter rate limit check | 2026-03-27 | 99f5d24 | [260327-3tc-add-openrouter-rate-limit-check-to-pre-e](./quick/260327-3tc-add-openrouter-rate-limit-check-to-pre-e/) |
| 260327-4az | Add propt clean + results management todo | 2026-03-27 | 2e0e376 | [260327-4az-add-propt-clean-command-and-results-mana](./quick/260327-4az-add-propt-clean-command-and-results-mana/) |
| 260327-qun | Add benchmark breakdown to propt report | 2026-03-27 | 7e3b1c5 | [260327-qun-add-benchmark-breakdown-to-report](./quick/260327-qun-add-benchmark-breakdown-to-report/) |
| 260327-r3e | Inspect preproc output and fix chatty responses | 2026-03-27 | 0f09d36 | [260327-r3e-inspect-pre-processor-output-and-fix-cha](./quick/260327-r3e-inspect-pre-processor-output-and-fix-cha/) |
| 260327-rhk | Per-session result tracking with list/delete/compare | 2026-03-27 | da29381 | [260327-rhk-results-management-per-session-tracking-](./quick/260327-rhk-results-management-per-session-tracking-/) |
| 260327-ub0 | Report output formats and multi-model comparison | 2026-03-27 | c1e304d | [260327-ub0-report-output-formats-and-multi-model-co](./quick/260327-ub0-report-output-formats-and-multi-model-co/) |

## Session Continuity

Last activity: 2026-03-27 - Completed quick task 260327-ub0: Report output formats and multi-model comparison
Last session: 2026-03-27T21:49:13.339Z
Stopped at: Completed 260327-ub0
Resume file: None
