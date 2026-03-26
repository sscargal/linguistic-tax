---
created: 2026-03-26T03:05:17.203Z
title: Experiment with provider prompt best practices as preprocessing
area: general
files:
  - src/prompt_compressor.py
  - src/noise_generator.py
  - src/run_experiment.py
---

## Problem

The current pre-processing pipeline only sanitizes (fix typos, grammar) and compresses (dedup, condense) prompts. Model providers publish detailed prompt engineering guides with best practices specific to their models. There's an open question: should the pre-processor also adapt prompts to follow provider-specific best practices, not just clean them up?

This opens several research directions:
1. **Best-practice adaptation as intervention:** A new intervention type where the pre-processor rewrites the prompt following the target model's official prompt guide (e.g., OpenAI's prompting guidance, Google's prompting strategies)
2. **A/B testing original vs best-practice prompts:** Compare the user's original prompt against a version rewritten per best practices to measure the effect
3. **Internet prompt guides:** Many third-party prompt guides exist that could be tested as alternative preprocessing strategies
4. **User-defined prompt styles/formats:** Allow researchers to define custom prompt templates and formats that the pre-processor applies

### Reference guides
- OpenAI: https://developers.openai.com/api/docs/guides/latest-model#prompting-guidance
- Google Gemini: https://ai.google.dev/gemini-api/docs/prompting-strategies

## Solution

TBD -- This is a significant experiment design extension. Potential approaches:
- Add a new intervention type (e.g., "Pre-Proc Best-Practice") that uses a cheap model to rewrite prompts per provider guidelines
- Encode provider best practices as structured rules or templates the pre-processor can apply
- Could become its own phase or milestone given the scope (new intervention types, new experiment conditions, potentially new hypothesis)
- Consider whether this fits within the existing 5-intervention framework or requires expanding it
