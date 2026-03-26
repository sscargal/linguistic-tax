---
phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention
plan: 01
subsystem: infra
tags: [emphasis, formatting, text-conversion, regex, code-protection]

# Dependency graph
requires: []
provides:
  - "6 emphasis conversion functions (bold, caps, quotes, instruction_caps, instruction_bold, lowercase_initial)"
  - "Code block protection helper (_split_code_and_text)"
  - "Dual-schema cache loader for pre-computed emphasis variants"
  - "11 registered intervention types in INTERVENTIONS tuple"
  - "Emphasis routing in apply_intervention match/case"
affects: [22-02, 22-03, experiment-matrix-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [sentinel-replacement-for-overlapping-terms, code-block-protection-segments]

key-files:
  created:
    - src/emphasis_converter.py
    - tests/test_emphasis_converter.py
  modified:
    - src/config.py
    - src/run_experiment.py
    - tests/test_run_experiment.py
    - tests/test_config.py

key-decisions:
  - "Sentinel replacement strategy for key-term matching prevents double-replacement and handles overlapping terms"
  - "prompt_id parameter added to apply_intervention with default empty string for backward compatibility"
  - "Schema auto-detection in load_emphasis_variant checks if 'prompts' key values are dicts vs strings"

patterns-established:
  - "Code block protection: _split_code_and_text segments text, _apply_to_text_only applies transforms to non-code only"
  - "Emphasis cache files: cluster_a_{type}.json (flat) and cluster_b_variants.json (nested with metadata)"

requirements-completed: [INFRA]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 22 Plan 01: Emphasis Infrastructure Summary

**6 emphasis conversion functions with code-block protection, dual-schema cache loader, and full routing through apply_intervention**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T20:31:35Z
- **Completed:** 2026-03-26T20:34:35Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created emphasis_converter.py with all 6 conversion functions and code-block protection
- Registered 6 new emphasis intervention types in config.py INTERVENTIONS (now 11 total)
- Wired emphasis routing in run_experiment.py apply_intervention with backward-compatible prompt_id parameter
- 91 tests passing across emphasis_converter, run_experiment, and config modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create emphasis_converter.py module with all 6 conversion functions and tests** - `726065a` (feat, TDD)
2. **Task 2: Register emphasis interventions in config.py and wire routing in run_experiment.py** - `4b5c935` (feat)

## Files Created/Modified
- `src/emphasis_converter.py` - All 6 conversion functions, code-block protection, sentinel replacement, dual-schema cache loader
- `tests/test_emphasis_converter.py` - 34 tests covering all functions, code protection, overlapping terms, cache schemas
- `src/config.py` - INTERVENTIONS tuple expanded from 5 to 11 entries
- `src/run_experiment.py` - Import emphasis_converter, add prompt_id param, 6 new match/case branches
- `tests/test_run_experiment.py` - 6 new emphasis routing tests
- `tests/test_config.py` - Updated assertion for 11 interventions

## Decisions Made
- Sentinel replacement strategy for key-term matching: replaces longest terms first with null-byte sentinels, then substitutes formatted versions to prevent double-replacement
- Added prompt_id parameter to apply_intervention with default empty string for backward compatibility (no existing callers broken)
- Schema auto-detection in load_emphasis_variant checks if "prompts" key exists and its values are dicts (nested) vs strings (flat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_config.py assertion for INTERVENTIONS count**
- **Found during:** Task 2
- **Issue:** test_interventions_count asserted len(INTERVENTIONS) == 5, but we added 6 new entries making it 11
- **Fix:** Updated assertion to == 11 and added 6 emphasis entries to expected set
- **Files modified:** tests/test_config.py
- **Verification:** pytest tests/test_config.py passes
- **Committed in:** 4b5c935 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test assertion update necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 emphasis conversion functions ready for use by Plans 02 and 03
- Emphasis routing wired and tested; experiment matrix generation can proceed
- Cache loader supports both flat (Cluster A) and nested (Cluster B) JSON schemas

---
*Phase: 22-experiment-all-caps-and-emphasis-formatting-effects-on-llm-attention*
*Completed: 2026-03-26*
