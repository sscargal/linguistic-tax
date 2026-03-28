---
created: 2026-03-28T19:19:59.224Z
title: "Fix GSM8K answer extraction for negative numbers"
area: general
files:
  - src/grade_results.py
---

## Problem

The `_RE_ANSWER_IS` and `_RE_ANSWER_COLON` patterns use `[\d,]+\.?\d*` which doesn't allow a leading minus sign. "The answer is -5" won't match, falling through to the less reliable last-number cascade.

## Solution

Update capture groups to allow optional leading minus: `(-?[\d,]+\.?\d*)` in both patterns.
