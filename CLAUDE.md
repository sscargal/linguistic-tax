# Linguistic Tax Research Project

## Project Overview

This is a research project producing an ArXiv paper titled "The Linguistic Tax: Quantifying Prompt Noise and Bloat in LLM Reasoning, and the Case for Automated Prompt Optimization." The Research Design Document (RDD) is the source of truth: `docs/RDD_Linguistic_Tax_v4.md`.

## What This Project Does

We measure how typos, grammatical errors, and verbose/duplicated prompts degrade LLM reasoning accuracy, then build and test a "prompt optimizer" (sanitizer + compressor) that recovers lost accuracy AND reduces token costs. We also test Google's prompt repetition technique as a zero-cost alternative.

## Architecture

This is NOT a web app or service. It is a research toolkit:

```
src/
  analyze_results.py     — GLMM, bootstrap CIs, McNemar's, Kendall's tau
  api_client.py          — Multi-provider API wrapper (Anthropic, Google, OpenAI, OpenRouter)
  cli.py                 — CLI entry point with 9 subcommands
  compute_derived.py     — Stability (CR), quadrant classification, cost rollups
  config.py              — ExperimentConfig, noise types, intervention constants
  config_commands.py     — Config subcommand handlers
  config_manager.py      — Config file I/O and validation
  db.py                  — SQLite schema and queries
  env_manager.py         — .env file loading, writing, and API key management
  execution_summary.py   — Pre-execution summary and confirmation gate
  generate_figures.py    — Publication figure generation
  grade_results.py       — Auto-grade outputs (HumanEval sandbox, GSM8K regex)
  model_discovery.py     — Live model queries from provider APIs
  model_registry.py      — Config-driven pricing, preproc mappings, rate limits
  noise_generator.py     — Inject controlled typos/ESL patterns into prompts
  pilot.py               — Pilot validation (20-prompt subset)
  prompt_compressor.py   — Compress prompts via dedup + condensation
  prompt_repeater.py     — Implement <QUERY><QUERY> repetition (Leviathan et al.)
  run_experiment.py      — Execution harness: send prompts to LLMs, log everything
  setup_wizard.py        — Interactive setup wizard

data/
  prompts.json           — 200 clean benchmark prompts (HumanEval, MBPP, GSM8K)
  experiment_matrix.json — Full experimental design (prompt x noise x intervention)
  default_models.json    — Default model configurations for 4 providers
  real_world_noisy/      — 20 real noisy prompts from public sources

results/                 — Populated by experiments (gitignored)
  results.db             — SQLite database of all experimental runs

docs/
  RDD_Linguistic_Tax_v4.md — Research Design Document (the spec)
  research_program.md      — Karpathy-style instructions for autonomous runs

figures/                 — Generated plots for the paper
```

## Tech Stack

- **Language:** Python 3.12+
- **APIs:** Anthropic (Claude), Google (Gemini), OpenAI (GPT), OpenRouter — direct API calls, NOT CLI
- **Statistics:** statsmodels (GLMM), scipy (McNemar's, bootstrap), bert-score
- **Data:** SQLite for results, JSON for prompts/configs
- **Grading:** HumanEval execution sandbox, regex matching for GSM8K

## Key Conventions

- All noise generation uses FIXED RANDOM SEEDS for reproducibility
- All API calls use temperature=0.0
- Every API call logs: TTFT, TTLT, token counts (in/out), cost, pass/fail
- Model versions are PINNED (e.g., "claude-sonnet-4-20250514")
- American English throughout
- Type hints on all Python functions
- Docstrings on all public functions

## Important Context

- The RDD (docs/RDD_Linguistic_Tax_v4.md) defines ALL experimental parameters
- Do NOT change experimental parameters without updating the RDD first
- The experiment matrix has 5 intervention types: Raw, Self-Correct, Pre-Proc
  Sanitize, Pre-Proc Sanitize+Compress, and Prompt Repetition
- Noise types: Type A (character-level, 5/10/20%) and Type B (ESL syntactic)
- We measure BOTH correctness AND stability (5 repetitions per condition)
- Pre-processor calls use a CHEAP model (configurable per provider via ModelRegistry)

## What NOT To Do

- Do NOT use Claude Code CLI for experiment execution — use API scripts
- Do NOT hardcode API keys — use environment variables
- Do NOT modify benchmark prompts — only inject noise into copies
- Do NOT run the full 20,000-call matrix without a pilot (20 prompts first)
- Do NOT use print() for logging — use Python logging module
- Do NOT store results as flat JSON files — use SQLite

## Testing

- Every module has a corresponding test file in tests/
- Run: `pytest tests/ -v`
- Noise generator tests verify determinism (same seed = same output)
- Grading tests verify against known HumanEval/GSM8K answers
- Use `pytest tests/ -k pilot` to run the 20-prompt pilot suite
