# Phase 11: Brainstorm Micro-Formatting Test Questions for Experiment Suite - Research

**Researched:** 2026-03-24
**Domain:** Experiment design for micro-formatting effects on LLM reasoning
**Confidence:** HIGH

## Summary

Phase 11 is a pure research/design phase that produces no code changes. The deliverable is a set of markdown documents in `docs/experiments/` containing atomic, self-contained experiment specifications for micro-formatting hypotheses. The work builds on Phase 10's 6 hypotheses (H-FMT-01 through H-FMT-06) by decomposing them into the smallest testable units, AND brainstorms new micro-formatting ideas across 4 categories (whitespace/layout, code-specific formatting, instruction phrasing, structural markers).

The research landscape for this phase is well-established. Multiple 2024-2025 papers provide empirical evidence on formatting effects: He et al. (ArXiv:2411.10541) demonstrated up to 40% performance variation from format alone; Pan et al. (ArXiv:2508.13666) showed 24.5% input token reduction from removing code formatting with negligible accuracy loss; three politeness studies (ArXiv:2510.04950, ArXiv:2512.12812, ArXiv:2402.14531) show conflicting but measurable tone effects; and three punctuation papers confirm punctuation's functional role as attention sinks. The existing experiment infrastructure (run_experiment.py, grade_results.py, analyze_results.py) handles new format interventions without code changes to the analysis pipeline.

**Primary recommendation:** Organize experiment specs into 6 topic-cluster files as specified in CONTEXT.md, with each atomic question containing a fully self-contained experiment spec (claim, variables, benchmarks, sample size, cost estimate, pilot protocol, success criteria). Use free OpenRouter Nemotron models as the default for initial experiments, with tiered escalation to paid models.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Build test questions for ALL 6 hypotheses from Phase 10 (H-FMT-01 through H-FMT-06)
- Actively brainstorm NEW micro-formatting ideas beyond Phase 10's list
- New brainstorming covers 4 categories: whitespace/layout, code-specific formatting, instruction phrasing, structural markers
- Top 3-5 new ideas get full hypothesis specs (claim, variables, sample size, cost, pilot protocol)
- Remaining new ideas captured as structured research notes for future work
- Primary deliverable: research documents in `docs/` -- pure research, no code changes
- Split into multiple files organized by topic cluster:
  - `docs/experiments/token_efficiency.md` -- TOON compact, bullet/outline (H-FMT-01, H-FMT-03)
  - `docs/experiments/structural_markup.md` -- XML structured markup (H-FMT-02)
  - `docs/experiments/punctuation_micro.md` -- punctuation removal, question marks (H-FMT-04, H-FMT-06)
  - `docs/experiments/format_noise_interaction.md` -- format x noise (H-FMT-05)
  - `docs/experiments/novel_hypotheses.md` -- all new brainstormed ideas with specs
  - `docs/experiments/README.md` -- index/overview with tiered execution plan
