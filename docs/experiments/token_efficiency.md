# Token Efficiency Experiments: TOON Compact and Bullet/Outline Formats

**Parent Hypotheses:** H-FMT-01 (TOON-like Compact Notation), H-FMT-03 (Bullet/Outline Format)
**Date:** 2026-03-24
**Status:** Draft
**Cluster ID:** TE (Token Efficiency)

---

## Overview

This document contains atomic experiment specifications for two token efficiency hypotheses from Phase 10's prompt format research:

- **H-FMT-01** tests whether TOON-like compact notation can reduce token counts by 30-40% on structured code prompts without degrading accuracy.
- **H-FMT-03** tests whether bullet/outline reformatting of prose prompts achieves 15-25% token reduction while maintaining accuracy.

Both hypotheses target the "formatting overhead" component of the linguistic tax: tokens that serve human readability but may be redundant for LLM processing. The key distinction is that H-FMT-01 targets structured data within prompts (parameter descriptions, I/O specs), while H-FMT-03 targets instruction and narrative text.

**Important caveats:**
- TOON notation is best suited for tabular/structured data (Pitfall 5 from research). Prompt selection criteria below filter for prompts with structured content.
- Bullet conversion of prose may strip reasoning cues embedded in connectors like "therefore" and "so." Each spec addresses this risk.
- LLM-based format conversions may introduce semantic drift (Pitfall 4). Specs requiring LLM conversion include a semantic equivalence check.
- All results must be analyzed per-model, not averaged, due to IoU < 0.2 between model format preferences (He et al., ArXiv:2411.10541).

---

## H-FMT-01: TOON Compact Notation

### AQ-TE-01: TOON Notation for HumanEval Function Docstrings

**Parent Hypothesis:** H-FMT-01
**Claim:** Converting HumanEval function docstrings with structured parameters from verbose natural language to TOON-like compact notation reduces input tokens by 30-40% with less than 5% accuracy change on code generation tasks.

**Independent Variable:** Prompt data format (verbose NL docstring vs. TOON-compact docstring)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified HumanEval docstring)
**Treatment Condition:** Docstring parameters, return types, and constraints reformatted to TOON key:value notation with abbreviated labels. Only the structured data portions are converted; the task instruction ("Write a function that...") remains in natural language.

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** HumanEval (code generation with function signatures and docstrings)
**Prompt Selection Criteria:** Select HumanEval prompts from data/prompts.json that contain at least 3 parameters OR have explicit input/output type specifications OR include structured constraints (e.g., "1 <= n <= 100"). Filter out prompts with only a single-sentence description and no structured data. This targets TOON's sweet spot: tabular/structured data.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet (claude-sonnet-4-20250514) / Gemini 1.5 Pro (gemini-1.5-pro) if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 2 conditions = 200 (free); 20 x 5 x 3 x 2 = 600 (with paid escalation)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation: Claude Sonnet $3.00/$15.00 per 1M in/out, Gemini 1.5 Pro $1.25/$5.00 per 1M in/out)

**Format Conversion Method:**
- Rule-based template conversion (no LLM needed)
- Conversion rules:
  1. Extract parameter name, type, and description from docstring
  2. Convert to `param_name: type | description` one per line
  3. Convert return type to `returns: type | description`
  4. Convert constraints to `constraint: expression` lines
  5. Preserve the natural language task instruction verbatim

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

*Treatment (TOON-compact):*
```
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """Check if any two numbers in list are closer than threshold.
    numbers: List[float] | input list
    threshold: float | minimum distance
    returns: bool | True if any pair closer than threshold
    ex: ([1.0,2.0,3.9,4.0,5.0,2.2], 0.3) -> True
    ex: ([1.0,2.0,3.9,4.0,5.0,2.2], 0.05) -> False
    """
```

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison, control vs. treatment per prompt)
- Secondary: Token count ratio (treatment/control), bootstrap CI for effect size on pass rate difference

**Success Criteria:**
- Positive result: Token reduction >= 25% AND accuracy change within +/-5% (statistically non-significant on McNemar's, p > 0.05)
- Negative result: Accuracy drops by > 5% (statistically significant, p < 0.05)
- Null result: Token reduction < 15% (TOON conversion does not achieve meaningful savings on this prompt type)

**Pilot Protocol:** 5 prompts first (5 x 5 reps x 2 conditions = 50 calls). Go if: token reduction > 20% and no accuracy drop > 10%. No-go if: token reduction < 10% or accuracy drops > 15%.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw HumanEval prompts) with AQ-TE-06 and AQ-SM-01

---

