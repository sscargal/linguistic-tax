# Novel Micro-Formatting Hypotheses: Brainstormed Ideas Beyond Phase 10

**Date:** 2026-03-24
**Status:** Draft
**Cluster ID:** NH (Novel Hypotheses)
**Note:** These ideas extend the whitepaper's scope beyond the original 6 hypotheses (H-FMT-01 through H-FMT-06). The top 5 have full experiment specs; remaining are structured research notes for future work.

---

## Section 1: Full Hypothesis Specs

### AQ-NH-01: Imperative vs. Interrogative vs. Declarative Instruction Phrasing

**Parent Hypothesis:** Novel
**Claim:** Imperative instruction phrasing ("Write a function...") produces higher coding accuracy than interrogative ("Can you write a function...?") or declarative ("The function should...") phrasing because LLM training data disproportionately pairs imperative instructions with high-quality code completions (StackOverflow answers, documentation, tutorials).

**Independent Variable:** Instruction phrasing mode (imperative vs. interrogative vs. declarative)
**Control Condition:** Original HumanEval/MBPP prompts (typically imperative: "Write a function that...")
**Treatment Condition A:** Interrogative rephrasing ("Can you write a function that...?")
**Treatment Condition B:** Declarative rephrasing ("The function should...")

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval + MBPP (coding instructions have clear phrasing patterns; imperative is the default in both benchmarks)
**Prompt Selection Criteria:** Select prompts from data/prompts.json (HumanEval + MBPP) that begin with imperative instructions ("Write," "Create," "Implement," "Return," "Given"). These are naturally convertible to interrogative and declarative forms.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet (claude-sonnet-4-20250514) / Gemini 1.5 Pro (gemini-1.5-pro) if results show signal
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 3 conditions = 300 (free); 20 x 5 x 3 x 3 = 900 (with paid escalation)
**Estimated Cost:** $0 (free models) / $6-14 (paid escalation)

**Format Conversion Method:**
- Regex + template-based conversion (no LLM needed for most cases)
- Conversion rules:
  1. Imperative (control): keep as-is ("Write a function that takes a list and returns...")
  2. Interrogative: prepend "Can you" and append "?" -- `"Can you write a function that takes a list and returns...?"`
  3. Declarative: change verb form -- `"The function should take a list and return..."`
- Edge cases: prompts starting with "Given..." or "Return..." need manual mapping for interrogative/declarative forms
- Manual review of 5 conversions before full run to verify semantic equivalence

**Concrete example:**

*Control (imperative):*
```
Write a function that takes a list of integers and returns the second largest unique value.
```

*Treatment A (interrogative):*
```
Can you write a function that takes a list of integers and returns the second largest unique value?
```

*Treatment B (declarative):*
```
The function should take a list of integers and return the second largest unique value.
```

**Statistical Analysis:**
- Primary: McNemar's test for each pair: (imperative vs. interrogative), (imperative vs. declarative), (interrogative vs. declarative)
- Secondary: Bootstrap CI for effect size across all three conditions; per-model comparison if escalated

**Success Criteria:**
- Positive result: Imperative significantly outperforms interrogative or declarative (> 5% difference, p < 0.10)
- Alternative result: All three perform equivalently (phrasing mode does not matter for coding tasks)
- Surprise result: Interrogative or declarative outperforms imperative

**Pilot Protocol:** 5 prompts first (5 x 5 x 3 = 75 calls). Go if: any pairwise difference > 5%. No-go if: all within 3%.

**Tier:** 2
**Bundling Opportunity:** Shares imperative control condition (raw HumanEval/MBPP prompts) with AQ-TE-01, AQ-TE-02, AQ-TE-06, AQ-TE-07

---

### AQ-NH-02: Politeness Markers ("Please"/"Thank you") Effect on Coding Accuracy

**Parent Hypothesis:** Novel
**Claim:** Adding politeness markers ("Please write..." / "Please write... Thank you.") has a measurable but inconsistent effect on coding accuracy, with the direction varying by model -- reflecting the conflicting findings across three 2024-2025 papers: ArXiv:2510.04950 (impolite > polite on GPT-4o), ArXiv:2512.12812 (neutral/friendly > rude across models), and ArXiv:2402.14531 (varies by language).

**Independent Variable:** Politeness level (neutral vs. polite-prefix vs. polite-bookend)
**Control Condition:** Original prompt with no politeness markers ("Write a function...")
**Treatment Condition A:** Polite prefix ("Please write a function...")
**Treatment Condition B:** Polite bookend ("Please write a function... Thank you.")

