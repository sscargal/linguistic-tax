# Micro-Formatting Experiment Suite: Master Index

**Date:** 2026-03-24
**Status:** Draft
**Purpose:** Index of all atomic experiment questions for testing micro-formatting effects on LLM reasoning accuracy. Each question is a self-contained experiment spec that can be executed independently.

---

## Section 1: Overview

This experiment suite explores how small formatting choices in prompts affect LLM reasoning accuracy and token efficiency. Building on Phase 10's literature survey of 13 published papers across 6 format categories, we decompose 6 hypotheses (H-FMT-01 through H-FMT-06) into 26 independently-executable atomic experiments, and add 5 novel hypotheses brainstormed beyond the original scope. The suite covers token-efficient notations, structural markup, punctuation effects, format-noise interactions, and newly brainstormed ideas across whitespace, code-specific formatting, instruction phrasing, and structural markers.

The key finding from the literature is that format effects are real -- performance can vary by up to 40% based solely on format choice (He et al., ArXiv:2411.10541) -- but they are model-specific and task-dependent. Every experiment in this suite is designed to produce per-model results, never averaging across model families. The suite is designed to be executed incrementally using a tiered priority system, with free OpenRouter models as the default to minimize cost.

**Related documents:**
- Literature survey: [docs/prompt_format_research.md](../prompt_format_research.md)
- Research Design Document: [docs/RDD_Linguistic_Tax_v4.md](../RDD_Linguistic_Tax_v4.md)

**Model strategy:** Default to free OpenRouter models (nvidia/nemotron-3-super-120b-a12b:free for target, nvidia/nemotron-3-nano-30b-a3b:free for pre-processing). Escalate to paid models (Claude Sonnet, Gemini 1.5 Pro, GPT-4o) if results show promise or null results need confirmation.

---

## Section 2: Experiment Cluster Index

| File | Topic | Parent Hypotheses | Atomic Questions | Description |
|------|-------|-------------------|------------------|-------------|
| [token_efficiency.md](token_efficiency.md) | Token-saving formats | H-FMT-01, H-FMT-03 | AQ-TE-01 through AQ-TE-07 (7) | TOON compact notation for HumanEval/MBPP/GSM8K, bullet/outline reformatting, telegraphic filler removal |
| [structural_markup.md](structural_markup.md) | Structural markup | H-FMT-02 | AQ-SM-01 through AQ-SM-06 (6) | XML tag wrapping, parameter annotation, nested vs. flat hierarchy, overhead measurement, markdown alternative |
| [punctuation_micro.md](punctuation_micro.md) | Punctuation effects | H-FMT-04, H-FMT-06 | AQ-PM-01 through AQ-PM-08 (8) | Per-punctuation-type removal, combined removal, question mark effects, imperative confound isolation |
| [format_noise_interaction.md](format_noise_interaction.md) | Format x noise | H-FMT-05 | AQ-FN-01 through AQ-FN-05 (5) | XML/bullet/TOON format resilience under Type A and Type B noise, micro-pilot gate |
| [novel_hypotheses.md](novel_hypotheses.md) | New ideas | Novel | AQ-NH-01 through AQ-NH-05 (5) | Instruction phrasing modes, politeness markers, code comments, newline density, emphasis markers |

**Total:** 31 atomic experiment questions across 5 topic clusters

---

## Section 3: Master Summary Table

