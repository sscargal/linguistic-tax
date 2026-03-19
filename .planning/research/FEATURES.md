# Feature Research

**Domain:** LLM prompt noise/robustness research toolkit for ArXiv paper
**Researched:** 2026-03-19
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Reviewers Expect These)

Features that ArXiv/peer reviewers assume exist. Missing these = paper rejected or "major revisions."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deterministic noise injection with fixed seeds | Reproducibility is non-negotiable for any empirical NLP paper. PromptBench and TextFlint both use deterministic perturbations. | MEDIUM | Two generators: Type A (character-level at 5/10/20%) and Type B (ESL syntactic). Must protect technical keywords from mutation. Seed must produce identical output across runs. |
| Multiple noise granularity levels | Papers like MulTypo (2025) and Gan et al. (2024) test across noise rates. A single noise level is insufficient to identify threshold effects. | LOW | 5%, 10%, 20% character error rates for Type A. Single ESL pattern set for Type B. Optional 30% if pilot suggests cliff between 20-30%. |
| Standard benchmark evaluation (HumanEval, MBPP, GSM8K) | Reviewers expect recognized benchmarks with known baselines. Custom-only benchmarks invite "not comparable" critique. | MEDIUM | 200 prompts sampled across three benchmarks. Must use canonical problem definitions, not modified versions. |
| Automated pass/fail grading | Manual grading of 20,000 outputs is impossible and introduces subjectivity. Every robustness paper automates this. | HIGH | HumanEval/MBPP require sandboxed code execution (security-critical). GSM8K uses regex extraction of final numerical answer. Must handle edge cases: timeouts, runtime errors, partial outputs. |
| Multiple model comparison | Single-model results are anecdotal. Reviewers expect at minimum 2 models from different providers to show generalizability. | LOW | Claude Sonnet + Gemini 1.5 Pro. Pin exact version strings. Different architectures (dense vs. MoE) strengthens generalizability claim. |
| Multiple repetitions per condition | A single run per condition conflates noise effects with LLM sampling variance. PromptSuite (2025) explicitly measures variance across prompt variations. | LOW | 5 repetitions per condition at temperature=0.0. Even at temp=0, API outputs are not perfectly deterministic due to batching/quantization. |
| Proper statistical testing beyond t-tests | NIST AI 800-3 (Feb 2026) recommends GLMMs for LLM evaluation. Papers using only t-tests face "insufficient statistical rigor" criticism. | HIGH | GLMM with prompt-level random effects, Benjamini-Hochberg correction for multiple comparisons, bootstrap CIs. statsmodels MixedLM implementation. |
| Baseline (clean prompt) measurement | Without clean baselines, noise degradation cannot be quantified. Every perturbation study includes unperturbed controls. | LOW | Clean prompts run through identical pipeline (same models, same repetitions, same grading). |
| Full experiment logging | Reviewers may ask "how long did inference take?" or "what was the cost?" Incomplete logs prevent answering. | MEDIUM | Every API call logs: prompt text, response text, model version, temperature, token counts (input/output), TTFT, TTLT, cost, timestamp, pass/fail. SQLite storage. |
| Pilot study before full run | Running 20,000 API calls without validation is reckless. Pilot validates tooling, catches bugs, estimates costs. | LOW | 20 prompts across all conditions. Validates: noise generation, API calls, grading, storage, cost estimates. |

### Differentiators (Competitive Advantage for the Paper)

