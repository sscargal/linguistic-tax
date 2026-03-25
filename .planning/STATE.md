---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 14-02-PLAN.md
last_updated: "2026-03-25T01:22:50.859Z"
progress:
  total_phases: 15
  completed_phases: 13
  total_plans: 29
  completed_plans: 29
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it
**Current focus:** Phase 14 — cli-config-subcommands-for-viewing-and-modifying-settings

## Current Position

Phase: 14 (cli-config-subcommands-for-viewing-and-modifying-settings) — EXECUTING
Plan: 2 of 2

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 3min | 2 tasks | 5 files |
| Phase 01 P03 | 3min | 2 tasks | 6 files |
| Phase 01 P02 | 4min | 2 tasks | 2 files |
| Phase 02 P01 | 8min | 2 tasks | 4 files |
| Phase 03 P01 | 5min | 2 tasks | 5 files |
| Phase 03 P02 | 7 | 1 tasks | 2 files |
| Phase 03 P03 | 11min | 2 tasks | 8 files |
| Phase 04 P01 | 5min | 1 tasks | 5 files |
| Phase 04 P02 | 9min | 2 tasks | 2 files |
| Phase 05 P01 | 5min | 2 tasks | 4 files |
| Phase 05 P02 | 6min | 2 tasks | 3 files |
| Phase 05 P03 | 4min | 2 tasks | 4 files |
| Phase 06 P01 | 5min | 2 tasks | 2 files |
| Phase 07 P01 | 5min | 1 tasks | 6 files |
| Phase 07 P02 | 4min | 2 tasks | 4 files |
| Phase 08 P03 | 8min | 1 tasks | 1 files |
| Phase 08 P01 | 10min | 2 tasks | 6 files |
| Phase 08 P02 | 4min | 2 tasks | 1 files |
| Phase 09 P01 | 3min | 2 tasks | 4 files |
| Phase 09 P02 | 6min | 2 tasks | 6 files |
| Phase 10 P01 | 3min | 1 tasks | 1 files |
| Phase 10 P02 | 4min | 1 tasks | 1 files |
| Phase 11 P01 | 6min | 2 tasks | 2 files |
| Phase 11 P02 | 8min | 2 tasks | 2 files |
| Phase 11 P03 | 5min | 2 tasks | 2 files |
| Phase 13 P01 | 3min | 1 tasks | 2 files |
| Phase 13 P02 | 4min | 2 tasks | 6 files |
| Phase 14 P01 | 3min | 2 tasks | 3 files |
| Phase 14 P02 | 4min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 6 phases derived from 36 requirements at standard granularity
- Roadmap: Phase 4 (Pilot) is a hard gate -- no full experiment run without successful pilot
- [Phase 01]: Frozen dataclass for config immutability with SHA-256 seed derivation and WAL-mode SQLite
- [Phase 01]: Full factorial matrix of 82,000 items for complete experimental coverage with deterministic HuggingFace sampling
- [Phase 01]: Widened mutation count test tolerances to account for invisible mutations on uniform strings
- [Phase 02]: Used Popen with manual process group kill for reliable subprocess timeout handling
- [Phase 02]: Overlap deduplication in GSM8K number extraction to prevent short matches inside longer ones
- [Phase 02]: RLIMIT_NPROC=50 to avoid interference with other user processes
- [Phase 03]: Callable injection pattern for API calls in prompt_compressor -- accepts call_fn parameter instead of importing api_client
- [Phase 03]: Used google.genai.errors.ClientError with code==429 for Google rate limit detection, keeping exception handling specific
- [Phase 03]: Standardized all imports to src. prefix across project for consistent module resolution
- [Phase 03]: Runtime noise application from clean prompts via derive_seed rather than pre-stored noisy text
- [Phase 04]: Used sanitize_and_compress for compress_only since compression instruction handles clean prompts correctly
- [Phase 04]: Sort prompt ID pools before sampling for cross-platform determinism
- [Phase 04]: BCa bootstrap with percentile fallback for degenerate cost data
- [Phase 04]: Lazy import pattern for bert_score with graceful degradation
- [Phase 05]: Pairwise CR via itertools.combinations for exact combinatorial agreement counting
- [Phase 05]: Defensive CREATE TABLE IF NOT EXISTS in compute_derived_metrics for schema safety
- [Phase 05]: Three-level GLMM fallback: BayesMixedGLM full -> reduced -> GEE with exchangeable correlation
- [Phase 05]: Explicit 2-way GLMM interactions via colon notation to avoid combinatorial explosion
- [Phase 05]: CR bootstrap CIs use optional db_path parameter for backward compatibility
- [Phase 05]: Sensitivity analysis excluded from CR bootstrap to avoid misleading filtered results
- [Phase 06]: Module-level _configure_style() call for consistent defaults across all entry points
- [Phase 07]: OpenAI streaming with stream_options include_usage for token extraction; gpt prefix routing matching existing provider patterns
- [Phase 07]: Derive _VALID_MODELS as set(MODELS) from config for automatic propagation of new models
- [Phase 08]: Auto-activate project venv in QA script for portable package availability
- [Phase 08]: In-process CLI testing via sys.argv patching for coverage attribution (subprocess tests don't count)
- [Phase 08]: Mock factory fixtures in conftest.py for project-wide API response mocking reuse
- [Phase 08]: No additional gap-closure tests needed; coverage already at 88% from plan 08-01
- [Phase 09]: Reuse OpenAI SDK with base_url override for OpenRouter provider
- [Phase 09]: Reuse _make_openai_stream_chunks helper for OpenRouter mocks since both use OpenAI SDK format
- [Phase 10]: Organized literature by 6 format categories; flagged punctuation removal as likely harmful; identified format-x-noise as novel contribution
- [Phase 10]: Ranked H-FMT-01 (TOON), H-FMT-02 (XML), H-FMT-04 (punctuation) as HIGH priority; H-FMT-05 (format x noise) as stretch goal
- [Phase 11]: Rule-based format conversion as default; LLM pre-processor only for AQ-TE-04 comparison
- [Phase 11]: Free OpenRouter Nemotron as default model; immediate paid escalation for model-specific XML hypothesis (AQ-SM-01)
- [Phase 11]: Punctuation removal uses regex patterns (zero-cost) not LLM pre-processing
- [Phase 11]: Micro-pilot gate (AQ-FN-05) uses 5pp slope difference go/3pp no-go thresholds for format x noise experiments
- [Phase 11]: Selected 5 novel hypotheses for full specs: instruction phrasing, politeness, code comments, newline density, emphasis markers
- [Phase 11]: Cross-cluster bundling saves ~30% API calls by sharing HumanEval/MBPP/GSM8K control conditions
- [Phase 13]: isinstance check on defaults for tuple detection (more robust than string type parsing)
- [Phase 13]: input_fn parameter injection for wizard testability instead of monkeypatching builtins.input
- [Phase 13]: Duplicated _check_config_exists in entry points for independence
- [Phase 14]: print() for CLI output instead of logging for user-facing commands
- [Phase 14]: SimpleNamespace with make_args() helper for argparse namespace mocking

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 7 added: Add OpenAI to the supported model provider
- Phase 8 added: Write unit tests
- Phase 9 added: Add OpenRouter support with free model defaults (Nemotron) — examine https://openrouter.ai/models?max_price=0 for free models, default to Nemotron models to avoid API costs
- Phase 10 added: Research optimal prompt input formats — investigate whether compact/structured prompt formats (analogous to TOON vs JSON) yield superior LLM results; human-convention-friendly notation that reduces tokens while improving accuracy; innovate testable ideas for whitepaper inclusion
- Phase 11 added: Brainstorm micro-formatting test questions — e.g. does a question mark at end of a question matter? Do newlines matter to LLMs or only for human readability? Explore and design testable hypotheses for the experiment suite
- Phase 12 added: Comprehensive docs for new users — README.md with quick start, docs/ with: install/setup/config guide, user guide with examples, analysis interpretation guide, and any other docs needed. Assume reader has zero context about the repo, its goals, or why it matters.
- Phase 13 added: Guided setup wizard for project configuration — brainstorm and potentially implement a Q&A wizard to help users choose model provider, models, working directory, etc. without manual config file editing
- Phase 14 added: CLI config subcommands — display config as JSON/text/table, set/modify any property, list command highlights changes from defaults
- Phase 15 added: Pre-execution experiment summary and confirmation gate — show cost/runtime/experiment count before running, accept/reject/modify flow, --yes flag for automation

### Blockers/Concerns

- Research flag: google-generativeai package in pyproject.toml is deprecated, must be replaced with google-genai before writing API code (Phase 3)
- ✓ RESOLVED: GLMM convergence handled with 3-level fallback chain (BayesMixedGLM → reduced → GEE) — Phase 5
- Research flag: Pre-processor prompt engineering for sanitizer/compressor not specified in RDD -- needs iteration (Phase 3)

## Session Continuity

Last session: 2026-03-25T01:19:14.069Z
Stopped at: Completed 14-02-PLAN.md
Resume file: None
