# GSD Project Description — Linguistic Tax Research Toolkit

## What Are We Building?

A Python research toolkit that measures how prompt noise (typos, grammar
errors, ESL patterns) and prompt bloat (redundancy, verbosity) degrade
LLM reasoning accuracy, and whether automated "prompt optimization"
(sanitization + compression) can recover that accuracy while reducing
token costs.

This is NOT a web app. It is a set of Python scripts and modules that:
1. Generate controlled noise variants of benchmark prompts
2. Compress verbose prompts by removing redundancy
3. Duplicate prompts for the "prompt repetition" intervention
4. Execute prompts against LLM APIs (Claude, Gemini) and log results
5. Auto-grade outputs against benchmark answers
6. Perform statistical analysis (GLMM, bootstrap, McNemar's)
7. Generate figures for an ArXiv paper

## Target Users

The researcher (me) running experiments from the command line.
No UI needed. No deployment. CLI-only.

## Tech Preferences

- Python 3.11+ (no other languages)
- Direct API calls via `anthropic` and `google-generativeai` SDKs
- SQLite for results storage (not Postgres, not flat files)
- pytest for testing
- Standard library `logging` (not print statements)
- Type hints everywhere
- No frameworks (no Flask, no FastAPI, no Django)

## What Success Looks Like

After Phase 1 (tooling), I can run:
```
python src/noise_generator.py --input data/prompts.json --type char --rate 0.10 --seed 42 --output data/noisy_10pct.json
python src/prompt_compressor.py --input data/prompts.json --output data/compressed.json
python src/run_experiment.py --matrix data/experiment_matrix.json --pilot 20 --output results/pilot.db
python src/grade_results.py --db results/pilot.db
python src/analyze_results.py --db results/pilot.db --output figures/
```

And get a pilot dataset of 20 prompts across all conditions with
pass/fail grades, token counts, TTFT/TTLT, costs, and stability
metrics.

## Constraints

- Must work offline (no network) for noise generation and grading
- API calls require ANTHROPIC_API_KEY and GOOGLE_API_KEY env vars
- All randomness uses fixed seeds for reproducibility
- Must not exceed ~$15 for the pilot run (20 prompts)
- Results must be stored in SQLite with the schema from the RDD

## The RDD Is The Spec

The full Research Design Document is at docs/RDD_Linguistic_Tax_v4.md.
It defines every parameter, every metric, every experimental condition.
GSD should read it as the project requirements source.

## Phase Structure (Suggested for GSD Roadmap)

Phase 1: Noise Generator (Type A character-level noise)
Phase 2: Noise Generator (Type B ESL syntactic patterns)
Phase 3: Prompt Compressor
Phase 4: Prompt Repeater + Intervention Pipeline
Phase 5: Execution Harness + Grading
Phase 6: Pilot Run (20 prompts, validate everything)
Phase 7: Statistical Analysis Module
Phase 8: Figure Generation

After Phase 8, we switch to API-driven experiment execution
(outside GSD) for the full 20,000-call matrix.
