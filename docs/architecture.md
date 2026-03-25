# Architecture

The Linguistic Tax toolkit is a batch-processing research pipeline, not a web service. It ingests benchmark prompts, applies controlled noise and intervention strategies, sends them to LLM APIs, grades the responses, and produces statistical analyses and publication figures.

```
prompts -> noise -> interventions -> API calls -> grading -> analysis -> figures
```

## Pipeline Architecture

```mermaid
flowchart LR
    A[prompts.json] --> B[Noise Generator]
    B --> C[Intervention Router]
    C --> D1[Raw]
    C --> D2[Self-Correct]
    C --> D3[Pre-Proc Sanitize]
    C --> D4[Sanitize+Compress]
    C --> D5[Repetition]
    D1 & D2 & D3 & D4 & D5 --> E[API Client]
    E --> F1[Claude]
    E --> F2[Gemini]
    E --> F3[GPT-4o]
    E --> F4[OpenRouter]
    F1 & F2 & F3 & F4 --> G[Grader]
    G --> H[(SQLite DB)]
```

Prompts are loaded from `data/prompts.json` (200 clean benchmarks from HumanEval, MBPP, and GSM8K). The noise generator applies Type A character-level mutations or Type B ESL syntactic patterns. The intervention router selects one of five strategies. The API client sends the processed prompt to the target model, measures TTFT and TTLT, and streams the response. The grader evaluates correctness (code execution sandbox for HumanEval/MBPP, regex number extraction for GSM8K) and writes everything to SQLite.

## Data Flow

```mermaid
flowchart TD
    A[prompts.json + experiment_matrix.json] --> B[run_experiment.py]
    B --> C[(results.db)]
    C --> D[analyze_results.py]
    C --> E[compute_derived.py]
    D --> F[analysis outputs in results/]
    E --> F
    F --> G[generate_figures.py]
    G --> H[figures/]
```

The experiment matrix (`data/experiment_matrix.json`) defines the full factorial design: 200 prompts x 8 noise types x 5 interventions x 4 models x 5 repetitions. `run_experiment.py` processes each work item and writes results to `results/results.db`. Post-experiment, `compute_derived.py` calculates per-prompt Consistency Rate, quadrant classification, and cost rollups. `analyze_results.py` runs GLMM, bootstrap CIs, McNemar's test, and Kendall's tau. Finally, `generate_figures.py` produces publication-quality PDF and PNG figures.

## CLI Command Map

```mermaid
flowchart TD
    PROPT[propt CLI] --> SETUP[setup]
    PROPT --> SHOWCONFIG[show-config]
    PROPT --> SETCONFIG[set-config]
    PROPT --> RESETCONFIG[reset-config]
    PROPT --> VALIDATE[validate]
    PROPT --> DIFF[diff]
    PROPT --> LISTMODELS[list-models]
    PROPT --> RUN[run]
    PROPT --> PILOT[pilot]

    SETUP --> SW[setup_wizard.py]
    SW --> CM[config_manager.py]
    CM --> CFG[experiment_config.json]

    SHOWCONFIG --> CC[config_commands.py]
    SETCONFIG --> CC
    RESETCONFIG --> CC
    VALIDATE --> CC
    DIFF --> CC
    LISTMODELS --> CC
    CC --> CM

    RUN --> ES[execution_summary.py]
    ES --> RE[run_experiment.py]
    RE --> AC[api_client.py]
    RE --> GR[grade_results.py]
    RE --> DB[(results.db)]

    PILOT --> ES2[execution_summary.py]
    ES2 --> PL[pilot.py]
    PL --> AC
    PL --> GR
    PL --> DB
```

All CLI commands are registered via argparse subparsers in `src/cli.py`. The `propt` entry point is defined in `pyproject.toml` (`propt = "src.cli:main"`).

## API Call Lifecycle

