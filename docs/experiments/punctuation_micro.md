# Punctuation Micro-Formatting Experiments: Removal Effects and Individual Punctuation Roles

**Parent Hypotheses:** H-FMT-04 (Punctuation Removal Effects on Coding Tasks), H-FMT-06 (Question Mark Presence for Query Prompts)
**Date:** 2026-03-24
**Status:** Draft
**Cluster ID:** PM (Punctuation Micro)

## Background

Punctuation tokens serve as attention sinks and carry context memory within transformer layers (LLM-Microscope, ArXiv:2502.15007). Three independent studies confirm that punctuation removal degrades LLM performance:

- **LLM-Microscope (ArXiv:2502.15007):** Mechanistic demonstration that punctuation tokens function as structural anchors in attention patterns, helping segment and organize input sequences.
- **"When Punctuation Matters" (ArXiv:2508.11383):** Large-scale empirical confirmation across 8 models and 52 tasks that punctuation sensitivity is consistent and non-trivial.
- **"Punctuation and Predicates" (ArXiv:2508.14067):** Model-specific nuance showing GPT-2, DeepSeek, and Gemma have different punctuation sensitivity profiles.

**Expected direction: NEGATIVE.** Punctuation removal is expected to HURT accuracy, not help it. This cluster tests the cautionary finding that not all "linguistic overhead" is waste -- some serves a functional purpose in model cognition.

**Format conversion method:** ALL punctuation removal in this cluster uses regex (zero-cost, no LLM pre-processor needed). This makes these experiments essentially free to run beyond the evaluation API calls themselves.

### Code Block Preservation Pattern

All regex-based punctuation removal MUST preserve code blocks. Before applying any regex, extract code blocks using placeholders:

```python
import re

def preserve_code_blocks(text: str) -> tuple[str, dict[str, str]]:
    """Extract code blocks and replace with placeholders before punctuation removal."""
    code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
    placeholders: dict[str, str] = {}
    for i, block in enumerate(code_blocks):
        ph = f"__CODE_BLOCK_{i}__"
        placeholders[ph] = block
        text = text.replace(block, ph)
    return text, placeholders

def restore_code_blocks(text: str, placeholders: dict[str, str]) -> str:
    """Restore code blocks from placeholders after punctuation removal."""
    for ph, block in placeholders.items():
        text = text.replace(ph, block)
    return text
```

All AQ-PM-* specs below assume this preservation step wraps each regex operation.

---

## Atomic Experiment Specifications

### AQ-PM-01: Remove Trailing Periods from Instruction Sentences in HumanEval Prompts

**Parent Hypothesis:** H-FMT-04
**Claim:** Removing trailing periods from instruction sentences degrades HumanEval accuracy by 2-5% because periods serve as sentence boundary markers that help transformer attention segment multi-sentence instructions.

**Independent Variable:** Trailing period presence (full punctuation vs. periods removed)
**Control Condition:** Original HumanEval prompts with all punctuation intact
**Treatment Condition:** Same prompts with trailing sentence periods removed

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval (coding task -- periods appear in docstring instructions)
**Prompt Selection Criteria:** Select 20 HumanEval prompts with multi-sentence docstrings (3+ sentences in the instruction) where period removal affects 3+ tokens. Exclude prompts with minimal prose (single-line instructions).
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation to Claude Sonnet (claude-sonnet-4-20250514) and Gemini 1.5 Pro (gemini-1.5-pro) if results show signal
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 2 conditions = 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Pattern: `re.sub(r'(?<=[a-zA-Z])\.\s', ' ', text)` -- removes trailing periods after letters, preserves decimal numbers (e.g., "3.14" unaffected)
- Apply code block preservation before regex

**Statistical Analysis:**
- Primary: McNemar's test (paired comparison of pass/fail outcomes)
- Secondary: Bootstrap CI for effect size (pass rate difference), CR comparison (does period removal hurt stability?)