| ID | Name | File | Tier | API Calls (Free) | API Calls (Paid) | Cost (Free) | Cost (Paid) | Parent Hypothesis |
|----|------|------|------|-------------------|-------------------|-------------|-------------|-------------------|
| AQ-TE-01 | TOON for HumanEval docstrings | token_efficiency.md | 1 | 200 | 600 | $0 | $5-12 | H-FMT-01 |
| AQ-TE-02 | TOON for MBPP descriptions | token_efficiency.md | 1 | 200 | 600 | $0 | $4-10 | H-FMT-01 |
| AQ-TE-03 | TOON for GSM8K math problems | token_efficiency.md | 2 | 200 | 600 | $0 | $3-7 | H-FMT-01 |
| AQ-TE-04 | TOON LLM vs. rule-based conversion | token_efficiency.md | 2 | 220 | 820 | $0 | $6-14 | H-FMT-01 |
| AQ-TE-05 | Bullet extraction of GSM8K problems | token_efficiency.md | 1 | 200 | 600 | $0 | $3-7 | H-FMT-03 |
| AQ-TE-06 | Outline for multi-step HumanEval | token_efficiency.md | 2 | 200 | 600 | $0 | $5-12 | H-FMT-03 |
| AQ-TE-07 | Telegraphic filler word removal | token_efficiency.md | 1 | 200 | 600 | $0 | $5-12 | H-FMT-03 |
| AQ-SM-01 | XML instruction/context wrapping | structural_markup.md | 1 | 200 | 600 | $0 | $5-12 | H-FMT-02 |
| AQ-SM-02 | XML parameter annotation | structural_markup.md | 2 | 200 | 600 | $0 | $5-12 | H-FMT-02 |
| AQ-SM-03 | XML for GSM8K structure | structural_markup.md | 2 | 200 | 600 | $0 | $3-8 | H-FMT-02 |
| AQ-SM-04 | Nested vs. flat XML | structural_markup.md | 2 | 200 | 600 | $0 | $5-12 | H-FMT-02 |
| AQ-SM-05 | XML token overhead measurement | structural_markup.md | 1 | 200 | 600 | $0 | $4-10 | H-FMT-02 |
| AQ-SM-06 | Markdown vs. XML structure | structural_markup.md | 2 | 300 | 900 | $0 | $7-16 | H-FMT-02 |
| AQ-PM-01 | Period removal | punctuation_micro.md | 1 | 200 | 600 | $0 | $3-5 | H-FMT-04 |
| AQ-PM-02 | Comma removal | punctuation_micro.md | 1 | 200 | 600 | $0 | $3-5 | H-FMT-04 |
| AQ-PM-03 | Semicolon removal | punctuation_micro.md | 2 | 200 | 600 | $0 | $3-5 | H-FMT-04 |
| AQ-PM-04 | All punctuation removal (HumanEval) | punctuation_micro.md | 1 | 200 | 600 | $0 | $3-5 | H-FMT-04 |
| AQ-PM-05 | All punctuation removal (GSM8K) | punctuation_micro.md | 1 | 200 | 600 | $0 | $3-5 | H-FMT-04 |
| AQ-PM-06 | Partial removal (periods only) | punctuation_micro.md | 2 | 200 | 200 | $0 | $0 | H-FMT-04 |
| AQ-PM-07 | Question mark removal | punctuation_micro.md | 2 | 200 | 600 | $0 | $2-5 | H-FMT-06 |
| AQ-PM-08 | Question mark vs. imperative | punctuation_micro.md | 3 | 300 | 300 | $0 | $0 | H-FMT-06 |
| AQ-FN-01 | XML x Type A noise | format_noise_interaction.md | 2 | 800 | 2,400 | $0 | $10-15 | H-FMT-05 |
| AQ-FN-02 | Bullet x Type A noise | format_noise_interaction.md | 2 | 400 | 1,200 | $0 | $5-10 | H-FMT-05 |
| AQ-FN-03 | TOON x Type A noise | format_noise_interaction.md | 2 | 400 | 1,200 | $0 | $5-10 | H-FMT-05 |
| AQ-FN-04 | XML x Type B ESL noise | format_noise_interaction.md | 3 | 400 | 400 | $0 | $3-5 | H-FMT-05 |
| AQ-FN-05 | Micro-pilot gate | format_noise_interaction.md | 1 | 300 | 300 | $0 | $0 | H-FMT-05 |
| AQ-NH-01 | Imperative vs. interrogative vs. declarative | novel_hypotheses.md | 2 | 300 | 900 | $0 | $6-14 | Novel |
| AQ-NH-02 | Politeness markers (Please/Thank you) | novel_hypotheses.md | 2 | 300 | 900 | $0 | $6-14 | Novel |
| AQ-NH-03 | Code comment presence in examples | novel_hypotheses.md | 1 | 200 | 600 | $0 | $5-12 | Novel |
| AQ-NH-04 | Newline density between sections | novel_hypotheses.md | 1 | 300 | 900 | $0 | $5-12 | Novel |
| AQ-NH-05 | Emphasis markers on key terms | novel_hypotheses.md | 2 | 400 | 1,200 | $0 | $8-18 | Novel |

**Totals:** 31 atomic questions | 7,920 free API calls | 22,520 paid API calls | $0 free cost | $141-312 paid cost

---

## Section 4: Tiered Execution Plan

### Tier 1 -- Cheapest, Highest Signal (Run First)

| ID | Name | Cluster | Free API Calls |
|----|------|---------|----------------|
| AQ-TE-01 | TOON for HumanEval docstrings | Token Efficiency | 200 |
| AQ-TE-02 | TOON for MBPP descriptions | Token Efficiency | 200 |
| AQ-TE-05 | Bullet extraction of GSM8K problems | Token Efficiency | 200 |
| AQ-TE-07 | Telegraphic filler word removal | Token Efficiency | 200 |
| AQ-SM-01 | XML instruction/context wrapping | Structural Markup | 200 |
| AQ-SM-05 | XML token overhead measurement | Structural Markup | 200 |
| AQ-PM-01 | Period removal | Punctuation | 200 |
| AQ-PM-02 | Comma removal | Punctuation | 200 |
| AQ-PM-04 | All punctuation removal (HumanEval) | Punctuation | 200 |
| AQ-PM-05 | All punctuation removal (GSM8K) | Punctuation | 200 |
| AQ-FN-05 | Micro-pilot gate (format x noise) | Format-Noise | 300 |
| AQ-NH-03 | Code comment presence in examples | Novel | 200 |
| AQ-NH-04 | Newline density between sections | Novel | 300 |

