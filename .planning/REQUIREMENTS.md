# Requirements: Linguistic Tax Research Toolkit

**Defined:** 2026-03-19
**Core Value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Infrastructure

- [x] **DATA-01**: Curate 200 clean benchmark prompts from HumanEval, MBPP, and GSM8K with canonical problem definitions
- [x] **DATA-02**: Build experiment matrix covering all prompt x noise x intervention combinations as self-contained work items
- [x] **DATA-03**: Store all experimental results in SQLite with schema matching RDD Section 9.2
- [x] **DATA-04**: Implement configuration module with pinned model versions, API settings, and seed registry

### Noise Generation

- [x] **NOISE-01**: Generate Type A character-level noise at 5%, 10%, and 20% error rates with fixed random seeds
- [x] **NOISE-02**: Protect technical keywords (function names, variable names, operators) from character mutation
- [x] **NOISE-03**: Generate Type B ESL syntactic noise patterns based on L1 transfer errors (Mandarin, Spanish, Japanese, mixed)
- [x] **NOISE-04**: Verify noise generator determinism — same seed produces identical output across runs

### Prompt Interventions

- [x] **INTV-01**: Implement prompt compressor that removes redundancy and condenses verbose language via cheap model (Haiku/Flash)
- [x] **INTV-02**: Implement prompt repeater using <QUERY><QUERY> duplication per Leviathan et al.
- [x] **INTV-03**: Implement self-correct prompt prefix intervention (zero-overhead prompt engineering)
- [x] **INTV-04**: Implement pre-processor pipeline that sanitizes noisy prompts via cheap model before sending to target model
- [x] **INTV-05**: Build intervention router that dispatches to Raw/Self-Correct/Pre-Proc Sanitize/Sanitize+Compress/Repetition

### Experiment Execution

- [x] **EXEC-01**: Execute prompts against Claude Sonnet and Gemini 1.5 Pro APIs with temperature=0.0
- [x] **EXEC-02**: Log every API call with: prompt text, response text, model version, token counts (in/out), TTFT, TTLT, cost, timestamp
- [x] **EXEC-03**: Run 5 repetitions per condition for stability measurement
- [x] **EXEC-04**: Implement resumable execution — skip already-completed work items on restart
- [x] **EXEC-05**: Implement proactive rate limiting to avoid API throttling

### Grading

- [x] **GRAD-01**: Auto-grade HumanEval/MBPP outputs via sandboxed subprocess code execution with timeout and resource limits
- [x] **GRAD-02**: Auto-grade GSM8K outputs via regex extraction of final numerical answer with format-variant handling
- [x] **GRAD-03**: Record pass/fail result for every experimental run in SQLite

### Pilot Validation

- [x] **PILOT-01**: Run pilot experiment with 20 prompts across all conditions to validate full pipeline end-to-end
- [x] **PILOT-02**: Verify grading accuracy via manual spot-check of pilot results
- [x] **PILOT-03**: Generate cost projection for full experiment run from pilot data

### Statistical Analysis

- [x] **STAT-01**: Fit GLMM with prompt-level random effects on binary pass/fail outcomes
- [x] **STAT-02**: Compute bootstrap confidence intervals for all reported metrics
- [x] **STAT-03**: Run McNemar's test for prompt-level fragility/recoverability analysis
- [x] **STAT-04**: Compute Kendall's tau for rank-order stability (uniform vs. targeted tax)
- [x] **STAT-05**: Apply Benjamini-Hochberg correction per test-type family (McNemar's, GLMM, Kendall's) across reported p-values

### Derived Metrics

- [x] **DERV-01**: Compute Consistency Rate (CR) from pairwise agreement across 5 repetitions per condition
- [x] **DERV-02**: Classify each prompt-condition pair into stability-correctness quadrant (Robust/Confidently-Wrong/Lucky/Broken)
- [x] **DERV-03**: Compute cost rollups and net ROI for optimizer interventions (savings minus pre-processor overhead)

### Figures

- [x] **FIG-01**: Generate accuracy degradation curves (noise level x accuracy, by model and intervention)
- [x] **FIG-02**: Generate stability-correctness quadrant plots
- [x] **FIG-03**: Generate cost-benefit heatmaps showing net token savings by condition
- [x] **FIG-04**: Generate Kendall's tau rank-order stability visualization

### Micro-Formatting Experiment Design

- [x] **MFMT-01**: Decompose all 6 Phase 10 hypotheses (H-FMT-01 through H-FMT-06) into atomic, independently executable test questions with self-contained experiment specs
- [x] **MFMT-02**: Brainstorm new micro-formatting ideas across 4 categories (whitespace/layout, code-specific formatting, instruction phrasing, structural markers) with full specs for top 3-5 ideas
- [x] **MFMT-03**: Create tiered execution plan (Tier 1/2/3) with cumulative cost estimates, model escalation strategy, and cross-cluster bundling opportunities
- [x] **MFMT-04**: Each atomic test question includes all required fields: claim, variables, benchmarks, prompt count, models, cost, conversion method, statistical analysis, success criteria, pilot protocol
- [x] **MFMT-05**: Organize experiment specs into topic-cluster files in docs/experiments/ with README index