### AQ-TE-02: TOON Notation for MBPP Task Descriptions

**Parent Hypothesis:** H-FMT-01
**Claim:** TOON-compact notation applied to MBPP task descriptions with input/output specifications achieves 25-35% token reduction with less than 5% accuracy change, though the effect may be smaller than HumanEval due to MBPP's typically shorter prompts.

**Independent Variable:** Prompt data format (verbose NL description vs. TOON-compact notation)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified MBPP task description)
**Treatment Condition:** Input/output specifications and constraints reformatted to TOON key:value notation. Task description sentence preserved in natural language.

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** MBPP (simpler Python programming tasks with I/O specs)
**Prompt Selection Criteria:** Select MBPP prompts from data/prompts.json that contain explicit input/output type descriptions or test case specifications. Filter out one-liner descriptions with no structured content. MBPP prompts are generally shorter than HumanEval, so expect smaller absolute token savings.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid escalation)
**Estimated Cost:** $0 (free models) / $4-10 (paid escalation)

**Format Conversion Method:**
- Rule-based template conversion (same rules as AQ-TE-01)
- Conversion rules:
  1. Extract function name, input types, output type from description
  2. Convert to `input: type | description` format
  3. Convert test cases to `ex: input -> output` format
  4. Preserve task description sentence verbatim

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio, bootstrap CI for effect size; compare effect magnitude to AQ-TE-01 (cross-benchmark comparison)

**Success Criteria:**
- Positive result: Token reduction >= 20% AND accuracy change within +/-5%
- Negative result: Accuracy drops by > 5% (p < 0.05)
- Null result: Token reduction < 10% (MBPP prompts too short for TOON to help)

**Pilot Protocol:** 5 prompts first (50 calls). Go if: token reduction > 15% and no accuracy drop > 10%. No-go if: token reduction < 8%.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw MBPP prompts) with AQ-TE-06; compare results with AQ-TE-01 for cross-benchmark analysis

---

### AQ-TE-03: TOON Notation for GSM8K Structured Math Problems

**Parent Hypothesis:** H-FMT-01
**Claim:** TOON-compact notation applied to GSM8K problems with explicit numerical parameters achieves moderate token reduction (15-25%) but may degrade accuracy if reasoning scaffolding embedded in prose is lost.

**Independent Variable:** Prompt data format (prose narrative vs. TOON-compact parameter listing)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified GSM8K word problem)
**Treatment Condition:** Numerical parameters and relationships extracted into TOON key:value notation. The question sentence is preserved verbatim. Prose connectors carrying reasoning cues ("therefore," "so," "which means") are removed.

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** GSM8K (math word problems with explicit numerical parameters)
**Prompt Selection Criteria:** Select GSM8K prompts from data/prompts.json that contain at least 3 explicit numerical values AND describe relationships between quantities. Avoid simple one-step problems where the narrative structure is trivially short. This targets prompts where TOON conversion has enough structured data to compress, while also being a stress test for reasoning scaffolding loss.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid escalation)
**Estimated Cost:** $0 (free models) / $3-7 (paid escalation)

**Format Conversion Method:**
- Rule-based template conversion
- Conversion rules:
  1. Extract named entities and their associated quantities
  2. Convert to `entity: quantity | unit` lines
  3. Extract relationships as `relation: entity1 op entity2` lines
  4. Preserve the question sentence verbatim
  5. WARNING: Prose connectors like "therefore" and "so" carry implicit reasoning cues. Their removal is the experimental variable -- document any cases where removal changes the problem's logical structure.

**Concrete example:**

*Control (original GSM8K):*
```
Janet's ducks lay 16 eggs per day. She eats three for breakfast every
morning and bakes muffins for her friends every day with four. She sells
every duck egg at the farmers' market for $2 each. How much in dollars
does she make every day at the farmers' market?
```

*Treatment (TOON-compact):*
```
duck_eggs_per_day: 16
eggs_eaten_breakfast: 3
eggs_baked_muffins: 4
price_per_egg: $2
question: How much does she make daily at the farmers' market?
```

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio, bootstrap CI for effect size; qualitative analysis of which problem types see the largest accuracy changes

**Success Criteria:**
- Positive result: Token reduction >= 15% AND accuracy change within +/-5%
- Negative result: Accuracy drops by > 8% (reasoning scaffolding was needed)
- Null result: Token reduction < 10% OR accuracy change is inconsistent across problems (some improve, some degrade, no pattern)

**Pilot Protocol:** 5 prompts first (50 calls). Go if: token reduction > 10% and accuracy drop < 15%. No-go if: accuracy drops > 20% (reasoning scaffolding clearly needed).

