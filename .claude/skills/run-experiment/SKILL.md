---
name: run-experiment
description: Execute the full experiment matrix or targeted subsets for the Linguistic Tax research project. Use this skill whenever the user wants to run experiments, execute the full matrix, run a specific model or intervention, resume interrupted runs, retry failed runs, or check execution cost before running. Also trigger when the user says "run experiments", "start the full run", "run claude only", "retry failed", "resume experiments", "how much will this cost", or "execute the matrix".
---

# Run Experiment

Execute experiment runs from the Linguistic Tax experimental matrix. Supports full runs, filtered runs (by model/intervention), resumability, and cost-gated execution.

## Prerequisites

Before running, ensure:
1. **Pilot completed successfully** — use `/check-results` to verify
2. **Config valid** — `propt validate`
3. **API keys set** — check environment variables for all target models. Verify with `env_manager.check_keys()` or `propt validate`
4. **Budget understood** — always do a dry run first

## Execution modes

### Dry run (always do this first)

```bash
propt run --dry-run
```

Shows: total items, items already completed, cost estimate, runtime estimate, model/intervention breakdown. Does not make API calls.

### Full matrix execution

```bash
propt run --yes
```

Runs all pending items in the experiment matrix. Skips already-completed runs (resumable by design).

### Filtered by model

```bash
propt run --model claude --yes     # Only Claude Sonnet
propt run --model gemini --yes     # Only Gemini 1.5 Pro
propt run --model gpt --yes        # Only GPT-4o
propt run --model openrouter --yes # Only OpenRouter/Nemotron
propt run --model all --yes        # All models (default)
```

### Filtered by intervention

```bash
propt run --intervention raw --yes
propt run --intervention self_correct --yes
propt run --intervention pre_proc_sanitize --yes
propt run --intervention pre_proc_sanitize_compress --yes
propt run --intervention prompt_repetition --yes
```

### Budget-gated execution

```bash
propt run --budget 50.00 --yes   # Exits non-zero if cost > $50
```

### Retry failed runs

```bash
propt run --retry-failed --yes
```

Reprocesses items that previously failed (status='failed' or 'error').

### Limit run count

```bash
propt run --limit 100 --yes   # Stop after 100 items
```

Useful for incremental testing or budget control.

### Custom database path

```bash
propt run --db results/test_results.db --yes
```

## Execution strategy

The recommended approach for the full ~20,000+ call matrix:

1. **Dry run** to check cost and scope
2. **Run one model at a time** to isolate API issues
3. **Start with the cheapest model** (OpenRouter/Nemotron is free)
4. **Monitor progress** with `/check-results` skill periodically
5. **Resume if interrupted** — the engine skips completed runs automatically

### Recommended execution order

```bash
# 1. Free model first (validates pipeline at zero cost)
propt run --model openrouter --yes

# 2. Check results look reasonable
# (use /check-results skill)

# 3. Cheapest paid model
propt run --model gemini --yes

# 4. More expensive models
propt run --model gpt --yes
propt run --model claude --yes
```

## Monitoring during execution

While experiments run, you can check progress in a separate session:

```bash
# Quick status
sqlite3 results/results.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"

# Per-model progress
sqlite3 results/results.db "SELECT model, status, COUNT(*) FROM experiment_runs GROUP BY model, status;"

# Cost so far
sqlite3 results/results.db "SELECT SUM(total_cost_usd) FROM experiment_runs WHERE status='completed';"
```

Or use the `/check-results` skill for a formatted report.

## After execution completes

1. Run `/check-results` to verify completeness and data quality
2. Run `python -m src.compute_derived --db results/results.db` for derived metrics
3. Run `/analyze` for statistical analysis
4. Run `/generate-figures` for publication plots

## Common issues

| Issue | Fix |
|-------|-----|
| Rate limit errors | Built-in delays per model via `model_registry.get_delay(model_id)` (from `src/model_registry.py`) |
| API key errors | Check environment variables for the target model |
| Partial completion | Just re-run — engine resumes from where it left off |
| Cost overrun | Use `--budget` flag or `--limit` to cap |
| Slow execution | Filter to one model/intervention to parallelize across sessions |

## Important notes

- Every run is logged with full instrumentation: TTFT, TTLT, token counts, cost, pass/fail
- Temperature is fixed at 0.0 for reproducibility
- Each condition has 5 repetitions for stability measurement
- The engine uses deterministic run IDs — re-running produces the same IDs, enabling dedup
- Pre-processing interventions make a separate cheap-model API call before the main call
- Model resolution uses `config_manager.load_config()` and `model_registry` — models are dynamically configured, not hardcoded
- Cost estimation uses `model_registry.compute_cost()` with registry-backed pricing