### Guided Setup Wizard

- [x] **SETUP-01**: Persist experiment configuration as JSON file (experiment_config.json) in project directory with sparse override pattern -- only user-changed values stored, missing keys fall back to ExperimentConfig defaults
- [x] **SETUP-02**: Validate config on load -- model strings match PRICE_TABLE keys, noise rates in [0,1], repetitions >= 1, temperature >= 0, data paths exist
- [x] **SETUP-03**: CLI entry point (src/cli.py) with argparse subparsers architecture extensible for Phase 14 config subcommands
- [x] **SETUP-04**: Interactive setup wizard (src/cli.py setup) guiding provider selection, model auto-fill from PREPROC_MODEL_MAP, path configuration, and config file generation
- [x] **SETUP-05**: API key validation via minimal test call (~$0.001) distinguishing auth errors from network/transient errors
- [x] **SETUP-06**: Environment prerequisite check -- Python >= 3.11, required packages installed, API key env vars set and non-empty
- [x] **SETUP-07**: Config-missing guard in run_experiment.py and pilot.py -- prints guidance message and exits if no config file found (does NOT auto-launch wizard)

### CLI Config Subcommands

- [x] **CFG-SHOW**: show-config subcommand displaying all properties in terminal table with Value/Default columns, `*` modified indicator, `--json`/`--changed`/`--verbose` flags, and single-property query mode
- [x] **CFG-SET**: set-config subcommand accepting multiple key-value pairs with auto type coercion from ExperimentConfig defaults, immediate validation, sparse config file auto-creation, and change summary output
- [x] **CFG-RESET**: reset-config subcommand removing overrides from sparse config file, with `--all` flag to reset entire config to defaults
- [x] **CFG-VALIDATE**: validate subcommand running validate_config on current effective config with exit code 0/non-zero
- [x] **CFG-DIFF**: diff subcommand showing only properties that differ from defaults in a diff-like format
- [x] **CFG-MODELS**: list-models subcommand printing all valid model strings from PRICE_TABLE with pricing info
- [x] **CFG-ENTRY**: Register `propt` as pyproject.toml console_scripts entry point (`propt = "src.cli:main"`)
- [x] **CFG-COMPLETE**: Shell tab completion for property names in set-config/show-config/reset-config via argcomplete

### Pre-Execution Confirmation Gate

- [x] **GATE-COST**: Static cost estimation from PRICE_TABLE using average token counts per benchmark (HumanEval ~500in/200out, GSM8K ~300in/100out) with separate target model and pre-processor cost line items
- [x] **GATE-RUNTIME**: Runtime estimation from RATE_LIMIT_DELAYS x number of calls per model, displayed as wall-clock lower bound
- [x] **GATE-SUMMARY**: Structured pre-execution summary with aligned columns showing per-model/per-intervention/per-noise-type counts and cost estimates, numbers only (no bar charts)
- [x] **GATE-CONFIRM**: Three-way confirmation prompt (Yes/No/Modify) after summary display with input_fn injection for testability
- [x] **GATE-BUDGET**: --budget flag exits non-zero if estimated cost exceeds threshold, checked before --yes auto-accept
- [x] **GATE-PLAN**: Save pre-execution summary to results/execution_plan.json with timestamp, item counts, cost projection, models, filters
- [x] **GATE-RESUME**: Show completed vs remaining counts when resuming a partial run, with adjusted cost for remaining items only
- [ ] **GATE-CLI-RUN**: `propt run` subcommand with --model, --limit, --retry-failed, --db, --yes, --budget, --dry-run, --intervention flags
- [ ] **GATE-CLI-PILOT**: `propt pilot` subcommand with --yes, --budget, --dry-run, --db flags wrapping pilot.py
- [ ] **GATE-DRYRUN**: --dry-run shows summary only and exits without executing (replaces old _show_dry_run)
- [ ] **GATE-PROGRESS**: tqdm progress bar during execution showing completion %, items done/total, ETA, cost-so-far
- [ ] **GATE-WIRE**: Confirmation gate integrated into both run_experiment.py run_engine() and pilot.py run_pilot()
- [ ] **GATE-TQDM**: tqdm added to pyproject.toml dependencies
- [ ] **GATE-TEST**: Unit tests for cost estimation, runtime estimation, summary formatting, confirmation gate, execution plan saving, and CLI subcommand registration

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Models

- **EXT-01**: Support for GPT-4 and open-source models (Llama)
- **EXT-02**: British English variant study

### Extended Interventions

- **EXTV-01**: Meta-prompting intervention (AI-rewritten "ideal" prompts)
- **EXTV-02**: Optional 30% noise level if pilot suggests cliff between 20-30%

### Extended Analysis

