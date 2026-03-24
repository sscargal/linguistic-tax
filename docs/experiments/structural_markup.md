# Structural Markup Experiments: XML Tags and Hierarchical Structure

**Parent Hypothesis:** H-FMT-02 (XML Structured Markup for Claude vs. Gemini)
**Date:** 2026-03-24
**Status:** Draft
**Cluster ID:** SM (Structural Markup)

---

## Overview

This document contains atomic experiment specifications for H-FMT-02, which tests whether XML-tagged prompt structure improves accuracy differently across model families. The core claim is that Claude benefits from XML structure (given Anthropic's explicit recommendation) while other models show neutral or negative effects, demonstrating model-specific format preferences.

**Critical design principles:**
- **Per-model analysis is mandatory.** He et al. (ArXiv:2411.10541) showed IoU < 0.2 between model format preferences, with up to 40% performance variation from format alone. Every spec below requires per-model results -- never average across models.
- **XML token overhead must be measured.** XML tags add tokens (estimated 5-15% overhead). Every spec includes token overhead as a measured dependent variable, not just accuracy.
- **Anthropic's XML recommendation is motivation, not evidence.** Anthropic recommends XML for Claude in their documentation, but this is not peer-reviewed empirical evidence. Our experiments provide the controlled measurement.
- **Claude's training bias:** Claude's training data likely includes XML-structured content, making Claude a biased test subject (favorable to XML). This is a feature of the experiment, not a bug -- we are testing whether training-aligned formatting helps.
- **Model-specific format preference is the KEY measurement.** If both Claude and Gemini respond identically to XML, the hypothesis is falsified. The expected finding is a model x format interaction.

---

## H-FMT-02: XML Structured Markup

### AQ-SM-01: XML Tags Wrapping Instruction vs. Context in HumanEval

**Parent Hypothesis:** H-FMT-02
**Claim:** Wrapping HumanEval prompts with XML tags separating instruction from context improves Claude accuracy by 5-10% but has no effect or negative effect on Gemini, demonstrating model-specific format preferences.

**Independent Variable:** Prompt structure (plain text vs. XML-tagged sections separating instruction and context)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified HumanEval prompt, no XML tags)
**Treatment Condition:** Same prompt content wrapped in XML tags: `<task>` for the instruction, `<context>` for the function signature and docstring, `<examples>` for test cases. No content is changed -- only structural markup is added.

**Dependent Variables:** Pass rate (per model), input token count, token overhead from XML tags, TTFT

**Benchmarks:** HumanEval (code generation with function signatures)
**Prompt Selection Criteria:** Select HumanEval prompts from data/prompts.json that have distinct instruction, context, and example sections (at least 2 of 3). Avoid single-sentence prompts where XML structure adds overhead with no structural benefit.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet (claude-sonnet-4-20250514) AND Gemini 1.5 Pro (gemini-1.5-pro) -- both paid models are essential since the hypothesis is about model-specific effects
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (with paid models)
**Estimated Cost:** $0 (free models) / $5-12 (paid: Claude Sonnet $3.00/$15.00 per 1M in/out, Gemini 1.5 Pro $1.25/$5.00 per 1M in/out)

**Format Conversion Method:**
- Rule-based template wrapping (no LLM needed)
- Conversion rules:
  1. Identify the task instruction (usually the first sentence or imperative statement)
  2. Identify the function signature and docstring (context)
  3. Identify test cases/examples (if present)
  4. Wrap each section:
     ```xml
     <task>Write a function that checks if any two numbers in a list are closer than a threshold.</task>
     <context>
     def has_close_elements(numbers: List[float], threshold: float) -> bool:
         """Check if in given list of numbers, are any two numbers closer to each
         other than given threshold."""
     </context>
     <examples>
     >>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3)
     True
     >>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05)
     False
     </examples>
     ```
  5. No content modification -- only add XML tags

**Concrete example:**

