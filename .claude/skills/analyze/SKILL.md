---
name: analyze
description: Run the statistical analysis pipeline for the Linguistic Tax research project and interpret results against the 5 hypotheses. Use this skill whenever the user wants to analyze experiment results, run statistics, interpret findings, check if hypotheses are supported, compute GLMM/bootstrap/McNemar/Kendall analyses, compare configured models, or understand what the data shows. Also trigger when the user says "analyze results", "run the stats", "what do the results show", "are the hypotheses supported", "compute derived metrics", "run the analysis pipeline", or "compare configured models".
---

# Analyze Results

Run the full statistical analysis pipeline on experiment results and interpret findings against the 5 research hypotheses (H1-H5).

## Pipeline overview

The analysis has three stages that must run in order:

```
Stage 1: Derived metrics    →  Stage 2: Statistical tests  →  Stage 3: Interpretation
(compute_derived.py)           (analyze_results.py)            (map to H1-H5)
```

Note: The analysis pipeline processes results for all models configured in the model registry. The number and identity of models is determined at setup time via `propt setup`, not hardcoded.

## Stage 1: Compute derived metrics

This must run first — it populates the `derived_metrics` table needed by Stage 2.

```bash
python -m src.compute_derived --db results/results.db
```

What it computes:
- **Consistency Rate (CR)**: Pairwise agreement over 5 reps per prompt-condition
- **Quadrant classification**: robust / confidently_wrong / lucky / broken
- **Cost rollups**: Mean cost per condition, token savings, net cost
- **Quadrant migration**: Transition matrices showing how prompts move between quadrants as noise increases

Output: Populates `derived_metrics` table + writes JSON/CSV to `results/`.

## Stage 2: Run statistical tests

### All tests at once (recommended)

```bash
python -m src.analyze_results all --db results/results.db
```

### Individual tests

```bash
python -m src.analyze_results glmm --db results/results.db       # GLMM with fallback
python -m src.analyze_results bootstrap --db results/results.db   # Bootstrap CIs
python -m src.analyze_results mcnemar --db results/results.db     # McNemar's pairwise
python -m src.analyze_results kendall --db results/results.db     # Kendall's tau
python -m src.analyze_results sensitivity --db results/results.db # Sensitivity analysis
```

Output: JSON + CSV + terminal summary in `results/analysis/`.

### What each test does

| Test | What it measures | Key output |
|------|-----------------|------------|
| **GLMM** | Effect of noise_type, intervention, model on pass/fail (with prompt random effects) | Coefficients, odds ratios, p-values |
| **Bootstrap** | 95% CIs for accuracy per condition (10,000 resamples) | CI bounds per (noise_type, intervention, model) |
| **McNemar's** | Per-prompt changes between conditions (fragile/recoverable prompts) | BH-corrected p-values, fragile prompt set |
| **Kendall's tau** | Rank-order stability of prompt difficulty across noise levels | tau values (1.0 = uniform tax, <1.0 = targeted tax) |
| **Sensitivity** | Effect of removing easy/hard prompts | Robustness of main findings |

## Stage 3: Interpret results

After running the analysis, map findings to the 5 hypotheses. Read the output files in `results/analysis/` and interpret.

### H1 — The Noise Cliff

**What to look for:** GLMM coefficients for noise_type. Is the effect non-linear?

- Compare accuracy at 5%, 10%, 20% noise levels
- Look for a threshold where accuracy drops sharply
- Bootstrap CIs show whether the differences are significant
- If the curve is gradual (linear), H1 is not supported — noise degrades smoothly

**Key metric:** Robustness Ratio R = Accuracy_Noisy / Accuracy_Clean at each level.

### H2 — The Compression Dividend

**What to look for:** Compression experiment results (Experiment 2).

- Token reduction percentage for compressed vs. original
- Accuracy preservation (delta should be near zero)
- BERTScore similarity (should be >0.95)

**Key metric:** Token Reduction TR = 1 - (Tokens_Compressed / Tokens_Original).

### H3 — The Recovery Rate

**What to look for:** Compare noisy-raw vs. noisy-intervened accuracy.

- Recovery Rate RR = (Acc_Intervened - Acc_Noisy) / (Acc_Clean - Acc_Noisy)
- Net token cost accounting for pre-processor overhead
- Does Sanitize+Compress have positive ROI?

**Key metric:** RR > 0.80 supports H3.

### H4 — The ESL Penalty

**What to look for:** GLMM interaction between noise_type and intervention.

- Compare Type A (character noise) vs Type B (syntactic noise) degradation
- At equivalent "severity," does Type B cause more damage?
- Which L1 patterns are worst? (Mandarin, Spanish, Japanese, Mixed)

**Key metric:** Compare R values for Type A 10% vs Type B patterns.

### H5 — The Stability Illusion

**What to look for:** Quadrant migration from `compute_derived` output.

- Do prompts move from "robust" to "confidently_wrong" (silent failure)?
- Or from "robust" to "broken" (visible failure)?
- Migration to "confidently_wrong" is the dangerous finding (H5 supported)

**Key metric:** Proportion of prompts in each quadrant per noise level.

## Presenting results

When the user asks what the data shows, present:

1. **One-line headline**: The most important finding
2. **Hypothesis scorecard**: H1-H5 each rated as Supported / Partially Supported / Not Supported / Insufficient Data
3. **Key numbers**: R, RR, TR values with CIs
4. **Surprises**: Anything unexpected (e.g., prompt repetition outperforming sanitization)
5. **Paper implications**: Which sections of the paper can be written from these results

## Important notes

- All analysis requires completed experiment runs in `results/results.db`
- The GLMM has a 3-level fallback chain (BayesMixedGLM → reduced → GEE → logistic)
- All p-values are BH-corrected for multiple comparisons
- Bootstrap uses 10,000 iterations with seed=42 for reproducibility
- Effect sizes (odds ratios with CIs) are always reported alongside p-values
- Results include data for all configured models — the analysis automatically handles variable model counts
