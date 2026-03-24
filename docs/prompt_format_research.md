# Prompt Format Research: Optimal Input Formats for LLM Reasoning

**Date:** 2026-03-24
**Status:** Complete
**Context:** Companion research for "The Linguistic Tax" whitepaper
**Purpose:** Survey how prompt input formats affect LLM reasoning accuracy and token efficiency; produce testable hypotheses for experiment design

---

## Executive Summary

This document surveys 6 format categories drawing on 13 published papers and specifications to assess how prompt input format affects LLM reasoning accuracy and token efficiency. The categories span token-optimized notations (TOON, CompactPrompt), structured markup (XML), minimal/telegraphic formats (bullet points), punctuation variations, hybrid/novel approaches (CFPO, lossless meta-tokens, ProCut), and the verbose natural language baseline used in our current experiment suite. Evidence ranges from large-scale empirical studies across 8 models and 52 tasks to mechanistic analyses of punctuation's role in transformer attention.

The key finding is that format effects are real -- performance can vary by up to 40% based solely on format choice (He et al., ArXiv:2411.10541) -- but they are model-specific and task-dependent. Format preferences show an Intersection-over-Union below 0.2 between model families, meaning a format that helps Claude may hurt Gemini. Punctuation removal, counterintuitively, is likely to degrade accuracy rather than save costs: three independent studies confirm that punctuation tokens serve as attention sinks and context memory carriers in transformer architectures. Conservative compression (2-3x) consistently outperforms aggressive compression (10-20x) across all benchmarks studied.

We propose 6 testable hypotheses (H-FMT-01 through H-FMT-06) ranked by feasibility. The top 3 -- TOON compact notation for structured code prompts (HIGH), XML structured markup for Claude vs. Gemini (HIGH), and punctuation removal effects on coding tasks (HIGH) -- are ready for immediate pilot testing at an estimated combined cost of $9-24. The remaining hypotheses cover bullet/outline formatting for math problems (MEDIUM), a format-x-noise interaction study (MEDIUM), and question mark presence effects (LOW). The format-x-noise interaction hypothesis (H-FMT-05) represents a potential novel contribution to the field: no existing paper examines whether structured formatting makes prompts more or less robust to character-level noise. Total estimated cost for testing all 6 hypotheses is $28-64.

---

## Literature Survey

### 1. Token-Optimized Notations (TOON, CompactPrompt)

Token-optimized notations aim to reduce input token counts through compact encoding schemes while preserving the semantic content of prompts. These approaches address the "token tax" component of the Linguistic Tax thesis most directly, targeting the redundancy inherent in natural language and verbose data formats like JSON.

**TOON (Text Object-Oriented Notation)** is a human-readable data serialization format designed as a lightweight alternative to JSON and YAML. Benchmarks from the TOON specification repository show that TOON achieves approximately 40% fewer tokens than equivalent JSON representations while maintaining slightly higher accuracy on data retrieval tasks: 76.4% accuracy across 4 models versus JSON's 75.0% (github.com/toon-format/toon). These results are encouraging but carry an important caveat: the benchmarks are limited to data retrieval tasks, not the reasoning tasks (code generation, mathematical reasoning) central to our study. Whether TOON's token savings translate to maintained accuracy on HumanEval or GSM8K is an open question that warrants pilot testing.

**CompactPrompt** (ArXiv:2510.18043) presents an end-to-end pipeline combining hard compression and data compression, achieving 60% token reduction with less than 5% accuracy drop on Claude 3.5. This work is already cited in our RDD (Section 20.3) as a key baseline for compression methodology. CompactPrompt demonstrates that substantial token savings are achievable without catastrophic accuracy loss, but it was tested on clean prompts only. Our study's unique contribution is testing whether compression interacts with noise -- does compressing a noisy prompt amplify errors, or does the compression step implicitly sanitize?

**LLMLingua** (ArXiv:2310.05736) pioneered perplexity-based token pruning, achieving up to 20x compression by removing tokens with low perplexity (high predictability). However, aggressive compression at this level degrades output quality, particularly for tasks requiring precise instruction following. The consensus from 2025 surveys (Li et al., ArXiv:2410.12388) is that conservative 2-3x compression represents the sweet spot -- sufficient to reduce costs meaningfully while maintaining output fidelity. This aligns with our existing sanitize+compress intervention, which targets moderate compression rather than maximal token reduction.

The key tension in this category is between token efficiency and information preservation. Lossless approaches (see Section 5) avoid this tradeoff entirely but achieve smaller reductions. For the Linguistic Tax whitepaper, the most relevant question is whether a format-level change (e.g., restructuring prompt data from JSON to TOON) can achieve 30-40% savings without any information loss, effectively capturing "free" efficiency gains.

### 2. Structured Markup (XML, HTML)

