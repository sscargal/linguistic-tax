# Phase 4: Pilot Validation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Run 20 prompts end-to-end through the full pipeline (all noise conditions, all intervention types, 5 repetitions), verify grading accuracy via spot-check, validate data completeness, and produce a cost projection with budget gate for the full experiment run. This is a validation gate — the execution engine already exists from Phase 3. No new intervention types, models, or experimental parameters in this phase.

</domain>

<decisions>
## Implementation Decisions

### Prompt Selection Strategy
- Stratified sample across benchmarks: ~7 HumanEval, ~7 MBPP, ~6 GSM8K
- Selection uses a fixed seed for reproducibility
- Full factorial design: all noise types x levels x interventions x 5 repetitions (~4,100 API calls)
- Selected prompt IDs saved to `data/pilot_prompts.json` for auditability
- Standalone `src/pilot.py` module with `select_pilot_prompts()`, `run_spot_check()`, `compute_cost_projection()`

### Grading Spot-Check
- Automated report: randomly sample results, show prompt + LLM response + extracted answer + expected answer + auto-grade side by side
- Coverage: ALL GSM8K results (regex grading is fragile) + 20% of code grading results (HumanEval/MBPP)
- Failure criterion: any systematic grading error pattern = fail. Isolated edge cases acceptable.
- Report saved to `results/pilot_spot_check.json` (citable in paper's methods section)

### Cost Projection
- Per-condition breakdown (model x intervention x noise type) with bootstrap confidence intervals showing best/worst case
- Budget gate: `--budget` flag with configurable threshold (default $200). Prints warning with breakdown if projected full-run cost exceeds threshold.
- Output: detailed breakdown saved to `results/pilot_cost_projection.json`, human-readable summary table printed to terminal

### Pass/Fail Criteria
- Minimum 95% completion rate (status='completed'). Up to 5% transient failures acceptable. Any systematic failure (entire model or intervention failing) = auto-fail.
- Zero-variance flag: if every prompt-condition has identical results across all 5 reps, flag for review (informational, not auto-fail). Expected with temp=0 but worth checking.
- Structured verdict: `results/pilot_verdict.json` with overall PASS/FAIL, completion rate, grading accuracy, cost projection, and flagged issues
- Informational power analysis: rough estimate of whether N=200 is sufficient for GLMM effect sizes observed in pilot data. Included in verdict report, does not block full run.

### Additional Validations
- **Latency profiling:** Analyze TTFT/TTLT distributions from pilot data. Flag model/intervention combos with unexpected latency spikes. Estimate wall-clock time for full run.
- **Pre-processor fidelity:** BERTScore between original clean prompt and pre-processed output on all sanitize/compress results. Flag pairs below 0.85 threshold. Manual review on flagged outliers. Belt-and-suspenders approach.
- **Data completeness audit:** Verify every DB field is populated — no NULLs where values are expected, correct model versions, proper timestamps, non-zero token counts.
- **Noise injection sanity check:** Verify runtime noise injection produces expected error rates (e.g., 5% noise has ~5% character mutations). Catches seed or config issues before full run.

### Claude's Discretion
- Exact BERTScore threshold tuning (0.85 is starting point)
- Bootstrap sample count for cost projection CIs
- Power analysis methodology (rough estimate is fine — full analysis in Phase 5)
- Internal structure of verdict report
- How to present the spot-check comparison (table format, grouping)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experimental Design
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for all experimental parameters. Key sections:
  - Section 9.2: Execution log schema (all DB fields pilot must validate)
  - Section 12: Optimizer overhead analysis (cost accounting the projection must capture)
  - Section 21.3: Power analysis recommendation after pilot

### Project Conventions
- `CLAUDE.md` — Coding conventions (type hints, docstrings, logging module, American English)

### Phase 3 Outputs (Dependencies)
- `src/run_experiment.py` — Execution engine with `--limit`, `--model`, `--retry-failed`, `--dry-run` flags
- `src/api_client.py` — Unified `call_model()` with streaming TTFT/TTLT measurement
- `src/config.py` — ExperimentConfig with pinned model versions, price table, MAX_TOKENS_BY_BENCHMARK
- `src/db.py` — SQLite schema, `insert_run()`, `query_runs()`, `save_grade_result()`
- `src/grade_results.py` — `grade_run()` for inline grading
- `src/noise_generator.py` — `inject_type_a_noise()`, `inject_type_b_noise()` for sanity check validation
- `data/experiment_matrix.json` — Full experiment matrix (~82,000 items)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/run_experiment.py`: Execution engine already supports `--limit N` to restrict prompt count — pilot can leverage this after filtering to pilot prompt IDs
- `src/db.py`: `query_runs()` can retrieve all pilot results by run_id pattern for spot-check and analysis
- `src/config.py`: Price table already exists for cost calculation via `compute_cost()`
- `src/grade_results.py`: `grade_run()` handles both code and math grading — spot-check compares against these grades
- `src/noise_generator.py`: Noise functions accept seeds — can verify determinism and error rates directly

### Established Patterns
- Flat module layout in `src/` — `pilot.py` follows this pattern
- argparse CLI pattern used by `noise_generator.py`, `grade_results.py`, `run_experiment.py`
- JSON for config/data files, SQLite for results
- Python `logging` module for all output

### Integration Points
- `data/pilot_prompts.json` — new file, pilot prompt selection written here
- `data/experiment_matrix.json` — pilot filters this to 20-prompt subset
- `results/results.db` — pilot reads completed results for analysis
- `results/pilot_spot_check.json` — new file, spot-check report
- `results/pilot_cost_projection.json` — new file, cost projection with CIs
- `results/pilot_verdict.json` — new file, structured pass/fail verdict

</code_context>

<specifics>
## Specific Ideas

- The pilot is a hard gate — no full experiment run without a passing pilot (per PROJECT.md decisions)
- GSM8K regex grading is the most fragile path, hence checking ALL GSM8K results in spot-check
- Pre-processor fidelity uses both automated (BERTScore) and manual review for outliers — catches both quantitative and qualitative meaning drift
- Budget default of $200 for the full run — the ~$15 pilot budget is separate and implicitly validated by running the pilot itself
- Power analysis is informational only — a rough sanity check, not the full GLMM power analysis from Phase 5

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-pilot-validation*
*Context gathered: 2026-03-21*
