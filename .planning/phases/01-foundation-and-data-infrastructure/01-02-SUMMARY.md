---
phase: 01-foundation-and-data-infrastructure
plan: 02
subsystem: noise-generation
tags: [noise-injection, qwerty-adjacency, esl-patterns, determinism, cli, random-seed, regex]

# Dependency graph
requires:
  - phase: 01-01
    provides: "config.py with derive_seed function for deterministic seed computation"
provides:
  - "Type A character-level noise injection at 5/10/20% error rates"
  - "Type B ESL syntactic noise for Mandarin, Spanish, Japanese, and Mixed L1 sources"
  - "QWERTY adjacency map for adjacent key swap mutations"
  - "Keyword protection for Python keywords, function names, operators, numbers"
  - "CLI interface for both char and esl noise modes"
affects: [03-experiment-execution, 04-pilot-study]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Isolated random.Random(seed) instances for determinism"
    - "QWERTY 2D grid with row offsets for geometric neighbor computation"
    - "ESLPattern dataclass for rule-based L1 transfer error templates"
    - "Regex-based protected span identification before mutation pass"

key-files:
  created:
    - src/noise_generator.py
    - tests/test_noise_generator.py
  modified: []

key-decisions:
  - "Widened mutation count test tolerances to account for invisible mutations (transposition of identical chars, omission/doubling length effects)"
  - "Used single-pass regex protection with merged overlapping spans for efficiency"

patterns-established:
  - "TDD workflow: write failing tests first, implement to pass, commit separately"
  - "ESLPattern dataclass as extensible container for L1 transfer rules"

requirements-completed: [NOISE-01, NOISE-02, NOISE-03, NOISE-04]

# Metrics
duration: 4min
completed: 2026-03-19
---

# Phase 01 Plan 02: Noise Generator Summary

**Type A/B noise generators with QWERTY adjacency mutations, ESL L1 transfer patterns, keyword protection, and deterministic CLI interface**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-19T22:36:44Z
- **Completed:** 2026-03-19T22:41:08Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Type A noise generator with weighted mutations (40% adj swap, 25% omission, 20% doubling, 15% transposition) at 5/10/20% error rates
- Keyword protection preserving Python keywords, function names, operators, and numbers in numeric prompts
- Type B ESL noise with 17 total patterns across Mandarin (6), Spanish (6), and Japanese (5) L1 sources plus mixed mode
- CLI interface supporting both noise types with --input, --type, --rate, --l1, --seed, --output arguments
- Full determinism verified: same seed produces byte-identical output across multiple calls

## Task Commits

Each task was committed atomically:

1. **Task 1: Type A noise with keyword protection (RED)** - `1e65781` (test)
2. **Task 1: Type A noise with keyword protection (GREEN)** - `101d545` (feat)
3. **Task 2: Type B ESL noise and CLI (RED)** - `3be3625` (test)
4. **Task 2: Type B ESL noise and CLI (GREEN)** - `8607aa4` (feat)

## Files Created/Modified
- `src/noise_generator.py` (585 lines) - Type A + Type B noise injection with keyword protection, ESL patterns, and CLI
- `tests/test_noise_generator.py` (340 lines) - 30 tests covering adjacency map, mutation rates, determinism, keyword protection, ESL patterns, and CLI

## Decisions Made
- Widened mutation count test tolerances: identical-char transpositions produce no visible change, and omission/doubling create length differences that simple position-based comparison misses
- Used merged overlapping spans for protection to handle cases where regex patterns overlap (e.g., a function name that is also a keyword)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted test tolerances for mutation rate assertions**
- **Found during:** Task 1 (Type A noise implementation)
- **Issue:** Test expected ~20 visible mutations at 10% rate on uniform "aaa..." string, but transposition of identical chars produces invisible mutations, and omission/doubling create length effects not captured by position-based diff
- **Fix:** Changed test to count non-original characters plus length difference, with wider tolerance bands accounting for mutation invisibility
- **Files modified:** tests/test_noise_generator.py
- **Verification:** All 14 Type A tests pass with adjusted tolerances
- **Committed in:** 101d545

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test tolerance adjustment necessary for correctness. No scope change.

## Issues Encountered
None -- both tasks executed smoothly after tolerance adjustment.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Noise generators ready for integration with experiment execution (Phase 3)
- CLI enables manual testing and verification of noise patterns
- derive_seed properly imported from config.py maintaining single source of truth
- All 86 tests across the project pass

---
*Phase: 01-foundation-and-data-infrastructure*
*Completed: 2026-03-19*