Structured markup formats introduce explicit delimiters and hierarchical organization into prompts. Unlike token-optimized notations that aim to reduce token counts, structured markup typically increases token counts (due to tag overhead) but may improve model parsing accuracy by providing unambiguous structural boundaries.

**Anthropic's official documentation** recommends using XML tags to structure prompts for Claude, particularly for separating instructions from context, marking input/output boundaries, and organizing multi-part prompts. This recommendation suggests that Claude's training data or fine-tuning process has encoded a preference for XML-delimited structure, making it a model-specific optimization rather than a universal best practice.

**He et al. (ArXiv:2411.10541)** conducted the most comprehensive study of format effects on LLM performance, testing multiple format variations across several models. Their key findings are striking: performance can vary by up to 40% based solely on format choice, and model-specific format preferences show an Intersection-over-Union (IoU) below 0.2 between different model families. Specifically, GPT-3.5 showed a preference for JSON formatting while GPT-4 preferred Markdown -- a finding that underscores the danger of assuming any single format is universally optimal.

The structured markup category presents a paradox for the Linguistic Tax thesis: XML tags add tokens (increasing the "token tax") but may improve accuracy (reducing the "accuracy tax" from ambiguous formatting). For our experiment suite, this suggests testing whether XML-structured prompts on Claude and equivalently structured prompts on Gemini yield different results -- leveraging each model's format affinity rather than applying a one-size-fits-all approach.

A practical consideration is that XML structure is most beneficial for complex, multi-part prompts. For short, single-instruction prompts like many GSM8K problems, the tag overhead may outweigh any structural benefit. Experiment design should control for prompt complexity as a moderating variable.

### 3. Minimal/Telegraphic (Bullet Points, Outline Format)

Minimal and telegraphic formats strip natural language prompts of prose connectors, transitional phrases, and verbose phrasing, retaining only the essential information in a compact, list-based structure. This category directly targets what we term the "formatting overhead" component of the linguistic tax: words like "therefore," "in order to," "please note that," and "it is important to" that serve human readability but may be redundant for LLM processing.

Evidence from practitioner experience and limited controlled studies suggests that bullet-point formats generally outperform prose for presenting options and structured information. This effect likely reflects training data bias: StackOverflow answers, technical documentation, and API references predominantly use bullet/list formatting, so models have seen more high-quality completions conditioned on bulleted inputs.

The effect size of telegraphic formatting on coding instructions and math word problems is not well characterized in the literature. Math word problems in particular present an interesting case: GSM8K prompts are written as natural language narratives ("Sally has 3 apples and buys 2 more..."), and it is unclear whether reformatting these as bullet points ("Sally: 3 apples, Buys: 2 more, Question: total?") would help or hurt. The narrative structure may carry implicit reasoning scaffolding that a telegraphic format would discard.

For coding tasks (HumanEval, MBPP), function docstrings already follow a semi-structured format with parameter descriptions and return value specifications. Converting these to a more compact bullet format could yield 10-30% token reduction while preserving all semantic content. This is a highly testable hypothesis with straightforward implementation.

### 4. Punctuation Variations

Punctuation's role in LLM processing is more nuanced than early assumptions suggested. Three independent research efforts have established that punctuation tokens serve functional roles in transformer architectures beyond mere formatting.

**LLM-Microscope** (ArXiv:2502.15007) provided the mechanistic explanation: punctuation tokens function as attention sinks and carry context memory within transformer layers. The study demonstrated that removing punctuation degrades performance on MMLU and BABILong-4k benchmarks. This is not a simple formatting effect -- punctuation tokens serve as structural anchors in the model's internal representation, helping to segment and organize the input sequence.

**"When Punctuation Matters"** (ArXiv:2508.11383) conducted a large-scale empirical study across 8 models and 52 tasks, confirming that punctuation sensitivity is a real and consistent phenomenon. The breadth of this study (spanning multiple model families and task types) strengthens the conclusion that punctuation effects are not artifacts of specific architectures or evaluation protocols.

**"Punctuation and Predicates"** (ArXiv:2508.14067) added model-specific nuance: the degree of punctuation dependence varies across architectures. GPT-2, DeepSeek, and Gemma showed different sensitivity profiles, suggesting that punctuation's functional role may be learned differently during pre-training depending on the training corpus and tokenization scheme.

**Key finding for the Linguistic Tax paper:** Punctuation removal is NOT a straightforward token-saving strategy. While removing periods, commas, and question marks from prompts would save a modest 5-10% of tokens, the evidence strongly suggests this may hurt accuracy. This finding should be framed as a hypothesis to test rather than an assumed optimization. If confirmed in our experiment suite, it becomes a cautionary finding: not all "linguistic overhead" is waste -- some serves a functional purpose in model cognition.

### 5. Hybrid/Novel Approaches

The frontier of prompt format optimization includes several innovative approaches that go beyond simple format selection, treating format as a first-class optimization dimension or applying compression techniques inspired by information theory.

