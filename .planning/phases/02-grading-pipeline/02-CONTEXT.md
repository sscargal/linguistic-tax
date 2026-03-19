# Phase 2: Grading Pipeline - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatically grade any LLM output: HumanEval/MBPP code is executed in a secure subprocess sandbox with pass/fail, GSM8K answers are extracted and compared via regex with normalization, and all grades plus grading metadata are recorded in SQLite. No API calls in this phase -- grading operates on stored LLM responses.

</domain>

<decisions>
## Implementation Decisions

### Sandbox Security Model
- **Isolation**: subprocess-based execution with resource limits (no Docker -- noted for future)
- **Timeout**: 10 seconds per test case execution
- **Memory**: 512 MB cap via RLIMIT_AS, configurable by the user
- **Import restrictions**: None -- rely on resource limits for safety
- **Fork limits**: RLIMIT_NPROC capped (e.g., max 10) to prevent fork bombs
- **File system**: Allow writes in a temp directory, cleaned up after execution
- **Network**: Allowed (no restriction)
- **Execution environment**: Same Python interpreter as the project (not isolated venv)
- **Concurrency**: Sequential execution for now; parallel execution deferred to Phase 3 if needed

### Code Execution Model
- **Separate runners per benchmark**: HumanEval and MBPP get distinct execution logic to handle convention differences
- **Code extraction**: Strip markdown fences (```python) and surrounding explanatory text from LLM responses
- **Multiple code blocks**: Use the last code block in the response (LLMs often iterate and refine)
- **Test assertions**: Bundled in prompts.json alongside canonical answers. If sourced from HuggingFace, provide a CLI subcommand to download/refresh test data

### GSM8K Answer Extraction
- **Comparison method**: Normalized -- strip commas, whitespace, currency symbols, units; convert to float; compare within epsilon (1e-6)
- **Extraction strategy**: Last number in the LLM response (standard GSM8K convention; ignores chain-of-thought intermediate calculations)
- **Fractions/percentages**: Convert to decimal (e.g., 3/4 -> 0.75, 50% -> 50)
- **Negative numbers**: Handle '-42' and '(42)' formats; ignore prose like "negative 42"
- **Unit stripping**: Remove trailing units ('$', 'dollars', 'meters', 'hours', '%', etc.) before comparison
- **Multi-answer**: Single final answer only -- GSM8K problems converge to one answer
- **Extraction method logging**: Record which method matched ('last_number', 'fraction_converted', etc.) for debugging during pilot spot-check (PILOT-02)

### Grading Interface and CLI
- **Architecture**: Python API (importable grade_code(), grade_math() functions) with thin CLI wrapper via argparse
- **File layout**: Single file -- `src/grade_results.py` -- matching existing flat module pattern
- **Batch mode**: CLI supports grading a single run by ID or batch-grading all runs where pass_fail is NULL
- **Auto-detection**: Grader reads the 'benchmark' column from SQLite to auto-route to code or math grader
- **CLI output**: Default to summary stats (total graded, passed, failed, errors). Support `--format json` and `--format table` options
- **Re-grading**: Skip already-graded runs by default; `--force` flag overwrites existing pass_fail values

### Edge Case Handling
- **Failure recording**: All execution failures recorded as pass_fail=0 with a reason code:
  - `timeout` -- execution exceeded 10s limit
  - `crash` -- unhandled runtime exception
  - `memory_exceeded` -- hit 512MB RLIMIT_AS cap
  - `syntax_error` -- Python SyntaxError in LLM output
  - `no_output` -- empty LLM response or extractor found nothing
  - `extraction_failed` -- GSM8K number extraction could not parse answer
  - `import_error` -- LLM imported unavailable package
- **Binary grading**: All-or-nothing -- all assertions must pass for pass_fail=1 (standard HumanEval convention)
- **Empty responses**: Fail with 'no_output' reason, not skipped

### Logging and Storage
- **Execution capture**: Full stdout, stderr, return code, and execution time captured per sandbox run
- **Storage location**: Grading details (stdout, stderr, reason code, extraction method) stored in SQLite alongside pass_fail
- **DB schema changes**: Need new columns or a grading_details table for stdout, stderr, fail_reason, extraction_method

### Testing
- **Adversarial sandbox tests**: Required -- test with actual infinite loops, large memory allocations, fork bombs to verify sandbox containment
- **GSM8K extraction tests**: Comprehensive -- 15-20 format variants covering integers, decimals, commas, currency, negatives, parenthetical negatives, fractions, percentages, LaTeX boxed, trailing units, mixed prose

### Claude's Discretion
- Return type design for grade_code()/grade_math() (bool, dataclass, or dict)
- Exact DB schema changes (new columns vs separate table)
- Specific regex patterns for GSM8K number extraction
- Pre-check with ast.parse() before subprocess (optimization choice)
- How to distinguish assertion failures from other runtime errors in reason codes

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experimental Design
- `docs/RDD_Linguistic_Tax_v4.md` -- Authoritative spec for grading requirements, pass/fail schema (Section 9.2), execution log fields, and auto-grader expectations

### Project Conventions
- `CLAUDE.md` -- Coding conventions (type hints, docstrings, logging module, American English), tech stack constraints
- `pyproject.toml` -- Dependencies and pytest configuration

### Phase 1 Outputs (Dependencies)
- `src/db.py` -- SQLite schema with pass_fail column, insert_run(), query_runs() helpers
- `src/config.py` -- ExperimentConfig with paths, model versions, seed management
- `data/prompts.json` -- 200 curated benchmark prompts with canonical answers and test assertions
- `src/noise_generator.py` -- CLI pattern (argparse) to follow for grade_results.py CLI design

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/db.py`: init_database(), insert_run(), query_runs() -- grader writes pass_fail and grading metadata to existing schema
- `src/config.py`: ExperimentConfig.results_db_path -- path to results SQLite database
- `src/noise_generator.py`: argparse CLI pattern -- follow same structure for grade_results.py CLI
- `data/prompts.json`: Contains benchmark prompts with canonical answers -- grader reads canonical answers for comparison

### Established Patterns
- Flat module layout in `src/` -- one file per concern (config.py, db.py, noise_generator.py)
- Python `logging` module for all output (no print statements)
- Type hints on all functions, docstrings on all public functions
- pytest with test files in `tests/` (test_config.py, test_db.py, test_noise_generator.py, test_prompts.py)

### Integration Points
- `experiment_runs.raw_output` -- LLM response text that the grader processes
- `experiment_runs.pass_fail` -- column the grader writes to (INTEGER: 0 or 1)
- `experiment_runs.benchmark` -- used for auto-routing to code vs math grader
- Phase 3 execution engine will import grade_code()/grade_math() directly

</code_context>

<specifics>
## Specific Ideas

- Docker container isolation noted as future enhancement to the TODO list -- subprocess + resource limits sufficient for now
- HuggingFace download subcommand for test data refresh -- prompts.json is primary source, but provide a way to update from upstream
- CLI output format flexibility (summary/JSON/table) mirrors the researcher workflow -- quick check vs detailed analysis vs piping to other tools

</specifics>

<deferred>
## Deferred Ideas

- Docker container isolation for sandbox execution -- future enhancement, subprocess sufficient for research use
- Parallel sandbox execution -- Phase 3 execution engine can add if needed
- Non-Python code detection (LLM returning wrong language)
- Multiple function definition handling (LLM iterating on solutions in output)

</deferred>

---

*Phase: 02-grading-pipeline*
*Context gathered: 2026-03-19*
