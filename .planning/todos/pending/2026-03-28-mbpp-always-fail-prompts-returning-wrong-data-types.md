---
created: 2026-03-28T19:04:22.157Z
title: MBPP always-fail prompts returning wrong data types
area: general
files:
  - src/grade_results.py
  - data/prompts.json
---

## Problem

Two MBPP prompts fail 0/5 on raw+clean because the model produces functionally wrong code:
- mbpp_463: Model returns `(max_product, start, end, subarray)` tuple but test expects just the integer product value
- mbpp_106: Model produces two function variants; extractor picks the wrong one (`append_list_as_single_element` instead of `append_list_to_tuple_elements`)

These are genuine model failures, not grading bugs. The aliasing system correctly maps function names, but the model's logic doesn't match the test expectations.

## Solution

1. Check if these prompts are ambiguous — is the model's interpretation reasonable given the prompt text?
2. If prompts are ambiguous, consider whether the test assertions are too strict or if the prompt needs clarification
3. For mbpp_106 (two variants), the code extractor now prefers blocks matching the expected function name — verify this helps on re-run
4. Mostly: document as known difficulty items. MBPP 48% clean baseline is partially explained by prompt ambiguity, not just model weakness