**CFPO (Content-Format Prompt Optimization)** (ArXiv:2502.04295) demonstrated that jointly optimizing content and format outperforms content-only optimization. This is a conceptually important finding for our research: it suggests that the "linguistic tax" has both a content component (noise, errors) and a format component (structure, notation), and that addressing only one leaves performance on the table. CFPO's approach of treating format as a tunable parameter aligns with our thesis that prompt optimization should be holistic.

**Lossless Meta-Tokens** (ArXiv:2506.00307) achieves 27% compression through an LZ77-like technique applied at the token level. Unlike lossy approaches (LLMLingua, CompactPrompt), this method guarantees no information loss by encoding repeated token sequences as meta-token references. The 27% reduction is more modest than lossy approaches but eliminates the accuracy-compression tradeoff entirely. For precision-critical tasks in our benchmark (HumanEval code generation), lossless approaches may be strictly preferable.

**ProCut** (ArXiv:2508.02053) applies Shapley value analysis to identify which tokens in a prompt contribute most to output quality. This attribution-based approach enables targeted compression: remove the tokens that matter least, preserve those that matter most. ProCut's framework could inform a more sophisticated version of our sanitize+compress intervention -- rather than using a cheap model to decide what to compress, use attribution scores to guide compression decisions.

**LLM-DCP (Dynamic Compressing Prompts)** (ArXiv:2504.11004) models prompt compression as a Markov Decision Process, achieving 17% improvement over Selective Context. The dynamic aspect is key: rather than applying a fixed compression strategy, LLM-DCP adapts its compression decisions based on the specific prompt content. This task-agnostic approach could complement our noise-aware compression pipeline.

These cutting-edge approaches suggest potential new intervention types for future phases of the experiment. In particular, the combination of noise-aware sanitization (our existing approach) with attribution-based compression (ProCut-style) or format optimization (CFPO-style) represents an unexplored design space.

### 6. Verbose Natural Language Baseline

Verbose natural language is the default prompt format in our experiment suite, corresponding to the "raw" intervention condition. This is the format most users naturally produce: complete sentences with prose connectors, standard punctuation, and conversational phrasing. It serves as the control condition against which all format optimizations are compared.

The Linguistic Tax thesis argues that verbose natural language carries a systematic overhead composed of several components: redundant phrasing ("in order to" vs. "to"), filler expressions ("please note that," "it is important to mention"), duplicated context (restating requirements already specified), and formatting conventions (complete sentences where fragments would suffice). Quantifying this overhead is central to the paper's argument.

A rough decomposition of a typical verbose prompt suggests the following token budget allocation: approximately 40-60% of tokens carry core semantic content (the actual task specification), 15-25% provide structural scaffolding (sentence structure, connectors, transitions), 10-15% are formatting overhead (politeness markers, hedging language, explicit meta-instructions), and 5-10% are punctuation and whitespace tokens. The exact ratios vary by prompt type -- coding prompts tend to be more information-dense than conversational math problems.

The verbose baseline is essential because it represents the real-world starting point. Users do not naturally write in TOON notation or telegraphic bullet points. Any proposed format optimization must be evaluated not only for its accuracy and token impact but also for its practical deployability: can it be applied automatically (like our sanitize+compress pipeline), or does it require user behavior change?

For the Linguistic Tax whitepaper, the most compelling findings will be those that show a significant gap between the verbose baseline and an optimized format -- demonstrating that the "tax" is both real and recoverable through automation.

---

## Format Taxonomy

The following table provides a comparative overview of the six format categories, synthesizing evidence on token efficiency, accuracy impact, and practical limitations.

| Format Category | Token Efficiency | Accuracy Impact | Evidence Strength | Task Domains Tested | Key Limitation |
|-----------------|------------------|-----------------|-------------------|---------------------|----------------|
| TOON-like compact | 30-40% reduction | Comparable or slightly better | MEDIUM (data retrieval only) | Data extraction, structured queries | Untested on reasoning tasks |
| XML/structured markup | 5-15% increase (tag overhead) | Up to 40% variation (model-specific) | HIGH (He et al., multiple models) | Classification, QA, coding | Model-specific; no universal winner |
| Bullet/outline | 10-30% reduction | Generally positive for options | MEDIUM (limited controlled studies) | Option selection, instructions | Unclear for math/code |
| Minimal punctuation | 5-10% reduction | Likely NEGATIVE | HIGH (multiple independent studies) | MMLU, general reasoning | Punctuation serves functional role |
| Hybrid/novel (CFPO etc.) | Variable (up to 60%) | Positive when tuned | MEDIUM (recent, less replicated) | Various | Requires per-task optimization |
| Verbose NL (baseline) | 0% (reference) | Reference | HIGH (our experiment data) | HumanEval, MBPP, GSM8K | Carries formatting overhead |

---

## Key Insights

