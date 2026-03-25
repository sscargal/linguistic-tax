# Analysis Guide

How to run the analysis pipeline, interpret statistical output, read derived metrics, understand figures, and query the results database directly.

All analysis reads from `results/results.db`, a SQLite database populated by experiment runs. If you have not run any experiments yet, see [Getting Started](getting-started.md).

## Overview

Three modules form the analysis pipeline:

| Module | Purpose | Key outputs |
|--------|---------|-------------|
| `src/compute_derived.py` | Consistency Rate (CR), quadrant classification, cost rollups | `derived_metrics` table, cost JSON/CSV |
| `src/analyze_results.py` | GLMM, bootstrap CIs, McNemar's test, Kendall's tau | JSON + CSV + terminal summary |
| `src/generate_figures.py` | Publication figures (accuracy curves, quadrant plots, heatmaps, bar charts) | PDF + PNG in `figures/` |

**Run order matters.** `compute_derived` must run first because it creates the `derived_metrics` table that the other modules reference.

## Running Analysis

```bash
# Step 1: Compute derived metrics (CR, quadrants, cost rollups)
python -m src.compute_derived --db results/results.db

# Step 2: Run statistical analyses (GLMM, bootstrap, McNemar's, Kendall's)
python -m src.analyze_results --db results/results.db all

# Step 3: Generate publication figures
python -m src.generate_figures all --db results/results.db
```

All outputs go to `results/analysis/` (JSON + CSV) and `figures/` (PDF + PNG) by default.

## Interpreting GLMM Output

A Generalized Linear Mixed Model (GLMM) is the primary analysis tool. It models binary pass/fail outcomes with prompt-level random effects to account for the fact that some prompts are inherently harder than others.

### What it tells you

- Which factors (noise type, intervention, model, benchmark) significantly affect pass probability
- The direction and magnitude of each effect
- Whether interactions between factors matter (e.g., does intervention effectiveness depend on noise level?)

### The 3-level fallback chain

The toolkit uses a fallback strategy to handle convergence issues:

1. **BayesMixedGLM (full)** -- Bayesian mixed-effects model with both prompt-level and prompt-by-model random effects. This is the gold standard when it converges.
2. **BayesMixedGLM (reduced)** -- Same model but drops the prompt-by-model interaction random effect. Used when the full model fails to converge.
3. **GEE (exchangeable)** -- Generalized Estimating Equations with exchangeable correlation structure. A population-averaged approach used when both mixed models fail.

The output reports which level was used in the `convergence_info` field.

### Reading the coefficients

Each coefficient represents the change in log-odds of passing when that factor is present (relative to the reference level):

| Field | Meaning |
|-------|---------|
| `name` | Factor name (e.g., `C(noise_type)[type_a_20pct]`) |
| `estimate` | Log-odds coefficient. Positive = increases pass probability; negative = decreases it |
| `std_err` | Standard error of the estimate |
| `p_value` | Statistical significance (after BH correction) |

**Example output:**

```
Coefficient                              Estimate   Std Err   P-value
C(noise_type)[type_a_5pct]                -0.312     0.089     0.001
C(noise_type)[type_a_20pct]               -1.247     0.102     <0.001
C(intervention)[pre_proc_sanitize]         0.485     0.076     <0.001
C(noise_type):C(intervention)[...]        -0.193     0.112     0.043
```

Reading this: Type A noise at 20% reduces pass probability substantially (estimate = -1.247, p < 0.001). Pre-processing with sanitization increases it (estimate = +0.485). The interaction term tells you whether the intervention's benefit changes at different noise levels.

### P-values and BH correction

Raw p-values are adjusted using the Benjamini-Hochberg (BH) procedure to control the false discovery rate across multiple comparisons. A BH-corrected p-value < 0.05 means the effect is statistically significant after accounting for multiple testing.

### Odds ratios

The output also includes odds ratios (exponentiated coefficients). An odds ratio of 1.5 means the odds of passing are 1.5 times higher when that factor is present. Values below 1.0 indicate reduced odds.

## Interpreting Bootstrap Confidence Intervals

Bootstrap CIs provide 95% confidence intervals for accuracy (mean pass rate) and Consistency Rate per experimental condition.

