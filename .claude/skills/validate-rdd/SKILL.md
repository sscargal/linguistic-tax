---
name: validate-rdd
description: Verify that the Linguistic Tax codebase correctly implements the Research Design Document (RDD) specification. Use this skill whenever the user asks to validate the implementation against the RDD, check for RDD compliance, verify experimental parameters match the spec, audit the code against the research design, or wants to know if anything has drifted from the specification. Also trigger when the user mentions "RDD compliance", "does the code match the spec", "validate parameters", or "check the implementation".
---

# Validate RDD

Cross-reference the codebase against `docs/RDD_Linguistic_Tax_v4.md` to find deviations between what the RDD specifies and what the code implements. The RDD is the source of truth for all experimental parameters.

## Why this matters

The RDD defines the exact experimental design that will be described in the ArXiv paper. Any deviation between the code and the RDD means either: (a) the paper will describe something different from what actually ran, or (b) the experiments won't produce the results the paper claims. Both are fatal for a research publication.

## Validation dimensions

Check each of these areas. Read the relevant source files and RDD sections, then compare. Report deviations as a checklist with PASS/FAIL/WARN status.

### 1. Noise parameters (RDD Section 5.1)

Read `src/noise_generator.py` and `src/config.py`, compare against RDD:

| Parameter | RDD Spec | Where to check |
|-----------|----------|----------------|
| Type A rates | 5%, 10%, 20% | `config.py:type_a_rates` |
| Type A mutation weights | 40% adj-key, 25% omission, 20% doubling, 15% transposition | `noise_generator.py` mutation weights |
| Seed determinism | Same seed = same output | `config.py:derive_seed()` + noise generator seed usage |
| Keyword protection | Technical terms not mutated | `noise_generator.py` keyword/protected token logic |
| Type B L1 patterns | Mandarin (article omission), Spanish (preposition), Japanese (topic-comment), Mixed ESL (tense/aspect) | `noise_generator.py` Type B functions |

### 2. Intervention definitions (RDD Section 6)

Read `src/prompt_compressor.py`, `src/prompt_repeater.py`, `src/run_experiment.py`:

| Intervention | RDD Spec | Where to check |
|-------------|----------|----------------|
| Raw | No processing, noisy prompt direct to model | `run_experiment.py` raw pathway |
| Self-Correct | Prepend "First, correct any spelling/grammar errors..." | `prompt_compressor.py:build_self_correct_prompt()` |
| Pre-Proc Sanitize | External cheap model call to clean prompt | `prompt_compressor.py:sanitize()` + preproc model mapping |
| Pre-Proc Sanitize+Compress | Sanitize then compress (dedup + condensation) | `prompt_compressor.py:sanitize_and_compress()` |
| Prompt Repetition | Duplicate input: `<QUERY><QUERY>` | `prompt_repeater.py:repeat_prompt()` |

### 3. Model configuration (RDD Section 4.2)

Read `src/model_registry.py`, `src/config.py`, and `src/api_client.py`:

| Parameter | RDD Spec | Where to check |
|-----------|----------|----------------|
| Models under test | Dynamically configured models from model registry (1-4+ models) | `model_registry.target_models()` (from `src/model_registry.py`) |
| Model versions pinned | Exact version strings, not "latest" | `model_registry` model configs (`ModelConfig.model_id`) |
| Temperature | 0.0 for all calls | `config.py:temperature`, `api_client.py` call sites |
| Pre-processor models | Cheap models (Haiku/Flash) for sanitize/compress | `model_registry.get_preproc(model_id)` (from `src/model_registry.py`) |

### 4. Experiment design (RDD Section 4.1, 4.3)

Read `data/experiment_matrix.json` structure, `src/config.py`:

| Parameter | RDD Spec | Where to check |
|-----------|----------|----------------|
| Prompt count | 200 (sampled subset) | `data/prompts.json` length |
| Benchmarks | HumanEval, MBPP, GSM8K | `data/prompts.json` benchmark_source values |
| Repetitions | 5 per condition | `config.py:repetitions` |
| Matrix size | ~20,000 LLM calls | `data/experiment_matrix.json` entry count |
| Noise types | 8 (clean + 3 Type A + 4 Type B) | `config.py:NOISE_TYPES` |
| Interventions | 5 | `config.py:INTERVENTIONS` |

### 5. Statistical methods (RDD Section 7)

Read `src/analyze_results.py` and `src/compute_derived.py`:

