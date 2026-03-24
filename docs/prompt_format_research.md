# Prompt Format Research: Optimal Input Formats for LLM Reasoning

**Date:** 2026-03-24
**Status:** Draft
**Context:** Companion research for "The Linguistic Tax" whitepaper
**Purpose:** Survey how prompt input formats affect LLM reasoning accuracy and token efficiency; produce testable hypotheses for experiment design

---

## Executive Summary

This document surveys 6 format categories and will propose testable hypotheses ranked by feasibility (to be finalized in Plan 02). The categories span token-optimized notations, structured markup, minimal/telegraphic formats, punctuation variations, hybrid/novel approaches, and the verbose natural language baseline used in our current experiment suite. Cross-cutting findings indicate that format effects are model-specific, punctuation removal is counterintuitively harmful, and the interaction of format with noise is an unstudied dimension that represents a potential novel contribution for the Linguistic Tax whitepaper. Hypotheses and concrete experiment designs will be added upon completion of the taxonomy analysis.

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
