# Phase 5: Statistical Analysis and Derived Metrics - Research

**Researched:** 2026-03-23
**Domain:** Statistical analysis (GLMM, bootstrap, McNemar's, Kendall's tau), derived metrics (CR, quadrants, cost rollups)
**Confidence:** HIGH

## Summary

Phase 5 implements two modules -- `compute_derived.py` (per-prompt: CR, quadrants, cost rollups, quadrant migration) and `analyze_results.py` (aggregate: GLMM, bootstrap CIs, McNemar's, Kendall's tau, BH correction, sensitivity analysis, effect size summary). All statistical methods are well-supported by the existing dependency stack (statsmodels >= 0.14, scipy >= 1.12, pandas, numpy). The primary risk is GLMM convergence with `BinomialBayesMixedGLM`, which has a defined fallback chain (GLMM -> GEE with exchangeable correlation for clustered standard errors).

The project already has a working bootstrap CI pattern in `src/pilot.py` using `scipy.stats.bootstrap` with BCa/percentile fallback. McNemar's test is available via `statsmodels.stats.contingency_tables.mcnemar`. Kendall's tau via `scipy.stats.kendalltau`. BH correction via `statsmodels.stats.multitest.multipletests`. All outputs go to JSON files, CSV tables, and terminal summaries via `tabulate`.

**Primary recommendation:** Build `compute_derived.py` first (simpler, populates `derived_metrics` table), then `analyze_results.py` (consumes both `experiment_runs` and `derived_metrics`). Reuse pilot.py bootstrap pattern. Use GEE (not plain logistic regression) as the GLMM fallback since it properly handles clustered data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **GLMM Approach:** Primary: statsmodels BinomialBayesMixedGLM with logit link on binary pass/fail. Fixed effects: Noise_Type, Noise_Level, Intervention, Model, benchmark_source (as covariate), all 2-way interactions. Random effects: Try (1|Prompt_ID) + (1|Prompt_ID:Model) first, drop interaction on convergence failure. Fallback: fixed-effects logistic regression with clustered standard errors. Pure Python, no R.
- **Derived Metrics:** Populate existing `derived_metrics` table in results.db. CR = pairwise pass/fail agreement across 5 runs. Quadrant thresholds: CR >= 0.8 for "stable", majority pass (3/5+) for "correct" -- configurable via --cr-threshold CLI flag, defaults to 0.8. Quadrant migration: transition matrices between quadrants as noise increases (clean->noisy_5pct, clean->noisy_10pct, clean->noisy_20pct).
- **Cost Rollups:** Per-condition aggregate (model x intervention x noise), not per-prompt. Per-prompt net_token_cost stored in derived_metrics.
- **Per-Benchmark:** benchmark_source as GLMM fixed effect (not separate models). Report aggregate metrics separately per benchmark in summary outputs.
- **BH Correction:** Per-test-type families (McNemar's, GLMM, Kendall's). Store both raw and BH-corrected p-values. Use statsmodels.stats.multitest.multipletests(method='fdr_bh').
- **Output Format:** Two modules: compute_derived.py and analyze_results.py. Output triple: JSON + CSV + terminal summary. CLI: argparse subcommands for analyze_results.py (glmm, mcnemar, bootstrap, kendall, all). compute_derived.py: single command.
- **Sensitivity Analysis:** Rerun key metrics after dropping hardest/easiest 10% of prompts.
- **Effect Size Summary Table:** Auto-generate CSV with all effect sizes (OR, RD, Cohen's d, Kendall's tau) with CIs.

