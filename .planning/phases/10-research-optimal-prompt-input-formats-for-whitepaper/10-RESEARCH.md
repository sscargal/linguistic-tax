# Phase 10: Research Optimal Prompt Input Formats for Whitepaper - Research

**Researched:** 2026-03-24
**Domain:** Prompt format optimization, token-efficient notation, structured prompting
**Confidence:** MEDIUM

## Summary

This phase is a pure research/documentation phase -- no code changes. The goal is to produce a structured research document in `docs/` surveying how prompt input formats (XML, JSON, YAML, TOON, bullet/outline, minimal punctuation, novel formats) affect LLM reasoning accuracy and token efficiency. The document must contain testable hypotheses ranked by feasibility for whitepaper inclusion, with concrete experiment designs ready for Phase 11.

The research landscape is rich and active. The key paper "Does Prompt Formatting Have Any Impact on LLM Performance?" (He et al., 2024, arXiv:2411.10541) demonstrates up to 40% performance variation from format choice on smaller models, though larger models are more robust. TOON (Token-Oriented Object Notation) achieves 40% fewer tokens than JSON with slightly higher accuracy on data retrieval tasks. The punctuation research (LLM-Microscope, arXiv:2502.15007; "When Punctuation Matters," arXiv:2508.11383) reveals that punctuation tokens serve as attention sinks and context memory carriers, meaning their removal can degrade performance -- a nuanced finding that complicates the "minimal notation" hypothesis.

