---
created: 2026-03-27T04:30:00.000Z
title: "Inspect pre-processor output and fix chatty responses"
area: general
files:
  - src/prompt_compressor.py
  - src/run_experiment.py
  - src/db.py
  - src/cli.py
---

## Problem

Pilot data shows the pre-processor (gpt-5-nano) generating 869K output tokens from 172K input — a 5x ratio. For sanitization ("fix typos, return only cleaned text"), output should be ~1x input. The model is likely generating explanations or chain-of-thought despite "no explanation" in the instruction.

Additionally:
- Pre-processor TTFT is 3633ms (7x slower than target's 521ms) — possibly caused by generating too much output
- Pre-processor output is NOT stored in the DB — only the final prompt_text (which may be the fallback noisy text if the preproc output was too long)
- The fallback threshold (1.5x input length) triggers silently, discarding preproc work and using the noisy original
- Need a `propt inspect` or `propt report --detail` command to view preproc outputs

## Solution

1. **Store preproc raw output** in a new `preproc_raw_output` column in experiment_runs
2. **Add `propt inspect` subcommand** — show individual run details including preproc input/output
3. **Tighten sanitization prompt** — add explicit instructions like "Do not explain. Do not add reasoning. Output ONLY the corrected text."
4. **Reduce max_tokens** for sanitization — `max(512, len(text)*2)` is too generous; try `max(256, int(len(text)*1.2))`
5. **Log fallback rate** in the post-run report (how often preproc output was discarded)