**Success Criteria:**
- Positive result: Statistically significant accuracy decrease (p < 0.05) confirming periods serve a functional role as sentence boundary markers
- Null result: Less than 2% accuracy difference, suggesting periods are redundant for coding task comprehension

**Pilot Protocol:** Run 5 prompts first (50 API calls on free model). Go if effect direction is negative (any decrease); no-go if treatment outperforms control.

**Tier:** 1
**Bundling Opportunity:** Shares control condition with AQ-PM-02, AQ-PM-03, AQ-PM-04, AQ-PM-06. Run all period/comma/semicolon experiments together using the same 20 raw prompts as control.

---

### AQ-PM-02: Remove Commas from Lists and Clauses in Coding Prompts

**Parent Hypothesis:** H-FMT-04
**Claim:** Removing commas from instruction prose degrades accuracy by 3-8% because commas delimit parameter lists, separate clauses, and help models parse multi-part instructions. The effect is larger than period removal because commas carry more structural information in coding contexts.

**Independent Variable:** Comma presence (full punctuation vs. commas removed)
**Control Condition:** Original HumanEval prompts with all punctuation intact
**Treatment Condition:** Same prompts with commas removed from prose (not from code blocks or numbers)

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval (coding task -- commas appear in parameter descriptions and constraint lists)
**Prompt Selection Criteria:** Select 20 HumanEval prompts with rich comma usage (5+ commas in the instruction text). Prioritize prompts with parameter lists ("takes a, b, and c") and multi-clause instructions.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation if results show signal
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Pattern: `re.sub(r'(?<=[a-zA-Z]),\s', ' ', text)` -- removes commas after letters, preserves number formats like "1,000"
- Apply code block preservation before regex

**Statistical Analysis:**
- Primary: McNemar's test (paired)
- Secondary: Bootstrap CI for effect size, CR comparison

**Success Criteria:**
- Positive result: Statistically significant accuracy decrease (p < 0.05), ideally larger than AQ-PM-01 effect
- Null result: Less than 2% difference, suggesting commas are redundant for LLM parsing

**Pilot Protocol:** Run 5 prompts first (50 API calls on free model). Go if effect direction is negative.

**Tier:** 1
**Bundling Opportunity:** Shares control condition with AQ-PM-01, AQ-PM-03, AQ-PM-04, AQ-PM-06.

---

### AQ-PM-03: Remove Semicolons from Multi-Clause Instructions

**Parent Hypothesis:** H-FMT-04
**Claim:** Removing semicolons from instructions has a smaller effect than removing periods or commas (1-3% accuracy decrease) because semicolons are less common in coding prompts and models rely on them less as structural markers.

**Independent Variable:** Semicolon presence (full punctuation vs. semicolons removed)
**Control Condition:** Original HumanEval prompts with all punctuation intact
**Treatment Condition:** Same prompts with semicolons removed

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Select 20 HumanEval prompts that contain at least 1 semicolon in the instruction prose. If fewer than 20 qualify, supplement with MBPP prompts.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation if results show signal
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Pattern: `re.sub(r';\s', ' ', text)` -- removes semicolons followed by whitespace
- Apply code block preservation before regex (critical: Python code uses semicolons rarely, but they must be preserved in code blocks)

**Statistical Analysis:**
- Primary: McNemar's test (paired)
- Secondary: Bootstrap CI for effect size, CR comparison

**Success Criteria:**
- Positive result: Statistically significant accuracy decrease, expected to be smaller than AQ-PM-01 and AQ-PM-02
- Null result: Less than 2% difference, suggesting semicolons contribute minimally to LLM comprehension

**Pilot Protocol:** Run 5 prompts first (50 API calls on free model). Go if effect direction is negative.

**Tier:** 2 (semicolons are less common in prompts; lower expected signal)
**Bundling Opportunity:** Shares control condition with AQ-PM-01, AQ-PM-02, AQ-PM-04, AQ-PM-06.

---

### AQ-PM-04: Remove ALL Optional Punctuation from HumanEval Prompts

