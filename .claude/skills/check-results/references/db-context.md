# Database Context

## Schema

```sql
CREATE TABLE experiment_runs (
    run_id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    benchmark TEXT NOT NULL,        -- 'humaneval', 'mbpp', 'gsm8k'
    noise_type TEXT NOT NULL,       -- 'clean', 'type_a_5pct', 'type_a_10pct', 'type_a_20pct',
                                    -- 'type_b_mandarin', 'type_b_spanish', 'type_b_japanese', 'type_b_mixed'
    noise_level TEXT,               -- '5', '10', '20', or NULL
    intervention TEXT NOT NULL,     -- 'raw', 'self_correct', 'pre_proc_sanitize',
                                    -- 'pre_proc_sanitize_compress', 'prompt_repetition'
    model TEXT NOT NULL,            -- 'claude-sonnet-4-20250514', 'gemini-1.5-pro',
                                    -- 'gpt-4o-2024-11-20', 'openrouter/nvidia/nemotron-3-super-120b-a12b:free'
    repetition INTEGER NOT NULL,    -- 1-5

    prompt_text TEXT,
    prompt_tokens INTEGER,
    optimized_tokens INTEGER,
    raw_output TEXT,
    cot_trace TEXT,
    completion_tokens INTEGER,
    pass_fail INTEGER,              -- 1=pass, 0=fail, NULL=ungraded
    ttft_ms REAL,
    ttlt_ms REAL,
    generation_ms REAL,
    preproc_model TEXT,
    preproc_input_tokens INTEGER,
    preproc_output_tokens INTEGER,
    preproc_ttft_ms REAL,
    preproc_ttlt_ms REAL,
    main_model_input_cost_usd REAL,
    main_model_output_cost_usd REAL,
    preproc_cost_usd REAL,
    total_cost_usd REAL,
    temperature REAL DEFAULT 0.0,
    timestamp TEXT,
    status TEXT DEFAULT 'pending'   -- 'pending', 'completed', 'failed', 'error'
);

CREATE TABLE derived_metrics (
    prompt_id TEXT NOT NULL,
    condition TEXT NOT NULL,         -- e.g. 'type_a_5pct|raw'
    model TEXT NOT NULL,
    consistency_rate REAL,           -- 0.0-1.0, pairwise CR over 5 reps
    majority_pass INTEGER,           -- 1 if majority of 5 reps passed
    pass_count INTEGER,              -- 0-5
    quadrant TEXT,                   -- 'robust', 'confidently_wrong', 'lucky', 'broken'
    mean_ttft_ms REAL,
    mean_ttlt_ms REAL,
    mean_total_latency_ms REAL,
    mean_total_cost_usd REAL,
    token_savings INTEGER,
    net_token_cost INTEGER,
    std_latency_ms REAL,
    PRIMARY KEY (prompt_id, condition, model)
);

CREATE TABLE grading_details (
    run_id TEXT PRIMARY KEY REFERENCES experiment_runs(run_id),
    fail_reason TEXT,
    extraction_method TEXT,
    stdout TEXT,
    stderr TEXT,
    execution_time_ms REAL,
    graded_at TEXT
);
```

## Experimental design constants

- **Prompts**: 200 total (from data/prompts.json)
  - ~70 HumanEval, ~70 MBPP, ~60 GSM8K
- **Noise types**: 8 (clean + 3 Type A levels + 4 Type B L1 patterns)
- **Interventions**: 5 (raw, self_correct, pre_proc_sanitize, pre_proc_sanitize_compress, prompt_repetition)
- **Models**: Dynamically configured via model registry (default: claude, gemini, gpt-4o, openrouter/nemotron)
- **Repetitions**: 5 per condition
- **Expected total**: ~20,000 runs (200 prompts x various conditions x 5 reps)
  - Experiment 1 (noise + recovery): 200 x 8 noise x 5 interventions x models x 5 reps
  - Experiment 2 (compression): 200 x clean x 2 models x 5 reps
  - Baseline: 200 x clean x raw x models x 5 reps

## Pilot

- 20 prompts (7 HumanEval + 7 MBPP + 6 GSM8K)
- Selected via `data/pilot_prompts.json` if it exists
- Pilot runs use the same schema, just fewer prompts

## CLI commands

- `propt pilot` — run pilot validation
- `propt run` — run full experiment matrix
- `propt run --model claude` — filter to specific model
- `propt run --intervention raw` — filter to specific intervention
- `python -m src.compute_derived --db results/results.db` — compute CR, quadrants, cost rollups
- `python -m src.analyze_results all --db results/results.db` — full statistical analysis
- `python -m src.generate_figures all --db results/results.db` — generate paper figures
- `propt list-models` — list available models from configured providers

## Price table (USD per 1M tokens)

> **NOTE:** These are approximate default prices. Actual pricing is loaded dynamically from the model registry via `model_registry.get_price(model_id)`. For OpenRouter models, live pricing is fetched from the OpenRouter API.

| Model | Input | Output |
|-------|-------|--------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gpt-4o-2024-11-20 | $2.50 | $10.00 |
| openrouter/nemotron (free) | $0.00 | $0.00 |