### Claude's Discretion
- Bootstrap iteration count (RDD says 10,000)
- Internal structure of JSON output files
- Exact tabulate table format (grid, github, etc.)
- Cohen's d computation details for continuous metrics
- Sensitivity analysis threshold (10% is starting point)
- How to handle prompts with incomplete repetitions (fewer than 5 runs)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STAT-01 | Fit GLMM with prompt-level random effects on binary pass/fail outcomes | BinomialBayesMixedGLM.from_formula with vc_formulas dict for random effects; GEE fallback with exchangeable correlation |
| STAT-02 | Compute bootstrap confidence intervals for all reported metrics | scipy.stats.bootstrap with BCa/percentile fallback pattern from pilot.py; 10,000 iterations |
| STAT-03 | Run McNemar's test for prompt-level fragility/recoverability analysis | statsmodels.stats.contingency_tables.mcnemar with exact=True for small cell counts |
| STAT-04 | Compute Kendall's tau for rank-order stability (uniform vs. targeted tax) | scipy.stats.kendalltau with variant='b', comparing clean vs. noisy pass-rate rankings |
| STAT-05 | Apply Benjamini-Hochberg correction across all reported p-values | statsmodels.stats.multitest.multipletests(method='fdr_bh'), per-test-type families |
| DERV-01 | Compute Consistency Rate (CR) from pairwise agreement across 5 repetitions | C(5,2)=10 pairwise comparisons of pass/fail, CR = agreements/10 |
| DERV-02 | Classify each prompt-condition pair into stability-correctness quadrant | CR >= 0.8 threshold (configurable), majority pass 3/5+; four quadrants: robust/confidently_wrong/lucky/broken |
| DERV-03 | Compute cost rollups and net ROI for optimizer interventions | Aggregate from experiment_runs cost columns; net = savings - preproc overhead |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | >= 0.14.0 (in pyproject.toml) | GLMM, McNemar's, BH correction | Only Python library with BinomialBayesMixedGLM and multipletests |
| scipy | >= 1.12.0 (in pyproject.toml) | Bootstrap CIs, Kendall's tau | Standard scientific Python; bootstrap already used in pilot.py |
| pandas | >= 2.2.0 (in pyproject.toml) | DataFrame operations for aggregation | Required for statsmodels formula API and CSV output |
| numpy | (transitive) | Array operations | Required by all above |
| tabulate | needs adding | Terminal summary tables | Lightweight, no heavy deps; decided in CONTEXT.md |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | Read experiment_runs, write derived_metrics | All data I/O |
| json | stdlib | Output JSON result files | All JSON outputs |
| csv | stdlib | Output CSV tables | LaTeX-ready CSV exports |
| itertools.combinations | stdlib | Pairwise CR computation | C(5,2) pair generation |
| math.comb | stdlib | Binomial coefficient for CR denominator | C(K,2) calculation |
| logging | stdlib | All output (no print) | Project convention |
| argparse | stdlib | CLI with subcommands | Project convention |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| BinomialBayesMixedGLM | GEE with Binomial family | GEE is the fallback -- handles clustering but no true random effects |
| scipy.stats.bootstrap | Manual bootstrap loop | scipy handles BCa automatically; manual only if edge cases arise |
| tabulate | rich.table | tabulate is simpler, no color dependency issues in logs |

**Installation:**
```bash
pip install tabulate
```

Note: `tabulate` is the only new dependency. All others are already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  compute_derived.py   # Per-prompt: CR, quadrants, cost, migration
  analyze_results.py   # Aggregate: GLMM, bootstrap, McNemar, Kendall, BH
  config.py            # Existing: PRICE_TABLE, compute_cost(), condition enums
  db.py                # Existing: init_database, query_runs, derived_metrics table

results/
  glmm_results.json
  mcnemar_results.json
  bootstrap_results.json
  kendall_results.json
  analysis_summary.json
  effect_size_summary.json
  csv/                 # New directory
    glmm_coefficients.csv
    mcnemar_fragile.csv
    bootstrap_cis.csv
    kendall_tau.csv
    effect_sizes.csv
    cost_rollups.csv
    quadrant_distribution.csv
    quadrant_migration.csv
```

### Pattern 1: Data Loading from SQLite
**What:** Load experiment_runs into a pandas DataFrame for statistical analysis
**When to use:** All analysis functions need this
**Example:**
```python
import sqlite3
import pandas as pd

