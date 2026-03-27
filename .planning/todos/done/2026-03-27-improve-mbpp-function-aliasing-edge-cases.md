---
created: 2026-03-27T06:00:00.000Z
title: "Improve MBPP function aliasing for edge cases"
area: general
files:
  - src/grade_results.py
---

## Problem

The function name aliasing fix (matching first `def` in LLM code to first function call in assertions) doesn't catch all cases:

- Multiple `def` statements — the first may be a helper, not the target function
- Class methods — `def method(self, ...)` inside a class
- The LLM defines the function with a completely unrelated name structure
- Test assertions call multiple different functions

Current alias regex: `re.search(r'def (\w+)\(', llm_code)` — only matches the first function.

## Solution

1. Extract the expected function name from test assertions (already done)
2. Search ALL `def` statements in the LLM code for the best match — prefer names that share words with the expected name
3. If no reasonable match, try fuzzy matching (Levenshtein or shared substrings)
4. Consider adding the expected function name to the prompt itself: "Write a function called `{expected_name}`..."
