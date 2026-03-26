# Roadmap: Linguistic Tax Research Toolkit

## Overview

This roadmap delivers a complete research pipeline for measuring how prompt noise degrades LLM accuracy and whether automated optimization recovers it. The work flows from foundational infrastructure (data, noise, config) through high-risk grading modules, then intervention/execution machinery, a pilot validation gate, statistical analysis, and finally publication figures. Every phase produces independently verifiable output. The full 20,000-call experiment run is explicitly out of scope for GSD -- the toolkit must be complete and pilot-validated.

## Milestones

- v1.0 MVP - Phases 1-15 (shipped 2026-03-25)
- v2.0 Configurable Models and Dynamic Pricing - Phases 16-19 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-15) - SHIPPED 2026-03-25</summary>

- [x] **Phase 1: Foundation and Data Infrastructure** - Config, SQLite schema, noise generators, benchmark prompts, and experiment matrix
- [x] **Phase 2: Grading Pipeline** - Sandboxed code execution grader and regex math grader with result storage
- [x] **Phase 3: Interventions and Execution Engine** - All 5 intervention strategies plus the orchestrating execution engine with full API instrumentation
- [x] **Phase 4: Pilot Validation** - 20-prompt end-to-end pilot run with grading spot-check and cost projection
- [x] **Phase 5: Statistical Analysis and Derived Metrics** - GLMM, bootstrap CIs, McNemar's, Kendall's tau, BH correction, CR, quadrants, cost rollups
- [x] **Phase 6: Publication Figures** - Accuracy curves, quadrant plots, cost heatmaps, rank-order visualizations
- [x] **Phase 7: OpenAI Integration** - GPT-4o as fully integrated third target model
- [x] **Phase 8: Test Coverage** - 80%+ line coverage with integration tests and QA script
- [x] **Phase 9: OpenRouter Support** - 4th provider gateway with free Nemotron models
- [x] **Phase 10: Prompt Format Research** - Literature survey and testable hypotheses for prompt formats
- [x] **Phase 11: Micro-Formatting Experiments** - Atomic experiment specs for micro-formatting effects
- [x] **Phase 12: Documentation** - Comprehensive docs for new users
- [x] **Phase 13: Setup Wizard** - Guided Q&A configuration flow
- [x] **Phase 14: CLI Config Subcommands** - View, modify, validate config via CLI
- [x] **Phase 15: Pre-Execution Gate** - Cost/runtime summary with confirmation before execution

</details>

### v2.0 Configurable Models and Dynamic Pricing

**Milestone Goal:** Make models fully configurable at setup time with live pricing, flexible wizard flow, .env API key management, and adaptive experiment scope -- so the toolkit works with any model, not just the four hardcoded ones.

- [x] **Phase 16: Config Schema and Defensive Fallbacks** - ModelConfig/ModelRegistry abstractions, backward-compatible migration, defensive compute_cost, env_manager (completed 2026-03-26)
- [x] **Phase 17: Registry Consumers** - Swap all hardcoded MODELS/PRICE_TABLE/RATE_LIMIT_DELAYS imports to registry lookups across consumer modules (completed 2026-03-26)
- [x] **Phase 18: Pricing Client and Model Discovery** - Live model listing from provider APIs, OpenRouter live pricing, enhanced propt list-models (completed 2026-03-26)
- [x] **Phase 19: Setup Wizard Overhaul** - Free-text model entry, multi-provider loop, .env creation, budget preview, model validation ping (completed 2026-03-26)

## Phase Details

### Phase 16: Config Schema and Defensive Fallbacks
**Goal**: Researcher has a config-driven model registry that replaces hardcoded constants -- custom models load without crashes, old configs migrate transparently, and .env files manage API keys
**Depends on**: Phase 15 (v1.0 complete)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, PRC-01, PRC-03
**Success Criteria** (what must be TRUE):
  1. Researcher can add a custom model ID to the config's models list and load it without any validation error or crash
  2. A config file saved by v1.0 (flat claude_model/gemini_model fields, no models list) loads correctly and auto-migrates to the new format
  3. Running compute_cost() with an unknown model ID returns $0.00 and logs a warning instead of crashing with KeyError
  4. PRICE_TABLE, PREPROC_MODEL_MAP, and RATE_LIMIT_DELAYS are built from the loaded config at runtime, not from hardcoded module-level constants
  5. python-dotenv is installed and env_manager module can load/write .env files
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md -- ModelConfig dataclass, ModelRegistry class, default_models.json
- [ ] 16-02-PLAN.md -- env_manager module and python-dotenv dependency
- [ ] 16-03-PLAN.md -- ExperimentConfig v2, config migration, validate_config update, integration