**Parent Hypothesis:** H-FMT-04
**Claim:** Simultaneously removing all "optional" punctuation (periods, commas, semicolons) from HumanEval instruction text produces a larger accuracy decrease (5-10%) than any individual punctuation type removal, because punctuation types serve complementary structural roles and their combined loss compounds the degradation.

**Independent Variable:** Punctuation level (full vs. all optional punctuation stripped)
**Control Condition:** Original HumanEval prompts with all punctuation intact
**Treatment Condition:** Same prompts with periods, commas, and semicolons all removed from prose

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Same 20 prompts used in AQ-PM-01 through AQ-PM-03 to enable direct comparison across removal levels.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation to Claude Sonnet and Gemini 1.5 Pro
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Combined pattern applying all three removals sequentially:
  ```python
  text = re.sub(r'(?<=[a-zA-Z])\.\s', ' ', text)  # periods
  text = re.sub(r'(?<=[a-zA-Z]),\s', ' ', text)    # commas
  text = re.sub(r';\s', ' ', text)                   # semicolons
  ```
- Apply code block preservation before all regex operations

**Statistical Analysis:**
- Primary: McNemar's test (paired comparison with control)
- Secondary: Bootstrap CI for effect size. Compare magnitude with AQ-PM-01, AQ-PM-02, AQ-PM-03 individual effects -- test whether combined > max(individual) to confirm compounding.

**Success Criteria:**
- Positive result: Combined removal effect is statistically significant AND larger than the largest individual removal effect (AQ-PM-01, AQ-PM-02, or AQ-PM-03), confirming compounding
- Null result: Combined effect is similar to the largest individual effect, suggesting one punctuation type dominates

**Pilot Protocol:** Run after individual experiments (AQ-PM-01 through AQ-PM-03) to compare. Same 5 pilot prompts.

**Tier:** 1
**Bundling Opportunity:** Shares control condition with AQ-PM-01, AQ-PM-02, AQ-PM-03, AQ-PM-06. This is the "full removal" arm of the punctuation experiment cluster.

---

### AQ-PM-05: Remove ALL Optional Punctuation from GSM8K Math Problems

**Parent Hypothesis:** H-FMT-04
**Claim:** Math problems are less sensitive to punctuation removal than coding prompts because reasoning structure in GSM8K is carried primarily by numbers and arithmetic relationships, not by prose punctuation. Expected accuracy decrease is 1-3% (smaller than the 5-10% expected for HumanEval in AQ-PM-04).

**Independent Variable:** Punctuation level (full vs. all optional punctuation stripped)
**Control Condition:** Original GSM8K prompts with all punctuation intact
**Treatment Condition:** Same prompts with periods, commas, and semicolons removed

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** GSM8K (math reasoning -- tests whether numerical reasoning is robust to punctuation loss)
**Prompt Selection Criteria:** Select 20 GSM8K prompts that are multi-sentence word problems (3+ sentences). Ensure variety in problem types (addition, subtraction, multiplication, multi-step).
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation if results differ from AQ-PM-04
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Same combined pattern as AQ-PM-04:
  ```python
  text = re.sub(r'(?<=[a-zA-Z])\.\s', ' ', text)  # periods
  text = re.sub(r'(?<=[a-zA-Z]),\s', ' ', text)    # commas
  text = re.sub(r';\s', ' ', text)                   # semicolons
  ```
- Note: GSM8K prompts contain numbers with commas ("1,000") and decimals ("3.14"). The regex patterns preserve these because they only match punctuation after letters, not digits.
- Apply code block preservation (unlikely to have code blocks, but defensive)

**Statistical Analysis:**
- Primary: McNemar's test (paired)
- Secondary: Bootstrap CI for effect size. Cross-benchmark comparison with AQ-PM-04 (HumanEval) to test the claim that math is less sensitive.

**Success Criteria:**
- Positive result: Accuracy decrease is smaller for GSM8K than for HumanEval (AQ-PM-04), confirming that numerical reasoning is more robust to punctuation loss
- Null result: Similar decrease across benchmarks, suggesting punctuation's role is task-independent