*Control (original):*
```
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each
    other than given threshold.
    >>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3)
    True
    >>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05)
    False
    """
```

*Treatment (XML-wrapped):*
```xml
<task>Check if in given list of numbers, are any two numbers closer to each other than given threshold.</task>
<context>
def has_close_elements(numbers: List[float], threshold: float) -> bool:
</context>
<examples>
>>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3)
True
>>> has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05)
False
</examples>
```

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison, per model separately)
- Secondary: GLMM with format x model interaction term; token overhead measurement (treatment tokens / control tokens); bootstrap CI for per-model effect sizes

**Success Criteria:**
- Positive result (model-specific): Claude accuracy improves >= 5% with XML (p < 0.10) AND Gemini accuracy change is < 3% or negative -- demonstrating model x format interaction
- Negative result (universal): Both models show same direction of accuracy change (> 3% change in same direction)
- Null result: Neither model shows > 3% accuracy change (XML structure does not matter for either)
- Key measurement: the model x format INTERACTION, not the main effect

**Pilot Protocol:** 5 prompts first (5 x 5 x 2 conditions = 50 calls on free model; 150 with paid). Go if: XML overhead < 20% additional tokens and no accuracy drop > 15%. No-go if: XML tags break model output formatting.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw HumanEval prompts) with AQ-TE-01 and AQ-TE-06

---

### AQ-SM-02: XML Tags for Parameter and Return-Type Annotation

**Parent Hypothesis:** H-FMT-02
**Claim:** Explicitly annotating function parameters and return types with XML tags (`<params>`, `<returns>`) in coding prompts helps models identify function signature requirements, improving accuracy by 3-8% on prompts with complex signatures.

**Independent Variable:** Parameter presentation (inline prose vs. XML-annotated parameters)
**Control Condition:** Original raw prompt from data/prompts.json (parameters described inline in docstring prose)
**Treatment Condition:** Parameters and return types extracted into dedicated XML-tagged sections within the docstring. The rest of the prompt is unchanged.

**Dependent Variables:** Pass rate (per model), input token count, token overhead from XML tags

**Benchmarks:** HumanEval + MBPP (coding tasks with function signatures)
**Prompt Selection Criteria:** Select prompts from data/prompts.json with at least 3 parameters OR complex return types (e.g., List[List[int]], Dict[str, Any]). These are prompts where parameter parsing is non-trivial and structural markup might help.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet and Gemini 1.5 Pro for model-specific comparison
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Rule-based extraction (no LLM needed)
- Conversion rules:
  1. Extract parameter names, types, and descriptions from docstring
  2. Extract return type and description
  3. Wrap in XML:
     ```xml
     <params>
       <param name="numbers" type="List[float]">input list of numbers</param>
       <param name="threshold" type="float">minimum distance between elements</param>
     </params>
     <returns type="bool">True if any pair closer than threshold</returns>
     ```
  4. Preserve task description and examples outside the XML block

**Statistical Analysis:**
- Primary: McNemar's test (per model)
- Secondary: Token overhead ratio; correlation between parameter count and accuracy improvement (does XML help more for complex signatures?)

**Success Criteria:**
- Positive result: Accuracy improves >= 3% on prompts with 3+ parameters (per at least one model)
- Negative result: Accuracy drops or XML overhead (> 15% more tokens) negates any accuracy benefit on a cost basis
- Null result: Accuracy change < 2% across all models

**Pilot Protocol:** 5 prompts first (50 calls). Go if: model output correctly uses all annotated parameter types. No-go if: XML parameter tags confuse model into generating XML in output.

**Tier:** 2
**Bundling Opportunity:** Shares control condition with AQ-SM-01 (both use raw HumanEval/MBPP prompts); can share XML-tagged prompts with AQ-SM-04 (nested vs. flat comparison)

---

### AQ-SM-03: XML Tags for GSM8K Problem Structure

