# Format x Noise Interaction Experiments: Does Structure Protect Against Noise?

**Parent Hypothesis:** H-FMT-05 (Format x Noise Interaction)
**Date:** 2026-03-24
**Status:** Draft
**Cluster ID:** FN (Format-Noise)

## Background

No existing paper examines whether structured formatting makes prompts more or less robust to character-level noise. This is a potential whitepaper-differentiating finding. Our experiment suite is uniquely positioned to test this because we already have:

1. **Noise injection infrastructure** (`src/noise_generator.py`) with Type A character-level noise at 5/10/20% and Type B ESL syntactic noise
2. **Format conversion methods** defined in the token efficiency (TOON, bullet) and structural markup (XML) experiment clusters
3. **Analysis infrastructure** (`src/analyze_results.py`) with GLMM capable of testing format x noise_level interaction terms

The core question: when noise corrupts a formatted prompt, does the structure survive better than prose? Or does noise on structural tokens (XML tags, bullet markers) cause catastrophic parsing failures that are WORSE than noise on prose connectors?

### Key Insight: Order of Operations

**Format conversion is performed BEFORE noise injection.** Noise is applied to the already-formatted prompt. This means:
- XML tags like `<task>` can be corrupted to `<tsak>` by character mutations
- Bullet markers like `- ` can be corrupted to `+ ` or `_ `
- TOON delimiters can be corrupted, breaking the compact notation

This order of operations is critical because it tests real-world robustness: if a user writes in a structured format but makes typos, does the structure help or hurt?

### Noise Injection Functions

From `src/noise_generator.py`:

```python
def inject_type_a_noise(
    text: str,
    error_rate: float,
    seed: int,
    answer_type: str = "code",
) -> str:
    """Inject character-level noise at the specified error rate.

    Applies weighted mutations: 40% adjacent key swap, 25% omission,
    20% doubling, 15% transposition. Protects Python keywords and operators.
    Uses isolated random.Random instance for determinism.
    """

def inject_type_b_noise(
    text: str,
    l1_source: str,
    seed: int | None = None,
) -> str:
    """Inject ESL syntactic noise based on L1 transfer patterns.

    Applies rule-based transformations simulating L1 interference.
    l1_source: "mandarin", "spanish", "japanese", or "mixed".
    Deterministic by design.
    """
```

### Risk Documentation

**XML tag corruption:** Noise injection on XML tags could BREAK the structure entirely (e.g., `<task>` becomes `<tsak>`, `</parameters>` becomes `</parametrs>`). If this happens and accuracy drops sharply, that is ITSELF a finding: it demonstrates that XML formatting is FRAGILE under noise rather than protective. The model may completely fail to parse corrupted tags, producing worse output than noisy prose where the degradation is gradual.

**TOON compact format vulnerability:** TOON's compact notation has fewer redundant tokens, so each corrupted token carries higher information density. A single mutation in a TOON-formatted prompt destroys more information than the same mutation in a verbose prose prompt. This expected asymmetry means noise may hurt MORE in compact formats, which would be a finding against naive "compress everything" advice.

**Bullet marker resilience:** Bullet markers (-, *, 1.) are short single-token markers. A character mutation on a dash changes it to an underscore or equals sign, which may or may not break the list structure for the model. This is an intermediate case between XML (multi-character, fragile) and prose (no structural markers to break).

---

## Atomic Experiment Specifications

### AQ-FN-01: XML-Structured Prompts x Type A Noise at 5/10/20% on HumanEval

**Parent Hypothesis:** H-FMT-05
**Claim:** XML-tagged prompts show a shallower accuracy degradation slope across noise levels (5%, 10%, 20%) compared to prose baseline because XML tags are multi-character sequences that survive character mutations better than single-token prose connectors. However, at high noise levels (20%), XML structure may break entirely and show steeper degradation than prose.