**Pilot Protocol:** Run 5 prompts first (50 API calls on free model). Compare effect direction with AQ-PM-04 pilot.

**Tier:** 1 (important cross-benchmark comparison)
**Bundling Opportunity:** Independent prompt set (GSM8K vs. HumanEval), but shares analysis framework with AQ-PM-04.

---

### AQ-PM-06: Partial Punctuation Removal -- Periods Only, Keep Commas and Semicolons

**Parent Hypothesis:** H-FMT-04
**Claim:** Removing only end-of-sentence periods while keeping commas and semicolons isolates the sentence boundary effect from clause-level effects. If periods serve primarily as attention sinks for sentence segmentation (per LLM-Microscope), this partial removal should show most of the degradation seen in AQ-PM-01 but less than AQ-PM-04's full removal.

**Independent Variable:** Punctuation removal scope (periods only vs. full punctuation vs. control)
**Control Condition:** Original HumanEval prompts with all punctuation intact
**Treatment Condition:** Same prompts with only trailing sentence periods removed (commas and semicolons preserved)

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Same 20 prompts as AQ-PM-01 through AQ-PM-04 for direct comparison.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free)
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free)
**Estimated Cost:** $0 (free models)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Pattern: `re.sub(r'(?<=[a-zA-Z])\.\s', ' ', text)` -- identical to AQ-PM-01
- Apply code block preservation before regex
- Note: This is intentionally the same transformation as AQ-PM-01. The distinction is analytical -- AQ-PM-06's value comes from comparing its effect with AQ-PM-04 (full removal) to determine what fraction of total degradation comes from sentence boundaries vs. clause-level punctuation.

**Statistical Analysis:**
- Primary: McNemar's test (paired)
- Secondary: Compare effect magnitude: if AQ-PM-06 effect is approximately equal to AQ-PM-04, sentence boundaries dominate; if AQ-PM-06 is much smaller, clause-level punctuation matters more.

**Success Criteria:**
- Positive result: AQ-PM-06 effect accounts for 50-80% of AQ-PM-04 effect, suggesting sentence boundaries are the primary mechanism
- Null result: AQ-PM-06 effect is less than 30% of AQ-PM-04, suggesting clause-level punctuation matters more than sentence boundaries

**Pilot Protocol:** Run after AQ-PM-01 and AQ-PM-04 to enable comparison. Same 5 pilot prompts.

**Tier:** 2 (diagnostic -- adds depth to the punctuation story but not essential for the main finding)
**Bundling Opportunity:** Shares control condition AND treatment condition with AQ-PM-01. The analysis is purely comparative.

---

### AQ-PM-07: Remove Terminal Question Mark from GSM8K Questions

**Parent Hypothesis:** H-FMT-06
**Claim:** Removing the terminal question mark from GSM8K math questions produces less than 2% accuracy difference because the question mark is largely redundant when the prompt text is clearly interrogative (e.g., "How many apples does Sally have" is unambiguous without "?").

**Independent Variable:** Terminal question mark (present vs. absent)
**Control Condition:** Original GSM8K prompts with question mark
**Treatment Condition:** Same prompts with terminal question mark removed

**Dependent Variables:** Pass rate

**Benchmarks:** GSM8K (math reasoning -- all prompts end with a question)
**Prompt Selection Criteria:** Select 20 GSM8K prompts that end with a question mark. Ensure all are clearly interrogative in phrasing (start with "How many," "What is," etc.) so the question mark is genuinely redundant from a semantic standpoint.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation only if a surprising result appears
**Repetitions:** 5 per condition
**Total API Calls:** 200 (free); 600 with paid escalation
**Estimated Cost:** $0 (free models) / $2-5 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Pattern: `re.sub(r'\?\s*$', '', text)` -- removes terminal question mark (and any trailing whitespace)

**Statistical Analysis:**
- Primary: McNemar's test (paired)
- Secondary: Bootstrap CI for effect size

