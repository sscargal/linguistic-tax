---
created: 2026-03-28T19:04:22.157Z
title: Fix GSM8K number extraction last-number heuristic
area: general
files:
  - src/grade_results.py
  - tests/test_grade_results.py
---

## Problem

The GSM8K number extractor (`_extract_number`) takes the LAST number in the entire output. Modern LLMs typically state the answer early then add explanatory working, parenthetical notes, or alternative calculations containing intermediate numbers. This causes 173 out of 184 GSM8K failures (94%) to be misextractions — the model produced the correct answer but the extractor grabbed a trailing intermediate value.

Examples:
- "You paid $35 (your wife paid $25)." → extracts 25, not 35
- "$35. Calculation: half of $50 is $25..." → extracts 25, not 35
- "60 + 15 = 75 mL. (Assumes 'weaker' means...15...)" → extracts 15, not 75

Impact: GSM8K accuracy appears 85% but is actually ~99%. This would invalidate noise impact conclusions for math benchmarks.

## Solution

Improve extraction with a priority cascade:
1. `\boxed{answer}` (already handled, highest priority)
2. `#### answer` (standard GSM8K delimiter — not currently checked)
3. `Answer: N` or `answer is N` pattern
4. Number on a standalone final line
5. Last number before a parenthetical `(` or `—` explanation
6. Fall back to last number (current behavior)

The key insight: avoid numbers inside parentheticals, "if"/"note" clauses, and explanatory text that follows the actual answer.