def load_experiment_data(db_path: str) -> pd.DataFrame:
    """Load completed experiment runs as a DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM experiment_runs WHERE status = 'completed' AND pass_fail IS NOT NULL",
        conn,
    )
    conn.close()
    return df
```

### Pattern 2: BinomialBayesMixedGLM with Fallback
**What:** Fit GLMM on binary pass/fail, fall back to GEE if convergence fails
**When to use:** STAT-01
**Example:**
```python
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

# Random effects specified as dict of formulas
vc_formulas = {
    "prompt_intercept": "0 + C(prompt_id)",
    "prompt_model": "0 + C(prompt_id):C(model)",
}

try:
    model = BinomialBayesMixedGLM.from_formula(
        "pass_fail ~ C(noise_type) * C(noise_level) * C(intervention) * C(model) + C(benchmark)",
        vc_formulas,
        data=df,
    )
    result = model.fit_vb()
    logger.info("GLMM (BayesMixedGLM) converged")
except Exception as exc:
    logger.warning("Full GLMM failed (%s), dropping prompt_model interaction", exc)
    vc_formulas_reduced = {"prompt_intercept": "0 + C(prompt_id)"}
    try:
        model = BinomialBayesMixedGLM.from_formula(
            "pass_fail ~ C(noise_type) * C(noise_level) * C(intervention) * C(model) + C(benchmark)",
            vc_formulas_reduced,
            data=df,
        )
        result = model.fit_vb()
        logger.info("GLMM (reduced random effects) converged")
    except Exception as exc2:
        logger.warning("GLMM fallback failed (%s), using GEE", exc2)
        # GEE fallback with exchangeable correlation
        import statsmodels.api as sm
        from statsmodels.genmod.generalized_estimating_equations import GEE
        model = GEE.from_formula(
            "pass_fail ~ C(noise_type) * C(noise_level) * C(intervention) * C(model) + C(benchmark)",
            groups="prompt_id",
            data=df,
            family=sm.families.Binomial(),
            cov_struct=sm.cov_struct.Exchangeable(),
        )
        result = model.fit()
        logger.info("GEE fallback converged")
```

### Pattern 3: Argparse Subcommands (from run_experiment.py)
**What:** CLI with subcommands for each analysis type
**When to use:** analyze_results.py CLI
**Example:**
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical analysis")
    parser.add_argument("--db", default="results/results.db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub_glmm = subparsers.add_parser("glmm")
    sub_mcnemar = subparsers.add_parser("mcnemar")
    sub_bootstrap = subparsers.add_parser("bootstrap")
    sub_kendall = subparsers.add_parser("kendall")
    sub_all = subparsers.add_parser("all")

    args = parser.parse_args()
    # dispatch based on args.command
```

### Pattern 4: Consistency Rate Computation
**What:** Pairwise pass/fail agreement for K=5 runs
**When to use:** DERV-01
**Example:**
```python
from itertools import combinations
from math import comb

def compute_cr(pass_fail_results: list[int]) -> float:
    """Compute consistency rate from K pass/fail results.

    CR = (number of agreeing pairs) / C(K, 2)
    """
    k = len(pass_fail_results)
    if k < 2:
        return 1.0  # Degenerate case
    total_pairs = comb(k, 2)
    agreeing = sum(
        1 for a, b in combinations(pass_fail_results, 2) if a == b
    )
    return agreeing / total_pairs
```

### Anti-Patterns to Avoid
- **Running separate GLMMs per benchmark:** Use benchmark_source as a fixed-effect covariate instead. Single model is statistically cleaner.
- **Pooling all p-values into one BH family:** Separate by test type (McNemar's, GLMM, Kendall's) as decided.
- **Using print() for any output:** Use logging module per project convention.
- **Storing analysis results only in SQLite:** Output triple (JSON + CSV + terminal) as decided.
- **Hardcoding CR threshold:** Must be configurable via --cr-threshold CLI flag.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bootstrap CIs | Manual resample loop | `scipy.stats.bootstrap(method='bca')` | Handles BCa acceleration, edge cases; already proven in pilot.py |
| McNemar's test | Manual chi-squared computation | `statsmodels.stats.contingency_tables.mcnemar(exact=True)` | Automatically handles exact binomial for small samples |
| BH correction | Manual p-value sorting | `multipletests(method='fdr_bh')` | Returns both corrected p-values and reject/accept decisions |
| Kendall's tau | Manual concordant/discordant pair counting | `scipy.stats.kendalltau` | O(n log n) algorithm, handles ties correctly |
| Odds ratios from GLMM | Manual exponentiation | `np.exp(result.fe_mean)` for BayesMixedGLM | Proper CI computation requires working with the model's variance estimates |
| Cohen's d | Manual pooled SD calculation | Simple formula: `(mean1 - mean2) / pooled_sd` | Straightforward enough, but use Welch's correction for unequal variances |
| CSV output | Manual string formatting | `pandas.DataFrame.to_csv()` | Handles quoting, escaping, headers automatically |

**Key insight:** The statistical analysis stack (statsmodels + scipy) provides all needed tests. The implementation work is in data wrangling (SQLite -> DataFrame), orchestration (fallback chains, aggregation logic), and output formatting -- not in reimplementing statistical methods.

## Common Pitfalls

### Pitfall 1: GLMM Convergence Failure
**What goes wrong:** BinomialBayesMixedGLM fails to converge with full random effects specification, especially with many prompt_id levels (200) and model interaction terms.
**Why it happens:** Binary outcomes with many random effect levels create a high-dimensional posterior that variational Bayes struggles with.
**How to avoid:** Implement the three-level fallback chain: full GLMM -> reduced GLMM (drop prompt:model interaction) -> GEE with exchangeable correlation. Log which model was actually fit. Store model metadata in output JSON.
**Warning signs:** fit_vb() throwing convergence warnings, NaN in coefficients, extremely large standard errors.

### Pitfall 2: McNemar's Test with All-Concordant Pairs
**What goes wrong:** When a prompt passes (or fails) under both conditions, the 2x2 table has zero discordant pairs, making McNemar's test undefined.
**Why it happens:** Easy prompts pass under all conditions; impossible prompts fail under all conditions.
**How to avoid:** Skip McNemar's for prompts where b + c = 0 (no discordant pairs). Report the count of skipped prompts. Only include prompts with discordant pairs in the BH correction family.
**Warning signs:** Division by zero, p-value = NaN, or p-value = 1.0 for all prompts.

### Pitfall 3: Bootstrap with Degenerate Data
**What goes wrong:** BCa bootstrap fails when the statistic has zero variance (all values identical) or when the jackknife produces NaN accelerations.
**Why it happens:** If all 5 repetitions pass (or all fail) for every prompt in a condition, accuracy is exactly 0 or 1 with no variance.
**How to avoid:** Use the pilot.py pattern: try BCa first, catch warnings, fall back to percentile method. Log fallback.
**Warning signs:** warnings from scipy about degenerate jackknife, NaN in CI bounds.

### Pitfall 4: Incorrect CR Computation for Incomplete Runs
**What goes wrong:** Some prompt-condition pairs may have fewer than 5 repetitions (e.g., API failures). Computing CR with fewer runs changes the denominator.
**How to avoid:** Filter to only complete groups (5 runs per prompt-condition-model). Log and report any incomplete groups separately. If a prompt has 3-4 runs, compute CR with actual K but flag it.
**Warning signs:** Unexpected CR values, prompt-condition groups with fewer than expected rows.

### Pitfall 5: Formula Specification for Interactions
**What goes wrong:** statsmodels formula syntax uses `*` for full interaction (main effects + interaction) and `:` for interaction only. Using `C(a) * C(b) * C(c) * C(d)` generates an explosion of high-order interaction terms.
**Why it happens:** The RDD says "all 2-way interactions" but `*` with 4+ variables creates 3-way and 4-way interactions too.
**How to avoid:** Explicitly specify 2-way interactions with `:` notation, or build the formula programmatically listing only desired terms. E.g.: `pass_fail ~ C(noise_type) + C(intervention) + C(model) + C(noise_type):C(intervention) + C(noise_type):C(model) + C(intervention):C(model) + C(benchmark)`.
**Warning signs:** Model matrix is enormous, fitting takes forever, rank deficiency warnings.

### Pitfall 6: Condition String Construction
**What goes wrong:** The `derived_metrics` table uses a `condition` TEXT field (e.g., "type_a_10pct_raw") but experiment_runs stores noise_type, noise_level, and intervention as separate columns.
**Why it happens:** Need to construct condition strings consistently for the composite primary key.
**How to avoid:** Define a canonical condition builder: `f"{noise_type}_{intervention}"` or similar. Ensure it matches any existing convention from pilot data.
**Warning signs:** Primary key violations on insert, missing joins.

## Code Examples

### McNemar's Test for Fragility Analysis
```python
# Source: statsmodels.stats.contingency_tables.mcnemar
from statsmodels.stats.contingency_tables import mcnemar
import numpy as np

def run_mcnemar_fragility(
    df: pd.DataFrame,
    condition_a: str,  # e.g., "clean"
    condition_b: str,  # e.g., "type_a_10pct"
    model: str,
) -> list[dict]:
    """Run McNemar's test per prompt comparing two conditions.

    Returns list of dicts with prompt_id, statistic, p_value, classification.
    """
    results = []
    # Use majority vote (3/5+) as the pass/fail for each prompt-condition
    for prompt_id in df["prompt_id"].unique():
        mask_a = (df["prompt_id"] == prompt_id) & (df["noise_type"] == condition_a) & (df["model"] == model)
        mask_b = (df["prompt_id"] == prompt_id) & (df["noise_type"] == condition_b) & (df["model"] == model)

        pass_a = int(df.loc[mask_a, "pass_fail"].mean() >= 0.5)  # majority vote
        pass_b = int(df.loc[mask_b, "pass_fail"].mean() >= 0.5)

        # Build 2x2 table from individual repetitions
        runs_a = df.loc[mask_a, "pass_fail"].values
        runs_b = df.loc[mask_b, "pass_fail"].values

        # Pair runs by repetition number
        table = np.zeros((2, 2), dtype=int)
        for ra, rb in zip(runs_a, runs_b):
            table[1 - int(ra)][1 - int(rb)] += 1

        b_count = table[0][1]  # pass in A, fail in B
        c_count = table[1][0]  # fail in A, pass in B

        if b_count + c_count == 0:
            continue  # Skip concordant pairs

        result = mcnemar(table, exact=True)
        classification = "fragile" if b_count > c_count else "recoverable"

        results.append({
            "prompt_id": prompt_id,
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "b_count": int(b_count),
            "c_count": int(c_count),
            "classification": classification,
        })
    return results
```

### BH Correction per Test Family
```python
# Source: statsmodels.stats.multitest.multipletests
from statsmodels.stats.multitest import multipletests

def apply_bh_correction(p_values: list[float], alpha: float = 0.05) -> tuple[list[bool], list[float]]:
    """Apply Benjamini-Hochberg FDR correction.

    Returns (reject_decisions, corrected_p_values).
    """
    reject, pvals_corrected, _, _ = multipletests(
        p_values, alpha=alpha, method="fdr_bh"
    )
    return reject.tolist(), pvals_corrected.tolist()
```

### Kendall's Tau for Rank-Order Stability
```python
# Source: scipy.stats.kendalltau
from scipy.stats import kendalltau

def compute_rank_stability(
    df: pd.DataFrame,
    clean_condition: str,
    noisy_condition: str,
    model: str,
) -> dict:
    """Compute Kendall's tau between clean and noisy pass-rate rankings."""
    # Compute per-prompt pass rate under each condition
    clean_rates = (
        df[(df["noise_type"] == clean_condition) & (df["model"] == model)]
        .groupby("prompt_id")["pass_fail"]
        .mean()
    )
    noisy_rates = (
        df[(df["noise_type"] == noisy_condition) & (df["model"] == model)]
        .groupby("prompt_id")["pass_fail"]
        .mean()
    )

    # Align on common prompts
    common = clean_rates.index.intersection(noisy_rates.index)
    tau, p_value = kendalltau(clean_rates[common], noisy_rates[common])

    return {
        "clean_condition": clean_condition,
        "noisy_condition": noisy_condition,
        "model": model,
        "tau": float(tau),
        "p_value": float(p_value),
        "n_prompts": len(common),
    }