**Success Criteria:**
- Positive result (expected): Less than 2% accuracy difference (null effect), confirming question marks are redundant for clearly interrogative prompts
- Surprise result: Statistically significant accuracy decrease, suggesting question marks serve an attention-cueing role even when semantically redundant

**Pilot Protocol:** Run 5 prompts first (50 API calls on free model). Go if any direction shows signal; report as null if within 2%.

**Tier:** 2 (quick to run, low expected signal, but potentially surprising)
**Bundling Opportunity:** Can share control condition with AQ-PM-05 since both use GSM8K raw prompts. Run the question-mark-only removal as an additional treatment arm in the punctuation experiment. Per Phase 10 recommendations and CONTEXT.md specifics, H-FMT-06 was recommended to bundle with H-FMT-04 rather than standalone.

---

### AQ-PM-08: Question Mark Removal vs. Imperative Rephrasing (Confound Isolation)

**Parent Hypothesis:** H-FMT-06
**Claim:** Rephrasing a question as an imperative ("What is X?" to "Calculate X.") is a confound that mixes two changes: question mark removal AND syntactic rephrasing. Comparing "What is X?" vs. "What is X" (question mark only) vs. "Calculate X." (imperative rephrasing) isolates the question mark's contribution from the rephrasing effect.

**Independent Variable:** Three conditions: (A) original question with "?", (B) same question without "?", (C) imperative rephrasing with "."
**Control Condition:** Original GSM8K prompts ("What is X?")
**Treatment Condition 1:** Question mark removed ("What is X")
**Treatment Condition 2:** Imperative rephrasing ("Calculate X.")

**Dependent Variables:** Pass rate

**Benchmarks:** GSM8K (math reasoning)
**Prompt Selection Criteria:** Select 20 GSM8K prompts that begin with "How many" or "What is" or "How much" -- these can be naturally rephrased as imperatives ("Calculate," "Find," "Determine").
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free)
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 3 conditions = 300 (free)
**Estimated Cost:** $0 (free models)

**Format Conversion Method:**
- Condition B (question mark removal): Regex `re.sub(r'\?\s*$', '', text)` -- zero-cost
- Condition C (imperative rephrasing): LLM pre-processor using Nemotron-3-Nano (free). Prompt: "Rephrase the following question as an imperative command. Change 'How many X?' to 'Calculate the number of X.' Preserve ALL numbers and names exactly. Output only the rephrased prompt."
- Note: Condition C introduces an LLM conversion step. Manual review of 5 converted prompts before proceeding to verify semantic preservation.

**Statistical Analysis:**
- Primary: McNemar's test for each pair: (A vs. B), (A vs. C), (B vs. C)
- Secondary: If (A vs. B) is null but (A vs. C) is significant, the effect is from rephrasing, not the question mark

**Success Criteria:**
- Positive result: (A vs. B) is null AND (A vs. C) is significant, confirming the question mark itself has no effect but rephrasing does
- Alternative result: Both (A vs. B) and (A vs. C) are null, suggesting neither question marks nor imperative rephrasing matter for math reasoning
- Surprise result: (A vs. B) is significant, suggesting question marks do carry signal

**Pilot Protocol:** Run 5 prompts for all 3 conditions (75 API calls on free model). Review imperative rephrasing quality before proceeding.

**Tier:** 3 (stretch -- adds nuance but requires more setup than pure regex experiments)
**Bundling Opportunity:** Can share control condition with AQ-PM-05 and AQ-PM-07 since all use GSM8K raw prompts. Per CONTEXT.md specifics, H-FMT-06 was recommended to bundle with H-FMT-04 rather than standalone.

---

## Concrete Examples

### Example 1: HumanEval Prompt with Punctuation Variations

**Original (full punctuation):**
```
Write a function that takes a list of integers and returns the sum of all even numbers.
The function should handle empty lists by returning 0. If the list contains non-integer
values, raise a TypeError.
```

**Periods removed (AQ-PM-01):**
```
Write a function that takes a list of integers and returns the sum of all even numbers
The function should handle empty lists by returning 0 If the list contains non-integer
values, raise a TypeError
```

