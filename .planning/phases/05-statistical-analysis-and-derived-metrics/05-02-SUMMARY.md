---
phase: 05-statistical-analysis-and-derived-metrics
plan: 02
subsystem: analysis
tags: [glmm, bootstrap, mcnemar, kendall-tau, bh-correction, sensitivity-analysis, effect-sizes, statsmodels, scipy]

# Dependency graph
requires:
  - phase: 01-project-foundation
    provides: SQLite schema (experiment_runs, derived_metrics tables), config constants
  - phase: 04-pilot-validation
    provides: Bootstrap CI BCa/percentile fallback pattern from pilot.py
  - phase: 05-statistical-analysis-and-derived-metrics
    provides: Plan 01 compute_derived.py (CR, quadrants, cost rollups), populated_test_db fixture
provides:
  - fit_glmm with three-level fallback chain (BayesMixedGLM -> reduced -> GEE)
  - compute_bootstrap_cis with BCa/percentile fallback for per-condition accuracy CIs
  - run_mcnemar_analysis for prompt-level fragile/recoverable classification
  - compute_kendall_tau for rank-order stability between clean and noisy conditions
  - apply_bh_correction per test-type family with raw and corrected p-values
  - run_sensitivity_analysis drops extreme prompts and reruns key analyses
  - generate_effect_size_summary table with OR, RD, Cohen's d, tau
  - CLI with subcommands: glmm, mcnemar, bootstrap, kendall, sensitivity, all
affects: [06-visualization, paper-tables]

# Tech tracking
tech-stack:
  added: []
  patterns: [glmm-fallback-chain, bca-percentile-bootstrap, mcnemar-paired-repetitions, bh-per-family-correction]

key-files:
  created:
    - src/analyze_results.py
    - tests/test_analyze_results.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Three-level GLMM fallback: BayesMixedGLM full -> reduced random effects -> GEE with exchangeable correlation"
  - "Explicit 2-way interactions in GLMM formula (not * operator) to avoid combinatorial explosion"
  - "McNemar pairs repetitions by repetition number for proper 2x2 contingency table construction"
  - "Approximate p-values for BayesMixedGLM via z-score from posterior mean/sd"

patterns-established:
  - "GLMM fallback chain: try full random effects, drop interactions, fall back to GEE"
  - "Bootstrap CI with BCa/percentile fallback pattern (matching pilot.py)"
  - "BH correction per test-type family: separate families for McNemar, GLMM, Kendall"
  - "Effect size summary table: OR, RD, Cohen's d, tau in unified DataFrame"

requirements-completed: [STAT-01, STAT-02, STAT-03, STAT-04, STAT-05]

# Metrics
duration: 6min
completed: 2026-03-23
---

# Phase 5 Plan 2: Statistical Analysis Summary

**GLMM with three-level fallback chain, bootstrap CIs, McNemar's fragility/recoverability, Kendall's tau, BH correction, sensitivity analysis, and effect size summary via analyze_results.py CLI**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T17:21:15Z
- **Completed:** 2026-03-23T17:27:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented GLMM fitting with explicit 2-way interactions and three-level fallback chain (BayesMixedGLM -> reduced random effects -> GEE)
- Bootstrap CIs with BCa/percentile fallback for per-condition accuracy metrics
- McNemar's test pairs repetitions to classify prompts as fragile (degrades under noise) or recoverable (improves with intervention)
- Kendall's tau-b measures rank-order stability between clean and noisy conditions
- BH FDR correction applied per test-type family, storing both raw and corrected p-values
- Sensitivity analysis drops hardest/easiest 10% of prompts and reruns GLMM + bootstrap
- Effect size summary table collects OR, RD, Cohen's d, and tau in unified CSV
- CLI with argparse subcommands (glmm, mcnemar, bootstrap, kendall, sensitivity, all) and JSON+CSV+terminal output

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold and synthetic data fixtures (TDD RED)** - `760fbbe` (test)
2. **Task 2: Implement analyze_results.py with full statistical analysis (TDD GREEN)** - `dacc3ec` (feat)

## Files Created/Modified
- `src/analyze_results.py` - GLMM, bootstrap, McNemar's, Kendall's tau, BH correction, sensitivity, effect sizes, CLI (9 public functions + helpers)
- `tests/test_analyze_results.py` - 14 unit tests covering all statistical methods
- `tests/conftest.py` - Added analysis_test_db (300 rows, 10 prompts) and degenerate_test_db (5 rows) fixtures

## Decisions Made
- Three-level GLMM fallback chain: BayesMixedGLM with full random effects -> reduced (drop prompt:model) -> GEE with exchangeable correlation. This handles both small datasets and convergence failures gracefully.
- Explicit 2-way interactions in GLMM formula using `:` notation instead of `*` operator to avoid combinatorial explosion of higher-order interaction terms.
- McNemar's test pairs runs by repetition number for proper 2x2 contingency table construction. Concordant prompts (b+c=0) are skipped.
- Approximate p-values for BayesMixedGLM posterior via z-scores from mean/sd (scipy.stats.norm). This is standard for variational Bayes results.
- Sensitivity analysis uses reduced bootstrap iterations (500) for speed since it is a robustness check, not primary analysis.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full statistical analysis pipeline ready for experiment data
- JSON/CSV outputs ready for Phase 6 visualization and paper tables
- Effect size summary CSV provides unified view of all effect measures
- All analyses can be run individually or together via CLI subcommands

---
*Phase: 05-statistical-analysis-and-derived-metrics*
*Completed: 2026-03-23*
