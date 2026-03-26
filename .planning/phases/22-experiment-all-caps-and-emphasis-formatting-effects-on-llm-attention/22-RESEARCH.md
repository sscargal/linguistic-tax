# Phase 22: Experiment: All-Caps and Emphasis Formatting Effects on LLM Attention - Research

**Researched:** 2026-03-26
**Domain:** Prompt emphasis formatting (CAPS, bold, quotes, instruction-word emphasis, sentence-initial capitalization)
**Confidence:** MEDIUM

## Summary

This phase extends the existing AQ-NH-05 experiment spec (emphasis markers on key terms) with two new experiment clusters: instruction-word emphasis (Cluster B) and sentence-initial capitalization (Cluster C). The implementation pattern is well-established -- new intervention types registered in `config.py`, routed through `run_experiment.py`'s match/case dispatch, with emphasis conversion functions in a new module. All three clusters use regex-based or semi-manual prompt transformations that are zero-cost (no LLM pre-processor calls needed), making this a cost-effective experiment.

The key research finding is that emphasis effects on LLMs are real but modest and model-specific. He et al. (ArXiv:2411.10541) showed formatting changes can cause up to 40% performance variation, but this was for structural format changes (JSON vs Markdown vs plain text), not text-level emphasis. For capitalization and bold specifically, evidence is sparser: commercial LLMs handle emphasis better than open-source models (Claude 3 Sonnet scored 3.73/5 on emphasis understanding vs 2.61 for Llama 2-7B per ArXiv:2406.11065), but no controlled study isolates CAPS vs bold vs quotes on coding benchmarks. This makes the experiment genuinely novel -- a key strength for the paper.

The "shouting confound" hypothesis for CAPS is well-grounded: ALL CAPS text is associated with urgency/anger in training data (emails, forums, social media), which could either help (models treat it as high-priority) or hurt (models change perceived task difficulty). This is explicitly worth testing and could yield a publishable negative result.

**Primary recommendation:** Implement all three clusters as independent experiment sets sharing the same infrastructure pattern. Use regex-based transformations for Clusters B and C; semi-manual key-term identification for Cluster A (as specified in AQ-NH-05). Store converted prompts as JSON for reproducibility. Start with free OpenRouter models per the tiered execution plan.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Extend beyond AQ-NH-05 to cover ALL test cases from the phase goal:
  - **Cluster A (AQ-NH-05):** Key-term emphasis -- bold, CAPS, quotes on function names, return types, constraints
  - **Cluster B (new):** Instruction-word emphasis -- "WILL" vs "will", "DO NOT" vs "do not" vs "**do not**" vs "Do **not**"
  - **Cluster C (new):** Sentence-initial capitalization effects -- whether capitalizing the first word of instructions affects compliance
- Each cluster is independently executable with its own pilot protocol
- AQ-NH-05 design (20 prompts, 4 conditions, 5 reps) serves as the template for new clusters
- Add new intervention types to config.py INTERVENTIONS tuple (e.g., "emphasis_bold", "emphasis_caps", "emphasis_quotes", "emphasis_instruction_caps")
- Route through existing run_experiment.py intervention dispatch
- Prompt conversion functions live in a new module or extend prompt_compressor.py
- Results flow through existing analysis pipeline without changes
- Cluster A: Semi-manual key-term identification for 20 HumanEval/MBPP prompts, then automated application
- Cluster B: Regex-based automated conversion for instruction verbs and negation patterns
- Cluster C: Regex-based lowercase first word of sentences, compare against original
- Store converted prompts as JSON alongside originals for reproducibility
- Store all results in existing results.db with new intervention type entries
- Free OpenRouter models first, escalate to paid if results show signal

### Claude's Discretion
- Exact prompt selection criteria within each cluster
- Whether Cluster B and C deserve separate modules or can share conversion logic
- Tier assignment for new clusters (Cluster A is Tier 2 per AQ-NH-05; new clusters TBD)
- Number of prompts for new clusters (likely 20 to match AQ-NH-05)
- Specific statistical thresholds for go/no-go pilot decisions on new clusters

### Deferred Ideas (OUT OF SCOPE)
- Emphasis x noise interaction (combining emphasis with Type A/B noise)
- Unicode emphasis variants (italic via Unicode math symbols, underline via combining characters)
- Emphasis in system prompts vs user prompts
</user_constraints>

