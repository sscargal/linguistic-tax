# Roadmap: Linguistic Tax Research Toolkit

## Overview

This roadmap delivers a complete research pipeline for measuring how prompt noise degrades LLM accuracy and whether automated optimization recovers it. The work flows from foundational infrastructure (data, noise, config) through high-risk grading modules, then intervention/execution machinery, a pilot validation gate, statistical analysis, and finally publication figures. Every phase produces independently verifiable output. The full 20,000-call experiment run is explicitly out of scope for GSD -- the toolkit must be complete and pilot-validated.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Data Infrastructure** - Config, SQLite schema, noise generators, benchmark prompts, and experiment matrix
- [ ] **Phase 2: Grading Pipeline** - Sandboxed code execution grader and regex math grader with result storage
- [ ] **Phase 3: Interventions and Execution Engine** - All 5 intervention strategies plus the orchestrating execution engine with full API instrumentation
- [ ] **Phase 4: Pilot Validation** - 20-prompt end-to-end pilot run with grading spot-check and cost projection
- [ ] **Phase 5: Statistical Analysis and Derived Metrics** - GLMM, bootstrap CIs, McNemar's, Kendall's tau, BH correction, CR, quadrants, cost rollups
- [ ] **Phase 6: Publication Figures** - Accuracy curves, quadrant plots, cost heatmaps, rank-order visualizations

## Phase Details

### Phase 1: Foundation and Data Infrastructure
**Goal**: Researcher has a complete, deterministic data foundation -- noise generators produce reproducible output, 200 benchmark prompts are curated, the experiment matrix is materialized, and all results can be stored in SQLite
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, NOISE-01, NOISE-02, NOISE-03, NOISE-04
**Success Criteria** (what must be TRUE):
  1. Running the noise generator twice with the same seed produces byte-identical output for both Type A and Type B noise
  2. 200 clean benchmark prompts exist in prompts.json with correct canonical answers for HumanEval, MBPP, and GSM8K
  3. The experiment matrix JSON enumerates every prompt x noise x intervention combination as a self-contained work item
  4. SQLite database can be created with the RDD schema and accepts insert/query of experimental result rows
  5. Configuration module exposes pinned model versions, API settings, and a seed registry that prevents global random state
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md -- Config module with pinned settings and seed registry, SQLite database with full RDD schema
- [ ] 01-02-PLAN.md -- Noise generators: Type A character-level with keyword protection, Type B ESL syntactic, CLI interface
- [ ] 01-03-PLAN.md -- Benchmark prompt curation (200 prompts from HumanEval/MBPP/GSM8K) and experiment matrix generation

### Phase 2: Grading Pipeline
**Goal**: Researcher can automatically grade any LLM output -- HumanEval/MBPP code is executed in a secure sandbox with pass/fail, GSM8K answers are extracted and compared via regex, and all grades are recorded in SQLite
**Depends on**: Phase 1 (needs SQLite schema for GRAD-03, benchmark prompts for test data)
**Requirements**: GRAD-01, GRAD-02, GRAD-03
**Success Criteria** (what must be TRUE):
  1. HumanEval/MBPP code outputs are executed in a subprocess sandbox with timeout and resource limits -- infinite loops and fork bombs do not hang or crash the host
  2. GSM8K grading correctly extracts and compares numerical answers across format variants (prose, LaTeX, units, comma-separated)
  3. Every grading result (pass/fail) is written to the SQLite results database with the corresponding run ID
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md -- Subprocess sandbox code grader (HumanEval/MBPP), regex math grader (GSM8K), CLI with batch mode, grading_details DB table

### Phase 3: Interventions and Execution Engine
**Goal**: Researcher can execute any experiment matrix work item end-to-end -- the intervention router dispatches to the correct strategy, the API client calls Claude or Gemini with full instrumentation, and the engine manages resumability and rate limiting
**Depends on**: Phase 1 (config, matrix, noise, DB), Phase 2 (grading)
**Requirements**: INTV-01, INTV-02, INTV-03, INTV-04, INTV-05, EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05
**Success Criteria** (what must be TRUE):
  1. The intervention router correctly dispatches to all 5 strategies: Raw, Self-Correct, Pre-Proc Sanitize, Pre-Proc Sanitize+Compress, and Prompt Repetition
  2. API calls to both Claude Sonnet and Gemini 1.5 Pro succeed at temperature=0.0 and log TTFT, TTLT, token counts, cost, and timestamp for every call
  3. Each condition is executed 5 times (repetitions) and all repetition results are stored
  4. Stopping and restarting the engine skips already-completed work items without data loss or duplication
  5. Rate limiting prevents API throttling errors during sustained execution
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md -- Intervention pure functions (repeater, compressor/sanitizer), config extensions (price table, max_tokens, preproc models)
- [ ] 03-02-PLAN.md -- Unified API client with streaming TTFT/TTLT, rate limiting, retry logic, pyproject.toml fix
- [ ] 03-03-PLAN.md -- Intervention router, execution engine with resumability and inline grading, CLI

### Phase 4: Pilot Validation
**Goal**: Researcher has validated the entire pipeline end-to-end on 20 prompts, confirmed grading accuracy, and produced a reliable cost projection for the full experiment run
**Depends on**: Phase 3 (complete execution pipeline)
**Requirements**: PILOT-01, PILOT-02, PILOT-03
**Success Criteria** (what must be TRUE):
  1. Pilot run completes for 20 prompts across all noise conditions and intervention types with results in SQLite
  2. Manual spot-check of at least 10% of pilot grading results confirms grading accuracy (no systematic errors)
  3. Cost projection for the full experiment run is computed from pilot data and falls within budget constraints
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md -- Core pilot module: compress_only fix, stratified prompt selection, pilot execution entry point, data completeness audit, noise sanity check
- [ ] 04-02-PLAN.md -- Pilot analysis: grading spot-check, cost projection with bootstrap CIs, BERTScore fidelity, latency profiling, verdict report, CLI

