---
created: 2026-03-27T04:30:00.000Z
title: "Investigate grading crash failures in pilot data"
area: general
files:
  - src/grade_results.py
  - results/results.db
---

## Problem

Pilot FAIL examples show `fail_reason: crash` with `extraction_method: None` — the HumanEval/MBPP code execution sandbox is crashing rather than producing wrong answers. This means the 59.6% pass rate may reflect grading infrastructure issues, not model reasoning failures.

Need to determine:
- What fraction of FAILs are crashes vs wrong answers?
- Are crashes model output format issues (code not extractable) or sandbox issues?
- Does GPT-5.1's output format differ from what the grading regex expects?

## Solution

1. **Query crash vs wrong-answer ratio**: `SELECT fail_reason, COUNT(*) FROM grading_details GROUP BY fail_reason`
2. **Inspect crash examples** — are they code extraction failures (model didn't produce valid Python) or execution failures (code ran but crashed)?
3. **Check if model output format needs new extraction patterns** — GPT-5.1 may wrap code differently than expected
4. **Add crash rate to `propt report`** — show fail_reason breakdown alongside pass rate