Features that set this paper apart from PromptBench, MulTypo, and other perturbation studies.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Stability-Correctness decomposition (4-quadrant analysis) | Most robustness papers measure only accuracy drops. Decomposing into Robust/Confidently-Wrong/Lucky/Broken is novel and actionable. The "Confidently Wrong" quadrant (stable but incorrect) is the paper's most dangerous finding. | MEDIUM | Requires Consistency Rate (CR) computed from pairwise agreement across 5 runs. Classify each prompt-condition pair into quadrant based on CR threshold (0.8) and majority-vote correctness. |
| ESL penalty quantification (Type B noise) | Existing perturbation studies focus on typos (character-level). Quantifying the "ESL tax" -- that syntactic errors from L1 transfer cause MORE degradation than equivalent character noise -- has equity implications and policy relevance. | HIGH | ESL patterns must be linguistically validated against L2 English error corpora (Cambridge Learner Corpus categories). Rule-based templates for Mandarin, Spanish, Japanese, and mixed ESL patterns. Reviewers will scrutinize linguistic accuracy. |
| Head-to-head intervention comparison (5 strategies) | Most papers test one fix. Comparing Raw vs. Self-Correct vs. Pre-Proc Sanitize vs. Sanitize+Compress vs. Prompt Repetition in the same matrix provides direct actionability. The Prompt Repetition comparison (Leviathan et al., 2025) is particularly timely. | MEDIUM | 5 intervention columns in factorial design. Self-Correct is zero-overhead (prompt prefix). Prompt Repetition doubles tokens but needs no external call. Pre-Proc interventions require cheap-model API calls (Haiku/Flash). |
| Net cost-benefit analysis (token ROI) | Papers typically report accuracy only. Showing that the optimizer produces BETTER results AND costs LESS (net savings after pre-processor overhead) is the headline finding for practitioners. | MEDIUM | Track token costs for pre-processor calls separately. Compute net savings = (tokens saved on main call) - (tokens consumed by pre-processor). Report break-even noise level where optimizer pays for itself. |
| Compression study (independent experiment) | Most noise papers ignore bloat. Showing that clean prompts contain 20-40% redundancy and compression preserves accuracy adds a second publishable contribution to the same paper. | MEDIUM | Separate from noise experiment. Compress clean prompts, measure token reduction, accuracy delta, and BERTScore of outputs vs. uncompressed baseline. |
| Rank-order stability (Kendall's tau) | Tests whether noise is a "uniform tax" (all prompts suffer equally) or a "targeted tax" (certain prompt structures are disproportionately fragile). The targeted tax finding is more interesting and actionable. | LOW | Rank prompts by pass rate under clean, then under each noisy condition. Compute Kendall's tau. Low tau = targeted vulnerability = actionable insight for prompt design. |
| Real-world noisy prompt validation | 20 real noisy prompts from public sources (forums, Stack Overflow) provide ecological validity beyond synthetic noise. | LOW | Small sample but validates that synthetic noise patterns match real-world noise. Qualitative comparison only -- too few for statistical power. |

### Anti-Features (Deliberately NOT Building)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Support for 5+ LLM providers | "More models = more generalizable" | Multiplies experiment matrix without proportional insight. 20,000 calls becomes 50,000+. Budget and timeline explode. Two architecturally distinct models (dense vs. MoE) suffice for a first paper. | Test 2 models. Flag model breadth as explicit future work in Section 23 of the paper. |
| Interactive web UI for experiment management | "Easier to monitor runs" | This is a single-researcher CLI tool, not a product. UI development time competes with research time. | Use SQLite queries + logging output. A simple `python run_experiment.py --status` command suffices. |
| Real-time streaming inference | "More realistic usage pattern" | Streaming adds complexity (partial response handling, token counting mid-stream) without changing the accuracy measurement. Batch mode is simpler and equally valid for the research question. | Batch execution with full response capture. |
| Adversarial/jailbreak prompt testing | "PromptBench does this" | PromptBench's adversarial attacks target model safety. Our paper is about *unintentional* human noise, not adversarial attacks. Conflating the two weakens the contribution claim. | Explicitly scope to unintentional noise (typos, ESL patterns, bloat). Cite PromptBench as related but distinct work. |
| Custom fine-tuning of noise-resistant models | "If noise hurts, train against it" | Fine-tuning is a completely different paper. Our contribution is measurement + lightweight intervention, not model modification. | Recommend noise-aware fine-tuning as future work. |
| Noise rates above 20% | "Test to destruction" | At 40%+ noise, text is unreadable even to humans. MulTypo (2025) showed performance collapses uninformatively at high rates. The interesting science is the 5-20% threshold region. | Cap at 20%. Add optional 30% only if pilot data suggests the cliff falls between 20-30%. |
| Semantic similarity as primary metric | "BERTScore for everything" | For code generation (HumanEval/MBPP), semantic similarity is meaningless -- code either passes tests or it does not. For GSM8K, the final number is either right or wrong. | Use pass/fail as primary metric. BERTScore only for compression study (measuring output preservation). |
| Langfuse/W&B integration for experiment tracking | "Industry standard observability" | Adds external dependency and complexity for a research project that runs once. SQLite + Python logging is sufficient and self-contained. | SQLite database with structured schema. All data stays local, queryable with standard SQL. |

## Feature Dependencies

```
[Benchmark Prompts (200 clean)]
    |
    +--requires--> [Noise Generator Type A] --enables--> [Experiment Matrix Cells 1-5]
    |
    +--requires--> [Noise Generator Type B] --enables--> [Experiment Matrix Cells 6-10]
    |
    +--requires--> [Prompt Compressor] --enables--> [Compression Study (Exp 2)]
    |
    +--requires--> [Prompt Repeater] --enables--> [Repetition Intervention (Cells 5, 10)]

[Experiment Harness]
    +--requires--> [API Client (Claude + Gemini)]
    +--requires--> [SQLite Schema + Logging]
    +--requires--> [Noise Generator Type A]
    +--requires--> [Noise Generator Type B]
    +--requires--> [Prompt Compressor]
    +--requires--> [Prompt Repeater]

[Automated Grading]
    +--requires--> [HumanEval Sandbox] (sandboxed code execution)
    +--requires--> [GSM8K Regex Matcher]
    +--requires--> [Experiment results in SQLite]

[Statistical Analysis]
    +--requires--> [Graded Results in SQLite]
    +--requires--> [GLMM Implementation]
    +--requires--> [Bootstrap CI Implementation]
    +--requires--> [McNemar's Test Implementation]
    +--requires--> [Kendall's Tau Implementation]
    +--requires--> [BH Correction Implementation]

[Derived Metrics]
    +--requires--> [Statistical Analysis]
    +--requires--> [Consistency Rate (CR) computation]
    +--requires--> [Quadrant Classification]
    +--requires--> [Cost Rollups]

[Publication Figures]
    +--requires--> [Derived Metrics]
    +--requires--> [Statistical Analysis]
```

### Dependency Notes

- **Noise generators must be built and tested before experiment harness:** The harness calls generators to create noisy variants. Generators must be deterministic (verified by unit tests) before any experiments run.
- **Grading requires sandboxed execution:** HumanEval code execution is a security concern. The sandbox must be built and tested independently before processing 20,000 code outputs.
- **Statistical analysis requires ALL graded results:** GLMM fits across the full dataset. Partial data analysis is possible for pilot validation but final analysis needs complete results.
- **Pilot study validates the full pipeline end-to-end:** Pilot (20 prompts) must exercise every component: noise generation, API calls, grading, storage, basic analysis. Build pipeline components first, then pilot, then full run.
- **Compression study is independent of noise study:** Can be run in parallel or sequentially. Shares benchmark prompts and grading infrastructure but has no dependency on noise generators.

## MVP Definition

### Phase 1: Core Pipeline (build first)

- [ ] **Benchmark prompt curation (200 prompts)** -- everything downstream depends on this
- [ ] **Noise Generator Type A (character-level)** -- core experimental variable
- [ ] **Noise Generator Type B (ESL syntactic)** -- core experimental variable
- [ ] **SQLite schema and logging infrastructure** -- must exist before any API calls
- [ ] **API client wrappers (Claude + Gemini)** -- with full instrumentation (TTFT, TTLT, tokens, cost)
- [ ] **Experiment harness (run_experiment.py)** -- orchestrates noise + API + storage
- [ ] **Auto-grading (HumanEval sandbox + GSM8K regex)** -- must grade before analysis

### Phase 2: Interventions + Pilot (validate the approach)

- [ ] **Prompt compressor** -- needed for Sanitize+Compress intervention
- [ ] **Prompt repeater** -- needed for Prompt Repetition intervention
- [ ] **Self-correct prompt prefix** -- trivial but must be standardized
- [ ] **Pre-processor pipeline (cheap model sanitize/compress)** -- Haiku/Flash API calls
- [ ] **Pilot run (20 prompts, all conditions)** -- validates entire pipeline end-to-end
- [ ] **Basic result inspection** -- verify grading accuracy, check for obvious bugs

### Phase 3: Analysis + Figures (after full experiment)

- [ ] **GLMM analysis** -- primary statistical test
- [ ] **Bootstrap confidence intervals** -- for all reported metrics
- [ ] **McNemar's test (prompt-level)** -- identifies fragile/recoverable prompts
- [ ] **BH multiple comparison correction** -- applied to all p-values
- [ ] **Kendall's tau (rank-order stability)** -- uniform vs. targeted tax
- [ ] **Consistency Rate + quadrant classification** -- stability-correctness decomposition
- [ ] **Cost rollups and ROI calculation** -- net benefit of optimizer
- [ ] **Publication-quality figures** -- heatmaps, degradation curves, quadrant plots, cost charts

### Future Consideration (post-paper)

- [ ] **Meta-prompting intervention** -- AI-rewritten "ideal" prompts. Test in pilot; add to full experiment only if results are promising.
- [ ] **Additional models (GPT-4, Llama)** -- future work for breadth
- [ ] **British English variant study** -- future work per RDD Section 23
- [ ] **Fine-grained ESL pattern analysis** -- per-L1 breakdown (requires more data)
- [ ] **Noise-aware prompt design guidelines** -- practitioner-facing output derived from findings

## Feature Prioritization Matrix

| Feature | Research Value | Implementation Cost | Priority |
|---------|---------------|---------------------|----------|
| Noise Generator Type A | HIGH | MEDIUM | P1 |
| Noise Generator Type B (ESL) | HIGH | HIGH | P1 |
| Benchmark prompt curation | HIGH | MEDIUM | P1 |
| Auto-grading (sandbox + regex) | HIGH | HIGH | P1 |
| API client wrappers with instrumentation | HIGH | MEDIUM | P1 |
| Experiment harness | HIGH | MEDIUM | P1 |
| SQLite schema + logging | HIGH | MEDIUM | P1 |
| Prompt compressor | HIGH | MEDIUM | P2 |
| Prompt repeater | MEDIUM | LOW | P2 |
| Pre-processor pipeline | HIGH | MEDIUM | P2 |
| Pilot run (20 prompts) | HIGH | LOW | P2 |
| GLMM analysis | HIGH | HIGH | P3 |
| Bootstrap CIs | HIGH | MEDIUM | P3 |
| McNemar's test | MEDIUM | LOW | P3 |
| Kendall's tau | MEDIUM | LOW | P3 |
| BH correction | HIGH | LOW | P3 |
| Consistency Rate + quadrants | HIGH | MEDIUM | P3 |
| Cost rollups + ROI | MEDIUM | LOW | P3 |
| Publication figures | HIGH | MEDIUM | P3 |
| BERTScore (compression study) | MEDIUM | LOW | P3 |

**Priority key:**
- P1: Must build first -- everything depends on these
- P2: Build second -- interventions and validation
- P3: Build after experiments complete -- analysis and output

## Competitor/Related Work Feature Analysis

| Feature | PromptBench (Microsoft) | TextFlint | MulTypo (2025) | Our Approach |
|---------|------------------------|-----------|----------------|--------------|
| Noise types | Character, word, sentence, semantic (adversarial focus) | WordNet synonyms, keyboard typos | Character-level typos at 10%, 40% | Character-level (5/10/20%) + ESL syntactic patterns. Non-adversarial focus is our differentiator. |
| Benchmarks | SST-2, MNLI, SQuAD, IWSLT, math | General NLU tasks | GSM8K | HumanEval, MBPP, GSM8K. Code + math reasoning, not NLU classification. |
| Intervention testing | None (measurement only) | None (measurement only) | None (measurement only) | 5 interventions compared head-to-head. This is the core differentiator. |
| Stability measurement | Not measured | Not measured | Not measured | 5 repetitions, CR metric, 4-quadrant decomposition. Novel contribution. |
| Cost analysis | Not measured | Not measured | Not measured | Full token cost tracking with net ROI calculation. |
| Statistical methods | Basic accuracy comparison | Accuracy + F1 | Accuracy comparison | GLMM, bootstrap CI, McNemar's, Kendall's tau, BH correction. Most rigorous in this space. |
| Ecological validity | Synthetic adversarial only | Synthetic only | Synthetic only | Synthetic + 20 real-world noisy prompts. |

## Sources

- [PromptBench (Microsoft)](https://github.com/microsoft/promptbench) -- unified LLM robustness evaluation framework
- [PromptSuite: Task-Agnostic Multi-Prompt Generation](https://arxiv.org/html/2507.14913v4) -- prompt sensitivity measurement
- [Enterprise Perturbation Robustness Benchmark](https://arxiv.org/abs/2601.06341) -- enterprise-focused perturbation consistency
- [When Punctuation Matters: Prompt Robustness Methods](https://arxiv.org/html/2508.11383v1) -- large-scale robustness comparison
- [LLM Robustness Against Perturbation (Nature Scientific Reports)](https://www.nature.com/articles/s41598-025-29770-0) -- perturbation impact on LLMs
- [EvalPlus (HumanEval/MBPP)](https://github.com/evalplus/evalplus) -- rigorous code evaluation with expanded test cases
- [EleutherAI lm-evaluation-harness](https://slyracoon23.github.io/blog/posts/2025-03-21_eleutherai-evaluation-methods.html) -- standard evaluation framework
- [Langfuse Token and Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking) -- LLM observability reference (decided against integrating)
- [GLMM Reporting Best Practices (Frontiers)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.666182/full) -- GLMM reporting standards

---
*Feature research for: LLM prompt noise/robustness research toolkit*
*Researched: 2026-03-19*
