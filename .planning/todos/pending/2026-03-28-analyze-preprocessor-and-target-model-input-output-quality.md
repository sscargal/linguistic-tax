---
created: 2026-03-28T18:12:00.000Z
title: Analyze preprocessor and target model input/output quality
area: general
files:
  - src/run_experiment.py
  - src/prompt_compressor.py
  - src/noise_generator.py
  - src/grade_results.py
---

## Problem

After the pilot run we need to inspect what the preprocessor and target models are actually receiving and producing. Key questions:
- Is the preprocessor effectively cleaning noisy prompts? (compare noisy input vs cleaned output)
- Is the preprocessor introducing artifacts, losing important content, or being too aggressive?
- Are target model responses in the expected format for grading? (code blocks for HumanEval/MBPP, numeric answers for GSM8K)
- Are there systematic failure patterns? (e.g., certain noise types or benchmarks that consistently produce bad preprocessor output)
- Why does self_correct have a 54.6% pass rate (14% worse than raw)? Is the self-correction prompt causing the model to overthink or change correct answers?
- Why does pre_proc_sanitize_compress (65.2%) perform worse than pre_proc_sanitize alone (71%)?

## Solution

1. Query results.db for sample rows across interventions and noise types
2. Inspect preprocessor input/output pairs to check cleaning quality
3. Inspect target model outputs to check grading compatibility
4. Look at failure cases specifically — what do wrong answers look like?
5. Cross-reference with self_correct and compress interventions to understand why they hurt accuracy
