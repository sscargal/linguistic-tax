# Architecture Research

**Domain:** LLM experiment execution pipeline (noise injection, benchmark evaluation, statistical analysis)
**Researched:** 2026-03-19
**Confidence:** HIGH

## System Overview

This is a batch-processing research pipeline, not a service. Data flows strictly left-to-right through five stages. Each stage is a standalone module that reads from and writes to a shared SQLite database (or JSON files for inputs). There is no event bus, no API server, no concurrency framework -- just sequential Python scripts coordinated by a thin execution harness.

```
                        DATA PREPARATION (offline, run once)
 +-----------+     +----------------+     +------------------+
 | Benchmark |---->| Noise          |---->| Experiment       |
 | Prompts   |     | Generator      |     | Matrix Builder   |
 | (JSON)    |     | (Type A + B)   |     | (JSON)           |
 +-----------+     +----------------+     +------------------+
                                                  |
                                                  v
                        INTERVENTION (per-prompt, inline)
                   +------------------+
                   | Intervention     |
                   | Router           |
                   | - Raw (noop)     |
                   | - Self-Correct   |
                   | - Pre-Proc San.  |-----> Cheap LLM (Haiku/Flash)
                   | - San.+Compress  |-----> Cheap LLM (Haiku/Flash)
                   | - Repetition     |
                   +--------+---------+
                            |
                            v
                        EXECUTION (per-prompt x 5 reps x 2 models)
                   +------------------+
                   | Execution Engine |
                   | - API dispatch   |
                   | - Retry/backoff  |
                   | - Timing capture |
                   | - Cost tracking  |
                   +--------+---------+
                            |
                            v
                        GRADING (per-response)
                   +------------------+
                   | Grader           |
                   | - HumanEval exec |
                   | - MBPP exec      |
                   | - GSM8K regex    |
                   +--------+---------+
                            |
                            v
                   +------------------+
                   | SQLite           |
                   | results.db       |
                   +------------------+
                            |
                            v
                        ANALYSIS (post-hoc, over full dataset)
              +-------------+-------------+
              |             |             |
              v             v             v
        +-----------+ +-----------+ +-----------+
        | Derived   | | Stats     | | Figure    |
        | Metrics   | | Analysis  | | Generator |
        | (CR, quad)| | (GLMM,CI)| | (plots)   |
        +-----------+ +-----------+ +-----------+
```

### Component Responsibilities

| Component | Responsibility | Input | Output |
|-----------|----------------|-------|--------|
| **Noise Generator** | Inject controlled Type A (character) and Type B (syntactic) noise into clean prompts | Clean prompts JSON, noise config (type, rate, seed) | Noisy prompts with metadata (noise type, rate, mutations applied) |
| **Experiment Matrix Builder** | Enumerate all (prompt x noise x intervention x model x repetition) combinations | Clean + noisy prompts, intervention list, model list | `experiment_matrix.json` -- flat list of work items |
| **Intervention Router** | Apply the correct intervention to a prompt before sending to the target model | Single work item from matrix | Processed prompt (possibly via cheap LLM call) |
| **Execution Engine** | Send prompts to LLM APIs, capture timing/tokens/cost, handle retries | Processed prompt + model config | Raw API response + execution metadata |
| **Grader** | Determine pass/fail for a single response against ground truth | Raw output + benchmark answer | Boolean pass/fail + grading metadata |
| **Derived Metrics** | Compute per-condition aggregates: Consistency Rate, quadrant classification, cost rollups | All 5 repetitions for a (prompt, condition) pair | Derived record in SQLite |
| **Statistical Analysis** | Run GLMM, bootstrap CIs, McNemar's test, Kendall's tau, BH correction | Full results table | Statistical results, p-values, effect sizes |
| **Figure Generator** | Produce publication-quality plots | Statistical results + raw data | PNG/PDF figures |

## Recommended Project Structure