**Parent Hypothesis:** H-FMT-02
**Claim:** Wrapping GSM8K math problems with XML tags separating given information (`<given>`), the question (`<question>`), and constraints (`<constraints>`) helps models parse word problems, with model-specific effects (Claude expected to benefit more than Gemini).

**Independent Variable:** Problem structure (prose narrative vs. XML-tagged sections)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified GSM8K prose word problem)
**Treatment Condition:** Same content restructured into XML sections:
  ```xml
  <given>Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four.</given>
  <question>How much in dollars does she make every day at the farmers' market?</question>
  <constraints>She sells every duck egg at the farmers' market for $2 each.</constraints>
  ```

**Dependent Variables:** Pass rate (per model), input token count, token overhead from XML tags

**Benchmarks:** GSM8K (math word problems)
**Prompt Selection Criteria:** Select GSM8K prompts from data/prompts.json with at least 3 sentences, containing distinct given information, a question, and ideally explicit constraints. Prefer multi-step problems where structural parsing is non-trivial.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet AND Gemini 1.5 Pro (model comparison is essential)
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid)
**Estimated Cost:** $0 (free models) / $3-8 (paid escalation)

**Format Conversion Method:**
- Manual template conversion (rule-based)
- Conversion rules:
  1. Identify given information (facts, quantities, relationships)
  2. Identify the question being asked
  3. Identify any explicit constraints or conditions
  4. Wrap each in the appropriate XML tag
  5. Preserve all content verbatim -- only add structural tags

**Statistical Analysis:**
- Primary: McNemar's test (per model separately)
- Secondary: GLMM with format x model interaction term; token overhead measurement

**Success Criteria:**
- Positive result (model-specific): Claude accuracy improves >= 5% with XML AND Claude-Gemini difference is significant in GLMM interaction term (p < 0.10)
- Negative result (universal help): Both models improve equally (no model-specific effect)
- Null result: Neither model shows > 3% accuracy change
- Note: For short GSM8K problems (< 3 sentences), XML overhead likely outweighs benefit. Track separately.

**Pilot Protocol:** 5 prompts first (50 calls). Go if: XML overhead < 25% and no accuracy drop > 10%. No-go if: XML structure breaks model's chain-of-thought reasoning.

**Tier:** 2
**Bundling Opportunity:** Shares control condition (raw GSM8K prompts) with AQ-TE-03 and AQ-TE-05

---

### AQ-SM-04: Nested XML Hierarchy vs. Flat XML Structure

**Parent Hypothesis:** H-FMT-02
**Claim:** Deeply nested XML hierarchy (`<task><context><constraints>...`) provides diminishing returns or hurts models compared to flat XML (all sections at the same nesting level), particularly for models not trained on deeply nested XML.

**Independent Variable:** XML nesting depth (flat: all tags at root level vs. nested: hierarchical structure)
**Control Condition:** Flat XML structure (all tags at the same level, as used in AQ-SM-01)
**Treatment Condition:** Nested XML structure with hierarchical containment:
  ```xml
  <task>
    <instruction>Write a function that...</instruction>
    <context>
      <signature>def has_close_elements(numbers: List[float], threshold: float) -> bool:</signature>
      <constraints>
        <constraint>Numbers can be negative</constraint>
        <constraint>Threshold is always positive</constraint>
      </constraints>
    </context>
    <examples>
      <example input="[1.0, 2.0], 0.3" output="False"/>
      <example input="[1.0, 2.0, 3.9, 4.0], 0.1" output="True"/>
    </examples>
  </task>
  ```

**Dependent Variables:** Pass rate (per model), input token count, token overhead (nested vs. flat)

**Benchmarks:** HumanEval (code generation -- complex enough to have meaningful nesting)
**Prompt Selection Criteria:** Select HumanEval prompts from data/prompts.json with at least 3 distinct sections (instruction, context/signature, constraints, examples). These are prompts where nesting depth is a meaningful variable.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet and Gemini 1.5 Pro for model comparison
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Rule-based template conversion (no LLM needed)
- Two templates prepared per prompt:
  - Flat: all XML tags at root level (same as AQ-SM-01 treatment)
  - Nested: hierarchical structure with task > context > constraints > examples nesting