**Tier:** 2
**Bundling Opportunity:** Shares control condition (raw GSM8K prompts) with AQ-TE-05 and AQ-SM-03

---

### AQ-TE-04: TOON via LLM Pre-processor vs. Rule-Based Conversion

**Parent Hypothesis:** H-FMT-01
**Claim:** LLM-based TOON conversion introduces semantic drift compared to rule-based conversion, measurable as lower accuracy or changed information content, even when the LLM is instructed to preserve semantics exactly.

**Independent Variable:** Conversion method (rule-based template vs. LLM pre-processor)
**Control Condition:** Rule-based TOON conversion (same as AQ-TE-01 treatment condition)
**Treatment Condition:** LLM pre-processor converts the same prompts to TOON notation using the prompt below

**Dependent Variables:** Pass rate, input token count, semantic equivalence score (manual review), cost

**Benchmarks:** HumanEval (same 20 prompts as AQ-TE-01 for direct comparison)
**Prompt Selection Criteria:** Same 20 prompts as AQ-TE-01 to enable paired comparison between conversion methods
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) for evaluation; nvidia/nemotron-3-nano-30b-a3b:free for pre-processing conversion
**Repetitions:** 5 per condition
**Total API Calls:** 20 pre-processing calls + 20 x 5 x 1 x 2 = 220 (free); add 600 for paid escalation = 820
**Estimated Cost:** $0 (free models) / $6-14 (paid escalation, includes pre-processing calls)

**Format Conversion Method:**
- LLM pre-processor using nvidia/nemotron-3-nano-30b-a3b:free
- Pre-processor prompt:
```
Convert the following code prompt to TOON-compact notation. Rules:
1. Extract all parameters with their types and descriptions
2. Format as: param_name: type | description
3. Format return type as: returns: type | description
4. Format examples as: ex: input -> output
5. Preserve the task description sentence EXACTLY as written
6. Do NOT add, remove, or rephrase any information
7. Do NOT add explanations or commentary

Input prompt:
{prompt}

TOON-compact version:
```
- Semantic equivalence check: After conversion, manually review 5 randomly selected conversions to verify no information was added, removed, or rephrased. Count information units (parameters, constraints, examples) in original vs. converted.

**Statistical Analysis:**
- Primary: McNemar's test comparing rule-based vs. LLM-converted accuracy
- Secondary: Information unit count (original vs. converted), token count comparison between methods

**Success Criteria:**
- Positive result (drift confirmed): LLM conversion produces measurably different accuracy (> 3% difference from rule-based, p < 0.10) OR manual review finds information changes in > 20% of conversions
- Negative result (drift absent): Accuracy within +/-2% of rule-based AND manual review finds no information changes
- Null result: Results are too noisy to distinguish methods

**Pilot Protocol:** 5 prompts first. Convert via both methods, manually compare outputs. Go if: LLM conversions are syntactically valid TOON. No-go if: LLM ignores formatting instructions or adds commentary.

**Tier:** 2
**Bundling Opportunity:** Must be run after AQ-TE-01 (reuses its rule-based conversion as control); can share evaluation model calls with AQ-TE-01

---

## H-FMT-03: Bullet/Outline Format

### AQ-TE-05: Bullet-Point Extraction of GSM8K Word Problems

**Parent Hypothesis:** H-FMT-03
**Claim:** Converting GSM8K prose word problems to a "Given/Find/Solve" bullet structure reduces tokens by 15-25% while maintaining accuracy, provided reasoning-carrying connectors are preserved as explicit "Reasoning hint" bullets.

**Independent Variable:** Instruction format (prose narrative vs. Given/Find/Solve bullet structure)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified GSM8K prose word problem)
**Treatment Condition:** Problem reformatted into three sections:
  - **Given:** bullet list of known quantities and relationships
  - **Find:** the question being asked
  - **Solve:** (empty, for model to fill)

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** GSM8K (math word problems)
**Prompt Selection Criteria:** Select GSM8K prompts from data/prompts.json with multi-sentence narratives (at least 3 sentences). Avoid already-terse problems. Prefer problems where prose connectors ("therefore," "so," "since") carry reasoning cues, as these are the stress test for bullet conversion.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid escalation)
**Estimated Cost:** $0 (free models) / $3-7 (paid escalation)

