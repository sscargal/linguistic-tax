# Phase 10: Research Optimal Prompt Input Formats for Whitepaper - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Investigate whether compact/structured prompt formats (analogous to TOON vs JSON) yield superior LLM reasoning results compared to verbose natural language. Produce a research document with testable hypotheses ranked by feasibility for whitepaper inclusion. This is a pure research phase — no code changes to the experiment suite.

</domain>

<decisions>
## Implementation Decisions

### Research scope and depth
- Literature survey of existing work on prompt format effects (TOON, CompactPrompt, structured prompting papers)
- Lightweight prototype experiments where feasible — quick manual tests to validate promising directions before committing to full experiment design
- Focus on formats that reduce tokens while maintaining or improving accuracy (aligns with the paper's "linguistic tax" thesis)

### Output format
- Structured research document in `docs/` with:
  - Literature findings organized by format category
  - Testable hypotheses ranked by feasibility and expected impact
  - Concrete experiment designs for the top hypotheses (ready for Phase 11 to pick up)
- Each hypothesis should specify: what to test, expected effect, how to measure, estimated API cost

### Format categories to investigate
- Cast a wide net across promising formats:
  - **TOON-like compact notation** — human-readable compressed syntax (the original motivation)
  - **XML/structured markup** — Claude and other models are known to handle XML well
  - **Bullet/outline formats** — stripped of prose, just key information
  - **Minimal punctuation** — does removing "fluff" punctuation (periods, commas in lists) affect results?
  - **Novel formats** — any new ideas discovered during literature review
- Compare against the existing verbose natural language baseline already in our experiment suite

### Integration with experiment suite
- Document findings as potential future intervention types only — do NOT modify existing `src/` code
- If a format shows strong promise, describe it as a candidate intervention for future phases
- Maintain separation: this phase produces knowledge, implementation phases produce code

### Claude's Discretion
- Exact structure and organization of the research document
- Which papers to prioritize in the literature survey
- How many prototype experiments to run (if any)
- Level of detail in experiment design proposals

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research Design
- `docs/RDD_Linguistic_Tax_v4.md` — The authoritative spec; defines existing intervention types, metrics, and the "prompt optimizer" concept that this research extends
- `docs/RDD_Linguistic_Tax_v4.md` §8 (Related Work) — Existing citations including CompactPrompt (60% token reduction) that directly relate to format optimization

### Existing Implementation
- `src/prompt_compressor.py` — Current sanitize/compress implementation; understanding what "compression" means today informs what new formats could improve
- `src/config.py` — Current intervention types and experiment matrix structure; new formats would need to fit this schema eventually

### Project Context
- `docs/research_program.md` — Karpathy-style instructions for autonomous research runs; may inform how prototype experiments should be structured

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/prompt_compressor.py`: Current compress/sanitize pipeline — new format interventions would follow this pattern
- `src/run_experiment.py`: Experiment harness with intervention routing — shows how new interventions would plug in
- `data/prompts.json`: 200 clean benchmark prompts available for any prototype testing

### Established Patterns
- Interventions are defined in `src/config.py` INTERVENTIONS tuple and routed via match/case in `run_experiment.py`
- Pre-processor calls use cheap models (Haiku/Flash) — any format conversion would follow this cost pattern
- All experiments log TTFT, TTLT, token counts, cost — format changes would show up in token reduction metrics

### Integration Points
- New format types would eventually become new entries in `INTERVENTIONS` tuple
- `compute_cost()` in config.py handles per-model pricing — format changes affect input token counts
- `analyze_results.py` GLMM analysis already handles intervention as a factor — new interventions slot in naturally

</code_context>

<specifics>
## Specific Ideas

- The original phase description mentions "TOON vs JSON" analogy — investigate TOON (Text Object-Oriented Notation) specifically as a compact alternative
- "Human-convention-friendly notation" is key — formats should be intuitive to write, not just machine-efficient
- The paper's thesis is about "linguistic tax" — format research should quantify how much of that tax comes from format verbosity vs content noise
- Phase 11 (micro-formatting questions) will pick up specific testable hypotheses from this research, so make them concrete and actionable

</specifics>

<deferred>
## Deferred Ideas

- Implementing new intervention types based on research findings — future phase after experimentation
- Modifying the experiment matrix to include new format conditions — requires RDD update first
- Running full-scale format comparison experiments — too costly for a research phase

</deferred>

---

*Phase: 10-research-optimal-prompt-input-formats-for-whitepaper*
*Context gathered: 2026-03-24*