**Tier 1 totals:**
- Questions: 13
- Free API calls: 2,800
- Cumulative cost: $0 (free models) / $49-107 (paid escalation)
- Estimated wall-clock time at 0.5s/call rate limit: ~23 minutes
- Expected outcomes: Establishes baselines for token-saving formats, confirms/refutes punctuation degradation, measures XML overhead, determines whether format x noise interaction warrants full investigation

### Tier 2 -- Run if Tier 1 Shows Interesting Results

| ID | Name | Cluster | Free API Calls |
|----|------|---------|----------------|
| AQ-TE-03 | TOON for GSM8K math problems | Token Efficiency | 200 |
| AQ-TE-04 | TOON LLM vs. rule-based conversion | Token Efficiency | 220 |
| AQ-TE-06 | Outline for multi-step HumanEval | Token Efficiency | 200 |
| AQ-SM-02 | XML parameter annotation | Structural Markup | 200 |
| AQ-SM-03 | XML for GSM8K structure | Structural Markup | 200 |
| AQ-SM-04 | Nested vs. flat XML | Structural Markup | 200 |
| AQ-SM-06 | Markdown vs. XML structure | Structural Markup | 300 |
| AQ-PM-03 | Semicolon removal | Punctuation | 200 |
| AQ-PM-06 | Partial removal (periods only) | Punctuation | 200 |
| AQ-PM-07 | Question mark removal | Punctuation | 200 |
| AQ-FN-01 | XML x Type A noise | Format-Noise | 800 |
| AQ-FN-02 | Bullet x Type A noise | Format-Noise | 400 |
| AQ-FN-03 | TOON x Type A noise | Format-Noise | 400 |
| AQ-NH-01 | Imperative vs. interrogative vs. declarative | Novel | 300 |
| AQ-NH-02 | Politeness markers (Please/Thank you) | Novel | 300 |
| AQ-NH-05 | Emphasis markers on key terms | Novel | 400 |

