---
phase: 05-statistical-analysis-and-derived-metrics
verified: 2026-03-23T18:10:00Z
status: passed
score: 13/13 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 12/13
  gaps_closed:
    - "Bootstrap CIs are computed for CR values sourced from derived_metrics.consistency_rate column"
    - "REQUIREMENTS.md STAT-05 wording matches the locked CONTEXT.md decision (per-test-type families)"
  gaps_remaining: []
  regressions: []
---

# Phase 5: Statistical Analysis and Derived Metrics — Verification Report

**Phase Goal:** Implement all statistical analyses (GLMM, bootstrap, McNemar's, Kendall's tau, BH) and derived metrics (CR, quadrants, cost, transitions) from the RDD
**Verified:** 2026-03-23T18:10:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 03)

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | CR is computed from pairwise pass/fail agreement across 5 repetitions and matches hand calculation | VERIFIED | `compute_cr` uses `itertools.combinations`; tests confirm CR=1.0 (all-pass), CR=0.4 (3/5 pass), CR=0.6 (4/5 pass) |
| 2  | Each prompt-condition-model triple is classified into exactly one quadrant (robust, confidently_wrong, lucky, broken) | VERIFIED | `classify_quadrant` returns one of four values; DB integration test confirms all 4 quadrant types with correct CR thresholds |
| 3  | Quadrant migration transition matrices show how prompts move between quadrants as noise increases | VERIFIED | `compute_quadrant_migration` builds 4x4 dict; test verifies exact cell counts for clean->type_a_10pct |
| 4  | Per-prompt cost fields (token_savings, net_token_cost) are stored in derived_metrics table | VERIFIED | `compute_derived_metrics` calculates and INSERTs both fields; schema CREATE TABLE includes both columns |
| 5  | Per-condition cost rollup aggregates are output as JSON and CSV | VERIFIED | `main()` writes cost_rollups.json and csv/cost_rollups.csv; `compute_cost_rollups` groups by (model, noise_type, intervention) |
| 6  | GLMM fits on binary pass/fail with prompt-level random effects and produces coefficient table with p-values | VERIFIED | `fit_glmm` uses `BinomialBayesMixedGLM.from_formula` with `vc_formulas`; `_extract_coefficients` returns name/estimate/std_err/p_value list |
| 7  | GLMM gracefully falls back to GEE when convergence fails, logging which model was fit | VERIFIED | Three-level fallback chain: BayesMixedGLM full -> reduced random effects -> GEE; test with degenerate_test_db confirms fallback to "gee" |
| 8  | Bootstrap CIs are computed for accuracy, CR, and cost metrics with BCa/percentile fallback | VERIFIED | `compute_bootstrap_cis` now accepts optional `db_path`; when provided, calls `load_derived_metrics` and computes CR CIs keyed with "cr_" prefix tagged `metric="consistency_rate"`; both `_run_bootstrap_analysis` and `_run_all_analysis` pass `db_path=args.db`; 3 new tests cover CR CI keys, value ranges, and backward compatibility |
| 9  | McNemar's test identifies fragile and recoverable prompts with BH-corrected p-values | VERIFIED | `run_mcnemar_analysis` classifies per prompt; BH correction applied in CLI via `apply_bh_correction`; tests confirm fragile/recoverable/skipped behavior |
| 10 | Kendall's tau measures rank-order stability between clean and noisy conditions | VERIFIED | `compute_kendall_tau` uses `scipy.stats.kendalltau(..., variant='b')`; test confirms tau and p_value keys present |
| 11 | BH correction is applied per-test-type family, storing both raw and corrected p-values | VERIFIED | `apply_bh_correction` accepts `dict[str, list[float]]`; returns raw_p_values, corrected_p_values, reject per family; test confirms counts and non-increase in significance |
| 12 | Sensitivity analysis reruns key metrics after dropping hardest/easiest 10% of prompts | VERIFIED | `run_sensitivity_analysis` sorts by pass rate, drops bottom/top `drop_pct`, reruns GLMM + bootstrap; test confirms n_prompts_filtered < n_prompts_original |
| 13 | Effect size summary table (OR, RD, Cohen's d, Kendall's tau) with CIs is output as CSV | VERIFIED | `generate_effect_size_summary` builds DataFrame with columns metric, comparison, effect_size, ci_lower, ci_upper, effect_type; CLI writes effect_size_summary.csv |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compute_derived.py` | CR computation, quadrant classification, cost rollups, migration matrices | VERIFIED | 519 lines; exports compute_cr, classify_quadrant, build_condition_string, load_experiment_data, compute_derived_metrics, compute_quadrant_migration, compute_cost_rollups, main |
| `tests/test_compute_derived.py` | Unit tests for all derived metric computations | VERIFIED | 197 lines (min_lines=100); 14 tests across CR, quadrant, condition string, DB integration, cost rollups, migration |
| `src/analyze_results.py` | GLMM, bootstrap, McNemar's, Kendall's tau, BH correction, sensitivity, effect sizes, CR bootstrap | VERIFIED | All 8 exported functions present and importable; `load_derived_metrics` added at line 78; `compute_bootstrap_cis` extended with `db_path` param at line 341 |
| `tests/test_analyze_results.py` | Unit tests for all statistical analysis functions, including CR bootstrap | VERIFIED | 290+ lines; 14+ tests covering all statistical methods plus 3 new CR bootstrap tests (TestBootstrapCR class) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/compute_derived.py` | `results/results.db` | sqlite3 read experiment_runs, write derived_metrics | WIRED | `SELECT * FROM experiment_runs WHERE status = 'completed'`; `INSERT OR REPLACE INTO derived_metrics` present |
| `src/compute_derived.py` | `src/config.py` | import NOISE_TYPES, INTERVENTIONS, MODELS | WIRED | `from src.config import INTERVENTIONS, MODELS, NOISE_TYPES` at line 22 |
| `src/analyze_results.py` | `results/results.db` | sqlite3 read experiment_runs | WIRED | `SELECT * FROM experiment_runs WHERE status = 'completed'` present |
| `src/analyze_results.py` | `results/results.db` | sqlite3 read derived_metrics for CR values | WIRED | `load_derived_metrics` at line 78 uses `pd.read_sql_query("SELECT prompt_id, condition, model, consistency_rate, ... FROM derived_metrics", conn)`; called inside `compute_bootstrap_cis` when `db_path` is provided |
| `src/analyze_results.py` | `results/*.json` | json.dump output files | WIRED | json.dump calls for bootstrap_results.json, effect_size_summary, etc. |
| `src/analyze_results.py` | `results/csv/*.csv` | pandas DataFrame.to_csv | WIRED | .to_csv calls for effect_sizes.csv, bootstrap CSVs |
| `tests/conftest.py` | `src/compute_derived.py` | analysis_test_db fixture populates derived_metrics | WIRED | `from src.compute_derived import compute_derived_metrics` at line 209; `compute_derived_metrics(db_path, cr_threshold=0.8)` at line 210 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DERV-01 | 05-01 | Compute Consistency Rate (CR) from pairwise agreement across 5 repetitions | SATISFIED | `compute_cr` uses `itertools.combinations`; 5 unit tests verify correct calculation |
| DERV-02 | 05-01 | Classify each prompt-condition pair into stability-correctness quadrant | SATISFIED | `classify_quadrant` implements all 4 quadrants with configurable threshold; DB integration test verifies all 4 are produced |
| DERV-03 | 05-01 | Compute cost rollups and net ROI for optimizer interventions | SATISFIED | `compute_cost_rollups` aggregates per (model, noise_type, intervention); token_savings and net_token_cost stored in derived_metrics |
| STAT-01 | 05-02 | Fit GLMM with prompt-level random effects on binary pass/fail outcomes | SATISFIED | `fit_glmm` uses BinomialBayesMixedGLM with vc_formulas for prompt_id random effects |
| STAT-02 | 05-02/05-03 | Compute bootstrap confidence intervals for all reported metrics | SATISFIED | Bootstrap CIs implemented for accuracy (experiment_runs) AND CR (derived_metrics.consistency_rate) via optional db_path param; 3 new tests confirm correct behavior |
| STAT-03 | 05-02 | Run McNemar's test for prompt-level fragility/recoverability analysis | SATISFIED | `run_mcnemar_analysis` classifies fragile/recoverable per prompt with exact binomial test |
| STAT-04 | 05-02 | Compute Kendall's tau for rank-order stability | SATISFIED | `compute_kendall_tau` uses `kendalltau(..., variant='b')` per model per condition pair |
| STAT-05 | 05-02/05-03 | Apply Benjamini-Hochberg correction per test-type family (McNemar's, GLMM, Kendall's) | SATISFIED | Implementation uses separate families per test type; REQUIREMENTS.md now reads "per test-type family (McNemar's, GLMM, Kendall's)" — requirement text and implementation are aligned |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No TODO/FIXME/placeholder comments, no empty return stubs, no print() statements in any modified file |

