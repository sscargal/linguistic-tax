---
created: 2026-03-27T01:12:30.858Z
title: "Experiment idea: Don't shout at your LLM — all-caps impact"
area: general
files:
  - src/emphasis_converter.py
  - data/experiment_matrix.json
---

## Problem

Inspired by Brendan Gregg's famous Sun Microsystems demonstration where shouting at a storage array measurably impacted spinning disk performance (https://www.youtube.com/watch?v=tDacjrSCeq4), the question is: what happens when you "shout" at an LLM by writing prompts in ALL CAPS?

This is related to the Phase 22 emphasis/formatting work (Cluster B "instruction-word emphasis" and Cluster C "sentence-initial capitalization"), but this todo captures a broader, more provocative framing:
- Does writing an entire prompt in ALL CAPS affect reasoning accuracy?
- Is there a threshold effect (some caps vs ALL caps)?
- Does it affect different benchmarks differently (code vs math)?
- Can the pre-processor "de-shout" a prompt and recover accuracy?

The Brendan Gregg analogy makes this a compelling narrative hook for the paper — "shouting at your hard drive" is a well-known tech folklore story, and "shouting at your LLM" would be an engaging way to frame the emphasis findings.

## Solution

TBD — Phase 22 already built the emphasis conversion infrastructure and generated Cluster B (instruction-word CAPS) and Cluster C (sentence-initial) variants. This todo captures the broader experiment framing and the Gregg reference for the paper narrative. Consider:
- Running the existing emphasis matrix items and analyzing the all-caps subset
- Adding a "full prompt ALL CAPS" variant if not already covered
- Using the Gregg video as a cultural reference in the paper introduction or discussion section