- Separate from `docs/prompt_format_research.md` (Phase 10's literature survey stays clean)
- Break each hypothesis into the smallest testable atomic unit
- Each atomic question gets its own fully independent experiment spec
- Per-question benchmark selection based on what the formatting change targets
- No cap on total question count
- No hard budget ceiling -- prioritize by scientific value with cost estimates
- Tiered execution plan: Tier 1 (cheapest, highest signal), Tier 2 (run if T1 interesting), Tier 3 (stretch)
- H-FMT-05 (format x noise, 2,400 calls): include with micro-pilot gate (60-call micro-pilot first)
- Model strategy: use FREE OpenRouter models first; escalate to paid models if results show promise
- Specific brainstormed ideas enumerated in CONTEXT.md decisions section

### Claude's Discretion
- Exact grouping of atomic questions into topic cluster files
- Which brainstormed ideas merit full hypothesis specs vs. research notes
- Tier assignment for each question in the execution plan
- How many prompts per atomic question (likely 10-20 given free model usage)
- Specific OpenRouter free models to recommend for initial experiments

### Deferred Ideas (OUT OF SCOPE)
- Language/locale variations (British vs American spelling, date formats, number formats)
- Encoding and special characters (Unicode vs ASCII quotes, em-dashes vs hyphens)
- Implementing new intervention types (code is a future phase)
- Running the actual experiments (execution is a separate phase)
- Modifying experiment matrix or RDD (requires formal RDD update process)
</user_constraints>

## Standard Stack

This phase produces only markdown documents -- no libraries or code are needed.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown | N/A | Document format for experiment specs | Already used throughout docs/ |
| docs/experiments/ | N/A | New directory for experiment specs | Specified in CONTEXT.md |

### Reference Sources (for content, not installation)
| Source | Purpose | Confidence |
|--------|---------|------------|
| `docs/prompt_format_research.md` | Phase 10 hypotheses H-FMT-01 through H-FMT-06 | HIGH |
| `docs/RDD_Linguistic_Tax_v4.md` | Experimental parameters and metrics | HIGH |
| `src/config.py` | Current INTERVENTIONS, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP | HIGH |
| He et al. (ArXiv:2411.10541) | Format effects across models | HIGH |
| Pan et al. (ArXiv:2508.13666) | Code formatting token costs | HIGH |
| ArXiv:2510.04950, ArXiv:2512.12812, ArXiv:2402.14531 | Politeness effect studies | MEDIUM |

## Architecture Patterns

### Recommended Document Structure
```
docs/
  prompt_format_research.md          # Phase 10 (DO NOT MODIFY)
  experiments/
    README.md                        # Index + tiered execution plan
    token_efficiency.md              # H-FMT-01, H-FMT-03 atomic questions
    structural_markup.md             # H-FMT-02 atomic questions
    punctuation_micro.md             # H-FMT-04, H-FMT-06 atomic questions
    format_noise_interaction.md      # H-FMT-05 atomic questions
    novel_hypotheses.md              # New brainstormed ideas + specs
```

### Pattern 1: Atomic Experiment Spec Template

Every atomic question MUST follow this self-contained template so any experiment can be picked up and executed independently:

```markdown
### AQ-{CLUSTER}-{NN}: {Descriptive Name}

**Parent Hypothesis:** H-FMT-{XX} (or "Novel")
**Claim:** {One sentence, falsifiable}

**Independent Variable:** {What changes}
**Control Condition:** {Baseline}
**Treatment Condition:** {What is different}

**Dependent Variables:** Pass rate, [token count | CR | TTFT | cost]

**Benchmarks:** {Which of HumanEval, MBPP, GSM8K and why}
**Prompt Selection Criteria:** {How to select the N prompts}
**Prompt Count:** {N prompts}

**Models:** {Which models, starting with free OpenRouter}
**Repetitions:** 5 per condition
**Total API Calls:** {calculated}
**Estimated Cost:** ${X} (free models) / ${Y} (paid escalation)

**Format Conversion Method:**
- {Regex-based | LLM pre-processor | Manual}
- {Specific conversion instructions}

**Statistical Analysis:**
- Primary: {test}
- Secondary: {test}

**Success Criteria:** {What constitutes a positive/negative/null result}

**Pilot Protocol:** {N prompts first, go/no-go criteria}

**Tier:** {1 | 2 | 3}
**Bundling Opportunity:** {Can run alongside AQ-XXX to share control condition}
```

### Pattern 2: README Index with Tiered Execution Plan

The README.md should contain:
1. Overview of all experiment clusters
2. Summary table of ALL atomic questions with tier, cost, API calls
3. Tiered execution plan with cumulative costs per tier
4. Model escalation strategy (free -> paid)
5. Cross-cluster bundling opportunities (shared control conditions)

### Pattern 3: Hypothesis Decomposition

Each Phase 10 hypothesis should be decomposed by asking:
- Are there sub-variations that should be tested independently? (e.g., H-FMT-04 punctuation removal: periods vs commas vs semicolons separately)
- Does the hypothesis apply differently to different benchmarks? (e.g., code vs math)
- Does the hypothesis have model-specific predictions? (e.g., XML for Claude vs Gemini)
- Can the hypothesis be tested at multiple intensity levels? (e.g., partial vs full punctuation removal)

### Anti-Patterns to Avoid
- **Monolithic experiment specs:** Each atomic question must be independently executable. Do not write specs that require running other experiments first (except H-FMT-05 which explicitly requires format x noise interaction).
- **Vague conversion methods:** Every spec must include concrete conversion instructions (regex patterns, LLM prompt text, or manual transformation rules). "Convert to bullet format" is too vague; "Extract key-value pairs, one per line, strip prose connectors, prefix each with dash" is concrete.
- **Assumed model behavior:** Do not assume format X helps model Y without citing evidence. State expected effects as hypotheses, not predictions.
- **Ignoring token overhead:** XML and structured formats ADD tokens. Every spec must account for token overhead in cost estimates and include it as a measured variable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Experiment spec format | Ad hoc varying formats per question | Standardized atomic template above | Consistency enables automated extraction later |
| Cost estimation | Rough guesses | Calculate from PRICE_TABLE in config.py | Free models = $0/call, paid = known rates |
| Statistical test selection | Invent new tests | McNemar's (paired), GLMM (multi-factor), bootstrap CIs | Already implemented in analyze_results.py |
| Prompt selection criteria | Random sampling | Criterion-based selection from data/prompts.json | Different formatting changes target different prompt types |

## Common Pitfalls

### Pitfall 1: Confounding Data Format with Instruction Format
**What goes wrong:** Mixing up "reformatting the data/context within a prompt" (e.g., JSON to TOON) with "reformatting the instruction itself" (e.g., prose to bullets). These are separate optimization dimensions with different evidence bases.
**Why it happens:** Both are "formatting changes" but operate on different parts of the prompt.
**How to avoid:** Each atomic question must specify exactly which part of the prompt is being reformatted: data/context, instruction text, structural markers, or the entire prompt.
**Warning signs:** A spec says "reformat the prompt" without specifying which component.

### Pitfall 2: Ignoring Tokenizer Differences
**What goes wrong:** Assuming all models tokenize the same formatting characters identically. Bullet characters (*, -, +), whitespace, and special markers tokenize differently across BPE tokenizers.
**Why it happens:** We think in characters but models think in tokens.
**How to avoid:** For micro-formatting questions like bullet character variation, note that the token count may differ between * and - and + even though they look equivalent to humans. This is actually a feature -- it makes them worth testing.
**Warning signs:** Assuming "these are equivalent changes" without checking tokenization.

### Pitfall 3: Statistical Power with Small Samples
**What goes wrong:** Running 10-20 prompts and expecting to detect a 2% effect size. With 20 prompts and 5 reps, McNemar's test has limited power for small effects.
**Why it happens:** Free models encourage running more experiments but with fewer prompts each.
**How to avoid:** Explicitly state the minimum detectable effect size for each atomic question's sample size. For 20-prompt experiments, effects below 10% absolute difference are unlikely to reach significance. Questions expecting <5% effects (like H-FMT-06 question marks) should note this limitation and specify larger sample sizes or bundling strategies.
**Warning signs:** Expected effect is "1-2%" but sample size is 20 prompts.

### Pitfall 4: Format Conversion Artifacts
**What goes wrong:** LLM-based format conversion (TOON, XML, bullets) introduces semantic changes alongside formatting changes, confounding the results.
**Why it happens:** When you ask a cheap model to "reformat this prompt," it may also rephrase, add, or remove content.
**How to avoid:** Every LLM-based conversion spec must include: (a) explicit instruction to preserve all semantic content, (b) manual review protocol for a subset of converted prompts, (c) a "semantic equivalence check" step in the pilot.
**Warning signs:** Converted prompt has different word count or information content than the original.

### Pitfall 5: TOON Format Mismatch
**What goes wrong:** Applying TOON-style compact notation to prompts that lack structured data. TOON's sweet spot is tabular/uniform data (key-value pairs, parameter lists), not free-text instructions.
**Why it happens:** Enthusiasm about 40% token reduction leads to applying TOON everywhere.
**How to avoid:** TOON atomic questions must specify prompt selection criteria that filter for prompts with structured data (parameter descriptions, input/output specs, constraint lists).
**Warning signs:** Applying TOON conversion to a GSM8K word problem narrative.

### Pitfall 6: Free Model Quality Floor
**What goes wrong:** Free OpenRouter models (Nemotron) may have a lower baseline accuracy than paid models, making format effects harder to detect or non-representative.
**Why it happens:** Free models are smaller/cheaper for a reason -- they may not be sensitive to the same formatting nuances as frontier models.
**How to avoid:** The tiered model strategy handles this: run on free models first, but interpret null results cautiously. A null result on Nemotron does not mean the effect does not exist on Claude/GPT-4o. Include a "model escalation" criterion in each spec: "If effect is null on free models, escalate to paid models before concluding."
**Warning signs:** Concluding "formatting does not matter" based solely on free model results.

## Code Examples

No code is produced in this phase. The following are reference patterns for experiment spec content:

### Regex-Based Punctuation Removal (for H-FMT-04 specs)
```python
# Reference: this pattern would be implemented in a future phase
# Included here so specs can reference concrete conversion logic
import re

def remove_optional_punctuation(text: str) -> str:
    """Remove periods, commas, semicolons from prose while preserving code blocks."""
    # Preserve code blocks
    code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
    placeholders = {}
    for i, block in enumerate(code_blocks):
        ph = f"__CODE_BLOCK_{i}__"
        placeholders[ph] = block
        text = text.replace(block, ph)

    # Remove trailing periods from sentences (not decimals)
    text = re.sub(r'(?<=[a-zA-Z])\.\s', ' ', text)
    # Remove commas in prose (not in numbers like 1,000)
    text = re.sub(r'(?<=[a-zA-Z]),\s', ' ', text)
    # Remove semicolons
    text = re.sub(r';\s', ' ', text)

    # Restore code blocks
    for ph, block in placeholders.items():
        text = text.replace(ph, block)
    return text
```

### Free OpenRouter Model Configuration (for cost estimates)
```python
# From src/config.py -- free models for initial experiments
# Primary: nemotron-3-super-120b-a12b:free (ranked 5th for coding on OpenRouter)
# Pre-proc: nemotron-3-nano-30b-a3b:free
# Both have $0.00/1M token pricing
# Both have 1M token context window
# Rate limit delay: 0.5s per call
```

## State of the Art

### Relevant Recent Papers for New Brainstormed Ideas

| Topic | Paper | Key Finding | Relevance to Phase 11 |
|-------|-------|-------------|----------------------|
| Code formatting tokens | Pan et al. (ArXiv:2508.13666), 2025 | 24.5% avg token reduction from removing indentation/whitespace/newlines, <1% accuracy change on code completion | Directly supports whitespace/indentation atomic questions |
| Politeness effects | ArXiv:2510.04950, 2025 | Impolite prompts outperform polite on GPT-4o (80.8% vs 84.8%); contradicts earlier studies | Supports "please/thank you" and politeness atomic questions |
| Politeness cross-lingual | ArXiv:2402.14531, 2024 | Best politeness level varies by language; impolite often poor | Adds nuance: effect is model- and language-dependent |
| Tone and accuracy | ArXiv:2512.12812, 2025 | Neutral/friendly prompts generally yield higher accuracy than rude; effect is model-dependent | Confirms politeness is testable but results will vary |
| Format x model interaction | He et al. (ArXiv:2411.10541), 2024 | IoU < 0.2 between model format preferences; up to 40% perf variation | Every format experiment must be per-model |
| Markdown structure | Multiple sources, 2025 | Markdown headers/lists help LLMs parse content; 34% higher retrieval accuracy | Supports structural marker atomic questions |

### Key Insight for New Hypotheses

The code formatting paper (Pan et al.) is the strongest evidence for several whitespace/layout brainstormed ideas. It found:
- Claude-3.7 performance varies by less than 1% when whitespace or indentation removed
- GPT-4o shows minimal fluctuations averaging 0.8%
- Newlines are the biggest token contributor for Claude and Gemini
- Java shows highest gains (34.9% reduction) due to verbose syntax

This suggests that for our code-focused benchmarks (HumanEval, MBPP), whitespace/indentation removal is likely a "free" token saving with no accuracy cost. This should be a Tier 1 experiment.

The politeness research is more conflicted. Three papers disagree on whether polite or impolite prompts perform better, but all agree the effect exists and is model-dependent. This makes politeness a good Tier 2 experiment -- interesting scientifically but lower confidence in the expected direction.

## Open Questions

1. **Free model sensitivity to micro-formatting**
   - What we know: Nemotron-3-Super ranks 5th for coding on OpenRouter; it has 120B params with 12B active (MoE)
   - What's unclear: Whether a MoE model with 12B active params is sensitive to the same micro-formatting effects that 200B+ frontier models show
   - Recommendation: Include in each spec a "model escalation" note -- if null on free models, test on paid before concluding

2. **Optimal prompt count for free model experiments**
   - What we know: Phase 10 specs used 20 prompts per experiment (matching pilot size); free models have 0.5s rate limit delay
   - What's unclear: Whether 20 prompts provides sufficient statistical power for small effects (<5%)
   - Recommendation: Use 20 prompts as baseline for Tier 1 experiments; consider 40 prompts for questions expecting small effects (budget is $0 for free models, only cost is time)

3. **Bundling strategy for shared control conditions**
   - What we know: Many atomic questions share the same control condition (original "raw" prompt)
   - What's unclear: Whether to run shared controls once and reuse, or run independently per experiment
   - Recommendation: Document bundling opportunities in README.md; recommend running shared controls once and flagging the shared data in specs

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `tests/conftest.py` (shared fixtures) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

Phase 11 is a pure documentation phase -- no code changes, no new test requirements. All deliverables are markdown files.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N/A | Markdown file creation | manual-only | Verify files exist in docs/experiments/ | N/A |
| N/A | Template compliance | manual-only | Review atomic question specs follow template | N/A |
| N/A | Completeness | manual-only | All 6 H-FMT hypotheses decomposed + new ideas | N/A |

### Sampling Rate
- **Per task commit:** Verify markdown files are well-formed and follow template
- **Per wave merge:** Review all specs for completeness and internal consistency
- **Phase gate:** All 6 files created in docs/experiments/, README.md has tiered plan

### Wave 0 Gaps
None -- this is a documentation-only phase with no test infrastructure requirements.

## Sources

### Primary (HIGH confidence)
- `docs/prompt_format_research.md` -- Phase 10 literature survey and 6 hypotheses (H-FMT-01 through H-FMT-06)
- `src/config.py` -- Current INTERVENTIONS, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, free model configs
- He et al. (ArXiv:2411.10541) -- Format effects across models, up to 40% variation, IoU < 0.2
- Pan et al. (ArXiv:2508.13666) -- Code formatting token costs: 24.5% reduction, <1% accuracy change
- LLM-Microscope (ArXiv:2502.15007) -- Punctuation as attention sinks
- "When Punctuation Matters" (ArXiv:2508.11383) -- Punctuation effects across 8 models, 52 tasks
- "Punctuation and Predicates" (ArXiv:2508.14067) -- Model-specific punctuation sensitivity

### Secondary (MEDIUM confidence)
- ArXiv:2510.04950 "Mind Your Tone" -- Politeness effects on GPT-4o (impolite > polite)
- ArXiv:2512.12812 "Does Tone Change the Answer?" -- Politeness across GPT, Gemini, LLaMA
- ArXiv:2402.14531 "Should We Respect LLMs?" -- Cross-lingual politeness study
- OpenRouter model pages for Nemotron-3-Super and Nemotron-3-Nano capability benchmarks

### Tertiary (LOW confidence)
- Practitioner blogs on markdown/bullet formatting improving LLM responses (multiple 2025 sources, not peer-reviewed)
- Role-framing ("you are an expert") -- established best practice but no rigorous 2025 study measuring effect size on coding benchmarks specifically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no libraries needed, pure documentation phase
- Architecture: HIGH -- document structure specified in CONTEXT.md, template pattern well-defined
- Pitfalls: HIGH -- drawn from Phase 10 research and verified literature
- New hypothesis content: MEDIUM -- brainstormed ideas have literature support but exact effect sizes on our benchmarks are unknown

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- formatting research moves slowly)
