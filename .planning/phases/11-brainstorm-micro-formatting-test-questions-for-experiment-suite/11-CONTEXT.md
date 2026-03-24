# Phase 11: Brainstorm Micro-Formatting Test Questions for Experiment Suite - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Design concrete, testable micro-formatting questions that explore how small formatting choices affect LLM reasoning accuracy and token efficiency. Build on Phase 10's 6 hypotheses (H-FMT-01 through H-FMT-06) by breaking them into atomic test questions, AND actively brainstorm new micro-formatting ideas across 4 categories (whitespace/layout, code-specific formatting, instruction phrasing, structural markers). Produce split research documents organized by topic cluster, with fully independent experiment specs for each atomic question. This is a pure research/design phase — no code changes.

</domain>

<decisions>
## Implementation Decisions

### Scope and hypothesis selection
- Build test questions for ALL 6 hypotheses from Phase 10 (H-FMT-01 through H-FMT-06)
- Actively brainstorm NEW micro-formatting ideas beyond Phase 10's list
- New brainstorming covers 4 categories: whitespace/layout, code-specific formatting, instruction phrasing, structural markers
- Top 3-5 new ideas get full hypothesis specs (claim, variables, sample size, cost, pilot protocol)
- Remaining new ideas captured as structured research notes for future work

### Output format and file organization
- Primary deliverable: research documents in `docs/` — pure research, no code changes
- Split into multiple files organized by topic cluster:
  - `docs/experiments/token_efficiency.md` — TOON compact, bullet/outline (H-FMT-01, H-FMT-03)
  - `docs/experiments/structural_markup.md` — XML structured markup (H-FMT-02)
  - `docs/experiments/punctuation_micro.md` — punctuation removal, question marks (H-FMT-04, H-FMT-06)
  - `docs/experiments/format_noise_interaction.md` — format x noise (H-FMT-05)
  - `docs/experiments/novel_hypotheses.md` — all new brainstormed ideas with specs
  - `docs/experiments/README.md` — index/overview with tiered execution plan
