---
created: 2026-03-28T19:19:59.224Z
title: "Fix AssertionError typo in grading — wrong_answer never classified"
area: general
files:
  - src/grade_results.py
---

## Problem

Line 412 of grade_results.py checks for `"AssertionError"` (typo) instead of `"AssertionError"`. Python raises `AssertionError` (no 'i' after 't'). This means the `wrong_answer` fail_reason is NEVER assigned — all assertion failures fall through to `"crash"`.

Pass/fail results are unaffected (based on returncode), but any analysis of `fail_reason` is broken. Filtering on `fail_reason = 'wrong_answer'` returns zero results.

## Solution

Fix the typo: `"AssertionError"` → `"AssertionError"`. One-line fix.