<phase_requirements>
## Phase Requirements

This phase does not map to formal v2.0 requirement IDs (those are all complete). It implements novel experiment AQ-NH-05 and extends it with two new clusters. Requirements are defined by:

| ID | Description | Research Support |
|----|-------------|-----------------|
| AQ-NH-05 | Emphasis markers on key terms (bold, CAPS, quotes) | Full spec in novel_hypotheses.md lines 275-342; 20 prompts, 4 conditions, 5 reps |
| CLUSTER-B | Instruction-word emphasis (WILL/will, DO NOT/do not/**do not**) | Novel extension; regex-based conversion; same experimental template |
| CLUSTER-C | Sentence-initial capitalization effects | Novel extension; regex-based conversion; same experimental template |
| INFRA | New intervention types, conversion module, experiment matrix entries | Follows existing pattern: config.py INTERVENTIONS + run_experiment.py dispatch |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Project standard |
| re (stdlib) | N/A | Regex-based prompt transformations for Clusters B and C | Zero-dependency, deterministic |
| json (stdlib) | N/A | Store converted prompt variants | Reproducibility requirement |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Test emphasis conversion functions | All new code gets tests |
| scipy | existing | McNemar's test, bootstrap CI for analysis | Post-experiment analysis |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| regex for Cluster B | spaCy NLP for verb detection | Overkill -- instruction verbs follow predictable patterns; regex suffices |
| New module | Extend prompt_compressor.py | Recommend NEW module -- emphasis is conceptually different from sanitize/compress |

No new packages needed. All emphasis conversions use stdlib regex and string operations.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── emphasis_converter.py  # NEW: All emphasis conversion functions
├── config.py              # MODIFY: Add new INTERVENTIONS entries
├── run_experiment.py      # MODIFY: Add match/case branches for emphasis interventions
data/
├── prompts.json           # EXISTING: Source prompts (unchanged)
├── emphasis/              # NEW: Directory for converted prompt variants
│   ├── cluster_a_bold.json
│   ├── cluster_a_caps.json
│   ├── cluster_a_quotes.json
│   ├── cluster_b_variants.json
│   └── cluster_c_variants.json
├── emphasis_matrix_a.json # NEW: Experiment matrix for Cluster A
├── emphasis_matrix_b.json # NEW: Experiment matrix for Cluster B
└── emphasis_matrix_c.json # NEW: Experiment matrix for Cluster C
tests/
└── test_emphasis_converter.py  # NEW: Tests for all conversion functions
```

### Pattern 1: Emphasis Conversion Module
**What:** A new `src/emphasis_converter.py` module containing all emphasis transformation functions.
**When to use:** All emphasis experiments route through this module.
**Rationale:** Emphasis conversion is conceptually distinct from sanitize/compress (which fix noise). A separate module keeps concerns clean and avoids bloating prompt_compressor.py.

```python
# src/emphasis_converter.py
import re
from typing import Any

def apply_bold_emphasis(text: str, key_terms: list[str]) -> str:
    """Wrap key terms in **bold** markdown markers."""
    result = text
    for term in key_terms:
        result = result.replace(term, f"**{term}**")
    return result

def apply_caps_emphasis(text: str, key_terms: list[str]) -> str:
    """Convert key terms to ALL CAPS."""
    result = text
    for term in key_terms:
        result = result.replace(term, term.upper())
    return result

def apply_quotes_emphasis(text: str, key_terms: list[str]) -> str:
    """Wrap key terms in 'single quotes'."""
    result = text
    for term in key_terms:
        result = result.replace(term, f"'{term}'")
    return result

def apply_instruction_caps(text: str) -> str:
    """Convert instruction verbs and negations to ALL CAPS."""
    # Pattern: common instruction words
    patterns = [
        (r'\bdo not\b', 'DO NOT'),
        (r'\bDo not\b', 'DO NOT'),
        (r'\bwill\b', 'WILL'),
        (r'\bshould\b', 'SHOULD'),
        (r'\bmust\b', 'MUST'),
        (r'\breturn\b', 'RETURN'),  # careful: context-dependent
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result

def apply_instruction_bold(text: str) -> str:
    """Wrap instruction verbs and negations in **bold**."""
    patterns = [
        (r'\b(do not)\b', r'**\1**'),
        (r'\b(Do not)\b', r'**\1**'),
        (r'\b(will)\b', r'**\1**'),
        (r'\b(should)\b', r'**\1**'),
        (r'\b(must)\b', r'**\1**'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result

def lowercase_sentence_initial(text: str) -> str:
    """Lowercase the first character of each sentence."""
    # Match sentence-initial capital after . ! ? or start of string
    def lower_first(match: re.Match) -> str:
        return match.group(0)[:-1] + match.group(0)[-1].lower()
    result = re.sub(r'(^|[.!?]\s+)[A-Z]', lower_first, text)
    return result
```

### Pattern 2: Intervention Routing (extends existing match/case)
**What:** Add new cases to `apply_intervention()` in run_experiment.py.
**Key difference from existing interventions:** Emphasis interventions are zero-cost (no LLM call). They load pre-converted prompts from JSON or apply regex in-place.

```python
# In run_experiment.py apply_intervention():
case "emphasis_bold":
    return (apply_bold_from_cache(prompt_text, prompt_id), {})
case "emphasis_caps":
    return (apply_caps_from_cache(prompt_text, prompt_id), {})
case "emphasis_quotes":
    return (apply_quotes_from_cache(prompt_text, prompt_id), {})
case "emphasis_instruction_caps":
    return (apply_instruction_caps(prompt_text), {})
case "emphasis_instruction_bold":
    return (apply_instruction_bold(prompt_text), {})
case "emphasis_lowercase_initial":
    return (lowercase_sentence_initial(prompt_text), {})
```

### Pattern 3: Pre-computed Prompt Variants (Cluster A)
**What:** Cluster A requires semi-manual key-term identification. Store the results as JSON for reproducibility.
**Why:** Key-term identification cannot be fully automated -- "function name", "return type", "primary constraint" require human judgment for each prompt.

```json
// data/emphasis/cluster_a_key_terms.json
{
  "HumanEval/1": {
    "key_terms": ["separate_paren_groups", "List[str]", "balanced"],
    "prompt_text": "original text..."
  }
}
```

**Conversion pipeline:** Read key terms JSON -> apply emphasis function -> store converted prompt -> use in experiment matrix.

### Pattern 4: Separate Experiment Matrices
**What:** Each cluster gets its own experiment matrix JSON rather than appending to the main 82,000-item matrix.
**Why:** Keeps emphasis experiments independent and avoids polluting the core noise-recovery matrix. The `--intervention` flag on `propt run` already supports filtering.

### Anti-Patterns to Avoid
- **Mixing emphasis with noise:** Deferred to future work (requires H-FMT-05 interaction framework). Each emphasis experiment uses CLEAN prompts only.
- **Averaging across models:** Format effects are model-specific (He et al. IoU < 0.2). Always report per-model results.
- **Regex over-matching in Cluster B:** The word "return" appears both as an instruction verb and a code keyword. Regex patterns must be context-aware (only match in natural language portions, not code blocks).
- **Modifying code blocks:** Emphasis conversions must NOT alter code examples, function signatures, or test cases within prompts. Only the natural language instruction portion should be modified.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statistical analysis | Custom significance tests | Existing McNemar's + bootstrap CI in analyze_results.py | Already validated and tested |
| Experiment execution | New execution harness | Existing run_experiment.py with new intervention cases | Resumability, logging, grading all built-in |
| Prompt grading | New grading logic | Existing grade_results.py (HumanEval sandbox, GSM8K regex) | Emphasis changes don't affect answer format |
| Cost estimation | Manual calculation | Existing execution_summary.py | Works for any intervention type |
| Key-term extraction | LLM-based extraction | Manual identification for 20 prompts | One-time effort; LLM would add cost/non-determinism |

**Key insight:** The emphasis experiment infrastructure is 90% existing code. The only new code is the conversion functions (pure string transforms) and the routing glue.

## Common Pitfalls

### Pitfall 1: Regex Clobbering Code Keywords
**What goes wrong:** Regex patterns for Cluster B (instruction-word emphasis) match code keywords inside docstring examples or function signatures. "return None" in a code example becomes "RETURN NONE".
**Why it happens:** HumanEval prompts contain both natural language descriptions and embedded code.
**How to avoid:** Parse prompts to identify code block boundaries (indented blocks, triple-quote sections). Only apply emphasis transformations to natural language portions. Alternatively, use the `prompt_text` field which typically has the docstring, and protect lines starting with whitespace (code indentation).
**Warning signs:** Test failures where code output changes due to modified function signatures.

### Pitfall 2: Bold Markers Changing Token Count Significantly
**What goes wrong:** Adding `**` markers around terms increases token count, creating a confound -- did accuracy change because of emphasis or because of extra tokens?
**Why it happens:** `**bold**` adds 4 characters (2 `**` pairs) per emphasized term.
**How to avoid:** Track and report token count differences for each emphasis condition. Include token count as a covariate in analysis. The AQ-NH-05 spec already lists "input token count" as a dependent variable.
**Warning signs:** Token count differences > 5% between control and treatment.

### Pitfall 3: Sentence Boundary Detection for Cluster C
**What goes wrong:** Naive regex `[.!?]\s+[A-Z]` misses abbreviations ("e.g. The"), decimal numbers ("3.5 The"), and ellipses ("... The").
**Why it happens:** English sentence boundaries are surprisingly complex.
**How to avoid:** For the 20-prompt experiment, manual verification of converted prompts is feasible and recommended. Automated regex should handle the common cases; edge cases get caught in manual review.
**Warning signs:** Lowercased characters inside code identifiers or acronyms.

### Pitfall 4: Free Model Sensitivity May Differ
**What goes wrong:** Free OpenRouter models (Nemotron 120B MoE with 12B active params) may show null results where frontier models would show effects.
**Why it happens:** Emphasis sensitivity may require more sophisticated language understanding (Claude scored 3.73/5 vs Llama 2-7B at 2.61/5 on emphasis comprehension per ArXiv:2406.11065).
**How to avoid:** Follow the escalation strategy in docs/experiments/README.md Section 6. If free models show null results, run 2-3 representative experiments on Claude Sonnet before concluding.
**Warning signs:** All conditions within +/-2% on free models.

### Pitfall 5: Overlapping Emphasis Markers
**What goes wrong:** In Cluster A, if a key term appears multiple times or key terms overlap (e.g., "list" and "list of integers"), replacement becomes order-dependent or double-wraps terms.
**Why it happens:** Simple string.replace() processes terms sequentially.
**How to avoid:** Sort key terms by length (longest first) to prevent partial matches. Use a single-pass replacement. Verify each converted prompt manually (only 20 prompts).
**Warning signs:** Double-wrapped terms like `**'**list of integers**'**`.

## Code Examples

### Intervention Registration (config.py)
```python
# Add to INTERVENTIONS tuple in src/config.py
INTERVENTIONS: tuple[str, ...] = (
    "raw",
    "self_correct",
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "prompt_repetition",
    # Emphasis experiments (Phase 22)
    "emphasis_bold",
    "emphasis_caps",
    "emphasis_quotes",
    "emphasis_instruction_caps",
    "emphasis_instruction_bold",
    "emphasis_lowercase_initial",
)
```

### Experiment Matrix Generation
```python
# Generate emphasis experiment matrix for Cluster A
import json
from itertools import product

PROMPTS = [...]  # 20 selected HumanEval/MBPP prompt IDs
EMPHASIS_TYPES = ["raw", "emphasis_bold", "emphasis_caps", "emphasis_quotes"]
REPETITIONS = 5
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

matrix = []
for prompt_id, intervention, rep in product(PROMPTS, EMPHASIS_TYPES, range(1, REPETITIONS + 1)):
    matrix.append({
        "prompt_id": prompt_id,
        "noise_type": "clean",
        "noise_level": None,
        "intervention": intervention,
        "model": MODEL,
        "repetition_num": rep,
        "status": "pending",
        "experiment": "emphasis_cluster_a",
    })

# 20 prompts x 4 conditions x 5 reps = 400 items
```

### Routing in run_experiment.py
```python
# Add to apply_intervention() match/case
from src.emphasis_converter import (
    apply_bold_from_cache,
    apply_caps_from_cache,
    apply_quotes_from_cache,
    apply_instruction_caps,
    apply_instruction_bold,
    lowercase_sentence_initial,
)

# In the match/case block:
case "emphasis_bold" | "emphasis_caps" | "emphasis_quotes":
    converted = load_emphasis_variant(prompt_text, intervention)
    return (converted, {})
case "emphasis_instruction_caps":
    return (apply_instruction_caps(prompt_text), {})
case "emphasis_instruction_bold":
    return (apply_instruction_bold(prompt_text), {})
case "emphasis_lowercase_initial":
    return (lowercase_sentence_initial(prompt_text), {})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ALL CAPS for compliance | Structural formatting (XML, headers) | 2024-2025 | CAPS seen as low-impact; structure matters more |
| Assume emphasis is universal | Per-model emphasis sensitivity | 2024 (ArXiv:2406.11065) | Commercial LLMs handle emphasis better than open-source |
| Format effects assumed small | Up to 40% variance from format | 2024 (He et al. ArXiv:2411.10541) | Format is a first-class optimization dimension |

**Key context for this experiment:**
- No published study isolates CAPS vs bold vs quotes on coding/math benchmarks specifically
- The "shouting confound" (CAPS = urgency in training data) is widely discussed in practitioner communities but not empirically tested in a controlled setting
- This experiment fills a genuine gap in the literature

## Discretion Recommendations

### Module Organization
**Recommendation:** Create a single `src/emphasis_converter.py` module containing all conversion functions for all three clusters. The functions are simple enough that splitting into three modules would be unnecessary fragmentation. The module cleanly separates from prompt_compressor.py (which handles LLM-based preprocessing).

### Tier Assignment
**Recommendation:**
- Cluster A: Tier 2 (per AQ-NH-05 spec)
- Cluster B: Tier 2 (novel, medium effort, good potential for "shouting confound" finding)
- Cluster C: Tier 3 (lowest expected effect size; sentence-initial caps is a very subtle signal)

### Prompt Count
**Recommendation:** 20 prompts per cluster, matching AQ-NH-05 template. For Clusters B and C, select from HumanEval + MBPP prompts that contain instruction verbs (Cluster B) or multiple sentences (Cluster C).

### Pilot Go/No-Go Thresholds
**Recommendation:** Same as AQ-NH-05:
- **Go:** Any emphasis type shows > 3% accuracy difference from control
- **No-go:** All emphasis types within +/-2% of control
- Pilot size: 5 prompts per cluster (5 x 5 reps x N conditions)

### Cluster B Condition Design
**Recommendation:** 5 conditions for Cluster B:
1. Control (original text)
2. Instruction verbs in ALL CAPS ("RETURN", "DO NOT")
3. Instruction verbs in **bold** ("**return**", "**do not**")
4. Mixed emphasis ("Do **NOT**" -- bold on the negative, normal on the verb)
5. All instruction words in ALL CAPS (aggressive -- includes "should", "must", "will")

This tests the "shouting confound" directly: condition 2 vs condition 3 isolates CAPS-specific effects from general emphasis effects.

## Open Questions

1. **Code-keyword protection scope**
   - What we know: HumanEval prompts mix natural language with code examples
   - What's unclear: Exact boundary between "instruction text" and "code" varies per prompt
   - Recommendation: For 20 prompts, manual verification is feasible. Build regex heuristic (protect indented lines) + manual spot-check

2. **Interaction between emphasis and model tokenizer**
   - What we know: Tokenizers treat "RETURN" and "return" as different tokens; "**bold**" adds markdown tokens
   - What's unclear: Whether tokenizer differences (not emphasis semantics) drive any observed effects
   - Recommendation: Log token-level diffs for each condition. Report as covariate in analysis

3. **GSM8K applicability**
   - What we know: AQ-NH-05 targets HumanEval + MBPP (code prompts with identifiable key terms)
   - What's unclear: Whether emphasis on math problem terms ("total", "remainder") has similar effects
   - Recommendation: Defer GSM8K emphasis to future work. Clusters B and C could include GSM8K if instruction verbs are present

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml or pytest.ini (existing) |
| Quick run command | `pytest tests/test_emphasis_converter.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONV-01 | Bold emphasis wraps key terms correctly | unit | `pytest tests/test_emphasis_converter.py::test_bold_emphasis -x` | No - Wave 0 |
| CONV-02 | CAPS emphasis uppercases key terms only | unit | `pytest tests/test_emphasis_converter.py::test_caps_emphasis -x` | No - Wave 0 |
| CONV-03 | Quotes emphasis wraps key terms correctly | unit | `pytest tests/test_emphasis_converter.py::test_quotes_emphasis -x` | No - Wave 0 |
| CONV-04 | Instruction CAPS converts instruction verbs | unit | `pytest tests/test_emphasis_converter.py::test_instruction_caps -x` | No - Wave 0 |
| CONV-05 | Instruction bold wraps instruction verbs | unit | `pytest tests/test_emphasis_converter.py::test_instruction_bold -x` | No - Wave 0 |
| CONV-06 | Lowercase initial lowercases sentence starts | unit | `pytest tests/test_emphasis_converter.py::test_lowercase_initial -x` | No - Wave 0 |
| CONV-07 | Code blocks are NOT modified by any conversion | unit | `pytest tests/test_emphasis_converter.py::test_code_protection -x` | No - Wave 0 |
| ROUTE-01 | New interventions route correctly in run_experiment | unit | `pytest tests/test_run_experiment.py::test_emphasis_routing -x` | No - Wave 0 |
| MATRIX-01 | Emphasis matrix generates correct item count | unit | `pytest tests/test_emphasis_converter.py::test_matrix_generation -x` | No - Wave 0 |
| INTEG-01 | Emphasis interventions registered in INTERVENTIONS tuple | unit | `pytest tests/test_config.py -x` | Partially (existing tests check tuple) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_emphasis_converter.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_emphasis_converter.py` -- covers CONV-01 through CONV-07, MATRIX-01
- [ ] Add emphasis routing tests to `tests/test_run_experiment.py` -- covers ROUTE-01

## Sources

### Primary (HIGH confidence)
- `docs/experiments/novel_hypotheses.md` lines 275-342 -- AQ-NH-05 full experiment spec with conversion rules, examples, statistical analysis, pilot protocol
- `docs/experiments/README.md` -- Master index, tiered execution plan, model strategy, bundling opportunities
- `src/config.py`, `src/run_experiment.py`, `src/prompt_compressor.py` -- Existing codebase patterns for interventions
- `docs/prompt_format_research.md` -- Literature survey on format effects being model-specific and task-dependent

### Secondary (MEDIUM confidence)
- [He et al. (ArXiv:2411.10541)](https://arxiv.org/html/2411.10541v1) -- Up to 40% performance variation from format; IoU < 0.2 between model format preferences
- [ArXiv:2406.11065](https://arxiv.org/html/2406.11065v2) -- LLM emphasis understanding: Claude 3 Sonnet 3.73/5, Llama 2-7B 2.61/5; commercial > open-source
- [Learn Prompting: Format and Labels](https://learnprompting.org/docs/intermediate/whats_in_a_prompt) -- ALL CAPS rarely improves performance; clear instructions > emphasis

### Tertiary (LOW confidence)
- [Hacker News discussion on CAPS compliance](https://news.ycombinator.com/item?id=41550941) -- Anecdotal: CAPS emphasis is common in system prompts but effectiveness is debated
- [LinkedIn: "Uppercase Is All You Need"](https://www.linkedin.com/posts/learn-prompting_uppercase-is-all-you-need-activity-7317584856782155776-APlU) -- Popular article on CAPS in prompts; no controlled study backing claims
- [Medium: Do Capital Letters Really Matter?](https://medium.com/@mirko.siddi/do-capital-letters-really-matter-a-curious-discovery-in-ai-prompting-988eafad9135) -- Anecdotal observations; needs verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses only stdlib (re, json) and existing project infrastructure
- Architecture: HIGH - Follows established intervention pattern (config.py + run_experiment.py dispatch)
- Conversion logic: MEDIUM - Regex patterns for Cluster B/C need careful testing; code-block protection is the main risk
- Experiment design: HIGH - Cluster A follows AQ-NH-05 spec exactly; Clusters B/C extend with same template
- Expected effect size: LOW - No published controlled study on CAPS/bold/quotes for coding benchmarks; effects may be null

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable domain; no fast-moving dependencies)
