---
phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention
plan: 03
subsystem: experiment-data
tags: [emphasis, cluster-b, cluster-c, instruction-caps, mixed-emphasis, experiment-matrix]

# Dependency graph
requires:
  - phase: 22-01
    provides: "6 emphasis conversion functions, dual-schema cache loader, routing in apply_intervention"
provides:
  - "20 Cluster B prompts with 5 conditions (500-item matrix) for instruction emphasis"
  - "20 Cluster C prompts with 2 conditions (200-item matrix) for sentence-initial capitalization"
  - "2 new conversion functions: apply_mixed_emphasis, apply_aggressive_caps"
  - "13 registered intervention types in INTERVENTIONS tuple"
  - "Reproducible generation script for Clusters B and C"
  - "30 validation tests for generated data"
affects: [22-04-experiment-execution, experiment-analysis]

# Tech tracking
tech-stack:
  added: []
  patterns: [docstring-aware-code-block-detection, natural-language-extraction-for-prompt-selection]

key-files:
  created:
    - scripts/generate_emphasis_clusters_bc.py
    - data/emphasis/cluster_b_variants.json
    - data/emphasis/cluster_c_variants.json
    - data/emphasis_matrix_b.json
    - data/emphasis_matrix_c.json
    - tests/test_emphasis_clusters_bc.py
  modified:
    - src/emphasis_converter.py
    - src/config.py
    - src/run_experiment.py
    - tests/test_config.py

key-decisions:
  - "Docstring content treated as natural language, not code, for emphasis conversion (indented lines inside triple-quoted strings are not protected)"
  - "Cluster B selects HumanEval/MBPP prompts with most instruction verbs in docstrings; Cluster C selects all benchmarks with most sentence boundaries"
  - "apply_mixed_emphasis applies bold to negations first, then caps to all instruction verbs (resulting in bold+caps on negations)"
  - "apply_aggressive_caps uses broader word set (27 words) including compute, validate, ensure, check, etc."

patterns-established:
  - "Natural language extraction: _extract_natural_language parses docstrings and filters code lines for prompt analysis"
  - "Nested schema for multi-condition variants: {metadata: {...}, prompts: {id: {intervention: text}}}"

requirements-completed: [CLUSTER-B, CLUSTER-C]

# Metrics
duration: 7min
completed: 2026-03-26
---

# Phase 22 Plan 03: Cluster B/C Generation Summary

**20-prompt Cluster B with 5 instruction-emphasis conditions (500 matrix items) and 20-prompt Cluster C with 2 sentence-capitalization conditions (200 matrix items), plus docstring-aware code-block detection**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-26T20:37:55Z
- **Completed:** 2026-03-26T20:45:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Added apply_mixed_emphasis() and apply_aggressive_caps() to emphasis_converter.py
- Created reproducible generation script selecting prompts by instruction verb count and sentence count
- Generated Cluster B variants (20 prompts x 4 treatments) and Cluster C variants (20 prompts x 1 treatment)
- Generated experiment matrices: 500 items (Cluster B) + 200 items (Cluster C)
- Fixed _split_code_and_text to treat docstring content as natural language, not code
- All 121 tests passing across emphasis, config, run_experiment, and cluster validation modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create generation script, new conversion functions, config/routing updates** - `e463032` (feat)
2. **Task 2: Validation tests and docstring code-block detection fix** - `89dbe16` (test)

## Files Created/Modified
- `scripts/generate_emphasis_clusters_bc.py` - Reproducible generation script with smart prompt selection
- `data/emphasis/cluster_b_variants.json` - 20 prompts x 4 treatment variants (nested schema)
- `data/emphasis/cluster_c_variants.json` - 20 prompts x 1 treatment variant (nested schema)
- `data/emphasis_matrix_b.json` - 500-item experiment matrix for Cluster B
- `data/emphasis_matrix_c.json` - 200-item experiment matrix for Cluster C
- `tests/test_emphasis_clusters_bc.py` - 30 validation tests
- `src/emphasis_converter.py` - 2 new functions + docstring-aware _split_code_and_text
- `src/config.py` - INTERVENTIONS expanded to 13 entries
- `src/run_experiment.py` - Routing extended for emphasis_mixed and emphasis_aggressive_caps
- `tests/test_config.py` - Updated assertions for 13 interventions

## Decisions Made
- Docstring content is treated as natural language for emphasis conversion -- indented lines inside triple-quoted strings are NOT protected as code blocks. This is essential because HumanEval/MBPP prompts have all their natural language inside indented docstrings.
- apply_mixed_emphasis applies bold to negations first, then caps to instruction verbs; since caps runs second, negation text inside bold markers also gets uppercased (e.g., **DO NOT**)
- Cluster B prompt selection uses docstring extraction to count instruction verbs in natural language only, avoiding false matches on code `return` statements
- apply_aggressive_caps uses a 27-word vocabulary covering modal verbs, imperative verbs, and common programming task verbs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed docstring code-block detection in _split_code_and_text**
- **Found during:** Task 2 (validation testing)
- **Issue:** All HumanEval prompts have natural language in indented docstrings (4+ spaces), which _split_code_and_text classified as code blocks. This made all conversions produce output identical to the original.
- **Fix:** Added _DOCSTRING_RE pattern to detect triple-quoted strings; indented lines inside docstrings are no longer classified as code.
- **Files modified:** src/emphasis_converter.py
- **Verification:** All 34 existing emphasis_converter tests + 30 new cluster tests pass
- **Committed in:** 89dbe16 (Task 2 commit)

**2. [Rule 1 - Bug] Updated test_config.py for 13 interventions**
- **Found during:** Task 1 (config update)
- **Issue:** test_interventions_count asserted 11 but we added 2 new entries making it 13
- **Fix:** Updated assertion to == 13 and added emphasis_mixed, emphasis_aggressive_caps to expected set
- **Files modified:** tests/test_config.py
- **Committed in:** e463032 (Task 1 commit)

**3. [Rule 3 - Blocking] Fixed prompt selection to extract natural language from docstrings**
- **Found during:** Task 1 (generation script)
- **Issue:** Initial selection logic used _split_code_and_text which treated docstring content as code, resulting in only 1 Cluster B prompt selected instead of 20
- **Fix:** Created _extract_natural_language() that parses docstring content for instruction verb counting
- **Files modified:** scripts/generate_emphasis_clusters_bc.py
- **Committed in:** e463032 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All fixes necessary for correct data generation. The docstring detection fix is the most significant -- without it, the Cluster B variants would be identical to raw prompts.

## Issues Encountered
None beyond the auto-fixed deviations.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 3 experiment matrices ready: Cluster A (400), Cluster B (500), Cluster C (200) = 1,100 total items
- All 13 intervention types registered and routable
- Validation tests confirm data integrity and routing
- Ready for experiment execution phase

---
*Phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention*
*Completed: 2026-03-26*