**Tier 2 totals:**
- Questions: 16
- Free API calls: 4,520
- Cumulative cost (Tier 1 + Tier 2): $0 (free models) / $118-249 (paid escalation)
- Estimated wall-clock time: ~38 minutes additional
- Go/no-go criteria from Tier 1: Proceed if any Tier 1 experiment shows a statistically significant effect (p < 0.05 on McNemar's test) OR a large effect size (> 10% accuracy difference) even without formal significance. For format-noise experiments (AQ-FN-01/02/03), proceed only if AQ-FN-05 micro-pilot passes go criteria (5pp slope difference).

### Tier 3 -- Stretch Goals

| ID | Name | Cluster | Free API Calls |
|----|------|---------|----------------|
| AQ-PM-08 | Question mark vs. imperative confound | Punctuation | 300 |
| AQ-FN-04 | XML x Type B ESL noise | Format-Noise | 400 |

**Tier 3 totals:**
- Questions: 2
- Free API calls: 700
- Cumulative cost (all tiers): $0 (free models) / $141-312 (paid escalation)
- Prerequisites: AQ-PM-08 requires AQ-PM-07 results for context; AQ-FN-04 requires AQ-FN-05 micro-pilot to pass go criteria

---

## Section 5: Cross-Cluster Bundling Opportunities

Several experiments across different clusters share control conditions (raw, unmodified prompts from data/prompts.json). Running shared controls once and reusing the data across experiments reduces total API calls significantly.

### Shared Control Groups

**HumanEval raw prompts (largest bundle):**
- AQ-TE-01, AQ-TE-06, AQ-TE-07, AQ-SM-01, AQ-SM-02, AQ-SM-04, AQ-SM-05 (partial), AQ-SM-06, AQ-PM-01, AQ-PM-02, AQ-PM-03, AQ-PM-04, AQ-PM-06, AQ-FN-01/02/03/05, AQ-NH-01, AQ-NH-02, AQ-NH-03, AQ-NH-05
- Control: 20 prompts x 5 reps x 1 model = 100 calls (instead of 100 per experiment)
- Estimated savings: ~1,500 API calls by running HumanEval control once

**MBPP raw prompts:**
- AQ-TE-02, AQ-TE-07, AQ-SM-02 (partial), AQ-NH-01, AQ-NH-02, AQ-NH-03
- Control: 100 calls shared
- Estimated savings: ~400 API calls

**GSM8K raw prompts:**
- AQ-TE-03, AQ-TE-05, AQ-SM-03, AQ-SM-05 (partial), AQ-PM-05, AQ-PM-07, AQ-PM-08, AQ-NH-04 (partial)
- Control: 100 calls shared
- Estimated savings: ~500 API calls

### Cross-Cluster Reuse

- **AQ-SM-01 flat XML output** serves as control for AQ-SM-04 (nested vs. flat) and as treatment for AQ-SM-06 (markdown comparison)
- **AQ-PM-01 output** is analytically identical to AQ-PM-06 (both remove periods only); the difference is analytical context, not execution
- **AQ-FN-01/02/03 prose-at-each-noise-level data** is collected once and reused across all format comparisons
- **AQ-TE-01 rule-based TOON output** serves as control for AQ-TE-04 (LLM vs. rule-based comparison)

### Total Estimated Savings

Without bundling: 7,920 free API calls
With bundling: ~5,500 free API calls (estimated 30% reduction)
Savings: ~2,400 API calls (~20 minutes wall-clock time at 0.5s/call)

---

## Section 6: Model Escalation Strategy

### Step 1: Run All Tier 1 on Free OpenRouter Models
- Model: nvidia/nemotron-3-super-120b-a12b:free
- Pre-processing: nvidia/nemotron-3-nano-30b-a3b:free
- Cost: $0
- Purpose: Establish baseline results across all experiment clusters

### Step 2: Replicate Significant Effects on Claude Sonnet
- Model: claude-sonnet-4-20250514 ($3.00/$15.00 per 1M in/out)
- Trigger: Any Tier 1 experiment shows statistically significant effect (p < 0.05) on free models
- Purpose: Verify whether effects are model-specific or universal
- Exception: AQ-SM-01 (XML wrapping) should be escalated to Claude Sonnet immediately since the hypothesis specifically predicts Claude benefits from XML

### Step 3: Extend to Gemini 1.5 Pro and GPT-4o
- Models: gemini-1.5-pro ($1.25/$5.00 per 1M in/out), gpt-4o-2024-11-20 ($2.50/$10.00 per 1M in/out)
- Trigger: Step 2 confirms model-specific effects (Claude result differs from Nemotron)
- Purpose: Test generalizability across model families; He et al. showed IoU < 0.2 between model format preferences
- Key question: Does the format effect persist, reverse, or disappear on non-Claude architectures?

### Step 4: Null-Result Confirmation on Paid Models
- Trigger: Tier 1 shows null results on free models across all experiments
- Action: Run 2-3 representative Tier 1 experiments on Claude Sonnet before concluding
- Rationale: Nemotron (120B MoE with 12B active params) may lack sensitivity that frontier models have (Pitfall 6). A null result on free models does not mean the effect does not exist.

### Cost Projection Per Escalation Step

| Step | Models | Experiments | Estimated Cost |
|------|--------|-------------|----------------|
| Step 1 | Free Nemotron | All Tier 1 (13) | $0 |
| Step 2 | Claude Sonnet | 3-5 significant | $8-20 |
| Step 3 | Gemini + GPT-4o | 2-3 model-specific | $10-25 |
| Step 4 | Claude Sonnet | 2-3 null confirmation | $5-12 |
| **Total escalation** | | | **$23-57** |

---

## Section 7: Infrastructure Notes

### Existing Infrastructure (No New Code Needed for Execution)

- **Experiment execution:** `src/run_experiment.py` -- harness for sending prompts to LLMs with intervention routing, logging TTFT/TTLT/token counts/cost
- **Grading:** `src/grade_results.py` -- auto-grading with HumanEval execution sandbox and GSM8K regex matching
- **Analysis:** `src/analyze_results.py` -- GLMM, bootstrap CIs, McNemar's test, Kendall's tau for all standard analyses
- **Derived metrics:** `src/compute_derived.py` -- consistency rate (CR), quadrant classification, cost rollups
- **Results storage:** SQLite database (`results/results.db`) with existing schema

### Future Code Changes (Separate Phase)

- New intervention types would be added to `INTERVENTIONS` in `src/config.py` (e.g., `"format_toon"`, `"format_xml_structured"`, `"format_no_punctuation"`, `"format_newline_reduced"`)
- Format conversion functions would follow the callable injection pattern from `src/prompt_compressor.py` (`call_fn` parameter)
- Regex-based interventions (punctuation removal, newline reduction, comment stripping) bypass the LLM pre-processor entirely (zero-cost)
- Analysis pipeline handles new interventions without code changes -- GLMM and McNemar's work on any intervention type
- OpenRouter integration (`src/api_client.py`) already supports free model calls via Phase 9 implementation
