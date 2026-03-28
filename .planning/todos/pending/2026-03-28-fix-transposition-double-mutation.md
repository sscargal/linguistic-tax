---
created: 2026-03-28T19:19:59.224Z
title: "Fix transposition double-mutation in noise generator"
area: general
files:
  - src/noise_generator.py
---

## Problem

The transposition mutation only skips the next character if it's immediately adjacent (`next_idx == i + 1`). When `next_idx > i + 1` (because intervening characters are protected/whitespace), the swapped character at `next_idx` will be visited again in a later iteration and potentially mutated a second time.

At low error rates (5%) this rarely triggers. At 20%, it causes occasional double-mutations, making the effective mutation rate slightly higher than nominal.

## Solution

Track all positions that have been involved in a swap (both source and target) in a set. Skip any position already in the set during subsequent iterations.