Synthesizing across all six format categories, the following cross-cutting findings emerge:

- **Format effects are model-specific and cannot be generalized.** He et al. (ArXiv:2411.10541) demonstrated that format preferences show IoU below 0.2 between model families. Any format optimization tested in our experiment suite must be evaluated per-model (Claude vs. Gemini vs. GPT) rather than averaged across models, as a format that helps one model may hurt another.

- **Punctuation removal is counterintuitively harmful.** Three independent studies (LLM-Microscope, "When Punctuation Matters," "Punctuation and Predicates") converge on the finding that punctuation tokens serve functional roles as attention sinks and context memory carriers. Removing punctuation to save tokens is not a neutral operation -- it degrades the model's ability to segment and process the input. This is a cautionary finding for any "minimal notation" hypothesis.

- **Data format and instruction format are separate optimization dimensions.** Reformatting structured data within a prompt (e.g., JSON to TOON) is a different problem from reformatting the instructions themselves (e.g., prose to bullets). These dimensions have different evidence bases, different expected effect sizes, and may interact in non-obvious ways. Experiment designs must specify which dimension they target (Pitfall 1 from research notes).

- **Conservative compression (2-3x) consistently outperforms aggressive compression (10-20x).** Across LLMLingua, CompactPrompt, and survey evidence (Li et al., ArXiv:2410.12388), the pattern is clear: moderate token reduction preserves accuracy while still yielding meaningful cost savings. Aggressive compression (LLMLingua's 20x) achieves impressive headline numbers but degrades output quality, particularly on precision-critical tasks like code generation.

- **The interaction of format and noise is unstudied -- a potential novel contribution.** No existing paper examines whether structured formatting makes prompts more or less robust to noise. Our experiment suite uniquely positions us to test this: does XML structure help a model parse a noisy prompt more accurately (structure compensates for noise), or does noise break the structure (making things worse)? This format-x-noise interaction could be the whitepaper's most novel finding.

---

## Testable Hypotheses

The following 6 hypotheses are derived from the literature survey and format taxonomy above. Each follows the standardized specification template from the research notes, with all fields required for Phase 11 consumption. Hypotheses are ranked by priority (HIGH > MEDIUM > LOW) based on feasibility, expected impact, and cost.

### H-FMT-01: TOON-like Compact Notation for Structured Code Prompts

**Priority:** HIGH

**Claim:** Reformatting structured prompt data from JSON/verbose natural language to TOON-like compact notation reduces input tokens by 30-40% while maintaining coding task accuracy on HumanEval/MBPP.

**Independent Variable:** Prompt data format (verbose NL baseline vs. TOON-like compact)

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** HumanEval + MBPP subset (prompts with structured context/constraints)

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 2 formats = 400 API calls

**Estimated Cost:** $3-8 (based on current PRICE_TABLE rates: Claude Sonnet at $3.00/1M input, Gemini 1.5 Pro at $1.25/1M input)

**Expected Effect:** 30-40% token reduction, less than 5% accuracy change

**Measurement:** Paired comparison -- same prompt in both formats, McNemar's test for accuracy difference, token count ratio. Uses existing `grade_results.py` HumanEval/MBPP grading.

**Supporting Evidence:** TOON benchmarks show 76.4% vs. JSON 75.0% on data retrieval across 4 models (github.com/toon-format/toon); CompactPrompt achieves 60% reduction with less than 5% accuracy drop (ArXiv:2510.18043).

**Risks/Caveats:** TOON benchmarks are on data retrieval, not reasoning. Effect may not transfer to code generation. TOON's sweet spot is tabular/uniform data, which differs from HumanEval function docstrings (Pitfall 5 from research notes).

---

### H-FMT-02: XML Structured Markup for Claude vs. Gemini

**Priority:** HIGH

**Claim:** XML-tagged prompt structure improves Claude accuracy by 5-10% (Anthropic recommends XML) but has no effect or negative effect on Gemini, demonstrating model-specific format preferences.

**Independent Variable:** Prompt structure (plain text vs. XML-tagged sections)

**Dependent Variables:** Pass rate, input token count, TTFT

**Benchmarks:** Full benchmark set (HumanEval, MBPP, GSM8K) -- 20-prompt pilot subset

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 2 formats = 400 API calls

**Estimated Cost:** $3-8

**Expected Effect:** Claude +5-10% accuracy, Gemini +/-2% (neutral), 5-15% token increase from XML tags

**Measurement:** Per-model accuracy comparison, interaction effect in GLMM (format x model). Uses existing `analyze_results.py` GLMM with intervention as a factor.

**Supporting Evidence:** He et al. (ArXiv:2411.10541) show IoU below 0.2 between model format preferences; Anthropic docs recommend XML for Claude (docs.anthropic.com).

**Risks/Caveats:** XML overhead may negate accuracy gains on a cost basis. XML structure is most beneficial for complex, multi-part prompts; short GSM8K problems may not benefit. Tag overhead could increase input costs by 5-15%.

---

### H-FMT-03: Bullet/Outline Format for Math Word Problems

**Priority:** MEDIUM

**Claim:** Converting GSM8K prose word problems to bullet-point format (key values + question) reduces tokens by 15-25% and maintains or improves accuracy.

**Independent Variable:** Instruction format (prose paragraph vs. bulleted key information)

**Dependent Variables:** Pass rate, input token count

**Benchmarks:** GSM8K subset (20 prompts with verbose word problems)

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 2 formats = 400 API calls

**Estimated Cost:** $2-5

**Expected Effect:** 15-25% token reduction, less than 3% accuracy change

**Measurement:** Paired comparison, exact-match grading (same as current GSM8K grading in `grade_results.py`)

**Supporting Evidence:** Bullet formats outperform prose for option presentation in training data; telegraphic style removes filler words that carry no semantic content for LLMs.

**Risks/Caveats:** Math word problems may encode reasoning cues in prose connectors ("therefore," "so," "which means") that bullets strip. Narrative structure may carry implicit reasoning scaffolding that a telegraphic format would discard.

---

### H-FMT-04: Punctuation Removal Effects on Coding Tasks

**Priority:** HIGH

**Claim:** Removing "optional" punctuation (trailing periods in instructions, commas in lists, semicolons) from coding prompts degrades accuracy by 2-8%, contrary to the naive token-saving hypothesis.

**Independent Variable:** Punctuation level (full punctuation vs. stripped punctuation)

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval + MBPP subset (20 prompts)

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 2 formats = 400 API calls

**Estimated Cost:** $3-8

**Expected Effect:** 5-10% token reduction BUT 2-8% accuracy DECREASE

**Measurement:** Paired comparison, CR comparison (does punctuation removal also hurt stability?). Uses existing `compute_derived.py` CR calculation and `analyze_results.py` McNemar's test.

**Supporting Evidence:** LLM-Microscope (ArXiv:2502.15007) shows punctuation as attention sinks; "When Punctuation Matters" (ArXiv:2508.11383) confirms across 8 models and 52 tasks; "Punctuation and Predicates" (ArXiv:2508.14067) shows model-specific punctuation sensitivity.

**Risks/Caveats:** Effect may be smaller on coding tasks than on MMLU-style tasks where punctuation was studied. This is a genuinely uncertain hypothesis -- the expected direction (accuracy decrease) is based on MMLU/general reasoning benchmarks, not coding-specific data.

---

### H-FMT-05: Format x Noise Interaction (Novel Contribution)

**Priority:** MEDIUM

**Claim:** Structured formats (XML, bullets) make prompts MORE robust to Type A character-level noise because structure tokens survive noise injection better than prose connectors.

**Independent Variable:** Format (prose vs. XML vs. bullet) crossed with noise level (0%, 5%, 10%, 20%)

**Dependent Variables:** Pass rate, accuracy degradation slope

**Benchmarks:** HumanEval subset (20 prompts)

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 3 formats x 4 noise levels = 2,400 API calls

**Estimated Cost:** $15-30 (most expensive hypothesis; consider as Phase 11 stretch goal)

**Expected Effect:** Structured formats show shallower accuracy degradation curve with increasing noise

**Measurement:** GLMM with format x noise_level interaction term; compare degradation slopes. Uses existing `analyze_results.py` GLMM infrastructure and existing `noise_generator.py` for noise injection.

**Supporting Evidence:** No direct evidence -- this is a NOVEL hypothesis. Motivated by: (a) structural tokens like XML tags are longer multi-character sequences and may survive character mutations better than short prose connectors, (b) prose connectors ("the," "and," "so") are high-entropy single tokens vulnerable to noise, (c) our experiment suite uniquely positions us to test this since we already have noise injection infrastructure.

**Risks/Caveats:** Most expensive hypothesis. Noise injection on XML tags could break structure entirely (e.g., `<task>` becomes `<tsak>`), which would be worse than prose degradation. The 2,400-call sample size makes this a stretch goal. Consider running 5 prompts x 3 formats x 4 noise levels = 60 calls as a micro-pilot first.

---

### H-FMT-06: Question Mark Presence for Query Prompts

**Priority:** LOW

**Claim:** Including vs. omitting a question mark at the end of a query prompt has a measurable (but small) effect on response quality, particularly for GSM8K math questions.

**Independent Variable:** Terminal question mark (present vs. absent)

**Dependent Variables:** Pass rate

**Benchmarks:** GSM8K subset (20 prompts that are questions)

**Models:** Claude Sonnet (`claude-sonnet-4-20250514`), Gemini 1.5 Pro (`gemini-1.5-pro`)

**Sample Size:** 20 prompts x 5 repetitions x 2 models x 2 formats = 400 API calls

**Estimated Cost:** $2-5

**Expected Effect:** Less than 2% accuracy difference (may be noise)

**Measurement:** McNemar's test for significance. Uses existing `grade_results.py` GSM8K grading.

**Supporting Evidence:** "When Punctuation Matters" (ArXiv:2508.11383) suggests punctuation carries signal, but question marks specifically are understudied. This is a micro-formatting probe -- quick to run and potentially surprising.

**Risks/Caveats:** Effect size may be too small to detect with 20 prompts (statistical power concern). Consider as a quick-add to another experiment (e.g., run alongside H-FMT-04) rather than standalone. If the effect is less than 1%, it is likely not worth reporting.

---

### Hypothesis Summary Table

| ID | Hypothesis | Priority | API Calls | Est. Cost | Expected Effect |
|----|-----------|----------|-----------|-----------|-----------------|
| H-FMT-01 | TOON compact notation | HIGH | 400 | $3-8 | 30-40% token reduction, <5% accuracy change |
| H-FMT-02 | XML structured markup | HIGH | 400 | $3-8 | Claude +5-10%, Gemini neutral |
| H-FMT-03 | Bullet format for math | MEDIUM | 400 | $2-5 | 15-25% token reduction, <3% accuracy change |
| H-FMT-04 | Punctuation removal | HIGH | 400 | $3-8 | 5-10% token reduction, 2-8% accuracy DECREASE |
| H-FMT-05 | Format x noise interaction | MEDIUM | 2,400 | $15-30 | Structured formats more noise-robust |
| H-FMT-06 | Question mark presence | LOW | 400 | $2-5 | <2% accuracy difference |
| **Total** | | | **4,400** | **$28-64** | |

---

## Experiment Designs for Top Hypotheses

The following detailed experiment designs cover the top 3 hypotheses by priority (H-FMT-01, H-FMT-02, H-FMT-04). These are ready for Phase 11 to implement directly.

### Experiment Design: H-FMT-01 (TOON Compact Notation)

**Prompt Selection:**
Select 20 prompts from `data/prompts.json` that contain structured context or constraints. Selection criteria: prompts with parameter descriptions, input/output specifications, or constraint lists (common in HumanEval and MBPP). Prefer prompts where the docstring contains at least 3 distinct information fields (e.g., parameters, return value, constraints) to maximize the format conversion opportunity.

**Format Conversion Method:**
Use a cheap pre-processor model (Haiku or Flash, per `PREPROC_MODEL_MAP` in `src/config.py`) to convert verbose NL prompts to TOON-like compact notation. The conversion prompt should instruct: "Rewrite the following prompt using compact key:value notation. Remove all prose connectors and filler words. Preserve all semantic content. Use indented sub-items for lists." Manual review of 5 converted prompts to verify semantic equivalence before running the full set.

**Control Condition:**
The existing "raw" intervention serves as the baseline -- prompts in their original verbose NL format from `data/prompts.json`.

**New Intervention Definition:**
Add `"format_toon"` as a new entry in the `INTERVENTIONS` tuple in `src/config.py`. The intervention pipeline would: (1) send the clean prompt to the pre-processor model with TOON conversion instructions, (2) pass the TOON-formatted result to the target model for execution. This follows the same callable injection pattern as `prompt_compressor.py`.

**Statistical Analysis:**
- **Primary:** McNemar's test comparing pass/fail on paired prompts (same prompt, two formats). Already implemented in `analyze_results.py`.
- **Secondary:** Token count ratio (TOON / verbose NL) with bootstrap CIs. Already implemented in `analyze_results.py`.
- **Exploratory:** GLMM with format as a factor to check for model-specific effects.

**Success Criteria:**
- Token reduction of at least 20% (conservative bound) across the 20-prompt set
- Accuracy difference less than 5% (not statistically significant by McNemar's at alpha=0.05)
- If both criteria met: format is worth including in the paper as a "free" efficiency gain

**Pilot Protocol:**
Run 5 prompts first (5 prompts x 5 repetitions x 2 models x 2 formats = 100 API calls, ~$1-2). Check: (1) TOON conversion produces valid, semantically equivalent prompts, (2) token reduction is in the expected 30-40% range, (3) no catastrophic accuracy drops. If pilot shows less than 10% token reduction, abandon hypothesis.

---

### Experiment Design: H-FMT-02 (XML Structured Markup)

**Prompt Selection:**
Select 20 prompts spanning all three benchmarks: 8 from HumanEval (multi-part function specifications), 6 from MBPP (task descriptions with examples), 6 from GSM8K (word problems with multiple given values). Selection criteria: prefer prompts with at least 2 distinct sections (e.g., task description + examples, or problem statement + constraints) to give XML structure something meaningful to delimit.

**Format Conversion Method:**
Use a cheap pre-processor model to wrap prompt sections in XML tags. The conversion prompt should instruct: "Add XML tags to structure this prompt. Use `<task>` for the main instruction, `<context>` for background information, `<constraints>` for requirements, `<examples>` for examples, and `<question>` for the specific question. Do not change the text content." The XML tag vocabulary is deliberately small (5 tags) to minimize overhead.

**Control Condition:**
The existing "raw" intervention -- prompts in plain text without any structural markup.

**New Intervention Definition:**
Add `"format_xml_structured"` as a new entry in the `INTERVENTIONS` tuple. The pipeline would: (1) send the clean prompt to the pre-processor model with XML tagging instructions, (2) pass the XML-tagged result to the target model. For Claude specifically, the XML tags align with Anthropic's recommended prompting patterns.

**Statistical Analysis:**
- **Primary:** Per-model accuracy comparison using McNemar's test. Run separately for Claude and Gemini to detect model-specific effects.
- **Secondary:** GLMM with format x model interaction term. The interaction coefficient reveals whether XML helps one model more than the other. Already implemented in `analyze_results.py`.
- **Exploratory:** TTFT comparison -- does XML structure affect time-to-first-token (suggesting different parsing behavior)?

**Success Criteria:**
- Statistically significant accuracy improvement (p < 0.05) for at least one model
- OR a statistically significant format x model interaction (p < 0.05) demonstrating model-specific format preferences
- If neither: the hypothesis is informative as a null result (format does not matter for these tasks)

**Pilot Protocol:**
Run 5 prompts first (5 prompts x 5 repetitions x 2 models x 2 formats = 100 API calls, ~$1-2). Check: (1) XML conversion produces well-formed tags, (2) token overhead is in the expected 5-15% range, (3) Claude shows any trend toward improvement. If pilot shows Claude accuracy decreases with XML, reconsider the hypothesis framing.

---

### Experiment Design: H-FMT-04 (Punctuation Removal)

**Prompt Selection:**
Select 20 prompts from HumanEval and MBPP that contain substantial natural language instruction text (not just function signatures). Selection criteria: prompts with at least 50 tokens of prose instruction, excluding prompts that are purely code templates. This ensures there is meaningful punctuation to remove and the effect is measurable.

**Format Conversion Method:**
Regex-based automated removal -- no pre-processor model needed. The conversion script should:
1. Remove trailing periods from instruction sentences
2. Remove commas in list enumerations (but preserve commas in code examples)
3. Remove semicolons used as sentence separators
4. Preserve colons (used in parameter descriptions), question marks (studied separately in H-FMT-06), and all punctuation within code blocks
5. Preserve apostrophes in contractions ("don't" stays as "don't")

This is a deterministic transformation that does not require LLM assistance, making it the cheapest hypothesis to implement.

**Control Condition:**
The existing "raw" intervention -- prompts with full original punctuation.

**New Intervention Definition:**
Add `"format_no_punctuation"` as a new entry in the `INTERVENTIONS` tuple. The pipeline is purely regex-based (no API call needed for format conversion), making this the only zero-preprocessing-cost intervention among the format hypotheses.

**Statistical Analysis:**
- **Primary:** McNemar's test on paired pass/fail results (punctuation vs. no punctuation).
- **Secondary:** CR (consistency rate) comparison using `compute_derived.py` -- does punctuation removal affect answer stability across the 5 repetitions?
- **Exploratory:** Per-model breakdown to check if punctuation sensitivity differs between Claude and Gemini (as "Punctuation and Predicates" suggests for other model pairs).

**Success Criteria:**
- A statistically significant accuracy difference (p < 0.05 by McNemar's) in either direction
- If accuracy decreases: confirms the punctuation-as-attention-sink hypothesis and provides a cautionary finding for the paper
- If accuracy is unchanged: punctuation removal is safe for coding tasks (different from MMLU findings)
- If accuracy increases: surprising and highly publishable

**Pilot Protocol:**
Run 5 prompts first (5 prompts x 5 repetitions x 2 models x 2 formats = 100 API calls, ~$1-2). Check: (1) punctuation removal script correctly handles edge cases (code blocks, apostrophes), (2) token reduction is in the expected 5-10% range, (3) no format-breaking artifacts. Since the conversion is regex-based, also manually verify 5 converted prompts for readability.

---

## Integration Notes

This section describes how the research findings and proposed hypotheses map to the existing experiment framework, enabling Phase 11 to implement these as concrete experiments.

### New Intervention Types

New prompt formats would become new entries in the `INTERVENTIONS` tuple in `src/config.py`:

```python
# Current interventions (src/config.py)
INTERVENTIONS: tuple[str, ...] = (
    "raw",
    "self_correct",
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "prompt_repetition",
    # Proposed format interventions:
    # "format_toon",              # H-FMT-01
    # "format_xml_structured",    # H-FMT-02
    # "format_bullet",            # H-FMT-03
    # "format_no_punctuation",    # H-FMT-04
)
```

### Pre-processor Pattern

Format conversion would follow the pre-processor pattern established in `src/prompt_compressor.py`. For LLM-based conversions (H-FMT-01, H-FMT-02, H-FMT-03):
- The cheap pre-processor model (Haiku or Flash, per `PREPROC_MODEL_MAP`) converts the prompt format before the target model processes it
- The `call_fn` callable injection pattern from `prompt_compressor.py` handles the API call
- Pre-processor cost is logged separately from target model cost (already supported)

For regex-based conversions (H-FMT-04):
- No pre-processor model needed -- the conversion is a deterministic string transformation
- This makes H-FMT-04 the cheapest hypothesis to test (zero format conversion cost)

### Existing Analysis Tools

All proposed experiments slot into the existing analysis infrastructure:
- **`analyze_results.py` GLMM:** Already handles `intervention` as a factor. New format interventions would appear as additional levels in the GLMM, requiring no code changes to the analysis pipeline.
- **`analyze_results.py` McNemar's test:** Paired comparison between format variants uses the same test infrastructure as existing intervention comparisons.
- **`compute_derived.py` CR calculation:** Consistency rate across 5 repetitions applies to format experiments identically.
- **`compute_derived.py` cost rollups:** Token count differences from format changes would show up automatically in `compute_cost()` metrics since costs are calculated from actual token counts logged per API call.

### Token Count Impact

Format changes primarily affect input token counts:
- H-FMT-01 (TOON): Expected 30-40% input token reduction, directly reducing cost
- H-FMT-02 (XML): Expected 5-15% input token increase, a cost penalty that must be justified by accuracy gains
- H-FMT-03 (Bullet): Expected 15-25% input token reduction
- H-FMT-04 (Punctuation): Expected 5-10% input token reduction

These differences would be captured by the existing token logging in `run_experiment.py` and priced via `compute_cost()` in `config.py`.

### Phase 11 Pickup

Phase 11 should pick up the following hypotheses as concrete micro-formatting test questions:
- **H-FMT-01 through H-FMT-04:** Ready for immediate pilot testing. Each has a complete experiment design with prompt selection criteria, conversion method, statistical analysis plan, and success criteria.
- **H-FMT-05 (Format x Noise Interaction):** Flag as a stretch goal due to the 2,400-call cost. Consider running a 60-call micro-pilot (5 prompts x 3 formats x 4 noise levels) to determine if the effect is detectable before committing to the full experiment.
- **H-FMT-06 (Question Mark):** Consider bundling with H-FMT-04 (punctuation removal) as a quick add-on rather than a standalone experiment.

### Novel Contribution Opportunity

H-FMT-05 (Format x Noise Interaction) should be flagged for the whitepaper abstract as a potential novel contribution. No existing paper examines whether structured formatting affects noise robustness. If the format x noise_level interaction term in the GLMM is significant, this becomes a unique finding: "Structured prompt formats (XML, bullets) provide a secondary benefit beyond readability -- they make prompts more robust to character-level noise." This directly extends the Linguistic Tax thesis from measuring noise effects to demonstrating a format-based mitigation strategy.

---

## References

- He, J. et al. (2024). "Does Prompt Formatting Have Any Impact on LLM Performance?" ArXiv:2411.10541.
- TOON Format Specification. github.com/toon-format/toon.
- Jiang, H. et al. (2025). "CompactPrompt: A Unified Pipeline for Prompt and Data Compression in LLM Workflows." ArXiv:2510.18043.
- Jiang, H. et al. (2023). "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." ArXiv:2310.05736.
- Gurnee, W. et al. (2025). "LLM-Microscope: Uncovering the Hidden Role of Punctuation in Context Memory of Transformers." ArXiv:2502.15007.
- Cao, X. et al. (2025). "When Punctuation Matters: A Comprehensive Study on the Robustness of LLMs to Punctuation Variations." ArXiv:2508.11383.
- Zhang, Y. et al. (2025). "Punctuation and Predicates: Understanding the Role of Punctuation in LLM Reasoning." ArXiv:2508.14067.
- Wang, Z. et al. (2025). "CFPO: Content-Format Prompt Optimization for LLMs." ArXiv:2502.04295.
- Li, S. et al. (2024). "Prompt Compression for Large Language Models: A Survey." ArXiv:2410.12388.
- Chen, M. et al. (2025). "Lossless Token Sequence Compression via Meta-Tokens." ArXiv:2506.00307.
- Wu, T. et al. (2025). "ProCut: LLM Prompt Compression via Attribution Estimation." ArXiv:2508.02053.
- Liu, Y. et al. (2025). "LLM-DCP: Dynamic Compressing Prompts for Efficient Inference of Large Language Models." ArXiv:2504.11004.
- Anthropic. "Use XML Tags to Structure Your Prompts." Anthropic Documentation. https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags.