**Format Conversion Method:**
- Manual template conversion (rule-based)
- Conversion rules:
  1. Identify all given quantities and label each with the entity name
  2. Identify all relationships between quantities
  3. Extract the question being asked
  4. Format as:
     ```
     Given:
     - [entity]: [quantity] [unit]
     - [entity]: [quantity] [unit]
     - [relationship]: [description]
     Find:
     - [question]
     ```
  5. WARNING: If a prose connector carries a reasoning cue (e.g., "She sells the remaining eggs" implies subtraction), include it as an explicit bullet: `- remaining eggs = total - eaten - baked`

**Concrete example:**

*Control (original GSM8K):*
```
Janet's ducks lay 16 eggs per day. She eats three for breakfast every
morning and bakes muffins for her friends every day with four. She sells
every duck egg at the farmers' market for $2 each. How much in dollars
does she make every day at the farmers' market?
```

*Treatment (Given/Find/Solve bullets):*
```
Given:
- duck eggs per day: 16
- eggs eaten for breakfast: 3
- eggs used for muffins: 4
- remaining eggs are sold (16 - 3 - 4 = 9)
- price per egg: $2
Find:
- daily earnings at farmers' market in dollars
```

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio, bootstrap CI; qualitative analysis of failure cases (did bullet conversion lose reasoning cues?)

**Success Criteria:**
- Positive result: Token reduction >= 15% AND accuracy change within +/-3%
- Negative result: Accuracy drops by > 5% (reasoning scaffolding was needed and bullets lost it)
- Null result: No consistent pattern -- some problems improve, others degrade

**Pilot Protocol:** 5 prompts first (50 calls). Go if: token reduction > 10% and accuracy stable. No-go if: accuracy drops > 15% or conversion introduces ambiguity.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw GSM8K prompts) with AQ-TE-03 and AQ-SM-03

---

### AQ-TE-06: Outline Format for Multi-Step HumanEval Problems

**Parent Hypothesis:** H-FMT-03
**Claim:** Reformatting complex HumanEval prompts with multiple constraints into a numbered outline (numbered requirements/constraints) helps models parse complex requirements, improving accuracy by 3-8% while achieving modest token reduction (5-15%).

**Independent Variable:** Instruction format (prose docstring vs. numbered outline of constraints)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified HumanEval docstring)
**Treatment Condition:** Constraints and requirements extracted from prose into a numbered list. Function signature and examples preserved. Task description sentence kept as-is.

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** HumanEval (complex code generation with multiple constraints)
**Prompt Selection Criteria:** Select HumanEval prompts from data/prompts.json with at least 3 distinct constraints or requirements mentioned in the docstring (e.g., edge cases, input ranges, special behaviors). Filter out simple prompts with only one constraint.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid escalation)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Manual template conversion (rule-based)
- Conversion rules:
  1. Identify all constraints and requirements in the docstring
  2. Number them sequentially
  3. Format as:
     ```
     Task: [task description sentence]
     Requirements:
     1. [constraint 1]
     2. [constraint 2]
     3. [constraint 3]
     Examples: [preserved from original]
     ```
  4. Preserve function signature and examples exactly as-is

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio, bootstrap CI; analyze whether accuracy improvement correlates with number of constraints (more constraints = bigger benefit from outline?)

**Success Criteria:**
- Positive result: Accuracy improves by >= 3% (p < 0.10) with any token change
- Negative result: Accuracy drops by > 3% (outline format confuses the model)
- Null result: Accuracy change < 2% (outline format neither helps nor hurts)

**Pilot Protocol:** 5 prompts first (50 calls). Go if: no accuracy drop > 10%. No-go if: model outputs suggest it misinterprets the outline format.

**Tier:** 2
**Bundling Opportunity:** Shares control condition (raw HumanEval prompts) with AQ-TE-01 and AQ-SM-01

---

### AQ-TE-07: Telegraphic Style Removal of Filler Words

**Parent Hypothesis:** H-FMT-03
**Claim:** Removing filler words and phrases ("please," "note that," "in order to," "it is important to," "make sure to") from coding instructions achieves 10-15% token reduction with no accuracy change, as these words carry no semantic content for LLMs.

**Independent Variable:** Instruction verbosity (original with filler vs. telegraphic without filler)
**Control Condition:** Original raw prompt from data/prompts.json (unmodified coding instruction)
**Treatment Condition:** Systematic removal of filler words and phrases using regex patterns. Only filler/hedging language is removed; all semantic content preserved.

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** HumanEval + MBPP (coding instructions where filler words are common)
**Prompt Selection Criteria:** Select prompts from data/prompts.json (HumanEval + MBPP) that contain at least 2 filler phrases from the target list. Pre-scan prompts for filler word density to ensure the treatment produces a measurable difference.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (paid escalation)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Regex-based removal (zero LLM cost)
- Target filler patterns:
  ```python
  FILLER_PATTERNS = [
      r'\bplease\b\s*',
      r'\bnote that\b\s*',
      r'\bin order to\b',        # replace with "to"
      r'\bit is important to\b', # replace with just the verb
      r'\bmake sure to\b',       # replace with just the verb
      r'\bkindly\b\s*',
      r'\bdo not forget to\b',   # replace with just the verb
      r'\bas mentioned\b\s*',
      r'\bas you can see\b\s*',
  ]
  ```
