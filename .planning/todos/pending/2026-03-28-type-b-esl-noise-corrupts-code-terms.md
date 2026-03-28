---
created: 2026-03-28T19:19:59.224Z
title: "Type B ESL noise corrupts code terms in prompts"
area: general
files:
  - src/noise_generator.py
---

## Problem

Type A noise carefully avoids protected spans (Python keywords, function names, operators). Type B ESL noise applies regex transformations to the ENTIRE prompt including code-related text:
- Article omission can remove "a " from code-adjacent text
- Plural omission strips trailing 's' from identifiers like "args", "items", "returns"
- Reflexive overuse transforms "return the result" and could match code patterns
- Adjective placement swaps "sorted list" → "list sorted"

This creates a confound: measured accuracy drops from Type B noise partially reflect code corruption rather than purely "ESL syntactic" noise.

## Solution

Add code-block protection to Type B noise similar to Type A's approach. Identify spans that look like code (indented blocks, lines starting with `def`/`import`/`class`, text inside backtick fences) and exclude them from ESL transformations. Apply ESL patterns only to natural-language portions of the prompt.
