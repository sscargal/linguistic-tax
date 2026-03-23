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

- [ ] **STAT-01**: Fit GLMM with prompt-level random effects on binary pass/fail outcomes
- [ ] **STAT-02**: Compute bootstrap confidence intervals for all reported metrics
- [ ] **STAT-03**: Run McNemar's test for prompt-level fragility/recoverability analysis
- [ ] **STAT-04**: Compute Kendall's tau for rank-order stability (uniform vs. targeted tax)
- [ ] **STAT-05**: Apply Benjamini-Hochberg correction across ALL reported p-values in a single family

### Derived Metrics

- [x] **DERV-01**: Compute Consistency Rate (CR) from pairwise agreement across 5 repetitions per condition
- [x] **DERV-02**: Classify each prompt-condition pair into stability-correctness quadrant (Robust/Confidently-Wrong/Lucky/Broken)
- [x] **DERV-03**: Compute cost rollups and net ROI for optimizer interventions (savings minus pre-processor overhead)

### Figures

- [ ] **FIG-01**: Generate accuracy degradation curves (noise level x accuracy, by model and intervention)
- [ ] **FIG-02**: Generate stability-correctness quadrant plots
- [ ] **FIG-03**: Generate cost-benefit heatmaps showing net token savings by condition
- [ ] **FIG-04**: Generate Kendall's tau rank-order stability visualization

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
| STAT-01 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-02 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-03 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-04 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-05 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| DERV-01 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| DERV-02 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| DERV-03 | Phase 5: Statistical Analysis and Derived Metrics | Complete |
| FIG-01 | Phase 6: Publication Figures | Pending |
| FIG-02 | Phase 6: Publication Figures | Pending |
| FIG-03 | Phase 6: Publication Figures | Pending |
| FIG-04 | Phase 6: Publication Figures | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