- Conversion rules for nested:
  1. Create root `<task>` element
  2. Nest `<instruction>` as child of `<task>`
  3. Nest `<context>` as child of `<task>`, containing `<signature>` and `<constraints>`
  4. Nest `<examples>` as child of `<task>`
  5. Use attributes for compact representation where appropriate (e.g., `<example input="..." output="..."/>`)

**Concrete example (flat vs. nested):**

*Flat XML:*
```xml
<instruction>Check if any two numbers in list are closer than threshold.</instruction>
<signature>def has_close_elements(numbers: List[float], threshold: float) -> bool:</signature>
<constraints>Numbers can be negative. Threshold is always positive.</constraints>
<examples>
>>> has_close_elements([1.0, 2.0, 3.9, 4.0], 0.3) -> True
>>> has_close_elements([1.0, 2.0, 3.9, 4.0], 0.05) -> False
</examples>
```

*Nested XML:*
```xml
<task>
  <instruction>Check if any two numbers in list are closer than threshold.</instruction>
  <context>
    <signature>def has_close_elements(numbers: List[float], threshold: float) -> bool:</signature>
    <constraints>
      <constraint>Numbers can be negative</constraint>
      <constraint>Threshold is always positive</constraint>
    </constraints>
  </context>
  <examples>
    <example input="[1.0, 2.0, 3.9, 4.0], 0.3" output="True"/>
    <example input="[1.0, 2.0, 3.9, 4.0], 0.05" output="False"/>
  </examples>
</task>
```

**Statistical Analysis:**
- Primary: McNemar's test comparing flat vs. nested accuracy (per model)
- Secondary: Token overhead comparison (nested typically adds 10-20% more tokens than flat due to closing tags and attributes); GLMM with nesting x model interaction

**Success Criteria:**
- Positive result (nesting hurts): Nested XML accuracy is lower than flat by >= 3% on at least one model (p < 0.10)
- Negative result (nesting helps): Nested XML accuracy is higher than flat by >= 3%
- Null result: Difference < 2% (nesting depth does not matter)
- Secondary: If nesting adds > 15% more tokens than flat with no accuracy benefit, flat is strictly preferred on cost basis

**Pilot Protocol:** 5 prompts first (50 calls). Go if: both flat and nested XML produce valid model output. No-go if: models generate XML in their output (confused by nested structure).

**Tier:** 2
**Bundling Opportunity:** Requires AQ-SM-01 flat XML data as control; can reuse flat XML prompts directly. Run after AQ-SM-01.

---

### AQ-SM-05: XML Tag Token Overhead Measurement

**Parent Hypothesis:** H-FMT-02
**Claim:** XML structural tags add 5-15% token overhead to prompts, with the exact overhead varying by prompt type (short prompts have proportionally higher overhead than long prompts) and by tokenizer (different models tokenize XML tags differently).

**Independent Variable:** XML presence (original prompt vs. XML-tagged prompt -- same content)
**Control Condition:** Original raw prompt from data/prompts.json (no XML tags)
**Treatment Condition:** Same prompt with XML structural tags added (same conversion as AQ-SM-01)

**Dependent Variables:** Input token count (primary), token overhead ratio (treatment/control), pass rate (secondary -- to confirm XML does not change accuracy on this measurement-focused experiment)

**Benchmarks:** All three benchmarks -- HumanEval, MBPP, GSM8K -- to measure overhead variation by prompt type
**Prompt Selection Criteria:** Select a stratified sample: 7 HumanEval, 7 MBPP, 6 GSM8K prompts from data/prompts.json, chosen to represent the range of prompt lengths (short/medium/long within each benchmark).
**Prompt Count:** 20 prompts (stratified across 3 benchmarks)

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) -- primarily a token counting exercise; escalate to Claude Sonnet and Gemini 1.5 Pro to compare tokenizer differences
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid)
**Estimated Cost:** $0 (free models) / $4-10 (paid escalation)

