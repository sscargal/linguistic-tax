---
created: 2026-03-25T23:37:17.217Z
title: Investigate fine-tuned small LM as pre-processor
area: general
files: []
---

## Problem

Currently the pre-processor pipeline uses off-the-shelf cheap models (Haiku, Flash, GPT-4o-mini) to sanitize and compress noisy prompts before sending to the target LLM. An open question is whether fine-tuning a small language model specifically for the sanitization/compression task would improve pre-processing quality and therefore boost downstream target model accuracy compared to using general-purpose cheap models.

## Solution

TBD — research question for future investigation. Would involve:
- Selecting a small open model (e.g., a 1-3B parameter model)
- Creating training data from noisy/clean prompt pairs
- Fine-tuning on the sanitization and compression tasks
- Comparing pre-processed output quality and downstream accuracy against current Haiku/Flash/Mini approach
- Evaluating cost-effectiveness (fine-tuning cost + inference cost vs API costs)
