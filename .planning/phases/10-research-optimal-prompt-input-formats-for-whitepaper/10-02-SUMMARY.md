---
phase: 10-research-optimal-prompt-input-formats-for-whitepaper
plan: 02
subsystem: docs
tags: [hypothesis-design, experiment-design, prompt-format, integration-notes]

# Dependency graph
requires:
  - phase: 10-research-optimal-prompt-input-formats-for-whitepaper
    provides: Literature survey of 6 format categories with 13 sources (Plan 01)
  - phase: 03-preprocessing-pipeline
    provides: Existing sanitize/compress pipeline pattern for format conversion
provides:
  - 6 testable hypotheses (H-FMT-01 through H-FMT-06) with full specifications
  - Detailed experiment designs for top 3 hypotheses ready for Phase 11
  - Integration notes mapping new formats to INTERVENTIONS tuple and analysis pipeline
  - Finalized executive summary with actual counts and findings
affects: [11-brainstorm-micro-formatting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hypothesis specification with claim, variables, cost, priority, supporting evidence, risks"
    - "Experiment designs include pilot protocol (5 prompts) before full 20-prompt run"
    - "Integration notes map research findings to existing config.py and analysis code"

key-files:
  created: []
  modified:
    - docs/prompt_format_research.md

key-decisions:
  - "Ranked H-FMT-01 (TOON), H-FMT-02 (XML), H-FMT-04 (punctuation) as HIGH priority for immediate pilot testing"
  - "Flagged H-FMT-05 (format x noise) as stretch goal due to 2,400-call cost but highest novelty value"
  - "H-FMT-04 uses regex-based conversion (zero preprocessing cost) while others use cheap model pre-processing"
  - "Total estimated cost for all 6 hypotheses: $28-64"

patterns-established:
  - "Experiment designs include pilot protocols with go/no-go criteria"
  - "Format interventions follow callable injection pattern from prompt_compressor.py"

requirements-completed: [FMT-RES-03, FMT-RES-04, FMT-RES-05]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 10 Plan 02: Testable Hypotheses and Experiment Designs Summary

**6 ranked hypotheses (H-FMT-01 through H-FMT-06) with full experiment designs for top 3, integration notes mapping to INTERVENTIONS tuple, and finalized executive summary**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T17:55:38Z
- **Completed:** 2026-03-24T17:59:38Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Wrote 6 testable hypotheses each with claim, independent/dependent variables, benchmarks, models, sample size, estimated cost, expected effect, measurement approach, supporting evidence, and risks/caveats
- Created detailed experiment designs for top 3 hypotheses (TOON compact, XML structured, punctuation removal) with prompt selection, conversion method, statistical analysis, success criteria, and pilot protocols
- Wrote integration notes connecting all hypotheses to existing config.py INTERVENTIONS tuple, prompt_compressor.py pre-processor pattern, and analyze_results.py GLMM infrastructure
- Finalized executive summary replacing placeholder with 3-paragraph synthesis of 13 sources, key findings, and proposed research program

## Task Commits

Each task was committed atomically:

1. **Task 1: Write testable hypotheses with experiment designs** - `06a883a` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `docs/prompt_format_research.md` - Complete research document with hypotheses, experiment designs, integration notes, and finalized executive summary

## Decisions Made
- Ranked H-FMT-01 (TOON compact notation), H-FMT-02 (XML structured markup), and H-FMT-04 (punctuation removal) as HIGH priority based on feasibility, cost, and evidence strength
- Flagged H-FMT-05 (format x noise interaction) as MEDIUM priority stretch goal -- highest novelty value but 2,400 API calls makes it expensive
- Designated H-FMT-04 as regex-based (zero preprocessing cost) while H-FMT-01/02/03 use cheap model pre-processing
- Recommended H-FMT-06 (question mark) be bundled with H-FMT-04 rather than standalone due to small expected effect size

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Research document is complete and ready for Phase 11 to pick up H-FMT-01 through H-FMT-04 as concrete micro-formatting test questions
- H-FMT-05 requires cost/benefit decision before committing to 2,400-call experiment
- All experiment designs include 5-prompt pilot protocols for feasibility validation before full runs

---
*Phase: 10-research-optimal-prompt-input-formats-for-whitepaper*
*Completed: 2026-03-24*
