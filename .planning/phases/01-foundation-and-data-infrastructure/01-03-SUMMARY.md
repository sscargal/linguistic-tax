---
phase: 01-foundation-and-data-infrastructure
plan: 03
subsystem: database
tags: [huggingface, datasets, benchmark-curation, experiment-matrix, humaneval, mbpp, gsm8k]

# Dependency graph
requires:
  - phase: 01-foundation-and-data-infrastructure/plan-01
    provides: ExperimentConfig, NOISE_TYPES, INTERVENTIONS, MODELS constants
provides:
  - 200 curated benchmark prompts in data/prompts.json
  - 82,000-item experiment matrix in data/experiment_matrix.json
  - Curation script (scripts/curate_prompts.py)
  - Matrix generation script (scripts/generate_matrix.py)
affects: [02-noise-generation, 03-api-integration, 04-pilot-experiment]

# Tech tracking
tech-stack:
  added: [datasets (HuggingFace)]
  patterns: [deterministic sampling with random.Random(seed), self-contained work items]

key-files:
  created:
    - scripts/curate_prompts.py
    - scripts/generate_matrix.py
    - data/prompts.json
    - data/experiment_matrix.json
    - tests/test_prompts.py
    - tests/test_matrix.py
  modified: []

key-decisions:
  - "Used random.Random(42) for isolated deterministic sampling across all three benchmarks"
  - "Full factorial matrix of 82,000 items rather than RDD's ~20,000 approximation for complete coverage"
  - "GSM8K prompts use dataset index as problem_id with SHA-256 question hash for dedup verification"

patterns-established:
  - "Curation scripts in scripts/ directory for one-time data generation tasks"
  - "Self-contained work items with status field for progress tracking"

requirements-completed: [DATA-01, DATA-02]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 01 Plan 03: Prompt Curation and Experiment Matrix Summary

**200 benchmark prompts curated from HumanEval/MBPP/GSM8K via HuggingFace datasets, plus 82,000-item experiment matrix covering all noise x intervention x model x repetition combinations**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T22:36:50Z
- **Completed:** 2026-03-19T22:40:21Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Curated 200 benchmark prompts (67 HumanEval + 67 MBPP + 66 GSM8K) with canonical answers and test code
- Generated 82,000 self-contained work items: 80,000 for Experiment 1 (noise recovery) + 2,000 for Experiment 2 (compression study)
- All 24 validation tests passing across both test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create prompt curation script and curate 200 benchmark prompts** - `52f9ae4` (feat)
2. **Task 2: Generate experiment matrix (RED)** - `2b8b209` (test)
3. **Task 2: Generate experiment matrix (GREEN)** - `3be3625` (feat)

## Files Created/Modified
- `scripts/curate_prompts.py` - Downloads and samples 200 prompts from HuggingFace with fixed seed
- `scripts/generate_matrix.py` - Materializes full factorial experiment matrix from config constants
- `data/prompts.json` - 200 curated benchmark prompts with canonical answers
- `data/experiment_matrix.json` - 82,000 self-contained work items with status="pending"
- `tests/test_prompts.py` - 11 validation tests for prompt curation
- `tests/test_matrix.py` - 13 validation tests for experiment matrix

## Decisions Made
- Used `random.Random(42)` instance (not global `random.seed()`) for isolated deterministic sampling
- Full factorial matrix yields 82,000 items (200x8x5x2x5 + 200x1x1x2x5) rather than RDD's ~20,000 approximation, which undercounts by not including all intervention combinations
- GSM8K problem_ids use original dataset index (`gsm8k_{idx}`) with a question_hash field for deduplication verification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- data/prompts.json provides the 200 prompts needed by noise generators (Phase 01 Plan 02)
- data/experiment_matrix.json provides the complete work item list for the experiment harness (Phase 03)
- Config constants (NOISE_TYPES, INTERVENTIONS, MODELS) are imported and validated against the matrix

---
*Phase: 01-foundation-and-data-infrastructure*
*Completed: 2026-03-19*
