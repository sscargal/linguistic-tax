# Requirements: Linguistic Tax Research Toolkit

**Defined:** 2026-03-19
**Core Value:** Produce rigorous, reproducible experimental data showing how prompt noise degrades LLM accuracy and whether automated prompt optimization recovers it

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Infrastructure

- [ ] **DATA-01**: Curate 200 clean benchmark prompts from HumanEval, MBPP, and GSM8K with canonical problem definitions
- [ ] **DATA-02**: Build experiment matrix covering all prompt x noise x intervention combinations as self-contained work items
- [ ] **DATA-03**: Store all experimental results in SQLite with schema matching RDD Section 9.2
- [ ] **DATA-04**: Implement configuration module with pinned model versions, API settings, and seed registry

### Noise Generation

- [ ] **NOISE-01**: Generate Type A character-level noise at 5%, 10%, and 20% error rates with fixed random seeds
- [ ] **NOISE-02**: Protect technical keywords (function names, variable names, operators) from character mutation
- [ ] **NOISE-03**: Generate Type B ESL syntactic noise patterns based on L1 transfer errors (Mandarin, Spanish, Japanese, mixed)
- [ ] **NOISE-04**: Verify noise generator determinism — same seed produces identical output across runs

### Prompt Interventions

- [ ] **INTV-01**: Implement prompt compressor that removes redundancy and condenses verbose language via cheap model (Haiku/Flash)
- [ ] **INTV-02**: Implement prompt repeater using <QUERY><QUERY> duplication per Leviathan et al.
- [ ] **INTV-03**: Implement self-correct prompt prefix intervention (zero-overhead prompt engineering)
- [ ] **INTV-04**: Implement pre-processor pipeline that sanitizes noisy prompts via cheap model before sending to target model
- [ ] **INTV-05**: Build intervention router that dispatches to Raw/Self-Correct/Pre-Proc Sanitize/Sanitize+Compress/Repetition

### Experiment Execution

- [ ] **EXEC-01**: Execute prompts against Claude Sonnet and Gemini 1.5 Pro APIs with temperature=0.0
- [ ] **EXEC-02**: Log every API call with: prompt text, response text, model version, token counts (in/out), TTFT, TTLT, cost, timestamp
- [ ] **EXEC-03**: Run 5 repetitions per condition for stability measurement
- [ ] **EXEC-04**: Implement resumable execution — skip already-completed work items on restart
- [ ] **EXEC-05**: Implement proactive rate limiting to avoid API throttling

### Grading

- [ ] **GRAD-01**: Auto-grade HumanEval/MBPP outputs via sandboxed subprocess code execution with timeout and resource limits
- [ ] **GRAD-02**: Auto-grade GSM8K outputs via regex extraction of final numerical answer with format-variant handling
- [ ] **GRAD-03**: Record pass/fail result for every experimental run in SQLite

### Pilot Validation

- [ ] **PILOT-01**: Run pilot experiment with 20 prompts across all conditions to validate full pipeline end-to-end
- [ ] **PILOT-02**: Verify grading accuracy via manual spot-check of pilot results
- [ ] **PILOT-03**: Generate cost projection for full experiment run from pilot data

### Statistical Analysis

- [ ] **STAT-01**: Fit GLMM with prompt-level random effects on binary pass/fail outcomes
- [ ] **STAT-02**: Compute bootstrap confidence intervals for all reported metrics
- [ ] **STAT-03**: Run McNemar's test for prompt-level fragility/recoverability analysis
- [ ] **STAT-04**: Compute Kendall's tau for rank-order stability (uniform vs. targeted tax)
- [ ] **STAT-05**: Apply Benjamini-Hochberg correction across ALL reported p-values in a single family

### Derived Metrics

- [ ] **DERV-01**: Compute Consistency Rate (CR) from pairwise agreement across 5 repetitions per condition
- [ ] **DERV-02**: Classify each prompt-condition pair into stability-correctness quadrant (Robust/Confidently-Wrong/Lucky/Broken)
- [ ] **DERV-03**: Compute cost rollups and net ROI for optimizer interventions (savings minus pre-processor overhead)

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
| DATA-01 | Phase 1: Foundation and Data Infrastructure | Pending |
| DATA-02 | Phase 1: Foundation and Data Infrastructure | Pending |
| DATA-03 | Phase 1: Foundation and Data Infrastructure | Pending |
| DATA-04 | Phase 1: Foundation and Data Infrastructure | Pending |
| NOISE-01 | Phase 1: Foundation and Data Infrastructure | Pending |
| NOISE-02 | Phase 1: Foundation and Data Infrastructure | Pending |
| NOISE-03 | Phase 1: Foundation and Data Infrastructure | Pending |
| NOISE-04 | Phase 1: Foundation and Data Infrastructure | Pending |
| GRAD-01 | Phase 2: Grading Pipeline | Pending |
| GRAD-02 | Phase 2: Grading Pipeline | Pending |
| GRAD-03 | Phase 2: Grading Pipeline | Pending |
| INTV-01 | Phase 3: Interventions and Execution Engine | Pending |
| INTV-02 | Phase 3: Interventions and Execution Engine | Pending |
| INTV-03 | Phase 3: Interventions and Execution Engine | Pending |
| INTV-04 | Phase 3: Interventions and Execution Engine | Pending |
| INTV-05 | Phase 3: Interventions and Execution Engine | Pending |
| EXEC-01 | Phase 3: Interventions and Execution Engine | Pending |
| EXEC-02 | Phase 3: Interventions and Execution Engine | Pending |
| EXEC-03 | Phase 3: Interventions and Execution Engine | Pending |
| EXEC-04 | Phase 3: Interventions and Execution Engine | Pending |
| EXEC-05 | Phase 3: Interventions and Execution Engine | Pending |
| PILOT-01 | Phase 4: Pilot Validation | Pending |
| PILOT-02 | Phase 4: Pilot Validation | Pending |
| PILOT-03 | Phase 4: Pilot Validation | Pending |
| STAT-01 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-02 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-03 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-04 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| STAT-05 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| DERV-01 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| DERV-02 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
| DERV-03 | Phase 5: Statistical Analysis and Derived Metrics | Pending |
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