```mermaid
sequenceDiagram
    participant Engine as run_engine
    participant Router as Intervention Router
    participant PreProc as Pre-Processor API
    participant Target as Target Model API
    participant Grader as grade_results
    participant DB as SQLite DB

    Engine->>Engine: Load matrix item, apply noise
    Engine->>Router: apply_intervention(prompt, type, model)
    alt pre_proc_sanitize or sanitize_compress
        Router->>PreProc: call_model(cheap_model, prompt)
        Note over PreProc: TTFT measured at first chunk
        PreProc-->>Router: cleaned/compressed text + metadata
    end
    Router-->>Engine: processed_text, preproc_metadata
    Engine->>Target: call_model(target_model, processed_text)
    Note over Target: TTFT measured at first chunk
    Note over Target: TTLT measured at last chunk
    Target-->>Engine: APIResponse(text, tokens, timing)
    Engine->>Grader: grade_run(response, prompt_record)
    alt HumanEval / MBPP
        Grader->>Grader: Extract code, sandbox execute
    else GSM8K
        Grader->>Grader: Extract number, compare to canonical
    end
    Grader-->>Engine: GradeResult(passed, fail_reason, timing)
    Engine->>DB: insert_run(run_data)
    Engine->>DB: save_grade_result(details)
```

Rate limiting uses per-model delays from `RATE_LIMIT_DELAYS` with adaptive backoff: on 429 errors, the delay doubles and the request retries up to 3 times with exponential backoff (1s, 4s, 16s).

## Module Reference

### Configuration Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `config.py` | Pinned models, experiment parameters, pricing | `ExperimentConfig` (frozen dataclass), `derive_seed()`, `compute_cost()`, `NOISE_TYPES`, `INTERVENTIONS`, `MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP` |
| `config_manager.py` | Config file I/O and validation | `find_config_path()`, `load_config()`, `save_config()`, `validate_config()`, `get_full_config_dict()` |
| `config_commands.py` | CLI config subcommand handlers | `handle_show_config()`, `handle_set_config()`, `handle_reset_config()`, `handle_validate()`, `handle_diff()`, `handle_list_models()` |

### Data Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `db.py` | SQLite schema and queries | `init_database()`, `insert_run()`, `query_runs()`, `save_grade_result()` |
| `noise_generator.py` | Type A and Type B noise injection | `inject_type_a_noise()`, `inject_type_b_noise()`, `identify_protected_spans()`, `build_adjacency_map()` |

### Intervention Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `prompt_compressor.py` | Sanitize and compress via cheap model | `build_self_correct_prompt()`, `sanitize()`, `sanitize_and_compress()` |
| `prompt_repeater.py` | Query duplication per Leviathan et al. | `repeat_prompt()` |

### Execution Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `run_experiment.py` | Execution engine with resumability | `run_engine()`, `apply_intervention()`, `make_run_id()` |
| `api_client.py` | Multi-provider API wrapper with streaming | `call_model()`, `APIResponse` (frozen dataclass), `_validate_api_keys()` |
| `execution_summary.py` | Pre-execution summary and confirmation gate | `estimate_cost()`, `estimate_runtime()`, `format_summary()`, `confirm_execution()`, `save_execution_plan()`, `count_completed()` |
| `pilot.py` | Pilot validation (20-prompt subset) | `run_pilot()`, `select_pilot_prompts()`, `filter_pilot_matrix()`, `audit_data_completeness()`, `run_pilot_verdict()` |

### Grading Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `grade_results.py` | HumanEval sandbox + GSM8K regex grading | `grade_run()`, `grade_code()`, `grade_math()`, `extract_code()`, `batch_grade()` |

### Analysis Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `analyze_results.py` | Statistical analysis suite | `fit_glmm()`, `compute_bootstrap_cis()`, `run_mcnemar_analysis()`, `compute_kendall_tau()`, `apply_bh_correction()`, `run_sensitivity_analysis()`, `generate_effect_size_summary()` |
| `compute_derived.py` | Derived metrics: CR, quadrants, cost | `compute_cr()`, `classify_quadrant()`, `compute_derived_metrics()`, `compute_quadrant_migration()`, `compute_cost_rollups()` |

### Visualization Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `generate_figures.py` | Publication figure generation | `generate_accuracy_curves()`, `generate_quadrant_plot()`, `generate_cost_heatmap()`, `generate_kendall_plot()` |

### CLI Layer

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `cli.py` | CLI entry point with 9 subcommands | `build_cli()`, `main()`, `handle_run()`, `handle_pilot()` |
| `setup_wizard.py` | Interactive setup wizard | `run_setup_wizard()`, `check_environment()`, `validate_api_key()` |

## Database Schema

All experiment data is stored in a single SQLite database (`results/results.db`) with WAL journal mode for concurrent read performance. Three tables:

### experiment_runs