**Format Conversion Method:**
- Rule-based XML wrapping (same as AQ-SM-01)
- For overhead measurement, count tokens using each model's tokenizer:
  - Claude: Anthropic token counting API
  - Gemini: Google token counting API
  - Nemotron/OpenRouter: tiktoken cl100k_base as approximation
- Record both character count and token count for control and treatment

**Statistical Analysis:**
- Primary: Paired t-test on token overhead ratio across prompts
- Secondary: Linear regression of overhead ratio vs. prompt length (test whether short prompts have proportionally higher overhead); per-benchmark comparison of overhead ratios

**Success Criteria:**
- Positive result: XML adds a measurable, consistent overhead with tight confidence interval (e.g., 8% +/- 2% across benchmarks)
- Key output: A concrete number for "XML costs X% more tokens" that other specs can reference
- Secondary: If overhead varies significantly by prompt length or benchmark, document the relationship

**Pilot Protocol:** 5 prompts first (2 HumanEval, 2 MBPP, 1 GSM8K). Go if: token counting works correctly. No-go if: tokenizer APIs are unavailable or give inconsistent counts.

**Tier:** 1
**Bundling Opportunity:** Can share XML-wrapped prompts with AQ-SM-01, AQ-SM-03; provides the overhead measurement needed by all other AQ-SM specs

---

### AQ-SM-06: Markdown Headers as Lightweight Structural Alternative

**Parent Hypothesis:** H-FMT-02
**Claim:** Markdown headers (`## Section`) provide some structural benefits of XML with lower token overhead (estimated 2-5% overhead vs. 5-15% for XML), making markdown a more cost-efficient structural alternative for models without XML training bias.

**Independent Variable:** Structural format (plain text vs. markdown headers vs. XML tags)
**Control Condition:** Original raw prompt from data/prompts.json (no structural markup)
**Treatment Condition A:** Markdown-structured prompt with `##` headers for sections
**Treatment Condition B:** XML-structured prompt (same as AQ-SM-01 treatment, for direct comparison)

**Dependent Variables:** Pass rate (per model), input token count, token overhead (markdown vs. XML vs. plain)

**Benchmarks:** HumanEval (code generation)
**Prompt Selection Criteria:** Same 20 prompts as AQ-SM-01 to enable direct three-way comparison (plain vs. markdown vs. XML).
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet and Gemini 1.5 Pro for model comparison
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 3 = 300 (free, 3 conditions); 20 x 5 x 3 x 3 = 900 (paid)
**Estimated Cost:** $0 (free models) / $7-16 (paid escalation)

**Format Conversion Method:**
- Rule-based template conversion (no LLM needed)
- Markdown conversion rules:
  1. Add `## Task` header before the instruction
  2. Add `## Context` header before the function signature
  3. Add `## Examples` header before test cases
  4. No content modification -- only add markdown headers and blank lines
- Markdown example:
  ```markdown
  ## Task
  Check if any two numbers in list are closer than threshold.

  ## Context
  def has_close_elements(numbers: List[float], threshold: float) -> bool:

  ## Examples
  >>> has_close_elements([1.0, 2.0, 3.9, 4.0], 0.3)
  True
  ```

**Statistical Analysis:**
- Primary: McNemar's test for each pairwise comparison (plain vs. markdown, plain vs. XML, markdown vs. XML) per model
- Secondary: Token overhead comparison (markdown vs. XML); GLMM with format (3 levels) x model interaction

**Success Criteria:**
- Positive result: Markdown achieves >= 50% of XML's accuracy benefit with <= 50% of XML's token overhead (markdown is more cost-efficient)
- Negative result: Markdown provides no accuracy benefit over plain text (structure requires explicit delimiters, not just headers)
- Null result: All three formats produce equivalent accuracy (structural markup does not matter)
- Key comparison: If XML helps Claude but not Gemini, does markdown help both equally (model-agnostic structure)?

