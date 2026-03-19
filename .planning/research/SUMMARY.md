# Project Research Summary

**Project:** Linguistic Tax -- LLM Prompt Noise/Optimization Research Toolkit
**Domain:** Empirical NLP research pipeline (ArXiv paper)
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

This project is a batch-processing research pipeline that measures how typos, ESL grammatical errors, and verbose prompts degrade LLM reasoning accuracy, then tests whether lightweight interventions (sanitization, compression, prompt repetition) can recover lost performance. The standard approach for this type of empirical NLP study is a deterministic pipeline: curate benchmark prompts, inject controlled noise, send prompts through multiple LLM APIs with full instrumentation, auto-grade results, and run rigorous statistical analysis. The RDD (v4.0) is a thorough spec that already addresses most design questions -- the implementation task is to build exactly what it describes, not to invent new approaches.

The recommended approach is a sequential, module-per-file Python pipeline with SQLite as the single integration point between stages. The stack is well-constrained: Python 3.11+, direct Anthropic and Google SDK calls (no LangChain), statsmodels for GLMM, and subprocess-based sandboxing for code execution. One critical migration is required immediately: the `google-generativeai` package in `pyproject.toml` is deprecated (support ended Nov 2025) and must be replaced with `google-genai`. Since no code exists yet beyond `__init__.py`, this is a clean start with no migration cost.

The top risks are: (1) HumanEval sandbox security -- executing 16,000+ LLM-generated code snippets requires robust process isolation, not just timeouts; (2) GSM8K grading fragility -- regex extraction of numerical answers produces false positives/negatives that can invalidate results; (3) noise injection corrupting prompt semantics at 20% noise level, confounding noise resilience with specification change; and (4) multiple comparisons inflation across hundreds of statistical tests. All four risks are manageable with upfront investment in validation (test suites for grading, semantic similarity checks for noise, BH correction built into the analysis pipeline from day one).

## Key Findings

### Recommended Stack

The stack is Python-native with two external API integrations. No web framework, no orchestration layer, no message queue. The heaviest dependency is `bert-score` (pulls in PyTorch + transformers at ~2GB) but it is required by the RDD for the compression study. All other dependencies are standard scientific Python.

**Core technologies:**
- **Python 3.11+ / uv:** Runtime and package management already in use. No reason to upgrade to 3.12+.
- **anthropic >= 0.86.0:** Official Claude SDK. Pin minimum version for structured responses and automatic retries.
- **google-genai >= 1.66.0:** Official Gemini SDK (replaces deprecated `google-generativeai`). Avoid 1.67.0 due to typing-extensions bug.
- **statsmodels >= 0.14.4:** GLMM via `BinomialBayesMixedGLM`, BH correction via `multipletests`. Fallback to `MixedLM` or logistic regression if convergence fails.
- **SQLite (stdlib):** Results storage. WAL mode for concurrent reads during analysis. No external DB dependency.
- **subprocess sandbox:** HumanEval/MBPP code execution. Docker/firejail for stronger isolation if needed. Never `exec()` in the main process.

**Critical action:** Replace `google-generativeai` with `google-genai` in `pyproject.toml` before writing any code. The import path, client initialization, and response structure all differ.

### Expected Features

**Must have (table stakes -- reviewers reject without these):**
- Deterministic noise injection with fixed seeds (Type A character-level at 5/10/20%, Type B ESL syntactic)
- Standard benchmark evaluation (HumanEval, MBPP, GSM8K -- 200 prompts)
- Automated pass/fail grading (sandboxed code execution + regex math grading)
- Multiple model comparison (Claude Sonnet + Gemini 1.5 Pro, pinned versions)
- 5 repetitions per condition at temperature=0.0
- GLMM with BH correction (not just t-tests)
- Clean prompt baselines
- Full experiment logging (every API call: tokens, timing, cost, pass/fail)
- Pilot study (20 prompts) before full run

**Should have (differentiators -- what makes this paper publishable):**
- Stability-Correctness 4-quadrant decomposition (Robust/Confidently-Wrong/Lucky/Broken)
- ESL penalty quantification with linguistic validation
- Head-to-head comparison of 5 intervention strategies
- Net cost-benefit analysis with token ROI
- Compression study as independent contribution
- Kendall's tau rank-order stability analysis

**Defer (post-paper):**
- Additional models (GPT-4, Llama)
- Meta-prompting intervention
- British English variant study
- Interactive UI or web dashboard

### Architecture Approach

A flat, sequential batch pipeline with SQLite as the integration point. Five stages flow left-to-right: data preparation (noise generation + matrix building), intervention routing, API execution with instrumentation, grading, and post-hoc analysis. Each stage is a standalone Python module in a flat `src/` layout (10-12 files, no packages). The experiment matrix is materialized as a JSON file of self-contained work items; the execution engine processes items one-by-one and skips already-completed items for resumability.