**Independent Variable:** Format (prose vs. XML) crossed with noise level (0%, 5%, 10%, 20%)
**Control Condition:** Original prose prompts at each noise level (0%, 5%, 10%, 20%)
**Treatment Condition:** XML-formatted prompts at each noise level (0%, 5%, 10%, 20%)

**Dependent Variables:** Pass rate, accuracy degradation slope (pass rate vs. noise level), input token count

**Benchmarks:** HumanEval (coding task -- XML tags wrap task description, parameters, constraints)
**Prompt Selection Criteria:** Select 20 HumanEval prompts with multi-part structure (task description + parameters + constraints + return spec) that benefit from XML tagging. These should be the same prompts used in structural_markup.md (AQ-SM-*) experiments for cross-cluster comparison.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); STRONGLY recommend paid escalation to Claude Sonnet (claude-sonnet-4-20250514) and Gemini 1.5 Pro (gemini-1.5-pro) since the interaction effect may be model-architecture-dependent
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 2 formats x 4 noise levels = 800 (free); 2,400 with 3 models
**Estimated Cost:** $0 (free models) / $10-15 (paid escalation)

**Format Conversion Method:**
- XML conversion: LLM pre-processor using Nemotron-3-Nano (free). Conversion prompt from structural_markup.md (AQ-SM-*) specs. Format conversion is performed BEFORE noise injection.
- Noise injection: `inject_type_a_noise(text, error_rate=rate, seed=seed, answer_type="code")` from `src/noise_generator.py` with rates 0.05, 0.10, 0.20
- Seeds: `derive_seed(base_seed=42, prompt_id=id, noise_type="type_a", noise_level=str(rate))` for reproducibility

**Statistical Analysis:**
- Primary: GLMM with format x noise_level interaction term. The interaction term tests whether degradation SLOPE differs between formats. Uses existing `analyze_results.py` GLMM infrastructure.
- Secondary: Bootstrap CI for slope difference. Compare degradation slopes (linear regression of pass rate on noise level) for each format.
- Tertiary: Point-wise McNemar's at each noise level (prose vs. XML at 5%, at 10%, at 20%)

**Success Criteria:**
- Positive result: GLMM interaction term is significant (p < 0.05), AND XML shows shallower degradation slope, confirming structural protection
- Alternative result: GLMM interaction term is significant but XML shows STEEPER degradation at 20%, confirming XML is fragile under high noise
- Null result: No significant interaction, suggesting format provides no noise protection

**Pilot Protocol:** Contingent on AQ-FN-05 micro-pilot gate. DO NOT RUN this full experiment unless AQ-FN-05 shows signal (see AQ-FN-05 go/no-go criteria).

**Tier:** 2 (runs only if micro-pilot passes)
**Bundling Opportunity:** Shares prose control condition with AQ-FN-02, AQ-FN-03. The prose x noise data is collected once and reused across all format comparisons. Cross-references structural_markup.md for XML conversion method.

**Dependency:** Requires AQ-FN-05 micro-pilot to pass go/no-go gate.

---

### AQ-FN-02: Bullet-Formatted Prompts x Type A Noise at 5/10/20% on HumanEval

**Parent Hypothesis:** H-FMT-05
**Claim:** Bullet-formatted prompts show an INTERMEDIATE noise resilience between prose and XML. Bullet markers (-, *, 1.) are short single-token markers that may be MORE vulnerable to noise than prose connectors (which are redundant and can absorb mutations), but less vulnerable than multi-character XML tags (whose corruption is catastrophic).

**Independent Variable:** Format (prose vs. bullet) crossed with noise level (0%, 5%, 10%, 20%)
**Control Condition:** Original prose prompts at each noise level
**Treatment Condition:** Bullet-formatted prompts at each noise level

**Dependent Variables:** Pass rate, accuracy degradation slope, input token count

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Same 20 HumanEval prompts as AQ-FN-01 for direct cross-format comparison.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation to Claude Sonnet and Gemini 1.5 Pro
**Repetitions:** 5 per condition
**Total API Calls:** 800 (free); 2,400 with 3 models (shares prose control with AQ-FN-01, so effective new calls = 400 free / 1,200 paid)
**Estimated Cost:** $0 (free models) / $5-10 (paid escalation, shares control)

