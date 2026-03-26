# Phase 22: Experiment: All-Caps and Emphasis Formatting Effects on LLM Attention - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement and run experiments testing whether all-caps words, bold/markdown emphasis, and capitalization patterns affect LLM attention and instruction-following accuracy. Covers three experiment clusters: (1) key-term emphasis markers (bold, CAPS, quotes) per AQ-NH-05, (2) instruction-word emphasis ("WILL" vs "will", "DO NOT" vs "do not"), and (3) sentence-initial capitalization effects. This is a code + execution phase -- builds new intervention types and runs the experiments.

</domain>

<decisions>
## Implementation Decisions

### Experiment scope
- Extend beyond AQ-NH-05 to cover ALL test cases from the phase goal:
  - **Cluster A (AQ-NH-05):** Key-term emphasis -- bold, CAPS, quotes on function names, return types, constraints
  - **Cluster B (new):** Instruction-word emphasis -- "WILL" vs "will", "DO NOT" vs "do not" vs "**do not**" vs "Do **not**"
  - **Cluster C (new):** Sentence-initial capitalization effects -- whether capitalizing the first word of instructions affects compliance
- Each cluster is independently executable with its own pilot protocol
- AQ-NH-05 design (20 prompts, 4 conditions, 5 reps) serves as the template for new clusters

### Implementation approach
- Add new intervention types to config.py INTERVENTIONS tuple (e.g., "emphasis_bold", "emphasis_caps", "emphasis_quotes", "emphasis_instruction_caps")
- Route through existing run_experiment.py intervention dispatch
- Prompt conversion functions live in a new module or extend prompt_compressor.py
- Results flow through existing analysis pipeline (analyze_results.py, compute_derived.py) without changes

### Prompt conversion method
- **Cluster A (key-term emphasis):** Semi-manual key-term identification for 20 HumanEval/MBPP prompts, then automated application of bold/CAPS/quotes markers per AQ-NH-05 conversion rules
- **Cluster B (instruction emphasis):** Regex-based automated conversion -- identify instruction verbs and negation patterns, apply CAPS/bold transformations
- **Cluster C (sentence-initial caps):** Regex-based -- lowercase first word of sentences, compare against original capitalized form
- Store converted prompts as JSON alongside originals for reproducibility

### Results integration
- Store all results in existing results.db with new intervention type entries
- Enables cross-experiment analysis with existing noise/intervention results
- Use existing McNemar's test, bootstrap CI, and per-model analysis patterns
- Free OpenRouter models first (per docs/experiments/README.md model strategy), escalate to paid if results show signal

### Claude's Discretion
- Exact prompt selection criteria within each cluster
- Whether Cluster B and C deserve separate modules or can share conversion logic
- Tier assignment for new clusters (Cluster A is Tier 2 per AQ-NH-05; new clusters TBD)
- Number of prompts for new clusters (likely 20 to match AQ-NH-05)
- Specific statistical thresholds for go/no-go pilot decisions on new clusters

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experiment Design (PRIMARY)
- `docs/experiments/novel_hypotheses.md` -- AQ-NH-05 emphasis markers experiment spec (lines 275-343): independent variables, conversion rules, concrete examples, statistical analysis, pilot protocol
- `docs/experiments/README.md` -- Master index of all 31 atomic experiments, tiered execution plan, model strategy, bundling opportunities

### Research Design
- `docs/RDD_Linguistic_Tax_v4.md` -- Authoritative spec for experimental parameters, metrics, reproducibility requirements (fixed seeds, temperature=0.0, 5 repetitions)
- `docs/prompt_format_research.md` -- Literature survey from Phase 10; context on format effects being model-specific and task-dependent

### Existing Implementation
- `src/config.py` -- INTERVENTIONS tuple, ModelRegistry integration, ExperimentConfig -- where new intervention types get registered
- `src/run_experiment.py` -- Experiment harness with intervention routing -- where new intervention dispatch logic goes
- `src/prompt_compressor.py` -- Existing pre-processor pattern (callable injection via call_fn) -- template for emphasis conversion functions
- `src/noise_generator.py` -- Noise injection patterns relevant if testing emphasis x noise interactions
- `data/prompts.json` -- 200 clean benchmark prompts (HumanEval, MBPP, GSM8K) -- source for prompt selection

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py` INTERVENTIONS tuple: New emphasis types become new entries (e.g., "emphasis_bold", "emphasis_caps")
- `src/prompt_compressor.py`: Callable injection pattern (call_fn parameter) -- emphasis conversion functions follow this model
- `src/run_experiment.py`: match/case intervention routing -- add new cases for emphasis interventions
- `data/prompts.json`: 200 clean prompts available; AQ-NH-05 specifies selecting 20 HumanEval+MBPP prompts with 3+ identifiable key terms
- `src/grade_results.py`: Existing grading (HumanEval sandbox, GSM8K regex) works unchanged for emphasis experiments
- `src/model_registry.py`: ModelRegistry handles model lookup for any configured provider

### Established Patterns
- Interventions registered in INTERVENTIONS tuple, routed via match/case in run_experiment.py
- Pre-processor calls use cheap models (per ModelRegistry preproc mapping) -- emphasis conversions may be regex-only (zero-cost)
- All experiments log TTFT, TTLT, token counts, cost -- emphasis changes show up in token metrics
- 5 repetitions per condition for CR measurement
- Free OpenRouter models as default for initial experiments

### Integration Points
- New intervention types -> INTERVENTIONS tuple in config.py
- Emphasis conversion functions -> new module or extension of prompt_compressor.py
- Analysis pipeline (GLMM, McNemar's, bootstrap) handles new interventions without code changes
- Pilot infrastructure (src/pilot.py) can run emphasis experiments with --model flag
- compute_derived.py CR calculation and cost rollups apply identically

</code_context>

<specifics>
## Specific Ideas

- Phase goal specifically lists these test cases: "WILL" vs "will", "DO NOT" vs "**do not**" vs "Do **not**", sentence-initial capitalization effects -- all three must be covered
- AQ-NH-05 already has concrete conversion rules and examples -- follow these as the template
- The "shouting" confound hypothesis (CAPS associated with urgency in training data) is explicitly worth testing -- could be a negative result that's still publishable
- Per Phase 11 context, emphasis markers were listed under "Structural markers" brainstorming category alongside separator lines and bullet variations

</specifics>

<deferred>
## Deferred Ideas

- Emphasis x noise interaction (combining emphasis with Type A/B noise) -- would require H-FMT-05 interaction framework, too complex for initial emphasis experiments
- Unicode emphasis variants (italic via Unicode math symbols, underline via combining characters) -- interesting but niche
- Emphasis in system prompts vs user prompts -- different positioning effects are a separate experiment

</deferred>

---

*Phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention*
*Context gathered: 2026-03-26*