```
src/
  noise_generator.py        # Type A + Type B noise injection
  prompt_compressor.py       # Dedup + condensation (used by Sanitize+Compress intervention)
  prompt_repeater.py         # <QUERY><QUERY> duplication
  intervention.py            # Router: applies correct intervention given condition
  api_client.py              # Unified wrapper for Anthropic + Google APIs
  run_experiment.py          # Execution harness: iterates matrix, calls intervention + API + grader
  grade_results.py           # HumanEval sandbox + GSM8K regex grading
  analyze_results.py         # GLMM, bootstrap, McNemar, Kendall
  compute_derived.py         # CR, quadrant, cost rollups (post-execution)
  db.py                      # SQLite schema init, insert/query helpers
  config.py                  # Model versions, API keys from env, cost tables
  matrix_builder.py          # Generate experiment_matrix.json from prompts + conditions

data/
  prompts.json               # 200 clean benchmark prompts
  experiment_matrix.json     # Generated work items (gitignored after generation)
  real_world_noisy/          # 20 manually curated noisy prompts

results/
  results.db                 # SQLite (gitignored)

tests/
  test_noise_generator.py    # Determinism tests (same seed = same output)
  test_grader.py             # Known-answer grading tests
  test_intervention.py       # Intervention routing logic
  test_api_client.py         # Mock API tests
  test_matrix_builder.py     # Matrix enumeration correctness
  test_compute_derived.py    # CR / quadrant computation

figures/                     # Generated plots (gitignored)
docs/
  RDD_Linguistic_Tax_v4.md   # Authoritative spec
  research_program.md        # Autonomous execution instructions
```

### Structure Rationale

- **Flat `src/` layout:** With 10-12 modules total, packages add friction without benefit. Every module is a single file with a clear name. No `src/generators/`, `src/analysis/` -- that is over-engineering for a research toolkit.
- **Separate `db.py`:** Centralizes all SQLite DDL, inserts, and query helpers. Every other module imports from `db.py` rather than writing raw SQL. This prevents schema drift.
- **Separate `intervention.py`:** The intervention router is the most complex branching logic (5 paths, 2 of which involve external API calls). Isolating it from the execution engine keeps both testable.
- **`config.py` for constants:** Pinned model versions, cost-per-token tables, and environment variable loading live in one place. When model versions change, you update one file.

## Architectural Patterns

### Pattern 1: Work Item Queue (Experiment Matrix as Data)

**What:** The experiment matrix is a JSON file where each entry is a self-contained work item: `{prompt_id, noise_type, noise_rate, intervention, model, repetition}`. The execution engine reads items, processes them one-by-one, and writes results to SQLite. Completed items are tracked in the database, so re-running the script skips already-done work.

**When to use:** Always. This is the core execution pattern.

**Trade-offs:** Simple and resumable. Not parallelized (one API call at a time), but rate limits make parallelism counterproductive for 2 APIs with generous but finite rate limits.

```python
def run_experiment(matrix_path: str, db_path: str) -> None:
    """Process all unfinished work items from the experiment matrix."""
    matrix = load_matrix(matrix_path)
    completed = get_completed_run_ids(db_path)

    for item in matrix:
        run_id = make_run_id(item)
        if run_id in completed:
            continue

        # 1. Apply intervention
        processed_prompt, preproc_meta = apply_intervention(
            item["prompt_text"], item["intervention"], item["noise_type"]
        )

        # 2. Call target model
        response, exec_meta = call_model(
            processed_prompt, item["model"]
        )

        # 3. Grade
        passed = grade(response, item["benchmark"], item["expected"])

        # 4. Write to DB
        insert_result(db_path, run_id, item, response, exec_meta,
                       preproc_meta, passed)
```

### Pattern 2: Two-Phase Execution (Pilot Then Full)

**What:** The execution engine supports a `--pilot` flag that limits to the first 20 prompts. Pilot results are stored in the same database with the same schema -- they are simply a subset. Analysis scripts work on whatever data exists.

**When to use:** Always run pilot first. This is enforced by convention, not code.

**Trade-offs:** No code difference between pilot and full run, which keeps things simple. The pilot is not a separate system -- it is the same system with a filter.