### Phase 5: Statistical Analysis and Derived Metrics
**Goal**: Researcher can compute all statistical analyses and derived metrics defined in the RDD from experimental results in SQLite
**Depends on**: Phase 4 (validated pilot data to develop against; modules work on any results data)
**Requirements**: STAT-01, STAT-02, STAT-03, STAT-04, STAT-05, DERV-01, DERV-02, DERV-03
**Success Criteria** (what must be TRUE):
  1. GLMM fits on binary pass/fail data with prompt-level random effects and produces coefficient estimates with p-values
  2. Bootstrap confidence intervals are computed for all reported accuracy and stability metrics
  3. McNemar's test identifies prompt-level fragility and recoverability with BH-corrected p-values across all comparisons
  4. Consistency Rate (CR) is computed from pairwise agreement across 5 repetitions, and each prompt-condition is classified into a stability-correctness quadrant
  5. Cost rollups show net ROI for each intervention (token savings minus pre-processor overhead)
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md -- Derived metrics: CR computation, quadrant classification, cost rollups, quadrant migration matrices, CLI
- [ ] 05-02-PLAN.md -- Statistical analysis: GLMM with fallback, bootstrap CIs, McNemar's fragility, Kendall's tau, BH correction, sensitivity analysis, effect size summary, CLI with subcommands
- [ ] 05-03-PLAN.md -- Gap closure: CR bootstrap CIs from derived_metrics, STAT-05 requirement wording fix

### Phase 6: Publication Figures
**Goal**: Researcher has publication-quality figures for all key results, ready for the ArXiv paper
**Depends on**: Phase 5 (analysis results to visualize)
**Requirements**: FIG-01, FIG-02, FIG-03, FIG-04
**Success Criteria** (what must be TRUE):
  1. Accuracy degradation curves show noise level on x-axis vs. accuracy on y-axis, faceted by model and intervention type
  2. Stability-correctness quadrant plots display each prompt-condition as a point in the 4-quadrant space (Robust/Confidently-Wrong/Lucky/Broken)
  3. Cost-benefit heatmaps show net token savings by condition with clear color scale
  4. All figures are saved as publication-quality vector graphics (PDF or SVG) in the figures/ directory
**Plans**: 1 plan

Plans:
- [ ] 06-01-PLAN.md -- All 4 figure types (accuracy curves, quadrant plots, cost heatmaps, Kendall tau bars) with shared style config, save helper, and argparse CLI (TDD)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Data Infrastructure | 0/3 | Planning complete | - |
| 2. Grading Pipeline | 0/1 | Planning complete | - |
| 3. Interventions and Execution Engine | 0/3 | Planning complete | - |
| 4. Pilot Validation | 0/2 | Planning complete | - |
| 5. Statistical Analysis and Derived Metrics | 2/3 | Gap closure planned | - |
| 6. Publication Figures | 0/1 | Planning complete | - |

### Phase 7: Add OpenAI to the supported model provider

**Goal:** GPT-4o is a fully integrated third target model in the experiment pipeline -- API client streams with TTFT/TTLT tracking, config has all pricing/routing entries, pilot and figures handle 3 models, and the full test suite passes
**Requirements**: OAPI-01, OAPI-02, OAPI-03, OAPI-04, OAPI-05, OAPI-06
**Depends on:** Phase 6
**Plans:** 1/2 plans executed

Plans:
- [ ] 07-01-PLAN.md -- Core OpenAI integration: config entries, _call_openai with streaming, call_model routing, retry/rate-limit, pyproject.toml, .env.example, comprehensive tests
- [ ] 07-02-PLAN.md -- Downstream updates: pilot _VALID_MODELS from config, figure layout scaling for 3 models, full suite verification

### Phase 8: Write unit tests

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 7
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 8 to break down)

### Phase 9: Add OpenRouter support with free model defaults (Nemotron)

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 8
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 9 to break down)

### Phase 10: Research optimal prompt input formats for whitepaper

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 9
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 10 to break down)

### Phase 11: Brainstorm micro-formatting test questions for experiment suite

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 10
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 11 to break down)

### Phase 12: Comprehensive documentation and README for new users

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 11
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 12 to break down)

### Phase 13: Guided setup wizard for project configuration

**Goal:** Brainstorm and potentially implement a guided setup wizard that helps new users get started quickly -- choose model provider, model(s), working directory, and other essential configuration through a simple Q&A flow instead of manually editing config files (manual config still supported)
**Requirements**: TBD
**Depends on:** Phase 12
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 13 to break down)

### Phase 14: CLI config subcommands for viewing and modifying settings

**Goal:** Add subcommands to display configuration as JSON, text, or terminal table, and allow users to set/modify any config property. The `list` (get) command shows all properties and highlights which have been changed from defaults, helping researchers understand which variables have been modified
**Requirements**: TBD
**Depends on:** Phase 13
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 14 to break down)

### Phase 15: Pre-execution experiment summary and confirmation gate

**Goal:** Before executing experiments, display a summary of what will run -- cost projection, number of experiments, estimated runtime, models, noise conditions, and interventions included. Researcher can accept/reject, make changes, and re-execute. Includes a --yes flag to skip confirmation for automated/scripted runs
**Requirements**: TBD
**Depends on:** Phase 14
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 15 to break down)
