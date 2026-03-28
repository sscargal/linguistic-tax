---
created: 2026-03-28T18:08:17.047Z
title: Fix triple pre-execution summary in pilot run
area: general
files:
  - src/pilot.py
  - src/run_experiment.py
---

## Problem

Running `propt pilot` prints the pre-execution summary 3 times before the experiment starts. It should only display once. The pilot flow likely calls into run_experiment which prints its own summary, and there may be redundant calls in the pilot wrapper.

## Solution

Trace the call path from `pilot.py` into `run_experiment.py` and find where the summary is printed multiple times. Likely need to either:
- Add a flag to suppress the summary in `run_experiment` when called from `pilot`
- Remove duplicate summary calls in the pilot flow