---

### Human Verification Required

No items require human verification. All observable behaviors are testable programmatically and confirmed by the test suite (31 tests pass: 0 failures, 1 warning).

---

### Re-Verification Summary

**Previous gaps (2 items):**

**Gap 1 (STAT-02, Bootstrap CIs for CR) — CLOSED**

`load_derived_metrics()` was added to `src/analyze_results.py` at line 78. It reads `consistency_rate` per `(prompt_id, condition, model)` from `derived_metrics`. `compute_bootstrap_cis` was extended with `db_path: str | None = None` — when provided, it calls `load_derived_metrics` and runs `_bootstrap_ci` per `(condition, model)` group of CR values. Results are keyed `cr_{condition}_{model}` with `"metric": "consistency_rate"`. Both `_run_bootstrap_analysis` and `_run_all_analysis` now pass `db_path=args.db`. The `analysis_test_db` conftest fixture now calls `compute_derived_metrics` to populate `derived_metrics` before tests run.

**Gap 2 (STAT-05, BH family wording) — CLOSED**

REQUIREMENTS.md line for STAT-05 now reads: "Apply Benjamini-Hochberg correction per test-type family (McNemar's, GLMM, Kendall's) across reported p-values" — aligned with the locked CONTEXT.md design decision. The previous wording "in a single family" no longer creates a contradiction with the implementation.

**No regressions detected.** All 31 tests across both test modules pass.

---

_Verified: 2026-03-23T18:10:00Z_
_Verifier: Claude (gsd-verifier)_