### Phase 17: Registry Consumers
**Goal**: Every module that previously imported hardcoded MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, or RATE_LIMIT_DELAYS now reads from the ModelRegistry -- custom models flow through the entire pipeline without hitting allowlist rejections
**Depends on**: Phase 16
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04
**Success Criteria** (what must be TRUE):
  1. Experiment matrix generation produces work items only for models present in the loaded config, not a hardcoded tuple
  2. Running `propt run --model <custom-model>` with a configured custom model does not raise "unknown model" errors
  3. Pilot run with a subset of providers (e.g., only Anthropic and OpenRouter) completes without errors about missing providers
  4. Derived metrics computation (compute_derived.py) processes results for exactly the configured models, no more and no less
**Plans**: 3 plans

Plans:
- [ ] 17-01-PLAN.md -- Migrate leaf consumers (api_client, prompt_compressor, config_commands, execution_summary) to registry
- [ ] 17-02-PLAN.md -- Migrate pipeline consumers (compute_derived, run_experiment, pilot, generate_matrix, setup_wizard) to registry
- [ ] 17-03-PLAN.md -- Remove backward-compat shims from config.py, migrate remaining tests

### Phase 18: Pricing Client and Model Discovery
**Goal**: Researcher can query live model availability and pricing from provider APIs -- propt list-models shows real model IDs, context windows, and pricing where available, with graceful fallback when APIs are unreachable
**Depends on**: Phase 16
**Requirements**: DSC-01, DSC-02, PRC-02
**Success Criteria** (what must be TRUE):
  1. Running `propt list-models` queries each configured provider's API and displays available model IDs
  2. Model listing output includes context window size and pricing columns (with pricing populated for OpenRouter, marked as "fallback" for other providers)
  3. When a provider API is unreachable (timeout or error), list-models falls back gracefully with a warning instead of crashing
**Plans**: 2 plans

Plans:
- [ ] 18-01-PLAN.md -- Model discovery module with per-provider query functions, parallel orchestration, fallback
- [ ] 18-02-PLAN.md -- CLI integration: enhanced handle_list_models with provider grouping, --json flag

### Phase 19: Setup Wizard Overhaul
**Goal**: Researcher can configure any combination of models and providers through the setup wizard -- free-text model entry with defaults, multi-provider flow, .env key management, model validation, and budget preview before committing
**Depends on**: Phase 16, Phase 17, Phase 18
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05, WIZ-06, DSC-03
**Success Criteria** (what must be TRUE):
  1. Wizard explains the distinction between target models and pre-processor models before asking the researcher to choose
  2. Researcher can configure 1 to 4 providers in a single wizard session, entering a custom model ID as free text for each
  3. When the researcher provides API keys during setup, a .env file is created (or updated) with correct file permissions and the keys are available immediately without restarting
  4. Wizard validates each selected model by making a small API call and reports success or failure before completing setup
  5. Wizard displays estimated experiment cost based on selected models before the researcher confirms the configuration
**Plans**: 2 plans

Plans:
- [ ] 19-01-PLAN.md -- Complete wizard rewrite: multi-provider flow, free-text model entry, .env key management, validation pings, budget preview
- [ ] 19-02-PLAN.md -- Test suite rewrite: comprehensive tests for all wizard functions and flows

## Progress

**Execution Order:**
Phases execute in numeric order: 16 -> 17 -> 18 -> 19
(Phases 17 and 18 can execute in parallel after 16 completes; Phase 19 depends on all three)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 16. Config Schema and Defensive Fallbacks | 3/3 | Complete    | 2026-03-26 | - |
| 17. Registry Consumers | 3/3 | Complete    | 2026-03-26 | - |
| 18. Pricing Client and Model Discovery | 2/2 | Complete    | 2026-03-26 | - |
| 19. Setup Wizard Overhaul | 2/2 | Complete   | 2026-03-26 | - |

### Phase 20: Update skills and agents in .claude using the skill-creator skill and re-run all optimizations and evaluations

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 19
**Plans:** 2/2 plans complete

Plans:
- [ ] TBD (run /gsd:plan-phase 20 to break down)

### Phase 21: Update all documentation

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 20
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 21 to break down)

### Phase 22: Experiment: All-caps and emphasis formatting effects on LLM attention

**Goal:** Investigate whether all-caps words, bold/markdown emphasis, and capitalization patterns affect LLM attention and instruction-following. Test cases: "WILL" vs "will", "DO NOT" vs "**do not**" vs "Do **not**", sentence-initial capitalization effects.
**Requirements**: TBD
**Depends on:** Phase 21
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 22 to break down)