**Dependent Variables:** Pass rate (per model), input token count

**Benchmarks:** HumanEval + MBPP (coding tasks -- testing whether politeness effects replicate on code generation, which has not been specifically tested in the 3 cited papers)
**Prompt Selection Criteria:** Select 20 prompts from data/prompts.json (HumanEval + MBPP) that start with imperative verbs and do not already contain "please" or "thank you."
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet AND Gemini 1.5 Pro (essential for testing model-specific politeness effects)
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 3 = 300 (free); 20 x 5 x 3 x 3 = 900 (with paid escalation)
**Estimated Cost:** $0 (free models) / $6-14 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Conversion rules:
  1. Neutral (control): keep as-is
  2. Polite prefix: `re.sub(r'^(\w)', r'Please \1'.lower(), text)` -- simplified; actually prepend "Please " before the first word and lowercase it
  3. Polite bookend: prepend "Please " + append "\nThank you."
- All conversions preserve code blocks and examples

**Concrete example:**

*Control (neutral):*
```
Write a function that checks if a given string is a palindrome.
```

*Treatment A (polite prefix):*
```
Please write a function that checks if a given string is a palindrome.
```

*Treatment B (polite bookend):*
```
Please write a function that checks if a given string is a palindrome. Thank you.
```

**Statistical Analysis:**
- Primary: McNemar's test per pair per model (neutral vs. polite-prefix, neutral vs. polite-bookend)
- Secondary: GLMM with politeness x model interaction term; bootstrap CI for per-model effect sizes

**Success Criteria:**
- Positive result: Statistically significant accuracy difference between any politeness level (p < 0.10), especially if direction varies by model (confirming literature disagreement)
- Null result: All politeness levels produce equivalent accuracy (< 2% difference)
- Key measurement: the model x politeness INTERACTION, not the main effect

**Pilot Protocol:** 5 prompts first (75 calls on free model). Go if: any direction shows > 3% difference. No-go if: all within 2%.

**Tier:** 2
**Bundling Opportunity:** Shares neutral control condition with AQ-NH-01 and AQ-TE-07 (which also tests filler word removal including "please")

---

### AQ-NH-03: Code Comment Presence in Example Code

**Parent Hypothesis:** Novel
**Claim:** Removing inline comments from code examples in coding prompts saves 10-20% tokens with less than 2% accuracy change, because LLMs extract function semantics from code structure and variable names rather than natural language comments. Supported by Pan et al. (ArXiv:2508.13666) finding that removing code formatting saves 24.5% tokens with < 1% accuracy change.