**Format Conversion Method:**
- Bullet conversion: LLM pre-processor using Nemotron-3-Nano (free). Conversion prompt from token_efficiency.md (AQ-TE-05/06) specs. Format conversion is performed BEFORE noise injection.
- Noise injection: Same as AQ-FN-01
- Seeds: Same derivation as AQ-FN-01

**Statistical Analysis:**
- Primary: GLMM with format x noise_level interaction term
- Secondary: Three-way slope comparison (prose vs. XML vs. bullet) if AQ-FN-01 data is available
- Tertiary: Point-wise McNemar's at each noise level

**Success Criteria:**
- Positive result: Bullet degradation slope is between prose and XML, confirming the "intermediate resilience" hypothesis
- Alternative result: Bullet shows better resilience than XML (short markers absorb noise better than complex tags)
- Null result: All formats degrade similarly

**Pilot Protocol:** Contingent on AQ-FN-05 micro-pilot gate.

**Tier:** 2 (runs only if micro-pilot passes)
**Bundling Opportunity:** Shares prose control with AQ-FN-01, AQ-FN-03. Cross-references token_efficiency.md for bullet conversion method.

**Dependency:** Requires AQ-FN-05 micro-pilot to pass go/no-go gate.

---

### AQ-FN-03: TOON-Formatted Prompts x Type A Noise at 5/10/20% on HumanEval

**Parent Hypothesis:** H-FMT-05
**Claim:** TOON-formatted prompts are the MOST vulnerable to noise because compact notation has the highest information density per token. Each corrupted character in a TOON prompt destroys more information than the same corruption in verbose prose, where redundant words serve as error-correcting buffers.

**Independent Variable:** Format (prose vs. TOON) crossed with noise level (0%, 5%, 10%, 20%)
**Control Condition:** Original prose prompts at each noise level
**Treatment Condition:** TOON-formatted prompts at each noise level

**Dependent Variables:** Pass rate, accuracy degradation slope, input token count

**Benchmarks:** HumanEval (coding task -- TOON applies to prompts with structured data like parameter specs)
**Prompt Selection Criteria:** Same 20 HumanEval prompts as AQ-FN-01/02, filtered to those with structured data suitable for TOON conversion (parameter descriptions, input/output specs). If fewer than 20 qualify for TOON, use the qualifying subset.
**Prompt Count:** 20 prompts (or fewer if TOON-eligible subset is smaller)

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation to Claude Sonnet and Gemini 1.5 Pro
**Repetitions:** 5 per condition
**Total API Calls:** 800 (free); 2,400 with 3 models (shares prose control, effective new calls = 400 free / 1,200 paid)
**Estimated Cost:** $0 (free models) / $5-10 (paid escalation, shares control)

**Format Conversion Method:**
- TOON conversion: LLM pre-processor using Nemotron-3-Nano (free). Conversion prompt from token_efficiency.md (AQ-TE-01/02/03) specs. Format conversion is performed BEFORE noise injection.
- Noise injection: Same as AQ-FN-01
- Seeds: Same derivation as AQ-FN-01

**Statistical Analysis:**
- Primary: GLMM with format x noise_level interaction term
- Secondary: Four-way slope comparison (prose vs. XML vs. bullet vs. TOON) if all format data available
- Tertiary: Information density metric: tokens-per-semantic-unit x noise rate, to quantify the "density vulnerability" hypothesis

**Success Criteria:**
- Positive result: TOON shows the steepest degradation slope (most vulnerable), confirming that information density and noise robustness trade off
- Alternative result: TOON performs similarly to prose (compact notation is not more vulnerable), suggesting the information density hypothesis is wrong
- Null result: All formats degrade similarly, no interaction effect