### Pattern 3: Grading Strategy Pattern

**What:** Each benchmark type (HumanEval, MBPP, GSM8K) has a different grading function. The grader dispatches based on the `benchmark` field in the work item.

**When to use:** Whenever grading a response.

**Trade-offs:** HumanEval/MBPP grading requires code execution in a sandbox (subprocess with timeout + restricted imports). GSM8K grading is pure regex. These have very different failure modes and security characteristics, so they must be separate implementations behind a common interface.

```python
def grade(response: str, benchmark: str, expected: str) -> bool:
    """Grade a model response against the expected answer."""
    if benchmark in ("HumanEval", "MBPP"):
        return grade_code_execution(response, expected)
    elif benchmark == "GSM8K":
        return grade_math_regex(response, expected)
    else:
        raise ValueError(f"Unknown benchmark: {benchmark}")
```

### Pattern 4: Idempotent Derived Metrics

**What:** `compute_derived.py` runs after all 5 repetitions for a condition are complete. It reads the 5 raw results, computes CR (consistency rate), majority vote pass/fail, quadrant classification, and mean latency/cost, then writes a single derived record. It can be re-run without side effects (upserts, not inserts).

**When to use:** After execution completes (or after each batch). Can be triggered manually or at the end of `run_experiment.py`.

**Trade-offs:** Keeping derived metrics separate from raw results means the raw data is never mutated. Analysis scripts can recompute derived metrics with different definitions without re-running experiments.

## Data Flow

### Primary Pipeline Flow

```
[Clean Prompts JSON]
    |
    v
[Noise Generator] --> [Noisy Prompts + Metadata]
    |
    v
[Matrix Builder] --> [experiment_matrix.json]
    |                    (prompt_id, noise_type, noise_rate,
    |                     intervention, model, repetition)
    v
[Execution Engine]
    |
    |-- for each work item:
    |     |
    |     v
    |   [Intervention Router]
    |     |-- Raw: pass through
    |     |-- Self-Correct: prepend instruction
    |     |-- Pre-Proc: call cheap LLM --> cleaned prompt
    |     |-- Pre-Proc+Compress: call cheap LLM --> cleaned+compressed prompt
    |     |-- Repetition: duplicate prompt text
    |     |
    |     v
    |   [API Client] --> LLM API (Claude or Gemini)
    |     |
    |     v
    |   [Grader] --> pass/fail
    |     |
    |     v
    |   [SQLite INSERT] --> results.db (execution_log table)
    |
    v
[Compute Derived] --> results.db (derived_metrics table)
    |
    v
[Analyze Results] --> statistical outputs (JSON/CSV)
    |
    v
[Figure Generator] --> figures/ (PNG/PDF)
```

### Database as Integration Point

The SQLite database is the single integration point between pipeline stages. Every stage reads from and writes to the same database. There are no in-memory hand-offs between stages (except within a single work-item processing loop).

**Tables:**

| Table | Written By | Read By |
|-------|-----------|---------|
| `execution_log` | Execution Engine | Compute Derived, Analyze Results |
| `derived_metrics` | Compute Derived | Analyze Results, Figure Generator |
| `prompts` | Matrix Builder (optional, or just use JSON) | Execution Engine |

### Key Data Flows

1. **Prompt through intervention:** A clean or noisy prompt enters the intervention router. For Pre-Proc interventions, the prompt makes a round-trip to a cheap LLM (Haiku/Flash) before reaching the target model. The intervention router returns both the processed prompt AND metadata about the pre-processing (tokens consumed, latency, cost). This metadata is stored alongside the main execution result.

2. **5-repetition aggregation:** The execution engine processes each work item independently. It does not "know" about the 5-repetition structure -- it just processes items. After all items are done, `compute_derived.py` groups by (prompt_id, condition) and computes aggregates over the 5 repetitions. This separation means the execution engine never needs to hold state across repetitions.