- Conversion preserves all code blocks, examples, and technical terms

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio, bootstrap CI for effect size

**Success Criteria:**
- Positive result: Token reduction >= 8% AND accuracy change within +/-2% (non-significant on McNemar's)
- Negative result: Accuracy drops by > 3% (filler words carry signal after all)
- Null result: Token reduction < 5% (prompts do not contain enough filler to matter)
- NOTE: With 20 prompts, effects below 5% absolute accuracy difference are unlikely to reach statistical significance. If pilot results suggest a small effect (2-4%), consider expanding to 40 prompts.

**Pilot Protocol:** 5 prompts first (50 calls). Go if: filler removal produces > 5% token reduction and no accuracy drop > 10%. No-go if: filler removal changes < 3% of tokens (not enough filler in benchmarks).

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw HumanEval/MBPP prompts) with AQ-TE-01, AQ-TE-02, AQ-TE-06

---

## Summary Table

| ID | Name | Parent | Tier | Benchmarks | Prompts | Free API Calls | Paid API Calls | Free Cost | Paid Cost |
|----|------|--------|------|------------|---------|----------------|----------------|-----------|-----------|
| AQ-TE-01 | TOON for HumanEval docstrings | H-FMT-01 | 1 | HumanEval | 20 | 200 | 600 | $0 | $5-12 |
| AQ-TE-02 | TOON for MBPP descriptions | H-FMT-01 | 1 | MBPP | 20 | 200 | 600 | $0 | $4-10 |
| AQ-TE-03 | TOON for GSM8K math problems | H-FMT-01 | 2 | GSM8K | 20 | 200 | 600 | $0 | $3-7 |
| AQ-TE-04 | TOON LLM vs. rule-based conversion | H-FMT-01 | 2 | HumanEval | 20 | 220 | 820 | $0 | $6-14 |
| AQ-TE-05 | Bullet extraction of GSM8K problems | H-FMT-03 | 1 | GSM8K | 20 | 200 | 600 | $0 | $3-7 |
| AQ-TE-06 | Outline for multi-step HumanEval | H-FMT-03 | 2 | HumanEval | 20 | 200 | 600 | $0 | $5-12 |
| AQ-TE-07 | Telegraphic filler word removal | H-FMT-03 | 1 | HumanEval+MBPP | 20 | 200 | 600 | $0 | $5-12 |
| **Totals** | | | | | **140** | **1,420** | **4,420** | **$0** | **$31-74** |

### Tier Breakdown

| Tier | Questions | Free API Calls | Paid API Calls | Description |
|------|-----------|----------------|----------------|-------------|
| 1 | AQ-TE-01, AQ-TE-02, AQ-TE-05, AQ-TE-07 | 800 | 2,400 | Cheapest, highest signal -- run first |
| 2 | AQ-TE-03, AQ-TE-04, AQ-TE-06 | 620 | 2,020 | Run if Tier 1 shows interesting results |

### Bundling Opportunities

- **HumanEval control group:** AQ-TE-01, AQ-TE-06, AQ-SM-01 share the same raw HumanEval prompts as control. Run control once, reuse for all three.
- **MBPP control group:** AQ-TE-02, AQ-TE-07 share raw MBPP prompts as control.
- **GSM8K control group:** AQ-TE-03, AQ-TE-05, AQ-SM-03 share raw GSM8K prompts as control.
- **Cross-benchmark TOON comparison:** AQ-TE-01 (HumanEval) + AQ-TE-02 (MBPP) + AQ-TE-03 (GSM8K) test the same conversion on different benchmarks -- compare effect sizes.

### Model Escalation Strategy

1. Run all Tier 1 experiments on nvidia/nemotron-3-super-120b-a12b:free
2. If any Tier 1 experiment shows > 15% token reduction AND accuracy within +/-5%:
   - Escalate that experiment to Claude Sonnet and Gemini 1.5 Pro
   - Compare per-model results (do not average)
3. If Nemotron shows null results on all Tier 1 experiments:
   - Run one Tier 1 experiment on Claude Sonnet before concluding
   - Null on Nemotron does not mean null on frontier models (Pitfall 6)