**Pilot Protocol:** Contingent on AQ-FN-05 micro-pilot gate.

**Tier:** 2 (runs only if micro-pilot passes)
**Bundling Opportunity:** Shares prose control with AQ-FN-01, AQ-FN-02. Cross-references token_efficiency.md for TOON conversion method.

**Dependency:** Requires AQ-FN-05 micro-pilot to pass go/no-go gate.

---

### AQ-FN-04: XML-Structured Prompts x Type B ESL Noise on HumanEval

**Parent Hypothesis:** H-FMT-05
**Claim:** XML structure is unaffected by Type B ESL noise because ESL patterns target prose grammar (article omission, tense removal, preposition confusion) rather than markup tokens. XML-formatted prompts should show EQUAL degradation to prose under ESL noise, unlike the differential degradation expected under Type A character noise.

**Independent Variable:** Format (prose vs. XML) crossed with noise type (none vs. Type B ESL mixed)
**Control Condition:** Original prose prompts (clean and with ESL noise)
**Treatment Condition:** XML-formatted prompts (clean and with ESL noise)

**Dependent Variables:** Pass rate, accuracy degradation (clean vs. ESL-noised)

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Same 20 HumanEval prompts as AQ-FN-01 for cross-noise-type comparison.
**Prompt Count:** 20 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free); paid escalation if results contrast with AQ-FN-01
**Repetitions:** 5 per condition
**Total API Calls:** 20 prompts x 5 reps x 1 model x 2 formats x 2 noise conditions = 400 (free)
**Estimated Cost:** $0 (free models) / $3-5 (paid escalation)

**Format Conversion Method:**
- XML conversion: Same as AQ-FN-01. Format conversion is performed BEFORE noise injection.
- Noise injection: `inject_type_b_noise(text, l1_source="mixed", seed=None)` from `src/noise_generator.py`. Uses "mixed" source combining Mandarin, Spanish, and Japanese L1 transfer patterns for maximum ESL effect.
- Note: Type B ESL noise is deterministic (same input always produces same output) regardless of seed.

**Statistical Analysis:**
- Primary: GLMM with format x noise_type interaction term
- Secondary: Compare the format x noise interaction magnitude for Type A (AQ-FN-01) vs. Type B (AQ-FN-04). If XML protects against Type A but not Type B, this confirms the mechanism is about structural token resilience, not general robustness.

**Success Criteria:**
- Positive result: No significant format x ESL-noise interaction (XML and prose degrade equally under ESL noise), confirming that ESL patterns target prose not markup
- Alternative result: XML shows LESS degradation under ESL noise (structural tags preserve meaning even when surrounding prose is grammatically degraded)
- Null result: Similar to positive -- no interaction

**Pilot Protocol:** Run as part of AQ-FN-05 micro-pilot if possible (add ESL noise as additional condition). Otherwise, run independently after micro-pilot passes.

**Tier:** 3 (stretch -- adds mechanistic nuance but not essential for the main finding)
**Bundling Opportunity:** Shares prose and XML control conditions with AQ-FN-01. Reuses XML conversion artifacts.

**Dependency:** Requires AQ-FN-05 micro-pilot to pass go/no-go gate (or run independently as Tier 3).

---

### AQ-FN-05: Micro-Pilot Gate Experiment (CRITICAL -- Run First)

**Parent Hypothesis:** H-FMT-05
**Claim:** A 300-call micro-pilot can determine whether the format x noise interaction effect is large enough to justify the full 2,400+ call experiment. This is the go/no-go gate for AQ-FN-01 through AQ-FN-04.

**Independent Variable:** Format (prose vs. XML vs. bullet) crossed with noise level (0%, 5%, 10%, 20%)
**Control Condition:** Prose at each noise level
**Treatment Conditions:** XML and bullet at each noise level

**Dependent Variables:** Pass rate, degradation slope per format