### Method

The toolkit uses BCa (bias-corrected and accelerated) bootstrap with 10,000 resamples. If BCa fails due to degenerate data (e.g., all values identical), it falls back to the percentile method. The `method_used` field reports which was applied.

### Reading the output

```
Condition                              Mean    CI Lower   CI Upper   Method
clean_raw_claude-sonnet-4-20250514     0.850     0.790      0.900    bca
type_a_20pct_raw_claude-sonnet-...     0.620     0.540      0.690    bca
```

- **Mean**: Point estimate of accuracy for that condition
- **CI Lower / CI Upper**: 95% confidence interval bounds
- **Interpretation**: If the CI for two conditions does not overlap, their accuracy difference is likely significant

### CR bootstrap CIs

When a database path is provided, bootstrap CIs are also computed for Consistency Rate values from the `derived_metrics` table. These entries are keyed with a `cr_` prefix and tagged with `metric: "consistency_rate"`.

## Interpreting McNemar's Test Results

McNemar's test examines prompt-level changes between two conditions using paired pass/fail outcomes across repetitions.

### What it tests

Two use cases:

1. **Fragility** (default mode): Compares clean vs. noisy conditions for the same intervention. Identifies prompts that pass when clean but fail when noisy -- these are "fragile" prompts.
2. **Recoverability** (`compare_interventions=True`): Compares raw vs. pre-processed within the same noise condition. Identifies prompts that fail raw but pass with intervention -- these are "recovered" prompts.

### Reading the output

Each comparison produces a 2x2 contingency table per prompt:

|              | Condition B Pass | Condition B Fail |
|--------------|-----------------|-----------------|
| **Cond A Pass** | Both pass (concordant) | A passes, B fails |
| **Cond A Fail** | A fails, B passes | Both fail (concordant) |

The test statistic and p-value tell you whether the off-diagonal cells (discordant pairs) are significantly asymmetric. Concordant prompts (both pass or both fail) are skipped.

**BH correction** is applied per test-type family (fragility tests as one family, recoverability tests as another) to control false discovery rate.

### Interpreting significance

A statistically significant McNemar's result (BH-corrected p < 0.05) means the intervention has a real, prompt-level effect -- not just a marginal average shift but a meaningful change in which specific prompts pass or fail.

## Interpreting Kendall's Tau

Kendall's tau measures rank-order correlation between two conditions.

### What it measures

Given the same set of prompts evaluated under two conditions (e.g., Type A 5% noise vs. Type A 20% noise), Kendall's tau tells you whether the difficulty ranking is preserved. Do the same prompts stay hard and the same prompts stay easy?

### Values

| Tau value | Interpretation |
|-----------|----------------|
| +1.0 | Perfect agreement -- identical difficulty ranking |
| 0.0 | No correlation -- rankings are unrelated |
| -1.0 | Perfect disagreement -- rankings are reversed |

### Use case

Comparing uniform noise (Type A at different rates) vs. targeted noise (Type B syntactic patterns). If tau is high between Type A rates, noise degrades prompts predictably. If tau is low between Type A and Type B, these noise types affect different prompts -- suggesting distinct failure mechanisms.

## Interpreting Consistency Rate (CR)

The Consistency Rate measures how reliably a model produces the same pass/fail outcome across repeated runs of the same prompt under the same conditions.

### Definition

Given K=5 repetitions, CR counts the fraction of all C(5,2)=10 pairwise comparisons where both repetitions agree (both pass or both fail):

```
CR = (number of agreeing pairs) / (total pairs)
   = (number of agreeing pairs) / 10
```

### Value range

| CR value | Meaning |
|----------|---------|
| 1.0 | All 5 repetitions produced the same result (all pass or all fail) |
| 0.8-1.0 | Highly stable -- at most 1 disagreement |
| 0.4-0.8 | Moderately stable -- mixed outcomes |
| 0.0-0.4 | Unstable -- outcomes appear random |
| 0.0 | Maximum disagreement (not achievable with odd K) |

### Bootstrap CIs for CR

Bootstrap CIs are computed over the CR values within each condition group (not over individual pairs). This quantifies the uncertainty in the average CR for a condition.

