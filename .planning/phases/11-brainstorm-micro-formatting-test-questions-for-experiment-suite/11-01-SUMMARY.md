---
phase: 11-brainstorm-micro-formatting-test-questions-for-experiment-suite
plan: 01
subsystem: research
tags: [experiment-design, TOON, XML, bullet-format, atomic-questions, prompt-formatting]

# Dependency graph
requires:
  - phase: 10-research-optimal-prompt-input-formats-for-whitepaper
    provides: "6 hypotheses (H-FMT-01 through H-FMT-06) and literature survey in docs/prompt_format_research.md"
provides:
  - "7 atomic experiment specs for token efficiency (TOON compact, bullet/outline) in docs/experiments/token_efficiency.md"
  - "6 atomic experiment specs for structural markup (XML tags, hierarchy) in docs/experiments/structural_markup.md"
  - "13 total independently-executable experiment specs with cost estimates, pilot protocols, and tiering"
affects: [11-02, 11-03, experiment-execution, docs/experiments/README.md]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic experiment spec template with standardized fields (claim, variables, benchmarks, cost, pilot, tier)"
    - "Tiered execution plan (Tier 1 cheapest/highest signal first, Tier 2 conditional on Tier 1 results)"
    - "Bundled control conditions to avoid redundant API calls across experiments"

key-files:
  created:
    - docs/experiments/token_efficiency.md
    - docs/experiments/structural_markup.md
  modified: []

key-decisions:
  - "Rule-based format conversion as default (no LLM cost); LLM pre-processor only for AQ-TE-04 comparison experiment"
  - "20 prompts per question as default; noted statistical power limitation for effects below 5%"
  - "Free OpenRouter Nemotron as default model with explicit paid escalation criteria per spec"
  - "XML model escalation recommended immediately for AQ-SM-01 since hypothesis is model-specific"

patterns-established:
  - "AQ-{CLUSTER}-{NN} naming convention for atomic experiment questions"
  - "Standardized 18-field template for every atomic question ensuring independent executability"
  - "Bundling opportunity documentation to reduce redundant control condition runs"

requirements-completed: [MFMT-01, MFMT-04, MFMT-05]

# Metrics
duration: 6min
completed: 2026-03-24
---

# Phase 11 Plan 01: Token Efficiency and Structural Markup Experiment Specs Summary

**13 atomic experiment specs decomposing H-FMT-01 (TOON), H-FMT-02 (XML), and H-FMT-03 (bullet/outline) into independently-executable experiments with free OpenRouter defaults and tiered paid escalation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-24T19:50:51Z
- **Completed:** 2026-03-24T19:57:00Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- Created 7 atomic experiment specs for token efficiency (AQ-TE-01 through AQ-TE-07) covering TOON notation across HumanEval/MBPP/GSM8K and bullet/outline reformatting with telegraphic filler removal
- Created 6 atomic experiment specs for structural markup (AQ-SM-01 through AQ-SM-06) covering XML wrapping, parameter annotation, nested vs. flat hierarchy, overhead measurement, and markdown alternative
- Every spec includes concrete before/after conversion examples, pilot protocols with go/no-go criteria, and bundling opportunities to minimize redundant API calls
- Total free-tier API calls: 2,720; total paid escalation: 8,320 calls at $60-144 estimated

## Task Commits

Each task was committed atomically:

1. **Task 1: Create token_efficiency.md** - `9367d8a` (feat)
2. **Task 2: Create structural_markup.md** - `3a5c747` (feat)

## Files Created/Modified
- `docs/experiments/token_efficiency.md` - 7 atomic experiment specs for H-FMT-01 (TOON) and H-FMT-03 (bullet/outline) with summary table and model escalation strategy
- `docs/experiments/structural_markup.md` - 6 atomic experiment specs for H-FMT-02 (XML markup) with per-model analysis requirements and overhead measurement

## Decisions Made
- Used rule-based format conversion as default for all specs except AQ-TE-04 (which specifically tests LLM vs. rule-based conversion). This keeps initial experiment cost at $0 using free OpenRouter models.
- Set 20 prompts as default with explicit notes on statistical power limitations for small effects (< 5%). Suggested 40 prompts for borderline cases.
- Recommended immediate paid model escalation for AQ-SM-01 since the XML hypothesis is specifically about Claude vs. Gemini model-specific effects that cannot be tested on a single free model.
- Included AQ-SM-06 (markdown as lightweight XML alternative) even though it was not explicitly in H-FMT-02, because it provides a cost-efficiency comparison directly relevant to the structural markup question.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Token efficiency and structural markup experiment specs are complete and independently executable
- Plan 11-02 can proceed with punctuation/micro-formatting and format-noise interaction specs (H-FMT-04, H-FMT-05, H-FMT-06)
- Plan 11-03 can proceed with novel brainstormed hypotheses and the README index
- Control condition bundling opportunities documented for cross-plan efficiency

---
*Phase: 11-brainstorm-micro-formatting-test-questions-for-experiment-suite*
*Completed: 2026-03-24*