**Benchmarks:** HumanEval (coding task)
**Prompt Selection Criteria:** Select 5 HumanEval prompts with multi-part structure suitable for both XML and bullet conversion. These 5 should be a representative subset of the 20 planned for the full experiments.
**Prompt Count:** 5 prompts

**Models:** Free OpenRouter (nvidia/nemotron-3-super-120b-a12b:free)
**Repetitions:** 5 per condition
**Total API Calls:** 5 prompts x 5 reps x 1 model x 3 formats x 4 noise levels = 300 (free)
**Estimated Cost:** $0 (free models)

**Format Conversion Method:**
- XML conversion: LLM pre-processor using Nemotron-3-Nano (free). Same prompt as AQ-FN-01.
- Bullet conversion: LLM pre-processor using Nemotron-3-Nano (free). Same prompt as AQ-FN-02.
- Noise injection: `inject_type_a_noise(text, error_rate=rate, seed=seed, answer_type="code")` at rates 0.05, 0.10, 0.20. Format conversion is performed BEFORE noise injection.
- Seeds: `derive_seed(base_seed=42, prompt_id=id, noise_type="type_a", noise_level=str(rate))`

**Statistical Analysis:**
- Primary: Compute degradation slope (linear regression of pass rate on noise level) for each format
- Secondary: Compare slopes visually and numerically. Test GLMM interaction term if sample size permits.
- Note: With only 5 prompts, formal statistical significance is unlikely. The go/no-go decision is based on EFFECT SIZE, not p-value.

**Go/No-Go Criteria:**

**GO (proceed to full experiments AQ-FN-01 through AQ-FN-04):**
- If ANY format shows a 5+ percentage point difference in degradation slope compared to prose baseline across noise levels
- Example: Prose drops from 80% to 60% (slope = -20pp), XML drops from 80% to 65% (slope = -15pp). Difference = 5pp. GO.
- Rationale: A 5pp slope difference on 5 prompts suggests a detectable and scientifically meaningful interaction on the full 20-prompt experiment.

**NO-GO (do not proceed to full experiments):**
- If ALL formats show similar degradation patterns (within 3 percentage points of prose slope)
- Example: Prose slope = -20pp, XML slope = -19pp, bullet slope = -21pp. All within 3pp. NO-GO.
- Rationale: If the interaction effect is this small, even a 20-prompt experiment is unlikely to produce a publishable finding, and the 2,400+ calls are not justified.

**CONDITIONAL GO:**
- If one format shows a 5+ pp difference but others do not, proceed with ONLY the promising format (e.g., run AQ-FN-01 but not AQ-FN-02/03). This reduces the full experiment cost.

**Pilot Protocol:** This IS the pilot. Run immediately. No prior gate.

**Tier:** 1 (MUST run before any other AQ-FN-* experiment)
**Bundling Opportunity:** None -- this is the gate experiment. All other AQ-FN-* depend on its results.

**Dependency:** None. This runs first.

---

## Concrete Examples

### Example: HumanEval Prompt in Three Formats with 10% Type A Noise

**Original prose (clean):**
```
Write a function that takes a list of integers and returns the second largest
unique value. If the list has fewer than two unique values, return None. The
function should handle negative numbers and duplicates correctly.
```

**Original prose with 10% Type A noise applied:**
```
Wrtie a functiom that takess a list of integres and retunrs the secnod largset
uniqeu value. If the lizt has fweer than two uniuqe valeus, return None. The
funtcion should habdle negatvie numbers and duplciates correcyly.
```

**XML format (clean):**
```xml
<task>Write a function that returns the second largest unique value</task>
<parameters>
  <param name="input">list of integers</param>
</parameters>
<constraints>
  <constraint>If fewer than two unique values, return None</constraint>
  <constraint>Handle negative numbers correctly</constraint>
  <constraint>Handle duplicates correctly</constraint>
</constraints>
```

