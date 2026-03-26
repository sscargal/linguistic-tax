---
phase: quick-260326-vzd
plan: 01
subsystem: cli
tags: [bugfix, qa, slicer-removal]
---

# Quick Task 260326-vzd: Fix slicer references and QA script failures

## Changes

1. **Replaced "slicer" with "experiment toolkit"** in 3 source files:
   - `src/cli.py:80` — setup subcommand help text
   - `src/pilot.py:1178` — config-not-found error message
   - `src/run_experiment.py:571` — config-not-found error message

2. **Fixed `--help` failing without config** in 2 modules:
   - `src/run_experiment.py` — moved `_check_config_exists()` after `parser.parse_args()` so `--help` works without a config file
   - `src/pilot.py` — same fix

## Result

QA script: 38 PASS, 0 FAIL, 1 WARN (expected: missing OPENROUTER_API_KEY), 2 INFO. Verdict: **PASS**.