## Interpreting Quadrant Classification

Each prompt-condition-model triple is classified into one of four quadrants based on accuracy (majority pass) and stability (CR).

### The four quadrants

```
                    High CR (>= 0.8)       Low CR (< 0.8)
                 +---------------------+---------------------+
  Majority Pass  |      ROBUST         |       LUCKY         |
                 | Reliably correct.   | Right sometimes by  |
                 | Model understands   | chance. Unstable    |
                 | this prompt.        | but occasionally    |
                 |                     | correct.            |
                 +---------------------+---------------------+
  Majority Fail  | CONFIDENTLY WRONG   |       BROKEN        |
                 | Consistently wrong. | Unreliably wrong.   |
                 | Model is confident  | Fails most of the   |
                 | but incorrect.      | time and varies.    |
                 +---------------------+---------------------+
```

### What each quadrant means

- **Robust**: The best outcome. The model reliably produces correct answers. These prompts work.
- **Confidently Wrong**: Concerning. The model consistently produces the wrong answer with high confidence. These prompts need intervention.
- **Lucky**: Misleading. Accuracy looks okay on average but results are unreliable. Treat with caution.
- **Broken**: The worst outcome. Low accuracy and low stability. These prompts are fundamentally difficult for the model.

### Quadrant migration matrices

Migration matrices show how prompts move between quadrants before and after an intervention. For example:

```
From \ To       Robust  Conf.Wrong  Lucky  Broken
Robust            45         0        2       0
Conf.Wrong         8        12        1       3
Lucky              5         0        3       1
Broken             2         1        0       7
```

Reading: Of the 24 prompts that were "Confidently Wrong" before intervention, 8 became "Robust" (recovered), 12 stayed wrong, 1 became "Lucky", and 3 became "Broken". The off-diagonal cells are the interesting ones -- they show intervention impact.

## Interpreting Cost Rollups

Cost rollups aggregate token usage and dollar costs per experimental condition.

### What is calculated

For each (model, noise_type, intervention) group:

| Metric | Description |
|--------|-------------|
| `mean_total_cost_usd` | Average total cost per run (main model + pre-processor) |
| `sum_total_cost_usd` | Total spending for that condition |
| `mean_preproc_cost_usd` | Average pre-processor overhead per run |
| `mean_main_cost_usd` | Average main model cost per run |
| `mean_token_savings` | Average tokens saved by compression (original - optimized) |

### Net ROI

To determine whether an intervention saves money:

```
Net savings = (cost_reduction_from_fewer_tokens) - (preproc_overhead)
```

- **Positive net savings**: The compression reduces main model costs by more than the pre-processor costs. Worth using.
- **Negative net savings**: The pre-processor overhead exceeds the savings. Raw prompts are cheaper.
- **Zero pre-processor cost**: `raw` and `prompt_repetition` interventions have no pre-processor, so their cost is purely main model.

### Per-model breakdown

Compare across models: expensive models (Claude, GPT-4o) benefit more from compression because the per-token savings are larger. Free models (Nemotron via OpenRouter) have zero main model cost, so pre-processing is pure overhead.

## Interpreting Figures

The toolkit generates four publication figure types.

### FIG-01: Accuracy Degradation Curves

- **X-axis**: Noise level (clean, 5%, 10%, 20% for Type A; or Type B variants)
- **Y-axis**: Accuracy (mean pass rate)
- **Facets**: By model and/or intervention type
- **What to look for**: The slope of degradation. Steeper = more fragile. Interventions that flatten the curve are effective.

### FIG-02: Stability-Correctness Quadrant Scatter

- **X-axis**: Accuracy (proportion of passes)
- **Y-axis**: Consistency Rate (CR)
- **Each dot**: One prompt-condition-model triple
- **Quadrant lines**: Vertical at 0.5 accuracy, horizontal at 0.8 CR
- **What to look for**: Cluster positions. A good intervention shifts dots toward the upper-right (Robust) quadrant. Migration arrows (if shown) illustrate movement.

### FIG-03: Cost-Benefit Heatmap