3. **Cost accounting flow:** Each API call (both pre-processor and main model) logs input tokens, output tokens, and dollar cost. The derived metrics compute net token savings (original prompt tokens minus optimized tokens, minus pre-processor overhead). This enables the ROI analysis that is central to the paper.

## Scaling Considerations

This project has a fixed scale: ~20,000 API calls, ~200 prompts, 2 models. There is no user growth curve. The relevant scaling concerns are:

| Concern | Approach |
|---------|----------|
| API rate limits | Sequential execution with exponential backoff. No parallelism needed -- rate limits are the bottleneck, not CPU. |
| SQLite write contention | Not an issue with single-process sequential execution. If ever parallelized, use WAL mode. |
| Results database size | ~20K rows with text blobs (raw_output, cot_trace). Estimated ~500MB. Well within SQLite's capabilities. |
| Resumability | Work-item idempotency. Check "does this run_id exist in DB?" before processing. Re-running the script after a crash picks up where it left off. |
| Cost control | Pilot (20 prompts, ~$15) validates everything before committing to the full ~$300-500 run. |

### First Bottleneck: API Rate Limits

The Anthropic and Google APIs have per-minute token and request limits. With 5 repetitions x 200 prompts x 8 conditions x 2 models = 16,000 calls for Experiment 1 alone, expect multi-hour runtimes. The execution engine must implement exponential backoff with jitter. Log every rate-limit hit so you can estimate total runtime.

### Second Bottleneck: Code Execution Grading

HumanEval/MBPP grading requires executing model-generated code in a sandbox. Each execution needs a timeout (5-10 seconds) and process isolation. With ~10,000 code execution calls, this is ~14-28 hours of grading time if done sequentially at 5s each. Consider: grade inline during execution (so grading is interleaved with API wait times) rather than as a separate post-hoc step.

## Anti-Patterns

### Anti-Pattern 1: Storing Results as Flat JSON Files

**What people do:** Write each result as a separate JSON file (e.g., `results/humaneval_042_type_a_10pct_raw_rep3.json`), then glob+parse them for analysis.

**Why it's wrong:** With 20,000 result files, directory listing becomes slow, querying requires loading everything into memory, and there is no atomic write guarantee. Aggregation queries (e.g., "average pass rate for Type A 10% across all prompts") require reading all 20K files.

**Do this instead:** SQLite with a proper schema. SQL queries handle aggregation, filtering, and joining natively. Single file, ACID writes, no parsing overhead.

### Anti-Pattern 2: Coupling Intervention Logic Into the Execution Engine

**What people do:** Put all 5 intervention branches (Raw, Self-Correct, Pre-Proc, etc.) inline in the main execution loop with nested if/elif blocks.

**Why it's wrong:** The execution engine becomes untestable -- you cannot test intervention logic without making real API calls. The 5 intervention paths have different I/O characteristics (some make API calls, some do not), and mixing them into the main loop creates a debugging nightmare.

**Do this instead:** Separate `intervention.py` module with a single `apply_intervention(prompt, intervention_type, config) -> (processed_prompt, metadata)` function. The execution engine calls this function and does not know or care what happens inside.

### Anti-Pattern 3: Computing Derived Metrics Inline During Execution

**What people do:** Try to compute consistency rate and quadrant classification as each repetition completes, maintaining state across the 5 repetitions in the execution loop.

**Why it's wrong:** The execution engine would need to track which repetitions are complete for each (prompt, condition) pair, adding complex stateful logic to what should be a stateless work-item processor. If execution crashes and resumes, the in-memory state is lost.

**Do this instead:** Compute derived metrics as a separate post-execution step. The execution engine writes raw results; `compute_derived.py` reads all 5 repetitions from the DB and computes aggregates. This is simpler, stateless, and idempotent.

### Anti-Pattern 4: Using print() for Logging

**What people do:** Scatter `print()` calls throughout the codebase for status updates and debugging.

**Why it's wrong:** No log levels, no timestamps, no structured output, cannot redirect to file, cannot control verbosity. For a 20K-call experiment running overnight, you need proper logging with rotation and level filtering.