**Pilot Protocol:** 5 prompts first (5 x 5 x 3 conditions = 75 calls). Go if: all three formats produce valid output. No-go if: markdown headers appear in model output (model treats headers as content).

**Tier:** 2
**Bundling Opportunity:** Must use same 20 prompts as AQ-SM-01 for valid comparison; shares XML treatment with AQ-SM-01; shares control with AQ-TE-01 and AQ-TE-06

---

## Summary Table

| ID | Name | Parent | Tier | Benchmarks | Prompts | Free API Calls | Paid API Calls | Free Cost | Paid Cost |
|----|------|--------|------|------------|---------|----------------|----------------|-----------|-----------|
| AQ-SM-01 | XML instruction/context wrapping | H-FMT-02 | 1 | HumanEval | 20 | 200 | 600 | $0 | $5-12 |
| AQ-SM-02 | XML parameter annotation | H-FMT-02 | 2 | HumanEval+MBPP | 20 | 200 | 600 | $0 | $5-12 |
| AQ-SM-03 | XML for GSM8K structure | H-FMT-02 | 2 | GSM8K | 20 | 200 | 600 | $0 | $3-8 |
| AQ-SM-04 | Nested vs. flat XML | H-FMT-02 | 2 | HumanEval | 20 | 200 | 600 | $0 | $5-12 |
| AQ-SM-05 | XML token overhead measurement | H-FMT-02 | 1 | All three | 20 | 200 | 600 | $0 | $4-10 |
| AQ-SM-06 | Markdown vs. XML structure | H-FMT-02 | 2 | HumanEval | 20 | 300 | 900 | $0 | $7-16 |
| **Totals** | | | | | **120** | **1,300** | **3,900** | **$0** | **$29-70** |

### Tier Breakdown

| Tier | Questions | Free API Calls | Paid API Calls | Description |
|------|-----------|----------------|----------------|-------------|
| 1 | AQ-SM-01, AQ-SM-05 | 400 | 1,200 | Core XML effect + overhead measurement -- run first |
| 2 | AQ-SM-02, AQ-SM-03, AQ-SM-04, AQ-SM-06 | 900 | 2,700 | Deeper investigation if Tier 1 shows model-specific effects |

### Bundling Opportunities

- **HumanEval control group:** AQ-SM-01, AQ-SM-02, AQ-SM-04, AQ-SM-06 all share the same raw HumanEval prompts as control. Run control once, reuse.
- **XML treatment reuse:** AQ-SM-01 flat XML prompts serve as control for AQ-SM-04 (nested comparison) and as treatment for AQ-SM-06 (markdown comparison).
- **Token overhead data:** AQ-SM-05 provides the overhead numbers referenced by all other AQ-SM specs. Run AQ-SM-05 first or concurrently with AQ-SM-01.
- **Cross-cluster control sharing:** AQ-SM-01 shares HumanEval control with AQ-TE-01 and AQ-TE-06 from the token efficiency cluster.

### Model Escalation Strategy

1. Run AQ-SM-01 and AQ-SM-05 on nvidia/nemotron-3-super-120b-a12b:free first
2. **Immediate paid escalation is recommended for AQ-SM-01** -- the hypothesis is specifically about Claude vs. Gemini, so free models cannot fully test it. If budget allows, run AQ-SM-01 on Claude Sonnet and Gemini 1.5 Pro from the start.
3. If Nemotron shows any accuracy difference (> 3%) between plain and XML:
   - Escalate to Claude Sonnet and Gemini 1.5 Pro to test model-specificity
   - This is the core hypothesis -- model x format interaction must be tested on different model families
4. If Nemotron shows null results:
   - Still escalate AQ-SM-01 to paid models (Nemotron null does not mean Claude null, given Claude's XML training)
   - Do not escalate other AQ-SM questions unless AQ-SM-01 shows something on paid models