```

### Quadrant Migration Transition Matrix
```python
def compute_quadrant_migration(
    derived_df: pd.DataFrame,
    from_condition: str,
    to_condition: str,
    model: str,
) -> dict:
    """Compute transition matrix between quadrants as noise changes."""
    quadrants = ["robust", "confidently_wrong", "lucky", "broken"]

    from_data = derived_df[
        (derived_df["condition"] == from_condition) & (derived_df["model"] == model)
    ].set_index("prompt_id")

    to_data = derived_df[
        (derived_df["condition"] == to_condition) & (derived_df["model"] == model)
    ].set_index("prompt_id")

    common = from_data.index.intersection(to_data.index)
    matrix = {q_from: {q_to: 0 for q_to in quadrants} for q_from in quadrants}

    for pid in common:
        q_from = from_data.loc[pid, "quadrant"]
        q_to = to_data.loc[pid, "quadrant"]
        matrix[q_from][q_to] += 1

    return {
        "from_condition": from_condition,
        "to_condition": to_condition,
        "model": model,
        "n_prompts": len(common),
        "transition_matrix": matrix,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| t-tests for LLM evaluation | GLMM with prompt-level random effects | NIST AI 800-3 (Feb 2026) recommendation | Properly accounts for prompt difficulty variation |
| Single-run accuracy | 5-repetition stability (CR) measurement | Riasat (March 2026) ArXiv:2603.15840 | Separates correctness from stability; detects silent failures |
| Bonferroni correction | Benjamini-Hochberg FDR control | Standard practice | Less conservative for hundreds of tests |
| Manual bootstrap loops | scipy.stats.bootstrap with BCa | scipy >= 1.9.0 | Built-in BCa acceleration, proper CI computation |

**Deprecated/outdated:**
- `scipy.stats.false_discovery_control()`: The RDD mentions this as an alternative to multipletests, but the CONTEXT.md locks `statsmodels.stats.multitest.multipletests(method='fdr_bh')`.

## Open Questions

1. **How to handle noise_level encoding for GLMM formula**
   - What we know: noise_level is stored as TEXT ("5", "10", "20", or NULL for clean/type_b). The GLMM needs it as a factor or numeric.
   - What's unclear: Whether to treat as ordered factor (preserves dose-response) or unordered categorical.
   - Recommendation: Treat as unordered categorical `C(noise_level)` for maximum flexibility. The interaction terms will capture dose-response patterns.

2. **Condition string format for derived_metrics**
   - What we know: The `condition` column in derived_metrics is TEXT, primary key component.
   - What's unclear: Exact format -- whether it includes noise_level separately or combined (e.g., "type_a_10pct_raw" vs "type_a_10pct|raw").
   - Recommendation: Use `f"{noise_type}_{intervention}"` as the condition string since noise_type already encodes level (e.g., "type_a_10pct"). This matches the experiment_runs naming convention visible in config.py NOISE_TYPES.

3. **Cohen's d for which continuous metrics**
   - What we know: RDD says Cohen's d for "continuous outcomes (BERTScore, token counts)".
   - What's unclear: BERTScore is Phase 6/optional territory. Token count differences may not need formal effect sizes.
   - Recommendation: Compute Cohen's d for token savings (optimized vs. original) and latency differences. Skip BERTScore d until Phase 6.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_compute_derived.py tests/test_analyze_results.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAT-01 | GLMM fits on binary data, produces coefficients + p-values | unit | `pytest tests/test_analyze_results.py::test_glmm_fit -x` | No - Wave 0 |
| STAT-01 | GLMM fallback chain works when convergence fails | unit | `pytest tests/test_analyze_results.py::test_glmm_fallback -x` | No - Wave 0 |
| STAT-02 | Bootstrap CIs computed for accuracy/CR/cost metrics | unit | `pytest tests/test_analyze_results.py::test_bootstrap_ci -x` | No - Wave 0 |
| STAT-03 | McNemar's test per prompt with fragile/recoverable classification | unit | `pytest tests/test_analyze_results.py::test_mcnemar -x` | No - Wave 0 |
| STAT-04 | Kendall's tau between clean and noisy rankings | unit | `pytest tests/test_analyze_results.py::test_kendall_tau -x` | No - Wave 0 |
| STAT-05 | BH correction applied per test family, both raw and corrected stored | unit | `pytest tests/test_analyze_results.py::test_bh_correction -x` | No - Wave 0 |
| DERV-01 | CR computed from pairwise agreement, matches hand calculation | unit | `pytest tests/test_compute_derived.py::test_cr_computation -x` | No - Wave 0 |
| DERV-02 | Quadrant classification correct for all four quadrant cases | unit | `pytest tests/test_compute_derived.py::test_quadrant_classification -x` | No - Wave 0 |
| DERV-03 | Cost rollups aggregate correctly per condition | unit | `pytest tests/test_compute_derived.py::test_cost_rollups -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_compute_derived.py tests/test_analyze_results.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_compute_derived.py` -- covers DERV-01, DERV-02, DERV-03
- [ ] `tests/test_analyze_results.py` -- covers STAT-01 through STAT-05
- [ ] `tests/conftest.py` -- add fixtures for synthetic experiment_runs data (5 reps per prompt-condition-model) for deterministic statistical test verification
- [ ] Framework install: `pip install tabulate` -- only new dependency

## Sources

### Primary (HIGH confidence)
- [statsmodels BinomialBayesMixedGLM docs](https://www.statsmodels.org/stable/generated/statsmodels.genmod.bayes_mixed_glm.BinomialBayesMixedGLM.html) - API signature, from_formula, fit_vb
- [statsmodels mcnemar docs](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html) - exact parameter, return values
- [statsmodels GEE docs](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_estimating_equations.GEE.html) - Binomial family, exchangeable correlation, clustered SEs
- [scipy kendalltau docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kendalltau.html) - variant='b', alternative parameter
- `docs/RDD_Linguistic_Tax_v4.md` sections 7.2-7.9, 8.1-8.3, 9.2 - Complete statistical specification
- `src/db.py` - Schema including derived_metrics table
- `src/pilot.py` - Bootstrap CI pattern with BCa/percentile fallback
- `src/config.py` - PRICE_TABLE, compute_cost(), NOISE_TYPES, INTERVENTIONS, MODELS enums

### Secondary (MEDIUM confidence)
- [statsmodels multipletests](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) - BH method parameter (verified via WebSearch + official docs)

### Tertiary (LOW confidence)
- None -- all findings verified against official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in pyproject.toml (except tabulate), APIs verified against official docs
- Architecture: HIGH - patterns match existing project conventions (pilot.py, db.py, config.py), CONTEXT.md decisions are specific
- Pitfalls: HIGH - GLMM convergence risk explicitly flagged in STATE.md, other pitfalls from direct API analysis

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable domain, statsmodels API unlikely to change)
