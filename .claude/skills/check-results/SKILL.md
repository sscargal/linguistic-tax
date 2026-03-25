---
name: check-results
description: Inspect experiment progress, data quality, and cost tracking for the Linguistic Tax research project. Use this skill whenever the user asks about experiment status, how many runs are complete, what the cost is so far, whether there are gaps in the matrix, database health, or anything related to the state of results.db. Also trigger when the user says things like "how's the experiment going", "what's left to run", "check progress", "show me the results so far", or "how much have we spent".
---

# Check Results

Inspect the state of experiment runs in the Linguistic Tax research project. This skill queries `results.db` directly to give accurate, up-to-date information about experiment progress, data quality, and costs.

## When to use

Any time the user wants to know about the state of their experiments:
- How many runs are complete vs. pending vs. failed
- Which cells in the experimental matrix have gaps
- Total cost spent and projected cost to complete
- Data quality issues (missing grades, null fields, anomalous pass rates)
- Whether the pilot is done and what it showed

## Context

The project runs a factorial experiment: noise types x interventions x models x repetitions = ~20,000 LLM calls. Results live in an SQLite database. The schema and experimental design are documented in `references/db-context.md` — read it before writing any queries.

## Process

### 1. Locate the database

Check for the database at the configured path. The default is `results/results.db`, but the user may have overridden it via config.

```python
import sqlite3, os

# Try default path first, then check config
db_path = "results/results.db"
if not os.path.exists(db_path):
    # Check if config overrides it
    from src.config_manager import find_config_path
    import json
    config_path = find_config_path()
    if config_path:
        with open(config_path) as f:
            cfg = json.load(f)
        db_path = cfg.get("results_db_path", db_path)

if not os.path.exists(db_path):
    # Tell the user no database exists yet
    pass
```

### 2. Run the appropriate queries

Depending on what the user asked, run one or more of these query categories. Default to the **overview** if the user's request is vague.

#### Overview (default)

Show a high-level summary: total runs, completion rate, cost, and status breakdown.

```sql
-- Status breakdown
SELECT status, COUNT(*) as n FROM experiment_runs GROUP BY status;

-- Completion by model
SELECT model,
       COUNT(*) as total,
       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
       SUM(CASE WHEN pass_fail IS NOT NULL THEN 1 ELSE 0 END) as graded
FROM experiment_runs GROUP BY model;

-- Cost summary
SELECT model,
       SUM(total_cost_usd) as total_cost,
       AVG(total_cost_usd) as avg_cost_per_run
FROM experiment_runs WHERE status='completed'
GROUP BY model;

-- Total cost
SELECT SUM(total_cost_usd) as total_spent FROM experiment_runs WHERE status='completed';
```

Present as a formatted table. Calculate % complete and estimate remaining cost by extrapolating average cost per run to remaining runs.

#### Matrix gaps

Show which (noise_type, intervention, model) cells are under-filled (fewer than 5 repetitions per prompt, or fewer than expected prompts).

```sql
SELECT noise_type, intervention, model,
       COUNT(DISTINCT prompt_id) as prompts,
       COUNT(*) as total_runs,
       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
FROM experiment_runs
GROUP BY noise_type, intervention, model
ORDER BY completed ASC;
```

Flag any cell where completed < expected (200 prompts x 5 reps = 1000 per cell).

#### Pass rates

Show accuracy by condition to check for anomalies.

```sql
SELECT noise_type, intervention, model,
       ROUND(AVG(pass_fail) * 100, 1) as pass_rate_pct,
       COUNT(*) as n
FROM experiment_runs
WHERE status='completed' AND pass_fail IS NOT NULL
GROUP BY noise_type, intervention, model
ORDER BY noise_type, intervention, model;
```

Look for suspicious patterns: pass rates that don't decrease with noise, interventions that perform worse than raw, or pass rates of exactly 0% or 100%.

#### Data quality

Check for issues that could invalidate results.

```sql
-- Runs completed but not graded
SELECT COUNT(*) FROM experiment_runs WHERE status='completed' AND pass_fail IS NULL;

-- Runs with missing cost data
SELECT COUNT(*) FROM experiment_runs WHERE status='completed' AND total_cost_usd IS NULL;

-- Runs with missing timing data
SELECT COUNT(*) FROM experiment_runs WHERE status='completed' AND (ttft_ms IS NULL OR ttlt_ms IS NULL);

-- Duplicate run IDs (should be 0)
SELECT run_id, COUNT(*) as n FROM experiment_runs GROUP BY run_id HAVING n > 1;
```

#### Pilot status

Check specifically whether the 20-prompt pilot is complete.

```sql
-- Pilot prompts are the first 20 by convention
-- Check if pilot_prompts.json exists for exact IDs
SELECT COUNT(DISTINCT prompt_id) as pilot_prompts,
       COUNT(*) as total_pilot_runs,
       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
       SUM(total_cost_usd) as pilot_cost
FROM experiment_runs
WHERE prompt_id IN (SELECT DISTINCT prompt_id FROM experiment_runs LIMIT 20);
```

#### Derived metrics status

Check if derived metrics (CR, quadrants) have been computed.

```sql
SELECT COUNT(*) as derived_rows FROM derived_metrics;
SELECT quadrant, COUNT(*) as n FROM derived_metrics GROUP BY quadrant;
```

### 3. Present results

Format output as clean markdown tables. Include:
- A one-line summary at the top ("42% complete, $12.50 spent, 0 data quality issues")
- Relevant tables based on what was asked
- Any warnings or recommendations (e.g., "3 cells have 0 completed runs — these models may need API key configuration")
- If the experiment is partially complete, estimate remaining cost and time

### 4. Recommendations

Based on what you find, suggest next steps:
- If no data: suggest running the pilot first (`propt pilot`)
- If pilot complete but full run not started: suggest `propt run`
- If gaps exist: suggest targeted runs (`propt run --model X --intervention Y`)
- If data quality issues: suggest re-grading or investigating failures
- If derived metrics missing: suggest running `python -m src.compute_derived`
- If analysis not run: suggest `python -m src.analyze_results all`

## Important notes

- Read `references/db-context.md` before writing queries — it has the full schema and experimental design constants
- The database uses WAL mode, so reads are safe during active experiments
- Cost values are in USD
- pass_fail is 1 for pass, 0 for fail, NULL if not yet graded
- status values are: 'pending', 'completed', 'failed', 'error'