- Separate from `docs/prompt_format_research.md` (Phase 10's literature survey stays clean)

### Question granularity
- Break each hypothesis into the smallest testable atomic unit
- Each atomic question gets its own fully independent experiment spec (self-contained, can be picked up and run independently)
- Per-question benchmark selection — each question specifies which benchmarks (HumanEval, MBPP, GSM8K) apply based on what the formatting change targets
- No cap on total question count — brainstorm freely, let prioritization sort what gets run

### Budget and prioritization
- No hard budget ceiling — prioritize by scientific value, with cost estimates per question
- Tiered execution plan: Tier 1 (cheapest, highest signal, run first), Tier 2 (run if Tier 1 shows interesting results), Tier 3 (stretch goals)
- Each tier includes cumulative cost estimate
- H-FMT-05 (format x noise, 2,400 calls): include with micro-pilot gate — 60-call micro-pilot first, go/no-go decision before full experiment
- Model strategy: use FREE OpenRouter models for initial experiments; escalate to paid models (Claude, Gemini, GPT-4o) if results show promise; model provider/model selection is the researcher's decision

### New brainstormed micro-formatting ideas to design

**Whitespace and layout:**
- Newlines between sections (single vs double vs none)
- Indentation in code prompts (indented examples vs flat)
- Trailing whitespace/newlines after prompt
- Line length and wrapping (80-char wrap vs continuous line)

**Code-specific formatting:**
- Comment presence in code examples (with vs stripped)
- Docstring style (Google vs NumPy vs one-liner)
- Type hint verbosity (full annotations vs prose descriptions)
- Variable naming in examples (descriptive vs short vs single-letter)

**Instruction phrasing:**
- Imperative vs interrogative vs declarative ("Write..." vs "Can you write...?" vs "The function should...")
- Polite vs direct ("Please write..." vs "Write...")
- "Please" and "Thank you" — does politeness wording affect output?
- Explicit task framing / role-framing ("You are a Python expert. Write..." vs "Write...")
- Prompt length padding (minimal vs padded with context/caveats/encouragement)

**Structural markers:**
- Numbered vs bulleted vs unmarked lists
- Bullet character variation (* vs - vs +)
- Section headers (## Parameters, ## Returns) — present vs absent
- Emphasis markers (**bold**, CAPS, 'quotes') around key terms
- Separator lines (--- or ===) between sections

### Claude's Discretion
- Exact grouping of atomic questions into topic cluster files
- Which brainstormed ideas merit full hypothesis specs vs. research notes
- Tier assignment for each question in the execution plan
- How many prompts per atomic question (likely 10-20 given free model usage)
- Specific OpenRouter free models to recommend for initial experiments

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 10 Research Output
- `docs/prompt_format_research.md` — Literature survey, 6 hypotheses (H-FMT-01 through H-FMT-06), experiment designs for top 3, integration notes for the experiment framework
- `.planning/phases/10-research-optimal-prompt-input-formats-for-whitepaper/10-CONTEXT.md` — Phase 10 context with format categories and integration decisions

### Research Design
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for experimental parameters, metrics, and conditions
- `docs/RDD_Linguistic_Tax_v4.md` §8 (Related Work) — Existing citations on format optimization

### Existing Implementation (reference only — no code changes in this phase)
- `src/config.py` — Current INTERVENTIONS tuple, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP — shows how format experiments would eventually plug in
- `src/prompt_compressor.py` — Callable injection pattern for pre-processor-based format conversions
- `src/noise_generator.py` — Noise injection infrastructure relevant to H-FMT-05 (format x noise interaction)
- `src/run_experiment.py` — Experiment harness with intervention routing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py` INTERVENTIONS tuple: new format interventions would become new entries (e.g., "format_toon", "format_xml_structured", "format_no_punctuation")
- `src/prompt_compressor.py`: callable injection pattern (`call_fn` parameter) — LLM-based format conversions follow this pattern
- `src/noise_generator.py`: noise injection at 5/10/20% — directly used by H-FMT-05 format x noise experiments
- `data/prompts.json`: 200 clean benchmark prompts available for experiment design

### Established Patterns
- Pre-processor calls use cheap models (Haiku/Flash per PREPROC_MODEL_MAP) — LLM-based format conversions would follow this cost pattern
- Regex-based interventions (like H-FMT-04 punctuation removal) can be zero-cost by bypassing the pre-processor
- All experiments log TTFT, TTLT, token counts, cost — format changes show up in token metrics automatically
- 5 repetitions per condition for CR (consistency rate) measurement

### Integration Points
- New intervention types → entries in INTERVENTIONS tuple in config.py
- Analysis pipeline (analyze_results.py GLMM, McNemar's) handles new interventions without code changes
- compute_derived.py CR calculation and cost rollups apply to format experiments identically
- OpenRouter integration (Phase 9) enables free model usage for initial experiments

</code_context>

<specifics>
## Specific Ideas

- Phase 10 recommended H-FMT-06 (question mark) be bundled with H-FMT-04 (punctuation) rather than standalone — the atomic breakdown should still separate them but note the bundling opportunity
- Bullet character variation (* vs - vs +) was specifically requested — this is a true micro-formatting question where tokenizer behavior might differ
- "Please" and "Thank you" politeness markers were specifically called out as an interesting test — separate from general polite vs direct phrasing
- Language/locale variations (British vs American spelling, date formats, number formats) were flagged as important for the whitepaper but deferred to future work — NOT in Phase 11 scope
- Free OpenRouter models first, paid models only if results warrant — this significantly reduces experimentation cost and enables broader exploration

</specifics>

<deferred>
## Deferred Ideas

- **Language/locale variations** — British vs American spelling, date formats (MM/DD vs DD/MM), number formats (1,000 vs 1.000). Flagged as important whitepaper material. Add to TODO list for future phase.
- **Encoding and special characters** — Unicode vs ASCII quotes, em-dashes vs hyphens, smart quotes. Potentially interesting but not in Phase 11 scope.
- **Implementing new intervention types** — Phase 11 produces research/design only; code implementation is a future phase
- **Running the actual experiments** — Phase 11 designs experiments; execution is a separate phase
- **Modifying experiment matrix or RDD** — Requires formal RDD update process

</deferred>

---

*Phase: 11-brainstorm-micro-formatting-test-questions-for-experiment-suite*
*Context gathered: 2026-03-24*