**Primary recommendation:** Structure the research document around 5-6 format categories with specific testable hypotheses, each including expected effect direction, measurement approach, and estimated API cost. Prioritize hypotheses that directly extend the paper's "linguistic tax" thesis by quantifying format-related token waste versus accuracy impact.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Literature survey of existing work on prompt format effects (TOON, CompactPrompt, structured prompting papers)
- Lightweight prototype experiments where feasible -- quick manual tests to validate promising directions before committing to full experiment design
- Focus on formats that reduce tokens while maintaining or improving accuracy (aligns with the paper's "linguistic tax" thesis)
- Structured research document in `docs/` with literature findings organized by format category, testable hypotheses ranked by feasibility and expected impact, concrete experiment designs for the top hypotheses (ready for Phase 11 to pick up)
- Each hypothesis should specify: what to test, expected effect, how to measure, estimated API cost
- Cast a wide net across promising formats: TOON-like compact notation, XML/structured markup, bullet/outline formats, minimal punctuation, novel formats
- Compare against the existing verbose natural language baseline already in our experiment suite
- Document findings as potential future intervention types only -- do NOT modify existing `src/` code
- If a format shows strong promise, describe it as a candidate intervention for future phases
- Maintain separation: this phase produces knowledge, implementation phases produce code

### Claude's Discretion
- Exact structure and organization of the research document
- Which papers to prioritize in the literature survey
- How many prototype experiments to run (if any)
- Level of detail in experiment design proposals

### Deferred Ideas (OUT OF SCOPE)
- Implementing new intervention types based on research findings -- future phase after experimentation
- Modifying the experiment matrix to include new format conditions -- requires RDD update first
- Running full-scale format comparison experiments -- too costly for a research phase
</user_constraints>

## Standard Stack

This is a documentation-only phase. No new libraries are needed.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown | N/A | Research document format | Consistent with existing `docs/` convention |
| Python (optional) | 3.11+ | Quick prototype token counting scripts | Already in project stack |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| tiktoken | Token counting for format comparisons | If running prototype token counts on sample prompts |
| Anthropic/Google APIs | Lightweight prototype accuracy tests | Only if quick manual validation is needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual token counting | tiktoken library | tiktoken gives exact counts per model tokenizer |
| Full experiment runs | Quick 5-10 prompt spot checks | Spot checks validate direction without cost commitment |

## Architecture Patterns

### Recommended Document Structure
```
docs/
  prompt_format_research.md     # Main research document
    - Executive Summary
    - Literature Survey (by format category)
    - Format Taxonomy (comparison table)
    - Testable Hypotheses (ranked)
    - Experiment Designs (for top hypotheses)
    - Integration Notes (how formats map to intervention types)
    - References
```

### Pattern 1: Hypothesis Specification Template
**What:** Each testable hypothesis follows a standardized format for Phase 11 consumption.
**When to use:** Every hypothesis proposed in the research document.
**Example:**
```markdown
### H-FMT-01: TOON vs JSON for Structured Code Prompts

**Claim:** Reformatting structured prompt data from JSON to TOON reduces input
tokens by 30-40% while maintaining or improving coding task accuracy.

**Independent Variable:** Prompt data format (JSON baseline vs TOON)
**Dependent Variables:** Pass rate, token count (input), cost
**Benchmarks:** HumanEval subset (prompts with structured context)
**Models:** Claude Sonnet, Gemini 1.5 Pro (same as main experiment)
**Sample Size:** 20 prompts x 5 repetitions x 2 models = 200 API calls
**Estimated Cost:** ~$2-5 (using existing benchmark prompts)
**Expected Effect:** 30-40% token reduction, <5% accuracy change
**Measurement:** Paired comparison (same prompt, different format)
**Priority:** HIGH (directly extends paper's compression thesis)
```

### Pattern 2: Format Category Organization
**What:** Group findings by format family rather than by paper.
**When to use:** The literature survey section.
**Example categories:**
1. Token-Optimized Notations (TOON, CompactPrompt-style)
2. Structured Markup (XML tags, HTML)
3. Minimal/Telegraphic (bullet points, outline format)
4. Punctuation Variations (question marks, periods, commas)
5. Whitespace/Formatting (newlines, indentation)
6. Hybrid/Novel Approaches (format mixing, CFPO-style)

### Anti-Patterns to Avoid
- **Ungrounded speculation:** Every hypothesis must cite at least one paper or empirical finding supporting the expected direction. Do not propose hypotheses based on intuition alone.
- **Overly ambitious experiment designs:** Keep estimated API costs under $20 per hypothesis. This is meant to be testable in a pilot, not a full experiment.
- **Ignoring model specificity:** He et al. (2024) showed format preferences differ across models. Every hypothesis must note expected model-specific variation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Manual character-based estimates | tiktoken or model-specific tokenizer | Token counts differ significantly from character counts; BPE tokenization is non-obvious |
| Literature search | Ad hoc Google searches | Systematic survey with ArXiv + citation chaining | Reproducible, complete coverage |
| Format conversion (TOON) | Custom TOON parser | toon-format/toon reference spec | Spec defines canonical encoding; hand-rolling risks non-standard output |

**Key insight:** This is a research phase. The main "don't hand-roll" concern is methodology -- use systematic literature review practices rather than cherry-picking papers that confirm a hypothesis.

## Common Pitfalls

### Pitfall 1: Confusing Data Formatting with Prompt Formatting
**What goes wrong:** Conflating "how structured data is encoded in prompts" (JSON vs TOON for passing data) with "how instructions are formatted" (prose vs bullets vs XML tags). These are different questions with different findings.
**Why it happens:** Both fall under "prompt format" but affect different parts of the prompt.
**How to avoid:** Clearly separate: (a) instruction format, (b) context/data format, (c) overall prompt structure. Different findings apply to each.
**Warning signs:** A hypothesis that treats all format changes as equivalent.

### Pitfall 2: Assuming Format Effects Are Model-Independent
**What goes wrong:** Stating "XML is better than Markdown" as a universal truth.
**Why it happens:** He et al. (2024) showed GPT-3.5 prefers JSON while GPT-4 prefers Markdown; IoU between model format preferences is often below 0.2.
**How to avoid:** Every hypothesis must be tested per-model. Design experiments to compare across Claude and Gemini separately.
**Warning signs:** Claims about "the best format" without model qualification.

### Pitfall 3: Ignoring the Punctuation Paradox
**What goes wrong:** Proposing "remove all unnecessary punctuation" as a token-saving strategy without accounting for punctuation's role as attention sinks.
**Why it happens:** LLM-Microscope (arXiv:2502.15007) showed punctuation tokens carry context memory. Removing them degrades MMLU and BABILong-4k performance.
**How to avoid:** Frame punctuation removal as a hypothesis to TEST, not an assumed benefit. The research suggests it may HURT accuracy.
**Warning signs:** Treating punctuation purely as formatting overhead.

### Pitfall 4: Comparing Apples to Oranges on Token Counts
**What goes wrong:** Comparing token counts across formats without controlling for information content. A shorter prompt that omits key information will naturally use fewer tokens.
**Why it happens:** Compression and information loss are intertwined.
**How to avoid:** Use semantic equivalence as a constraint -- all format variants must encode the same information. Use BERTScore or manual verification.
**Warning signs:** Token reduction numbers without accuracy comparison.

### Pitfall 5: Overgeneralizing from Data Retrieval to Reasoning
**What goes wrong:** TOON's benchmarks (76.4% vs JSON's 75.0%) are on data retrieval tasks, not reasoning tasks like HumanEval or GSM8K.
**Why it happens:** TOON's sweet spot is tabular/uniform data, which differs from code generation prompts.
**How to avoid:** Note which findings come from which task types. Code generation, math reasoning, and data retrieval are different domains.
**Warning signs:** Citing TOON benchmarks as evidence for coding task improvements.