**Do this instead:** Python `logging` module with a configured handler. `INFO` for progress (every 100 items), `DEBUG` for individual API calls, `WARNING` for retries, `ERROR` for failures.

## Integration Points

### External Services

| Service | Integration Pattern | Key Concerns |
|---------|---------------------|--------------|
| Anthropic API (Claude) | `anthropic` Python SDK, direct `client.messages.create()` | Pin model version string. Capture `usage.input_tokens`, `usage.output_tokens` from response. Implement retry with exponential backoff on 429/529 errors. |
| Google Gemini API | `google-generativeai` Python SDK, `model.generate_content()` | Pin model version string. Token counting via `model.count_tokens()`. Different error codes than Anthropic -- handle both. |
| HumanEval Sandbox | `subprocess.run()` with timeout and restricted environment | Use `subprocess.run(timeout=10)`, capture stdout/stderr, match against expected test cases. Never execute model output in the main process. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Noise Generator <-> Matrix Builder | JSON files on disk | Noise generator writes noisy prompts to JSON. Matrix builder reads them. No runtime dependency. |
| Intervention Router <-> API Client | Function call (in-process) | Intervention router may call API client for pre-processing (cheap model). Returns processed prompt to execution engine, which calls API client again for main model. Two separate API calls per work item for Pre-Proc interventions. |
| Execution Engine <-> SQLite | `db.py` module (function calls) | All SQL goes through `db.py`. Execution engine never writes raw SQL. Schema changes happen in one place. |
| Compute Derived <-> SQLite | `db.py` module (function calls) | Reads `execution_log`, writes `derived_metrics`. Idempotent (UPSERT). |
| Analysis <-> SQLite | `db.py` module or direct pandas `read_sql()` | Analysis scripts may use pandas for convenience. This is acceptable -- analysis is exploratory, not production. |

## Build Order (Dependencies Between Components)

The following build order respects data-flow dependencies. Each stage can be built and tested independently once its upstream dependency exists.

```
Phase 1: Foundation (no upstream dependencies)
  1. config.py          -- constants, env vars, model versions
  2. db.py              -- schema DDL, insert/query helpers
  3. noise_generator.py -- Type A + Type B (testable with unit tests, no API needed)

Phase 2: Data Preparation (depends on Phase 1)
  4. prompt_compressor.py  -- needs API client for cheap model calls
  5. prompt_repeater.py    -- trivial string duplication, no dependencies
  6. matrix_builder.py     -- reads prompts + noise configs, writes matrix JSON

Phase 3: Execution Core (depends on Phases 1-2)
  7. api_client.py      -- unified Anthropic + Google wrapper (needs config.py)
  8. intervention.py    -- routes to compressor/repeater/API client
  9. grade_results.py   -- HumanEval sandbox + GSM8K regex (no API dependency)
  10. run_experiment.py  -- orchestrates intervention + API + grading + DB writes

Phase 4: Analysis (depends on Phase 3 producing data)
  11. compute_derived.py  -- reads execution_log, writes derived_metrics
  12. analyze_results.py  -- GLMM, bootstrap, McNemar, Kendall
  13. figure generation   -- publication plots from analysis output
```

**Critical path:** `config.py` -> `db.py` -> `api_client.py` -> `intervention.py` -> `run_experiment.py`. Everything else hangs off this spine.

**Parallelizable work:** `noise_generator.py`, `grade_results.py`, and `prompt_repeater.py` have no dependencies on each other and can be built simultaneously. Similarly, all analysis modules (Phase 4) can be built in parallel once the DB schema is defined.

## Sources

- RDD v4.0 (`docs/RDD_Linguistic_Tax_v4.md`) -- authoritative spec for experimental design, schema, and metrics
- CLAUDE.md -- project conventions and constraints
- PROJECT.md -- requirements and scope boundaries
- HumanEval benchmark patterns (OpenAI, standard code execution grading)
- SQLite documentation (WAL mode, UPSERT semantics)

---
*Architecture research for: LLM experiment execution pipeline (Linguistic Tax)*
*Researched: 2026-03-19*