**Independent Variable:** Comment presence (commented code examples vs. stripped-comment code examples)
**Control Condition:** Original HumanEval/MBPP prompts with any inline comments preserved
**Treatment Condition:** Same prompts with all inline comments (# comments) and multi-line docstrings in example code stripped

**Dependent Variables:** Pass rate, input token count, cost

**Benchmarks:** HumanEval + MBPP (code-only -- prompts with code examples containing comments)
**Prompt Selection Criteria:** Select prompts from data/prompts.json (HumanEval + MBPP) that contain inline comments (# ...) or multi-line comments in docstring examples. Require at least 2 comment lines to ensure measurable token difference.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 2 = 200 (free); 20 x 5 x 3 x 2 = 600 (with paid escalation)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Conversion rules:
  1. Remove lines that are solely comments: `re.sub(r'^\s*#.*\n', '', text, flags=re.MULTILINE)`
  2. Remove inline trailing comments: `re.sub(r'\s+#\s+.*$', '', text, flags=re.MULTILINE)`
  3. Preserve shebang lines (`#!/...`) and type comments (`# type: ...`)
  4. Do NOT remove docstrings that are part of the task description (only remove comments within example code blocks)

**Concrete example:**

*Control (with comments):*
```python
def fibonacci(n):
    # Base cases
    if n <= 0:
        return 0  # Return 0 for non-positive input
    if n == 1:
        return 1
    # Recursive case
    return fibonacci(n-1) + fibonacci(n-2)
```

*Treatment (comments stripped):*
```python
def fibonacci(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)
```

**Statistical Analysis:**
- Primary: McNemar's test (paired accuracy comparison)
- Secondary: Token count ratio (treatment/control), bootstrap CI for effect size on pass rate difference

**Success Criteria:**
- Positive result: Token reduction >= 8% AND accuracy change within +/-2% (confirming comments are redundant for LLM comprehension)
- Negative result: Accuracy drops by > 3% (comments carry useful context for code understanding)
- Null result: Token reduction < 5% (not enough comments in benchmark prompts to matter)

**Pilot Protocol:** 5 prompts first (50 calls). Go if: token reduction > 5% and accuracy within +/-5%. No-go if: too few prompts have sufficient comments for measurable reduction.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw HumanEval/MBPP prompts) with AQ-TE-01, AQ-TE-02, AQ-TE-07

---

### AQ-NH-04: Newline Density Between Prompt Sections

**Parent Hypothesis:** Novel
**Claim:** Reducing newline density between prompt sections (single newline vs. double newline vs. no newline) saves 5-10% tokens with negligible accuracy change, because newlines are the biggest token contributor for Claude and Gemini (Pan et al., ArXiv:2508.13666) but serve only human readability, not LLM comprehension.

**Independent Variable:** Newline density (double newline separation vs. single newline vs. no separation)
**Control Condition:** Original prompts with standard double-newline paragraph separation
**Treatment Condition A:** Single newline between sections
**Treatment Condition B:** No newlines between sections (continuous text)

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** All three (HumanEval, MBPP, GSM8K) -- newlines appear in all prompt types
**Prompt Selection Criteria:** Select prompts from data/prompts.json across all benchmarks that have at least 2 distinct sections separated by blank lines (double newlines). Select 7 HumanEval, 7 MBPP, 6 GSM8K for balanced coverage.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show promise
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 3 = 300 (free); 20 x 5 x 3 x 3 = 900 (with paid escalation)
**Estimated Cost:** $0 (free models) / $5-12 (paid escalation)

**Format Conversion Method:**
- Regex-based (zero-cost)
- Conversion rules:
  1. Control: keep as-is (double newline separation)
  2. Single newline: `re.sub(r'\n\n+', '\n', text)` -- collapse consecutive newlines to single
  3. No newlines: `re.sub(r'\n\n+', ' ', text)` -- replace paragraph breaks with space
- Apply ONLY outside code blocks (preserve code block formatting):
  - Extract code blocks with placeholders before regex
  - Restore code blocks after regex

**Concrete example:**

*Control (double newline):*
```
Write a function that takes a list of integers and returns the sum of all even numbers.

The function should handle empty lists by returning 0.

If the list contains non-integer values, raise a TypeError.
```

*Treatment A (single newline):*
```
Write a function that takes a list of integers and returns the sum of all even numbers.
The function should handle empty lists by returning 0.
If the list contains non-integer values, raise a TypeError.
```

*Treatment B (no newlines):*
```
Write a function that takes a list of integers and returns the sum of all even numbers. The function should handle empty lists by returning 0. If the list contains non-integer values, raise a TypeError.
```

**Statistical Analysis:**
- Primary: McNemar's test for each pair per model
- Secondary: Token count ratio per condition; per-benchmark analysis (are code prompts more sensitive than math prompts?)

**Success Criteria:**
- Positive result: Token reduction >= 5% from double to no-newline AND accuracy change within +/-3%
- Negative result: Accuracy drops by > 5% when newlines are removed (newlines serve a parsing function)
- Null result: Token reduction < 3% (not enough newlines in benchmark prompts to matter)

**Pilot Protocol:** 5 prompts first (75 calls). Go if: token reduction > 3% and accuracy within +/-10%. No-go if: token reduction < 2%.

**Tier:** 1
**Bundling Opportunity:** Shares control condition (raw prompts with standard formatting) with AQ-SM-05 (XML overhead measurement uses same prompt set across benchmarks)

---

### AQ-NH-05: Emphasis Markers on Key Terms (Bold, CAPS, Quotes)

**Parent Hypothesis:** Novel
**Claim:** Adding emphasis markers to key terms in coding prompts (**bold** for function name, CAPS for return type, 'quotes' for key constraints) may improve accuracy by 2-5% by directing model attention to critical information, but CAPS emphasis may confuse models (associated with shouting/urgency in training data, potentially changing perceived task difficulty).

**Independent Variable:** Emphasis type (none vs. **bold** vs. CAPS vs. 'single quotes')
**Control Condition:** Original prompts with no emphasis on key terms
**Treatment Condition A:** Key terms wrapped in **bold** markdown
**Treatment Condition B:** Key terms in ALL CAPS
**Treatment Condition C:** Key terms in 'single quotes'

**Dependent Variables:** Pass rate, input token count, consistency rate (CR)

**Benchmarks:** HumanEval + MBPP (emphasize function name, return type, and key constraints)
**Prompt Selection Criteria:** Select prompts from data/prompts.json (HumanEval + MBPP) with at least 3 identifiable key terms (function name, return type, primary constraint). Filter out prompts where key terms are ambiguous.
**Prompt Count:** 20 prompts

**Models:** nvidia/nemotron-3-super-120b-a12b:free (via OpenRouter) as default; escalate to Claude Sonnet / Gemini 1.5 Pro if results show signal
**Repetitions:** 5 per condition
**Total API Calls:** 20 x 5 x 1 x 4 = 400 (free); 20 x 5 x 3 x 4 = 1,200 (with paid escalation)
**Estimated Cost:** $0 (free models) / $8-18 (paid escalation)

**Format Conversion Method:**
- Semi-manual template conversion (identify key terms, apply emphasis)
- Conversion rules:
  1. Identify 3 key terms per prompt: function/task name, return type or expected output, primary constraint
  2. Bold: wrap each key term in `**term**`
  3. CAPS: convert each key term to uppercase
  4. Quotes: wrap each key term in `'term'`
  5. Preserve all other text verbatim
- Key term identification requires manual review for the 20 prompts (one-time effort)

**Concrete example:**

*Control (no emphasis):*
```
Write a function that takes a list of integers and returns the second largest unique value. If the list has fewer than two unique values, return None.
```

*Treatment A (bold):*
```
Write a function that takes a **list of integers** and returns the **second largest unique value**. If the list has fewer than two unique values, return **None**.
```

*Treatment B (CAPS):*
```
Write a function that takes a LIST OF INTEGERS and returns the SECOND LARGEST UNIQUE VALUE. If the list has fewer than two unique values, return NONE.
```

*Treatment C (quotes):*
```
Write a function that takes a 'list of integers' and returns the 'second largest unique value'. If the list has fewer than two unique values, return 'None'.
```

**Statistical Analysis:**
- Primary: McNemar's test for each emphasis type vs. control
- Secondary: Bootstrap CI for effect sizes; compare emphasis types against each other; per-model analysis

**Success Criteria:**
- Positive result: Any emphasis type improves accuracy by >= 3% (p < 0.10)
- Negative result: CAPS emphasis degrades accuracy (> 3% drop), confirming the "shouting" confound
- Null result: All emphasis types within +/-2% of control (emphasis does not help or hurt)

**Pilot Protocol:** 5 prompts first (5 x 5 x 4 = 100 calls). Go if: any emphasis type shows > 3% difference. No-go if: all within 2%.

**Tier:** 2
**Bundling Opportunity:** Shares control condition (raw HumanEval/MBPP prompts) with AQ-TE-01, AQ-TE-02, AQ-NH-01, AQ-NH-02

---

## Section 2: Structured Research Notes

The following ideas from the Phase 11 brainstorming categories did not receive full experiment specs but are documented as structured research notes for future work.

### Whitespace and Layout

#### Indentation in Code Prompts
**Category:** Whitespace/layout
**Description:** Testing whether indentation style (tabs vs. spaces vs. no indentation) in code examples within prompts affects model accuracy. Pan et al. found indentation removal had minimal accuracy impact.
**Why interesting:** If indentation is truly redundant for LLMs, stripping it saves tokens and simplifies prompt pre-processing. Contradicts human coding conventions where indentation is critical for readability.
**Expected difficulty:** Easy -- regex replacement of leading whitespace
**Literature support:** Pan et al. (ArXiv:2508.13666) showed < 1% accuracy change from removing indentation in code completion tasks
**Future priority:** Medium -- strong literature support but expected null result reduces novelty

#### Trailing Whitespace and Newlines After Prompt
**Category:** Whitespace/layout
**Description:** Testing whether trailing whitespace or newlines at the end of a prompt affect model output. Some APIs silently strip trailing whitespace; others pass it through.
**Why interesting:** If trailing whitespace matters, it indicates fragility in model input processing. If it does not matter, it confirms that models handle trivial formatting noise robustly.
**Expected difficulty:** Easy -- append/remove trailing characters
**Literature support:** None specific; anecdotal reports from practitioners
**Future priority:** Low -- likely null result with minimal scientific value

#### Line Length and Wrapping
**Category:** Whitespace/layout
**Description:** Testing whether wrapping long instruction lines at 80 characters vs. leaving them as continuous single lines affects accuracy. Human conventions strongly favor wrapping, but tokenizers do not operate on visual line length.
**Why interesting:** If wrapping matters, it could be because newline tokens serve as attention anchors (per LLM-Microscope). If it does not, wrapping is pure human convention.
**Expected difficulty:** Easy -- regex wrap at N characters
**Literature support:** Indirect -- Pan et al. newline findings suggest newlines carry tokenizer weight
**Future priority:** Low -- narrow scope and expected small effect

### Code-Specific Formatting

#### Docstring Style: Google vs. NumPy vs. One-Liner
**Category:** Code-specific formatting
**Description:** Testing whether the docstring convention (Google-style with Args/Returns sections, NumPy-style with Parameters/Returns sections, or a single-line summary) affects coding accuracy on prompts that include docstrings.
**Why interesting:** Different training corpora emphasize different docstring styles. Models trained heavily on Google-internal code may prefer Google-style docstrings. This tests training data bias in a controlled, measurable way.
**Expected difficulty:** Medium -- requires template conversion between docstring styles, some prompts may not have enough structure for all three styles
**Literature support:** None direct; inferred from training data composition patterns
**Future priority:** Medium -- interesting for model-specific analysis but requires significant manual effort for conversion

#### Type Hint Verbosity
**Category:** Code-specific formatting
**Description:** Testing whether verbose type hints (`numbers: List[float]`) vs. prose descriptions ("takes a list of floating-point numbers") vs. no type information affects coding accuracy.
**Why interesting:** Type hints are machine-readable and unambiguous; prose descriptions are natural language approximations. Models may parse type hints more reliably, or they may rely on the prose description more heavily.
**Expected difficulty:** Medium -- requires converting between type hint formats and prose equivalents
**Literature support:** None direct
**Future priority:** Medium -- interesting intersection of format and information content

#### Variable Naming in Examples
**Category:** Code-specific formatting
**Description:** Testing whether descriptive variable names (`total_count`, `user_list`) vs. short names (`tc`, `ul`) vs. single-letter names (`x`, `y`) in code examples affect model accuracy.
**Why interesting:** Human best practice strongly favors descriptive names, but models may parse any naming convention equally well. If single-letter names hurt accuracy, it demonstrates that LLMs, like humans, benefit from semantic naming.
**Expected difficulty:** Easy -- regex rename in code blocks
**Literature support:** None direct
**Future priority:** Low -- interesting but narrow scope

### Instruction Phrasing

#### Role-Framing ("You are a Python expert...")
**Category:** Instruction phrasing
**Description:** Testing whether prepending a role-framing instruction ("You are an expert Python developer. " or "You are a senior software engineer. ") before the task instruction improves coding accuracy.
**Why interesting:** Role-framing is a widely recommended prompting technique but has not been rigorously tested on coding benchmarks with controlled experiments. Practitioners claim 5-15% improvement; actual effect size on HumanEval/MBPP is unknown.
**Expected difficulty:** Easy -- prepend template string
**Literature support:** Widely cited in prompting guides; no rigorous 2025 study measuring effect size on coding benchmarks specifically
**Future priority:** High -- high practitioner interest, easy to implement, potentially large effect

#### Prompt Length Padding
**Category:** Instruction phrasing
**Description:** Testing whether adding contextual padding (caveats, encouragement, meta-instructions like "Think step by step" or "Be careful with edge cases") affects accuracy beyond what the base instruction provides.
**Why interesting:** Padded prompts are common in production systems. If padding helps, it quantifies the value of prompt engineering. If it hurts, it demonstrates that verbosity carries a real cost.
**Expected difficulty:** Medium -- need to design standardized padding templates that can be applied across prompts
**Literature support:** Chain-of-thought prompting literature (Wei et al.) shows "think step by step" helps reasoning; but generic encouragement is unstudied
**Future priority:** Medium -- overlaps with existing chain-of-thought research

### Structural Markers

#### Numbered vs. Bulleted vs. Unmarked Lists
**Category:** Structural markers
**Description:** Testing whether presenting multi-constraint instructions as numbered lists (1. 2. 3.), bulleted lists (- item), or unmarked continuous prose affects accuracy on coding tasks with multiple requirements.
**Why interesting:** Numbered lists imply ordering/priority; bulleted lists imply unordered set; continuous prose embeds constraints in narrative. The numbering may help models track constraint satisfaction.
**Expected difficulty:** Easy -- template conversion between list formats
**Literature support:** Practitioner consensus favors bulleted/numbered over prose for structured content; no rigorous comparison
**Future priority:** High -- directly actionable, easy to implement, complements AQ-TE-06 (outline format)

#### Bullet Character Variation (* vs. - vs. +)
**Category:** Structural markers
**Description:** Testing whether the specific bullet character used in markdown-style lists affects accuracy. All three characters (*, -, +) are valid markdown list markers, but they tokenize differently across BPE tokenizers.
**Why interesting:** This is a true micro-formatting question where tokenizer behavior is the key variable. The characters * (asterisk, often tokenized with surrounding text), - (hyphen, common standalone token), and + (plus, often part of operators) have different token representations. If accuracy differs, it is purely due to tokenizer/training data effects, not semantic content. Per Pitfall 2 from research notes: tokenizer differences mean these may tokenize differently across models.
**Expected difficulty:** Easy -- single character replacement
**Literature support:** Indirect -- He et al. (ArXiv:2411.10541) showed format preferences vary by model, which could include sub-format variations like bullet characters
**Future priority:** High -- novel micro-formatting question with clear mechanism (tokenizer effects), easy to execute, genuinely unknown outcome. Specifically requested in CONTEXT.md.

#### Section Headers Present vs. Absent
**Category:** Structural markers
**Description:** Testing whether adding section headers (## Parameters, ## Returns, ## Constraints) to coding prompts that lack them improves accuracy by providing explicit structural cues.
**Why interesting:** Related to AQ-SM-06 (markdown vs. XML) but focuses on the minimal intervention of adding headers without full structural markup. If headers alone help, it is a lower-cost alternative to XML tagging.
**Expected difficulty:** Easy -- prepend header text before identified sections
**Literature support:** Multiple 2025 practitioner sources report markdown headers improve LLM parsing; no controlled study
**Future priority:** Medium -- complements AQ-SM-06 but narrower scope

#### Separator Lines (--- or ===) Between Sections
**Category:** Structural markers
**Description:** Testing whether adding horizontal rule separators (--- or ===) between prompt sections improves accuracy by providing visual/token boundaries between distinct information blocks.
**Why interesting:** Separator lines are common in documentation and chat interfaces. They add 1-3 tokens per separator but may help models segment multi-part prompts. If --- and === produce different results, it demonstrates another tokenizer-mediated micro-formatting effect.
**Expected difficulty:** Easy -- insert separator lines between identified sections
**Literature support:** None direct; inferred from general structural markup findings
**Future priority:** Low -- narrow scope, expected small or null effect

---

## Summary Table

### Full Experiment Specs

| ID | Name | Category | Tier | Benchmarks | Prompts | Free API Calls | Paid API Calls | Free Cost | Paid Cost |
|----|------|----------|------|------------|---------|----------------|----------------|-----------|-----------|
| AQ-NH-01 | Imperative vs. interrogative vs. declarative | Instruction phrasing | 2 | HumanEval+MBPP | 20 | 300 | 900 | $0 | $6-14 |
| AQ-NH-02 | Politeness markers (Please/Thank you) | Instruction phrasing | 2 | HumanEval+MBPP | 20 | 300 | 900 | $0 | $6-14 |
| AQ-NH-03 | Code comment presence in examples | Code-specific | 1 | HumanEval+MBPP | 20 | 200 | 600 | $0 | $5-12 |
| AQ-NH-04 | Newline density between sections | Whitespace/layout | 1 | All three | 20 | 300 | 900 | $0 | $5-12 |
| AQ-NH-05 | Emphasis markers on key terms | Structural markers | 2 | HumanEval+MBPP | 20 | 400 | 1,200 | $0 | $8-18 |
| **Totals** | | | | | **100** | **1,500** | **4,500** | **$0** | **$30-70** |

### Research Notes by Category

| Category | Ideas | Future Priority Distribution |
|----------|-------|------------------------------|
| Whitespace/layout | 3 (indentation, trailing whitespace, line wrapping) | 1 Medium, 2 Low |
| Code-specific | 3 (docstring style, type hint verbosity, variable naming) | 2 Medium, 1 Low |
| Instruction phrasing | 2 (role-framing, prompt length padding) | 1 High, 1 Medium |
| Structural markers | 4 (numbered vs. bulleted, bullet character, section headers, separators) | 2 High, 1 Medium, 1 Low |
| **Total** | **12 research notes** | **3 High, 5 Medium, 4 Low** |
