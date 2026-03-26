---
phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention
plan: 02
subsystem: experiment-data
tags: [emphasis, bold, caps, quotes, humaneval, mbpp, experiment-matrix]

# Dependency graph
requires:
  - phase: 22-01
    provides: emphasis_converter module with apply_bold/caps/quotes functions and _replace_terms
provides:
  - 20 HumanEval/MBPP prompts with identified key terms (cluster_a_key_terms.json)
  - 3 emphasis variant JSON files (bold, caps, quotes) with 20 prompts each
  - 400-item experiment matrix for Cluster A (emphasis_matrix_a.json)
  - Reproducible generation script (generate_emphasis_cluster_a.py)
affects: [22-03, experiment-execution]

# Tech tracking
tech-stack:
  added: []
  patterns: [direct _replace_terms for indented docstring prompts]

key-files:
  created:
    - data/emphasis/cluster_a_key_terms.json
    - data/emphasis/cluster_a_bold.json
    - data/emphasis/cluster_a_caps.json
    - data/emphasis/cluster_a_quotes.json
    - data/emphasis_matrix_a.json
    - scripts/generate_emphasis_cluster_a.py
  modified: []

key-decisions:
  - "Natural-language key terms instead of function identifiers to avoid breaking code in def lines"
  - "Direct _replace_terms bypasses code-block protection for HumanEval indented docstrings"

patterns-established:
  - "Key term selection: use descriptive phrases from docstrings, not Python identifiers"
  - "Emphasis generation: _replace_terms directly when code protection is overcautious"

requirements-completed: [AQ-NH-05]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 22 Plan 02: Cluster A Data Generation Summary

**20 HumanEval/MBPP prompts with bold/CAPS/quotes emphasis variants and 400-item experiment matrix for AQ-NH-05**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T20:37:54Z
- **Completed:** 2026-03-26T20:42:35Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Selected 20 prompts (10 HumanEval + 10 MBPP) with 3 natural-language key terms each
- Generated 3 emphasis variant files (bold, caps, quotes) with verified key term application
- Created 400-item experiment matrix (20 prompts x 4 conditions x 5 repetitions)
- Built idempotent generation script for reproducibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Select 20 prompts and identify key terms, create generation script** - `71ed012` (feat)
2. **Task 2: Run generation script to produce variant JSONs and experiment matrix** - `e210bb0` (feat)

## Files Created/Modified
- `data/emphasis/cluster_a_key_terms.json` - 20 prompts with 3 key terms each (task description, return type, constraint)
- `data/emphasis/cluster_a_bold.json` - 20 prompts with **bold** emphasis on key terms
- `data/emphasis/cluster_a_caps.json` - 20 prompts with ALL CAPS emphasis on key terms
- `data/emphasis/cluster_a_quotes.json` - 20 prompts with 'quoted' key terms
- `data/emphasis_matrix_a.json` - 400-item experiment matrix for Cluster A
- `scripts/generate_emphasis_cluster_a.py` - Reproducible generation script

## Decisions Made
- Used natural-language descriptive terms from docstrings instead of Python function identifiers as key terms, because function names appear in `def` lines which are unindented code that the emphasis converter does not protect
- Used `_replace_terms` directly instead of `apply_*_emphasis` public API to bypass code-block protection, since HumanEval prompts have 4-space-indented docstrings that are incorrectly classified as code blocks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Key terms breaking function definition lines**
- **Found during:** Task 2 (running generation script)
- **Issue:** Original key terms included function names (e.g., `triangle_area`, `histogram`) which appeared in `def` lines. The emphasis converter's code-block protection does not cover unindented lines, so `def **triangle_area**(a, b, c):` was produced, breaking Python syntax.
- **Fix:** Replaced all function_name key terms with natural-language descriptive phrases from docstring text (e.g., "three sides" instead of "triangle_area"). Also switched from `apply_*_emphasis` to `_replace_terms` directly to handle 4-space-indented docstring text.
- **Files modified:** data/emphasis/cluster_a_key_terms.json, scripts/generate_emphasis_cluster_a.py
- **Verification:** All variants checked -- no `**` in def lines, all key terms correctly emphasized in docstrings
- **Committed in:** e210bb0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- without it, all HumanEval bold/caps/quotes variants would produce syntactically invalid Python code. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Cluster A data ready for experiment execution (Plan 03)
- Matrix has 400 items with model nvidia/nemotron-3-super-120b-a12b:free
- Variant files loadable via emphasis_converter.load_emphasis_variant()

---
*Phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention*
*Completed: 2026-03-26*