**Major components:**
1. **Noise Generator** -- inject Type A (character) and Type B (ESL syntactic) noise with deterministic seeds
2. **Intervention Router** -- dispatch to Raw/Self-Correct/Pre-Proc Sanitize/Sanitize+Compress/Repetition
3. **Execution Engine** -- iterate matrix, call intervention + API + grader, write to SQLite
4. **Grader** -- HumanEval sandbox execution + GSM8K regex extraction (separate implementations behind common interface)
5. **Derived Metrics** -- post-execution computation of CR, quadrant classification, cost rollups (idempotent, separate from execution)
6. **Statistical Analysis** -- GLMM, bootstrap CIs, McNemar's, Kendall's tau, BH correction

### Critical Pitfalls

1. **HumanEval sandbox security** -- LLM-generated code can contain infinite loops, fork bombs, or file I/O. Use subprocess with timeout + resource limits + process group kill. Stress-test with adversarial code before pilot.
2. **GSM8K regex extraction fragility** -- models produce answers in varied formats (prose, LaTeX, units). Use two-stage extraction with fallback regex and number normalization. Build a 20+ variant test suite before pilot.
3. **Noise corrupts semantics at 20%** -- character mutations can change prompt meaning, not just surface form. Run semantic similarity checks on noisy prompts; protect semantically critical terms; manually review a sample at 20% noise.
4. **Multiple comparisons inflation** -- hundreds of tests at alpha=0.05 produce ~25 spurious significant results. Apply BH correction across ALL reported p-values in a single call. Build correction into the analysis pipeline, not as a post-hoc step.
5. **Seed management across pipeline** -- global `random.seed()` breaks when modules interact. Use independent `random.Random(seed)` instances per randomness source with a seed registry in config.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation and Data Infrastructure

**Rationale:** Everything downstream depends on the database schema, configuration, noise generators, and benchmark prompts. These have zero external dependencies and can be fully unit-tested without API calls.
**Delivers:** Config module, SQLite schema + helpers, noise generators (Type A + B), benchmark prompt curation (200 prompts), experiment matrix builder.
**Addresses:** Deterministic noise injection, clean baselines, seed management, benchmark curation.
**Avoids:** Seed management pitfall (establish seed registry from day one), noise semantic corruption pitfall (build semantic similarity checks into noise generator validation).

### Phase 2: API Clients and Grading

**Rationale:** The API client and grading modules are the two highest-risk components (security, reliability, cost) and must be hardened before any experiment runs. Building them before the execution engine allows isolated testing.
**Delivers:** Unified API client (Anthropic + Gemini) with full instrumentation, HumanEval sandbox grader, GSM8K regex grader, grading test suites.
**Addresses:** Multiple model comparison, automated grading, full experiment logging.
**Avoids:** HumanEval sandbox security pitfall (stress-test before pilot), GSM8K regex pitfall (validate against format variants), API rate limit pitfall (build proactive rate limiting).

### Phase 3: Interventions and Execution Engine

**Rationale:** With foundation, API client, and grading in place, the execution engine is a thin orchestrator. Interventions (compressor, repeater, self-correct prefix, pre-processor pipeline) must be built before the engine can process the full matrix.
**Delivers:** Prompt compressor, prompt repeater, intervention router, execution engine with resumability, pre-processor pipeline (cheap model calls).
**Addresses:** 5 intervention strategies, pilot study capability, cost tracking.
**Avoids:** Coupling intervention logic into execution engine (keep separate), pre-processor cost accounting pitfall (log all costs from first call), prompt repetition cost pitfall (track doubled input tokens).

### Phase 4: Pilot Validation

**Rationale:** The pilot (20 prompts, all conditions) is the cheapest way to validate the entire pipeline end-to-end before committing to the $300-500 full run. Every pitfall prevention strategy must be verified here.
**Delivers:** Pilot results in SQLite, validated grading accuracy, cost estimates for full run, baseline CR measurements, confirmation that noise does not corrupt semantics excessively.
**Addresses:** Pilot study requirement, cost control, pipeline validation.
**Avoids:** All pitfalls are verified at pilot scale. Specific checks: seed determinism (rerun produces identical output), grading accuracy (manual spot-check), cost projections (within budget), sandbox containment (no escapes during pilot).

### Phase 5: Full Experiment Execution

**Rationale:** With a validated pipeline, execute the full ~20,000-call matrix. This is a multi-hour unattended run requiring robust logging, resumability, and rate limiting.
**Delivers:** Complete results database (~20K rows), all 5 repetitions for all conditions, comprehensive cost and timing logs.
**Addresses:** All table-stakes features exercised at full scale.
**Avoids:** API rate limit bias (randomize prompt order, interleave models), model version drift (pin exact version strings), cost overrun (monitor against pilot projections).

### Phase 6: Analysis and Figures

**Rationale:** All analysis requires complete (or near-complete) experimental data. GLMM fits across the full dataset; partial analysis is only valid for pilot checks.
**Delivers:** Derived metrics (CR, quadrants, cost rollups), GLMM results, bootstrap CIs, McNemar's tests, Kendall's tau, BH-corrected p-values, publication-quality figures.
**Addresses:** All differentiator features (4-quadrant decomposition, ESL penalty quantification, cost-benefit analysis, rank-order stability), compression study (BERTScore).
**Avoids:** Multiple comparisons pitfall (single BH correction across all tests), temperature non-determinism pitfall (report baseline CR and measure degradation relative to it).