## Code Examples

No code is produced in this phase. However, here are reference patterns for the research document:

### Token Count Comparison Template
```python
# Quick prototype: compare token counts across formats
# (Optional -- only if running lightweight experiments)
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")  # cl100k_base

json_prompt = '{"task": "write a function", "language": "python", "constraints": ["O(n)", "no imports"]}'
toon_prompt = 'task: write a function\nlanguage: python\nconstraints:\n  - O(n)\n  - no imports'
xml_prompt = '<task>write a function</task>\n<language>python</language>\n<constraints>\n<c>O(n)</c>\n<c>no imports</c>\n</constraints>'

for name, prompt in [("JSON", json_prompt), ("TOON-like", toon_prompt), ("XML", xml_prompt)]:
    tokens = len(enc.encode(prompt))
    print(f"{name}: {tokens} tokens ({len(prompt)} chars)")
```

### Existing Intervention Integration Point
```python
# From src/config.py -- new formats would become new entries here
INTERVENTIONS: tuple[str, ...] = (
    "raw",
    "self_correct",
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "prompt_repetition",
    # Future: "format_toon", "format_xml_structured", "format_minimal", etc.
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain text prompts assumed neutral | Format shown to affect performance up to 40% | Nov 2024 (He et al.) | Must control for format in experiments |
| JSON as default structured format | TOON achieves 40% fewer tokens with comparable accuracy | 2025 | New option for structured data in prompts |
| Punctuation treated as formatting | Punctuation shown to serve as attention sinks and context memory | Feb 2025 (LLM-Microscope) | Removal may hurt, not help |
| Content-only prompt optimization | CFPO jointly optimizes content AND format | Feb 2025 | Format is a first-class optimization dimension |
| Aggressive token pruning (LLMLingua 20x) | Conservative 2-3x compression safest | 2025 surveys | Light compression is the sweet spot |

**Key papers for literature survey:**

| Paper | ArXiv ID | Key Finding | Relevance |
|-------|----------|-------------|-----------|
| He et al. "Does Prompt Formatting Have Any Impact on LLM Performance?" | 2411.10541 | Up to 40% variation; model-specific format preferences | Core -- establishes format matters |
| TOON Format | github.com/toon-format/toon | 76.4% accuracy vs JSON 75%, 40% fewer tokens | Core -- compact notation benchmark |
| CompactPrompt | 2510.18043 | 60% token reduction, <5% accuracy drop | Already in RDD as baseline |
| LLMLingua | 2310.05736 | Up to 20x compression via perplexity pruning | Compression baseline |
| LLM-Microscope | 2502.15007 | Punctuation carries context memory in transformers | Punctuation hypothesis |
| "When Punctuation Matters" | 2508.11383 | 8 models, 52 tasks; punctuation sensitivity is real | Punctuation hypothesis |
| Punctuation and Predicates | 2508.14067 | Model-specific punctuation necessity (GPT-2 vs DeepSeek vs Gemma) | Nuances punctuation finding |
| CFPO | 2502.04295 | Joint content+format optimization outperforms content-only | Novel approach |
| Li et al. Survey | 2410.12388 | Comprehensive prompt compression survey | Background |
| Lossless Meta-Tokens | 2506.00307 | 27% lossless compression via LZ77-like technique | Lossless alternative |
| ProCut | 2508.02053 | Shapley-value-based compression | Attribution-based approach |
| LLM-DCP | 2504.11004 | MDP-based dynamic compression, 17% over Selective Context | Dynamic approach |

## Open Questions

1. **TOON accuracy on reasoning tasks**
   - What we know: TOON outperforms JSON on data retrieval (76.4% vs 75.0%) across 4 models
   - What's unclear: Performance on code generation (HumanEval) and math reasoning (GSM8K) -- the benchmarks in our study
   - Recommendation: Flag as a HIGH priority hypothesis to test in Phase 11 with a small pilot

2. **Optimal format per model family**
   - What we know: He et al. showed format preferences differ by model with IoU < 0.2 between families
   - What's unclear: Whether Claude and Gemini specifically have known format preferences for coding/math tasks
   - Recommendation: Design experiments with per-model analysis; Anthropic docs recommend XML for Claude

3. **Punctuation removal: net positive or negative?**
   - What we know: Punctuation tokens serve as attention sinks (LLM-Microscope); removing them degrades MMLU
   - What's unclear: Whether this applies to the types of prompts in our benchmark (coding, math)
   - Recommendation: This is a genuinely uncertain hypothesis -- design as a controlled experiment, not an assumed benefit

4. **Interaction between noise and format**
   - What we know: Our paper studies noise. Format is a separate dimension. No paper studies both together.
   - What's unclear: Does structured formatting make prompts MORE robust to noise, or does noise break structure (making it worse)?
   - Recommendation: This is a potential NOVEL CONTRIBUTION -- the interaction of format x noise is unstudied

5. **Bullet/outline format for instructions vs prose**
   - What we know: Bullet formats generally outperform prose for option presentation; training data bias likely explains this
   - What's unclear: Effect size for our specific task types (coding instructions, math word problems)
   - Recommendation: Quick-win hypothesis -- easy to test, likely small but measurable effect

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | N/A -- this is a documentation phase |
| Config file | N/A |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements -> Test Map
This phase produces a research document, not code. Validation is through document review, not automated testing.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N/A | Research document completeness | manual-only | N/A -- review docs/prompt_format_research.md | N/A |
| N/A | Hypothesis specifications are complete | manual-only | N/A -- check each has: claim, variables, cost, priority | N/A |

### Sampling Rate
- **Per task commit:** Manual review of document sections
- **Per wave merge:** Full document review for completeness and internal consistency
- **Phase gate:** Document exists in docs/ with all required sections

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. No test files needed for a documentation phase.

## Sources

### Primary (HIGH confidence)
- ArXiv:2411.10541 (He et al.) - Prompt formatting impact on LLM performance, up to 40% variation
- ArXiv:2502.15007 (LLM-Microscope) - Punctuation as context memory carriers in transformers
- ArXiv:2508.11383 - When Punctuation Matters, large-scale robustness comparison
- ArXiv:2510.18043 (CompactPrompt) - 60% token reduction, <5% accuracy drop (already in RDD)
- ArXiv:2310.05736 (LLMLingua) - Foundational prompt compression, up to 20x
- github.com/toon-format/toon - TOON spec and benchmarks (76.4% vs JSON 75%, 40% fewer tokens)
- Anthropic official docs - XML tag prompting best practices for Claude

### Secondary (MEDIUM confidence)
- ArXiv:2502.04295 (CFPO) - Content-format integrated optimization
- ArXiv:2508.14067 - Punctuation and Predicates, model-specific punctuation roles
- ArXiv:2506.00307 (Lossless Meta-Tokens) - 27% lossless compression
- ArXiv:2508.02053 (ProCut) - Shapley-value attribution for compression
- ArXiv:2504.11004 (LLM-DCP) - MDP-based dynamic compression
- ArXiv:2410.12388 (Li et al. Survey) - Comprehensive prompt compression survey

### Tertiary (LOW confidence)
- Medium/blog posts on bullet vs prose performance - anecdotal, needs validation
- Dev.to post on line breaks and indentation in RAG - single study, narrow scope
- Community forum discussions on XML vs Markdown - practitioner experience, not controlled studies

## Metadata

**Confidence breakdown:**
- Literature survey: HIGH - Multiple ArXiv papers with clear findings, cross-verified
- TOON findings: MEDIUM - Benchmarks exist but on data retrieval, not reasoning tasks
- Punctuation findings: HIGH - Multiple independent studies confirm punctuation matters
- Format-x-noise interaction: LOW - Novel hypothesis, no existing research found
- Bullet vs prose: MEDIUM - Evidence exists but mainly for option presentation, not coding/math

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days -- field is moderately active but core findings are stable)
