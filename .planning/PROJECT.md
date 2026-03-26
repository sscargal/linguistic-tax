# Linguistic Tax Research Toolkit

## What This Is

A Python research toolkit that measures how prompt noise (typos, grammar errors, ESL patterns) and prompt bloat (redundancy, verbosity) degrade LLM reasoning accuracy, and whether automated "prompt optimization" (sanitization + compression) can recover that accuracy while reducing token costs. The output is data, figures, and statistical analysis for an ArXiv paper. This is a CLI-only toolkit for a single researcher — no UI, no deployment, no web framework.

## Core Value

Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it — every design choice must serve statistical validity and reproducibility.

## Requirements

### Validated

- ✓ Generate controlled Type A (character-level) noise at 5%, 10%, 20% rates with fixed seeds — Phase 1
- ✓ Generate controlled Type B (ESL syntactic) noise patterns with fixed seeds — Phase 1
- ✓ Store all results in SQLite with schema from the RDD — Phase 1
- ✓ Curate 200 clean benchmark prompts (HumanEval, MBPP, GSM8K) — Phase 1
- ✓ Build experiment matrix covering 5 intervention types x noise conditions — Phase 1
- ✓ Auto-grade HumanEval/MBPP outputs via sandboxed subprocess execution — Phase 2
- ✓ Auto-grade GSM8K outputs via regex-based numerical answer extraction — Phase 2
- ✓ Record all grading results (pass/fail + metadata) to SQLite — Phase 2
- ✓ Compress prompts by removing redundancy and condensing verbose language — Phase 3
- ✓ Implement prompt repetition (<QUERY><QUERY>) intervention per Leviathan et al. — Phase 3
- ✓ Execute prompts against Claude and Gemini APIs with full logging (TTFT, TTLT, tokens, cost) — Phase 3
- ✓ Run pilot experiment tooling (20 prompts across all conditions) with spot-check, cost projection, and structured verdict — Phase 4

### Active

#### Current Milestone: v2.0 — Configurable Models and Dynamic Pricing

**Goal:** Make models fully configurable at setup time with live pricing, flexible wizard flow, .env API key management, and adaptive experiment scope — so the toolkit works with any model, not just the four hardcoded ones.

**Target features:**
- Dynamic model configuration (free-text entry with sensible defaults)
- Per-provider pricing APIs with offline fallback
- Multi-provider setup wizard with target/preproc explanations
- .env file creation for API keys
- Config-driven PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS
- Enhanced `propt list-models` with live provider queries
- Budget awareness at setup time
- Experiment scope adapts to configured models

### Recently Validated
- ✓ Skills and agents updated for v2.0 — all 7 SKILL.md files updated with model_registry/config_manager/env_manager references, evals regenerated, triggers re-optimized, zero stale refs — Phase 20
- ✓ Setup wizard overhaul — multi-provider selection, free-text model entry with live browser, .env key management, validation pings, budget preview — Phase 19
- ✓ Pricing client and model discovery — live model listing from 4 provider APIs, OpenRouter live pricing, enhanced propt list-models with context windows and --json flag — Phase 18
- ✓ Registry consumers — all modules migrated from hardcoded constants to ModelRegistry, shims removed, custom models flow through entire pipeline — Phase 17
- ✓ Config schema and defensive fallbacks — ModelConfig dataclass, ModelRegistry, env_manager, ExperimentConfig v2 with migration — Phase 16
- ✓ Comprehensive documentation and README for new users — root README.md, architecture docs, getting-started guide, analysis guide, contributing guide, docs index — Phase 12
- ✓ Pre-execution experiment summary and confirmation gate — cost/runtime estimation, structured summary display, three-way confirmation (Y/N/M), --yes/--budget flags, propt run/pilot CLI subcommands, tqdm progress bar, execution plan saving — Phase 15
- ✓ CLI config subcommands (show/set/reset/validate/diff/list-models) with JSON/text/table output, changed-from-defaults highlighting, and tab completion — Phase 14
- ✓ Guided setup wizard for project configuration — interactive Q&A flow for model provider, models, API keys, paths; CLI entry point with argparse subparsers; config-missing guards — Phase 13
- ✓ Research optimal prompt input formats with 6 testable hypotheses and 3 experiment designs for whitepaper — Phase 10
- ✓ Add OpenRouter as 4th model provider with free Nemotron model defaults, full test coverage — Phase 9
- ✓ Expand test coverage to 80%+ line coverage (achieved 88.37%) with integration tests and QA script — Phase 8
- ✓ Integrate OpenAI GPT-4o as full third target model (API client, config, pilot, figures) — Phase 7
- ✓ Generate publication-quality figures (accuracy curves, quadrant plots, cost heatmaps, Kendall's tau) — Phase 6
- ✓ Perform GLMM, bootstrap CI, McNemar's, and Kendall's tau analysis — Phase 5
- ✓ Compute derived metrics: Consistency Rate, quadrant classification, cost rollups — Phase 5

### Out of Scope

- Web UI or API server — CLI-only research tool
- Mobile or desktop app — command-line scripts only
- Full 20,000-call matrix execution — handled outside GSD after tooling is complete
- Real-time or streaming inference — batch execution only
- Deployment or packaging for distribution — single-researcher use

## Context

- The Research Design Document (RDD) at `docs/RDD_Linguistic_Tax_v4.md` is the authoritative spec for all experimental parameters, metrics, and conditions
- 5 intervention types: Raw, Self-Correct, Pre-Proc Sanitize, Pre-Proc Sanitize+Compress, Prompt Repetition
- Pre-processor calls use cheap models (Haiku or Flash) to sanitize/compress before sending to target model
- Each condition requires 5 repetitions for stability measurement (Consistency Rate)
- Existing code structure already established in `src/` and `tests/` directories
- API keys via environment variables: ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY
- Budget constraint: ~$15 for pilot run (20 prompts)

## Constraints

- **Language**: Python 3.11+ only — no other languages
- **APIs**: Direct SDK calls via `anthropic`, `google-genai`, `openai`, and OpenRouter (via `openai` with base_url override) — no CLI wrappers
- **Storage**: SQLite only — no Postgres, no flat JSON files for results
- **Reproducibility**: All randomness uses fixed seeds; all API calls use temperature=0.0
- **Logging**: Python `logging` module only — no print statements
- **Testing**: pytest with determinism tests for noise generators
- **Style**: Type hints on all functions, docstrings on all public functions, American English

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over flat files | Single-file DB, SQL queries for analysis, no server needed | — Pending |
| Fixed random seeds everywhere | Reproducibility is non-negotiable for a research paper | — Pending |
| temperature=0.0 for all API calls | Minimize variance from model sampling | — Pending |
| Pilot before full run | Validate tooling on 20 prompts before committing to 20K calls | — Pending |
| Cheap model for pre-processing | Haiku/Flash for sanitize/compress keeps costs low | — Pending |
| 5 repetitions per condition | Balance statistical power with API cost | — Pending |

---
*Last updated: 2026-03-26 after Phase 18 complete — Pricing Client and Model Discovery*
