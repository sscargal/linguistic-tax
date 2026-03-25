---
name: run-pilot
description: Run the 20-prompt pilot experiment for the Linguistic Tax research project. Use this skill whenever the user wants to run the pilot, start a small test run, validate the experiment pipeline, do a dry run, check pilot costs, or kick off initial experiments. Also trigger when the user says "run pilot", "test run", "try 20 prompts", "validate the pipeline", "how much will the pilot cost", or "start small before full run".
---

# Run Pilot

Execute the 20-prompt pilot experiment that validates the full experiment pipeline before committing to the ~20,000-call matrix. The pilot tests all noise types, interventions, and models on a small stratified sample.

## Why the pilot matters

The RDD (Section 4.3) explicitly warns: "Do NOT run the full 20,000-call matrix without a pilot." The pilot catches:
- API key misconfigurations before wasting budget
- Grading bugs that would invalidate thousands of results
- Cost overruns (the pilot projects full-run costs with bootstrap CIs)
- Noise injection issues (are mutations actually happening?)
- Rate limiting or timeout problems

## Prerequisites

Before running the pilot, verify:

1. **API keys are set** as environment variables:
   ```bash
   echo $ANTHROPIC_API_KEY  # For Claude
   echo $GOOGLE_API_KEY     # For Gemini (or GOOGLE_GENAI_API_KEY)
   ```

2. **Config exists** — run `propt setup` if not:
   ```bash
   propt validate
   ```

3. **Prompts data exists**:
   ```bash
   ls data/prompts.json data/experiment_matrix.json
   ```

## Running the pilot

### Dry run first (recommended)

Show what the pilot will do without spending money:

```bash
propt pilot --dry-run
```

This shows: number of items, models involved, estimated cost, estimated runtime. Review this before proceeding.

### Cost check

If the user is concerned about cost, check the estimate:

```bash
propt pilot --dry-run --budget 5.00
```

This exits non-zero if projected cost exceeds $5.00.

### Execute the pilot

```bash
propt pilot --yes
```

The `--yes` flag auto-accepts the confirmation gate. Without it, the user will be prompted interactively.

For a specific database path:
```bash
propt pilot --db results/pilot_results.db --yes
```

### What happens during execution

1. **Prompt selection**: Stratified sample of 20 prompts (7 HumanEval + 7 MBPP + 6 GSM8K) saved to `data/pilot_prompts.json`
2. **Matrix filtering**: Full experiment matrix filtered to only those 20 prompts
3. **Confirmation gate**: Shows cost estimate, runtime estimate, item breakdown
4. **Execution**: Sends prompts through all conditions (noise types x interventions x models x 5 reps)
5. **Inline grading**: Each response is graded immediately (HumanEval/MBPP via sandbox execution, GSM8K via regex)
6. **Results written** to `results/results.db`

### Monitoring progress

While the pilot runs, you can check progress:

```sql
-- In a separate terminal or via the check-results skill
sqlite3 results/results.db "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status;"
```

Or use the `/check-results` skill to get a formatted report.

## After the pilot completes

### Validate results

Run these checks (or use `/check-results`):

1. **Completeness**: All 20 prompts x all conditions should have runs
2. **Grading**: No ungraded runs (`pass_fail IS NOT NULL`)
3. **Cost tracking**: All runs have cost data
4. **Sanity check**: Clean baseline pass rates should be reasonable (60-90% for code, 50-80% for math)
5. **Noise effect**: Pass rates should generally decrease with noise level

### Compute derived metrics

```bash
python -m src.compute_derived --db results/results.db
```

This populates the `derived_metrics` table with consistency rates, quadrant classifications, and cost rollups.

### Review pilot report

The pilot produces several analysis artifacts:
- Cost projection with bootstrap CIs for the full run
- Spot check of graded outputs
- Noise injection sanity check (deterministic seed verification)

### Decision point

Based on pilot results, decide:
- **Proceed**: If data looks clean, costs are within budget, pass rates are sensible
- **Fix and re-run**: If grading bugs, API errors, or cost surprises found
- **Adjust parameters**: If the 82K-entry matrix is too expensive, consider trimming

## Common issues

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| "No config found" | Config not initialized | Run `propt setup` |
| API rate limits | Too many concurrent calls | Rate limit delays are in `config.py:RATE_LIMIT_DELAYS` |
| All runs failing | API key issue | Check `$ANTHROPIC_API_KEY`, `$GOOGLE_API_KEY` |
| 100% pass rate on noisy prompts | Grading too lenient or noise not applied | Check `noise_generator.py` output manually |
| Cost higher than expected | Pre-processing adds overhead | Check `preproc_cost_usd` column in results |

## Important notes

- The pilot uses the SAME infrastructure as the full run — it's not a separate system
- Pilot results persist in the database and are NOT discarded; the full run builds on them
- Seed determinism means re-running the pilot produces identical prompt selections
- The pilot's 20 prompts are a subset of the full 200 — they're included in the full run