The primary table storing one row per API call.

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | TEXT PK | Deterministic ID: `prompt_id|noise_type|noise_level|intervention|model|repetition` |
| `prompt_id` | TEXT | Benchmark prompt identifier |
| `benchmark` | TEXT | `humaneval`, `mbpp`, or `gsm8k` |
| `noise_type` | TEXT | One of 8 noise conditions |
| `intervention` | TEXT | One of 5 interventions |
| `model` | TEXT | Target model identifier |
| `repetition` | INTEGER | Repetition number (1-5) |
| `prompt_text` | TEXT | The processed prompt sent to the model |
| `prompt_tokens` | INTEGER | Input token count |
| `optimized_tokens` | INTEGER | Output tokens from pre-processor (if applicable) |
| `raw_output` | TEXT | Full LLM response text |
| `pass_fail` | INTEGER | 1 = pass, 0 = fail |
| `ttft_ms` | REAL | Time to first token (milliseconds) |
| `ttlt_ms` | REAL | Time to last token (milliseconds) |
| `preproc_model` | TEXT | Pre-processor model used (if applicable) |
| `preproc_input_tokens` | INTEGER | Pre-processor input tokens |
| `preproc_output_tokens` | INTEGER | Pre-processor output tokens |
| `total_cost_usd` | REAL | Total cost including pre-processing |
| `status` | TEXT | `pending`, `completed`, or `failed` |
| `timestamp` | TEXT | ISO 8601 UTC timestamp |

Indexed on: `prompt_id`, `(noise_type, intervention, model)`, `status`.

### derived_metrics

Computed by `compute_derived.py`. One row per (prompt, condition, model) triple.

| Column | Type | Description |
|--------|------|-------------|
| `prompt_id` | TEXT | Benchmark prompt identifier |
| `condition` | TEXT | Combined `noise_type_intervention` string |
| `model` | TEXT | Target model identifier |
| `consistency_rate` | REAL | Pairwise CR across repetitions |
| `majority_pass` | INTEGER | 1 if majority of repetitions passed |
| `quadrant` | TEXT | `robust`, `confidently_wrong`, `lucky`, or `broken` |
| `mean_total_cost_usd` | REAL | Average cost across repetitions |
| `token_savings` | INTEGER | Mean token savings from compression |

Primary key: `(prompt_id, condition, model)`.

### grading_details

Diagnostic metadata from the grading pipeline. One row per graded run.

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | TEXT PK | References `experiment_runs.run_id` |
| `fail_reason` | TEXT | Reason code: `syntax_error`, `timeout`, `wrong_answer`, etc. |
| `extraction_method` | TEXT | GSM8K extraction method: `latex_boxed`, `integer`, etc. |
| `stdout` | TEXT | Captured stdout from sandbox execution |
| `stderr` | TEXT | Captured stderr from sandbox execution |
| `execution_time_ms` | REAL | Wall-clock grading time |

## Configuration System

All experiment parameters are defined in a frozen `ExperimentConfig` dataclass in `config.py`:

```python
@dataclass(frozen=True)
class ExperimentConfig:
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-1.5-pro"
    openai_model: str = "gpt-4o-2024-11-20"
    openrouter_model: str = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
    base_seed: int = 42
    type_a_rates: tuple[float, ...] = (0.05, 0.10, 0.20)
    repetitions: int = 5
    temperature: float = 0.0
    prompts_path: str = "data/prompts.json"
    matrix_path: str = "data/experiment_matrix.json"
    results_db_path: str = "results/results.db"
```

### Sparse Override Pattern

The config file (`experiment_config.json`) stores only properties that differ from defaults. When loaded, `config_manager.load_config()` merges overrides onto `ExperimentConfig()` defaults. This means:

- A missing config file uses all defaults
- An empty `{}` config file uses all defaults
- Only explicitly changed values are persisted

### Validation

`config_manager.validate_config()` checks:

- Model identifiers exist in `PRICE_TABLE`
- `type_a_rates` values are in [0, 1]
- `repetitions` >= 1
- `temperature` >= 0
- File paths exist on disk (for `prompts_path` and `matrix_path`)

Run `propt validate` to check the current configuration.

## Cross-References

- [Research Design Document (RDD)](RDD_Linguistic_Tax_v4.md) -- authoritative spec for all experimental parameters, metrics, and analysis methods
- [Getting Started](getting-started.md) -- end-to-end walkthrough from installation to first results
- [Analysis Guide](analysis-guide.md) -- interpreting statistical output, reading figures, running queries