| Method | RDD Spec | Where to check |
|--------|----------|----------------|
| GLMM | Binary pass/fail with random effects | `analyze_results.py:fit_glmm()` |
| Bootstrap CIs | 10,000 resamples, 95% CI | `analyze_results.py` bootstrap params |
| McNemar's test | Pairwise prompt-level 2x2 tables | `analyze_results.py` mcnemar function |
| Kendall's tau | Rank-order stability clean vs noisy | `analyze_results.py` kendall function |
| BH correction | FDR at 5% | `analyze_results.py` multipletests usage |
| Consistency Rate | C(5,2)=10 pairwise comparisons | `compute_derived.py:compute_cr()` |
| Quadrant classification | CR>=0.8 threshold, majority vote | `compute_derived.py:classify_quadrant()` |

### 6. Grading (RDD Section implied by benchmarks)

Read `src/grade_results.py`:

| Parameter | RDD Spec | Where to check |
|-----------|----------|----------------|
| HumanEval grading | Execution sandbox, pass/fail | `grade_results.py` HumanEval grading |
| GSM8K grading | Numerical regex match | `grade_results.py` GSM8K grading |
| MBPP grading | Execution sandbox | `grade_results.py` MBPP grading |

### 7. Logging and instrumentation (RDD Section 8.3)

Read `src/run_experiment.py`, `src/db.py`:

| Requirement | RDD Spec | Where to check |
|-------------|----------|----------------|
| TTFT logging | Time to first token | `run_experiment.py` / `api_client.py` timing |
| TTLT logging | Time to last token | Same |
| Token counts | Input and output tokens per call | `db.py` schema columns |
| Cost tracking | Per-call USD cost | `db.py` cost columns, `model_registry.compute_cost(model_id, in_tok, out_tok)` (from `src/model_registry.py`) |
| Pre-proc tracking | Separate logging for optimizer calls | `db.py` preproc columns |

### 8. Configuration management

Read `src/config_manager.py`, `src/model_registry.py`, `src/env_manager.py`, `src/setup_wizard.py`, `src/model_discovery.py`:

| Parameter | Expected | Where to check |
|-----------|----------|----------------|
| Config loading | `load_config()` loads ExperimentConfig v2 with `models` list field | `config_manager.py:load_config()` |
| Config persistence | `save_config()` persists to JSON | `config_manager.py:save_config()` |
| Config validation | `validate_config()` validates the config | `config_manager.py:validate_config()` |
| Model registry | `ModelRegistry` singleton is the source of truth for model data | `model_registry.py:ModelRegistry` |
| API key validation | `check_keys()` validates API keys are present | `env_manager.py:check_keys()` |
| Setup wizard | `run_setup_wizard()` configures models and providers | `setup_wizard.py:run_setup_wizard()` |
| Model discovery | `discover_all_models()` queries live model listings | `model_discovery.py:discover_all_models()` |

## Process

1. Read `docs/RDD_Linguistic_Tax_v4.md` sections relevant to the checks above
2. Read each source file mentioned in the "Where to check" columns
3. Compare actual implementation against RDD spec
4. For each check, determine: PASS (matches), FAIL (deviates), or WARN (partially matches or unclear)
5. Present as a compliance matrix table
6. For any FAIL items, explain the deviation and suggest a fix
7. For WARN items, explain what's ambiguous

## Output format

```markdown
# RDD Compliance Report

**Date:** [date]
**RDD Version:** 4.0
**Overall:** X/Y checks passed, Z warnings

## Results

| # | Category | Check | Status | Notes |
|---|----------|-------|--------|-------|
| 1 | Noise | Type A rates match | PASS | 5%, 10%, 20% confirmed |
| 2 | Noise | Mutation weights match | FAIL | Code has 35/25/20/20, RDD says 40/25/20/15 |
| ... | ... | ... | ... | ... |

## Deviations requiring action

### [FAIL] Mutation weights (Noise #2)
- **RDD says:** 40% adjacent key, 25% omission, 20% doubling, 15% transposition
- **Code has:** [actual values]
- **Impact:** Different noise distribution could affect results
- **Fix:** Update `noise_generator.py` line XX or update RDD Section 5.1

## Warnings

### [WARN] Matrix size exceeds RDD
- **RDD says:** ~20,000 calls
- **Code has:** ~82,000 entries
- **Assessment:** Code tests all Type A levels and Type B sub-types individually, which is more thorough but 4x the RDD budget
```