**Commas removed (AQ-PM-02):**
```
Write a function that takes a list of integers and returns the sum of all even numbers.
The function should handle empty lists by returning 0. If the list contains non-integer
values raise a TypeError.
```

**All punctuation removed (AQ-PM-04):**
```
Write a function that takes a list of integers and returns the sum of all even numbers
The function should handle empty lists by returning 0 If the list contains non-integer
values raise a TypeError
```

### Example 2: GSM8K Prompt with Question Mark Variations

**Original (with question mark, AQ-PM-07 control):**
```
Sally has 3 red apples and 5 green apples. She gives 2 red apples to her friend.
How many apples does Sally have now?
```

**Question mark removed (AQ-PM-07 treatment):**
```
Sally has 3 red apples and 5 green apples. She gives 2 red apples to her friend.
How many apples does Sally have now
```

**Imperative rephrasing (AQ-PM-08 treatment C):**
```
Sally has 3 red apples and 5 green apples. She gives 2 red apples to her friend.
Calculate the total number of apples Sally has now.
```

---

## Summary Table

| ID | Atomic Question | Parent | Benchmark | Tier | API Calls (Free) | API Calls (Paid) | Cost (Free) | Cost (Paid) |
|----|----------------|--------|-----------|------|-------------------|-------------------|-------------|-------------|
| AQ-PM-01 | Period removal | H-FMT-04 | HumanEval | 1 | 200 | 600 | $0 | $3-5 |
| AQ-PM-02 | Comma removal | H-FMT-04 | HumanEval | 1 | 200 | 600 | $0 | $3-5 |
| AQ-PM-03 | Semicolon removal | H-FMT-04 | HumanEval | 2 | 200 | 600 | $0 | $3-5 |
| AQ-PM-04 | All punctuation removal (HumanEval) | H-FMT-04 | HumanEval | 1 | 200 | 600 | $0 | $3-5 |
| AQ-PM-05 | All punctuation removal (GSM8K) | H-FMT-04 | GSM8K | 1 | 200 | 600 | $0 | $3-5 |
| AQ-PM-06 | Partial removal (periods only) | H-FMT-04 | HumanEval | 2 | 200 | 200 | $0 | $0 |
| AQ-PM-07 | Question mark removal | H-FMT-06 | GSM8K | 2 | 200 | 600 | $0 | $2-5 |
| AQ-PM-08 | Question mark vs. imperative | H-FMT-06 | GSM8K | 3 | 300 | 300 | $0 | $0 |
| **Totals** | | | | | **1,700** | **3,700** | **$0** | **$11-30** |

### Tier Breakdown

- **Tier 1** (AQ-PM-01, 02, 04, 05): 800 free API calls, $0 cost. Core punctuation removal experiments establishing the "punctuation is functional" finding.
- **Tier 2** (AQ-PM-03, 06, 07): 600 free API calls, $0 cost. Diagnostic and fine-grained experiments adding depth to the story.
- **Tier 3** (AQ-PM-08): 300 free API calls, $0 cost. Confound isolation stretch goal.

### Bundling Strategy

The HumanEval experiments (AQ-PM-01 through AQ-PM-04, AQ-PM-06) all share the same 20 raw prompts as the control condition. Run the control condition ONCE and reuse across all treatment arms. This saves 800 API calls (4 experiments x 200 control calls each, replaced by 200 shared control calls).

The GSM8K experiments (AQ-PM-05, AQ-PM-07, AQ-PM-08) share a different set of 20 raw prompts as control. Similarly, run control once and reuse.

### Model Escalation Strategy

1. Run all experiments on free OpenRouter models first (nvidia/nemotron-3-super-120b-a12b:free)
2. If Tier 1 results show statistically significant punctuation effects: escalate to Claude Sonnet and Gemini 1.5 Pro to test model-specificity (per "Punctuation and Predicates" finding that sensitivity varies across architectures)
3. If Tier 1 results show NULL effects on free models: escalate to paid models before concluding -- free model may lack sensitivity (see Pitfall 6 in research notes)