- **Rows**: Intervention types
- **Columns**: Models or noise conditions
- **Color**: Net token savings (green = saves tokens, red = costs more)
- **What to look for**: Which intervention-model combinations have the best cost-benefit ratio. Dark green cells are sweet spots.

### FIG-04: Kendall's Tau Rank-Stability Bar Chart

- **X-axis**: Comparison pairs (e.g., "5% vs 10%", "Type A vs Type B")
- **Y-axis**: Kendall's tau value (-1 to +1)
- **What to look for**: High bars = similar difficulty ranking between conditions. Low bars = different prompts are affected. Comparing within-type vs. across-type reveals whether noise mechanisms differ.

## Common SQLite Queries

Ready-to-run queries against `results/results.db`. Open with `sqlite3 results/results.db` or any SQLite client.

### Accuracy by noise level

```sql
SELECT noise_type,
       AVG(CASE WHEN pass_fail = 1 THEN 1.0 ELSE 0.0 END) AS accuracy,
       COUNT(*) AS n_runs
FROM experiment_runs
WHERE status = 'completed'
GROUP BY noise_type
ORDER BY accuracy DESC;
```

### Accuracy by model and intervention

```sql
SELECT model,
       intervention,
       AVG(CASE WHEN pass_fail = 1 THEN 1.0 ELSE 0.0 END) AS accuracy,
       COUNT(*) AS n_runs
FROM experiment_runs
WHERE status = 'completed'
GROUP BY model, intervention
ORDER BY model, accuracy DESC;
```

### Cost per model

```sql
SELECT model,
       SUM(total_cost_usd) AS total_cost,
       AVG(total_cost_usd) AS avg_cost_per_run,
       COUNT(*) AS n_runs
FROM experiment_runs
WHERE status = 'completed'
GROUP BY model
ORDER BY total_cost DESC;
```

### Most fragile prompts

Prompts that pass clean but fail noisy most often:

```sql
SELECT e_clean.prompt_id,
       e_clean.model,
       COUNT(*) AS noisy_fails
FROM experiment_runs e_clean
JOIN experiment_runs e_noisy
  ON e_clean.prompt_id = e_noisy.prompt_id
  AND e_clean.model = e_noisy.model
  AND e_clean.intervention = e_noisy.intervention
WHERE e_clean.noise_type = 'clean'
  AND e_clean.pass_fail = 1
  AND e_noisy.noise_type != 'clean'
  AND e_noisy.pass_fail = 0
  AND e_clean.status = 'completed'
  AND e_noisy.status = 'completed'
GROUP BY e_clean.prompt_id, e_clean.model
ORDER BY noisy_fails DESC
LIMIT 20;
```

### Most recovered prompts

Prompts that fail with raw intervention but pass with pre-processing:

```sql
SELECT e_raw.prompt_id,
       e_raw.model,
       e_raw.noise_type,
       COUNT(*) AS recoveries
FROM experiment_runs e_raw
JOIN experiment_runs e_proc
  ON e_raw.prompt_id = e_proc.prompt_id
  AND e_raw.model = e_proc.model
  AND e_raw.noise_type = e_proc.noise_type
  AND e_raw.repetition = e_proc.repetition
WHERE e_raw.intervention = 'raw'
  AND e_raw.pass_fail = 0
  AND e_proc.intervention = 'pre_proc_sanitize'
  AND e_proc.pass_fail = 1
  AND e_raw.status = 'completed'
  AND e_proc.status = 'completed'
GROUP BY e_raw.prompt_id, e_raw.model, e_raw.noise_type
ORDER BY recoveries DESC
LIMIT 20;
```

### CR distribution by condition

```sql
SELECT condition,
       model,
       AVG(consistency_rate) AS mean_cr,
       MIN(consistency_rate) AS min_cr,
       MAX(consistency_rate) AS max_cr,
       COUNT(*) AS n_prompts
FROM derived_metrics
GROUP BY condition, model
ORDER BY mean_cr ASC;
```

## Cross-References

- [Research Design Document](RDD_Linguistic_Tax_v4.md) -- Full statistical methodology (Sections 7.2-7.8)
- [Architecture](architecture.md) -- Module descriptions and data flow diagrams
- [Getting Started](getting-started.md) -- Running experiments and generating results