- **EXTA-01**: Per-L1 ESL pattern breakdown (requires more data)
- **EXTA-02**: Noise-aware prompt design guidelines for practitioners

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI or API server | CLI-only research tool for single researcher |
| Real-time streaming inference | Batch execution sufficient for research question |
| Adversarial/jailbreak testing | Paper focuses on unintentional human noise, not attacks |
| Fine-tuning noise-resistant models | Different paper; our contribution is measurement + intervention |
| Noise rates above 20% | Text unreadable at 40%+; interesting science is 5-20% range |
| Langfuse/W&B integration | SQLite + logging sufficient; avoids external dependency |
| Support for 5+ models | Two architecturally distinct models sufficient for first paper |
| Mobile or desktop app | Command-line scripts only |
| Full 20,000-call execution via GSD | Handled outside GSD after tooling is complete |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1: Foundation and Data Infrastructure | Complete |
| DATA-02 | Phase 1: Foundation and Data Infrastructure | Complete |
| DATA-03 | Phase 1: Foundation and Data Infrastructure | Complete |
| DATA-04 | Phase 1: Foundation and Data Infrastructure | Complete |
| NOISE-01 | Phase 1: Foundation and Data Infrastructure | Complete |
| NOISE-02 | Phase 1: Foundation and Data Infrastructure | Complete |
| NOISE-03 | Phase 1: Foundation and Data Infrastructure | Complete |
| NOISE-04 | Phase 1: Foundation and Data Infrastructure | Complete |
| GRAD-01 | Phase 2: Grading Pipeline | Complete |
| GRAD-02 | Phase 2: Grading Pipeline | Complete |
| GRAD-03 | Phase 2: Grading Pipeline | Complete |
| INTV-01 | Phase 3: Interventions and Execution Engine | Complete |
| INTV-02 | Phase 3: Interventions and Execution Engine | Complete |
| INTV-03 | Phase 3: Interventions and Execution Engine | Complete |
| INTV-04 | Phase 3: Interventions and Execution Engine | Complete |
| INTV-05 | Phase 3: Interventions and Execution Engine | Complete |
| EXEC-01 | Phase 3: Interventions and Execution Engine | Complete |
| EXEC-02 | Phase 3: Interventions and Execution Engine | Complete |
| EXEC-03 | Phase 3: Interventions and Execution Engine | Complete |
| EXEC-04 | Phase 3: Interventions and Execution Engine | Complete |
| EXEC-05 | Phase 3: Interventions and Execution Engine | Complete |
| PILOT-01 | Phase 4: Pilot Validation | Complete |
| PILOT-02 | Phase 4: Pilot Validation | Complete |
| PILOT-03 | Phase 4: Pilot Validation | Complete |
| STAT-01 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| STAT-02 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| STAT-03 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| STAT-04 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| STAT-05 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| DERV-01 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| DERV-02 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| DERV-03 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| FIG-01 | Phase 6: Publication Figures | Complete |
| FIG-02 | Phase 6: Publication Figures | Complete |
| FIG-03 | Phase 6: Publication Figures | Complete |
| FIG-04 | Phase 6: Publication Figures | Complete |
| MFMT-01 | Phase 11: Brainstorm micro-formatting test questions | Planned |
| MFMT-02 | Phase 11: Brainstorm micro-formatting test questions | Planned |
| MFMT-03 | Phase 11: Brainstorm micro-formatting test questions | Planned |
| MFMT-04 | Phase 11: Brainstorm micro-formatting test questions | Planned |
| MFMT-05 | Phase 11: Brainstorm micro-formatting test questions | Planned |
| SETUP-01 | Phase 13: Guided setup wizard | Planned |
| SETUP-02 | Phase 13: Guided setup wizard | Planned |
| SETUP-03 | Phase 13: Guided setup wizard | Planned |
| SETUP-04 | Phase 13: Guided setup wizard | Planned |
| SETUP-05 | Phase 13: Guided setup wizard | Planned |
| SETUP-06 | Phase 13: Guided setup wizard | Planned |
| SETUP-07 | Phase 13: Guided setup wizard | Planned |
| CFG-SHOW | Phase 14: CLI config subcommands | Planned |
| CFG-SET | Phase 14: CLI config subcommands | Planned |
| CFG-RESET | Phase 14: CLI config subcommands | Planned |
| CFG-VALIDATE | Phase 14: CLI config subcommands | Planned |
| CFG-DIFF | Phase 14: CLI config subcommands | Planned |
| CFG-MODELS | Phase 14: CLI config subcommands | Planned |
| CFG-ENTRY | Phase 14: CLI config subcommands | Planned |
| CFG-COMPLETE | Phase 14: CLI config subcommands | Planned |
| GATE-COST | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-RUNTIME | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-SUMMARY | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-CONFIRM | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-BUDGET | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-PLAN | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-RESUME | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-CLI-RUN | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-CLI-PILOT | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-DRYRUN | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-PROGRESS | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-WIRE | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-TQDM | Phase 15: Pre-execution confirmation gate | Planned |
| GATE-TEST | Phase 15: Pre-execution confirmation gate | Planned |

**Coverage:**
- v1 requirements: 70 total
- Mapped to phases: 70
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-25 after Phase 15 planning*