### Phase Ordering Rationale

- **Phases 1-2 are parallelizable internally** but must both complete before Phase 3. Noise generators, API clients, and graders have no dependencies on each other.
- **Phase 3 depends on Phases 1-2** because the execution engine orchestrates noise generation, intervention routing, API calls, and grading.
- **Phase 4 (pilot) is a hard gate.** No full run without successful pilot. This is the cheapest place to find bugs.
- **Phase 5 is the longest elapsed-time phase** (~5-10 hours of API calls) but the least code to write -- just running the validated pipeline.
- **Phase 6 modules can be scaffolded during Phase 5** (define interfaces, write tests against mock data) but final analysis requires complete results.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Grading):** HumanEval sandbox isolation patterns vary significantly by platform. May need Docker vs. firejail vs. subprocess decision. GSM8K regex edge cases need comprehensive test data.
- **Phase 3 (Interventions):** The prompt compressor's behavior with a cheap LLM (Haiku/Flash) needs prompt engineering research. What system prompt produces reliable sanitization without semantic drift?
- **Phase 6 (Analysis):** GLMM convergence is a known risk (RDD risk register). If statsmodels fails, fallback to R's lme4 via rpy2 adds significant complexity. Research the convergence characteristics of `BinomialBayesMixedGLM` on binary data with crossed random effects.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** SQLite schema design, JSON loading, random seed management -- all well-documented patterns.
- **Phase 4 (Pilot):** Just running the pipeline at small scale. No new patterns.
- **Phase 5 (Full Run):** Same as pilot, longer. Rate limiting and retry are well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified against PyPI with current versions. Critical finding: `google-generativeai` deprecation is confirmed. `google-genai` 1.67.0 bug is documented. |
| Features | HIGH | Feature landscape mapped against 6+ competing papers (PromptBench, MulTypo, TextFlint, PromptSuite). Table stakes vs. differentiators clearly delineated. |
| Architecture | HIGH | Batch pipeline pattern is standard for empirical research. No novel architectural decisions needed. The RDD and CLAUDE.md already constrain most choices. |
| Pitfalls | HIGH | All 10 pitfalls sourced from published papers, CVE databases, or documented API behavior. Temperature non-determinism, benchmark contamination, and sandbox security are well-studied. |

**Overall confidence:** HIGH

### Gaps to Address

- **GLMM convergence behavior:** statsmodels `BinomialBayesMixedGLM` may struggle with the specific crossed random effects structure in this study. Validate during pilot analysis. Have R/lme4 fallback plan ready but do not build it unless needed.
- **Gemini safety filter behavior on noisy prompts:** Noisy prompts with garbled text may trigger Gemini's safety filters. The rate of `SAFETY_BLOCK` responses is unknown until pilot. If substantial (>5%), this introduces missing data that complicates analysis.
- **Pre-processor prompt engineering:** The system prompt for the cheap-model sanitizer/compressor is not specified in the RDD. Its effectiveness depends heavily on prompt design. Needs iteration during Phase 3.
- **Code execution grading throughput:** At 5-10 seconds per HumanEval execution with ~10,000 code outputs, grading alone takes 14-28 hours if done post-hoc. The architecture research recommends inline grading (interleaved with API wait times) but this increases execution engine complexity. Decision needed in Phase 3 planning.

## Sources

### Primary (HIGH confidence)
- RDD v4.0 (`docs/RDD_Linguistic_Tax_v4.md`) -- authoritative project spec
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python/releases) -- v0.86.0 confirmed
- [google-genai PyPI](https://pypi.org/project/google-genai/) -- v1.66.0 recommended, 1.67.0 bug documented
- [statsmodels GLMM docs](https://www.statsmodels.org/stable/mixed_glm.html) -- BinomialBayesMixedGLM
- [RestrictedPython CVE-2025-22153](https://www.sentinelone.com/vulnerability-database/cve-2025-22153/) -- critical, avoid

### Secondary (MEDIUM confidence)
- [Non-Determinism of "Deterministic" LLM Settings (ArXiv 2408.04667)](https://arxiv.org/html/2408.04667v5)
- [GSM8K-Platinum](https://gradientscience.org/gsm8k-platinum/) -- contamination and label errors
- [Pitfalls of Evaluating Language Models (ArXiv 2507.00460)](https://arxiv.org/abs/2507.00460)
- [Simulating Training Data Leakage (ArXiv 2505.24263)](https://arxiv.org/html/2505.24263v1) -- 5-14% HumanEval score inflation
- [A Statistical Approach to Model Evals (Anthropic)](https://www.anthropic.com/research/statistical-approach-to-model-evals)
- [PromptBench (Microsoft)](https://github.com/microsoft/promptbench)

### Tertiary (LOW confidence)
- Pre-processor cost overhead estimate (20-40% hidden costs) -- single source, needs validation against actual API billing
- google-genai 1.67.0 typing-extensions bug -- community reports, not in official changelog

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
