---
created: 2026-03-28T18:08:17.047Z
title: Investigate compress_only 100 calls vs 800 for other interventions
area: general
files:
  - src/execution_summary.py
---

## Problem

The `compress_only` intervention only had 100 API calls in the pilot while all other interventions had 800. Its 83% pass rate isn't directly comparable to others.

**Investigation result:** `compress_only` is NOT in the RDD — it's an extra intervention added beyond the 5 defined ones. It only runs on clean prompts in the matrix (2000 items total, all noise_type=clean). This is by design: compression without sanitization only makes sense on clean text.

## Solution

The report's intervention table should annotate `compress_only` to indicate it only runs on clean prompts and isn't directly comparable to other interventions that run across all noise conditions. Add a "(clean only)" note or similar in `format_post_run_report()`.
