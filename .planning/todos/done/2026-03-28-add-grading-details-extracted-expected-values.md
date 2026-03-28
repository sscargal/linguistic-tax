---
created: 2026-03-28T19:19:59.224Z
title: "Add extracted/expected values to grading_details table"
area: general
files:
  - src/db.py
  - src/grade_results.py
---

## Problem

The `grading_details` table stores `fail_reason`, `extraction_method`, `stdout`, `stderr`, but is missing:
- `extracted_value REAL` — the number extracted from GSM8K output
- `expected_value REAL` — the canonical answer being compared against
- `extracted_raw_match TEXT` — the raw string before normalization
- `extracted_code TEXT` — the code extracted from HumanEval/MBPP output

These values are computed during grading but not persisted. Debugging extraction failures requires re-running the grader.

## Solution

Add the 4 columns to `grading_details` and populate them from `GradeResult` / `ExtractionResult` in the grading pipeline.