**XML format with 10% Type A noise applied:**
```xml
<taks>Write a funtcion that retunrs the secnod largset uniqeu value</taks>
<paramteres>
  <parem name="inptu">list of integres</parem>
</paramteres>
<constraitns>
  <constraitn>If fweer than two uniuqe valeus, return None</constraitn>
  <constraitn>Habdle negatvie numbers correcyly</constraitn>
  <constraitn>Habdle duplciates correcyly</constraitn>
</constraitns>
```

Note how XML tag corruption (`<taks>`, `<paramteres>`, `<constraitn>`) may prevent the model from parsing the structure entirely, potentially causing worse performance than noisy prose where degradation is gradual.

**Bullet format (clean):**
```
- Write function: returns second largest unique value
- Input: list of integers
- Edge case: fewer than 2 unique values -> return None
- Handle: negative numbers
- Handle: duplicates
```

**Bullet format with 10% Type A noise applied:**
```
- Wrtie functiom: retunrs secnod largset uniqeu value
- Inptu: list of integres
- Edeg case: fweer than 2 uniuqe valeus -> return None
- Habdle: negatvie numbers
- Habdle: duplciates
```

Note how bullet markers (-) survive noise (they are not letter characters and are not mutated by Type A noise, which only targets non-whitespace, non-protected characters). The structure remains parseable even though the content is noisy.

---

## Summary Table

| ID | Atomic Question | Formats Tested | Noise Type | Tier | API Calls (Free) | Cost (Free) | Cost (Paid) | Depends on Micro-Pilot |
|----|----------------|---------------|------------|------|-------------------|-------------|-------------|----------------------|
| AQ-FN-01 | XML x Type A noise | Prose, XML | Type A (5/10/20%) | 2 | 800 | $0 | $10-15 | Yes |
| AQ-FN-02 | Bullet x Type A noise | Prose, Bullet | Type A (5/10/20%) | 2 | 400* | $0 | $5-10 | Yes |
| AQ-FN-03 | TOON x Type A noise | Prose, TOON | Type A (5/10/20%) | 2 | 400* | $0 | $5-10 | Yes |
| AQ-FN-04 | XML x Type B ESL noise | Prose, XML | Type B (ESL mixed) | 3 | 400 | $0 | $3-5 | Yes |
| AQ-FN-05 | **Micro-pilot gate** | Prose, XML, Bullet | Type A (5/10/20%) | **1** | **300** | **$0** | **$0** | **No (IS the pilot)** |
| **Totals** | | | | | **2,300** | **$0** | **$23-40** | |

*AQ-FN-02 and AQ-FN-03 share prose control condition with AQ-FN-01, reducing effective new calls.

### Tier Breakdown

- **Tier 1** (AQ-FN-05): 300 free API calls, $0 cost. The micro-pilot gate that determines whether the full experiment suite is worth running. MUST run first.
- **Tier 2** (AQ-FN-01, 02, 03): 1,600 free API calls (with shared controls), $0 cost. Full format x noise interaction experiments. Run only if micro-pilot passes.
- **Tier 3** (AQ-FN-04): 400 free API calls, $0 cost. ESL noise variant for mechanistic insight. Stretch goal.

### Execution Order

1. **AQ-FN-05** (micro-pilot): Run first. Evaluate go/no-go criteria.
2. If GO: Run **AQ-FN-01**, **AQ-FN-02**, **AQ-FN-03** in parallel (they share prose control data).
3. If partial GO: Run only the format(s) that showed signal in the micro-pilot.
4. If time/interest permits: Run **AQ-FN-04** for ESL noise comparison.

### Model Escalation Strategy

1. Run micro-pilot (AQ-FN-05) on free OpenRouter models only
2. If micro-pilot passes GO: run full experiments on free models first
3. STRONGLY recommend paid model escalation for the full experiments -- the interaction effect may be model-architecture-dependent (per He et al. finding that format preferences have IoU < 0.2 between model families). A format that protects against noise on one model may not protect on another.
4. Priority paid models: Claude Sonnet (claude-sonnet-4-20250514) and Gemini 1.5 Pro (gemini-1.5-pro)
