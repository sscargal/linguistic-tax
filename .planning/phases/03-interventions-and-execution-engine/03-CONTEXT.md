# Phase 3: Interventions and Execution Engine - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build all 5 intervention strategies (Raw, Self-Correct, Pre-Proc Sanitize, Pre-Proc Sanitize+Compress, Prompt Repetition) plus the orchestrating execution engine that sends prompts to Claude Sonnet and Gemini Pro APIs with full instrumentation (TTFT, TTLT, token counts, cost), manages resumability and rate limiting, and grades results inline. No new intervention types or model providers in this phase.

</domain>

<decisions>
## Implementation Decisions

### Pre-processor Prompt Design
- **Sanitize instruction:** Minimal, direct — "Fix all spelling and grammar errors in the following text. Return only the corrected text, no explanation."
- **Sanitize+Compress instruction:** Single combined call — "Fix all spelling and grammar errors in the following text, then remove redundancy and condense to minimal phrasing. Preserve all original intent. Return only the optimized text, no explanation."
- **Message format:** System prompt ("You are a text corrector" / "You are a prompt optimizer") + user message containing instruction and noisy prompt separated by `---`
- **Pre-processor models:** Vendor-matched — Claude Haiku 4.5 when main model is Claude Sonnet, Gemini Flash 2.0 when main model is Gemini Pro. Pinned in config.py.
- **Bad output handling:** Fall back to raw noisy prompt if pre-processor returns empty output or output longer than 1.5x original length. Log the fallback with warning. Mark `preproc_failed=True`.
- **Scope:** Apply pre-processing to ALL prompts including clean baselines (full factorial design — measures whether sanitize/compress changes already-correct prompts)
- **Runtime validation:** Skip embedding similarity check at runtime. BERTScore validation is a Phase 5 post-hoc analysis concern.

### Self-Correct Prefix
- Use RDD Section 6 wording exactly: "Note: my prompt below may contain spelling or grammar errors. First, correct any errors you find, then execute the corrected version of my request."
- Prepended to the noisy prompt with a `---` separator
- ~15 token overhead, no external API call

### Prompt Repetition
- **Separator:** Two newlines between copies (`{prompt}\n\n{prompt}`)
- **Scope:** User message only — system prompt (if any) is not duplicated
- **Content:** Repeat the noisy version verbatim — both copies are identical. Tests whether double-attention helps the model self-correct noise.
- **Count:** Double only (no triple repetition). Matches the Leviathan et al. paper.
- **Token tracking:** Log actual input tokens sent (doubled count). `optimized_tokens` stays NULL. `preproc_model` and `preproc_cost` are NULL/0.

### Module Architecture
- **Separate pure functions per intervention:**
  - `prompt_repeater.py` — `repeat_prompt(text: str) -> str`
  - `prompt_compressor.py` — `sanitize(text, model, config) -> str`, `sanitize_and_compress(text, model, config) -> str`
  - `run_experiment.py` — intervention router + execution engine + CLI
  - `api_client.py` — unified `call_model()` with internal Anthropic/Google routing
- **Router pattern:** match/case on intervention type in `run_experiment.py`, dispatching to the appropriate pure function

### Execution Ordering and Resumability
- **Order:** Group by model — all Claude items first (randomized within), then all Gemini items (randomized within). One API client active at a time.
- **Resumability:** DB status field is the single source of truth. On startup, query `experiment_runs WHERE status='completed'` and skip those run_ids. On each completion, update `status='completed'`.
- **Failure handling:** Exponential backoff with 3 retries (1s, 4s, 16s delays). After 4 total attempts, mark `status='failed'` with `fail_reason` and continue to next item. `--retry-failed` CLI flag reprocesses all failed items.
- **Grading:** Inline — grade each response immediately after receiving it. Enables real-time accuracy monitoring during execution.
- **Concurrency:** Sequential — one API call at a time. Simplest, no race conditions, rate limiting is trivial.

### CLI Design
- **File:** `src/run_experiment.py` with argparse (follows existing pattern from noise_generator.py, grade_results.py)
- **Flags:** `--model` (claude/gemini/all), `--limit N` (stop after N items), `--retry-failed`, `--dry-run` (show plan without API calls)
- **Progress:** One-line log per completed item + periodic summary every 100 items (accuracy %, cost so far, ETA)

### API and Cost Instrumentation
- **Streaming:** Use streaming API for all calls to measure TTFT (time from request to first chunk) and TTLT (time to final chunk). Accumulate full response from chunks.
- **Cost calculation:** Hardcoded price table in config.py per model (input_per_1m_tokens, output_per_1m_tokens). Calculate cost from API-reported token counts.
- **Rate limiting:** Fixed delay between calls per model (e.g., 200ms Claude Sonnet, 100ms Gemini Pro). On 429 response, double the delay and retry.
- **Max tokens:** Benchmark-appropriate — HumanEval/MBPP: 2048 tokens, GSM8K: 1024 tokens. Pinned in config.py.
- **Gemini SDK:** Replace deprecated `google-generativeai` with `google-genai` in pyproject.toml
- **API keys:** `os.environ.get()` with clear `EnvironmentError` if missing. No .env file loading.

### Claude's Discretion
- Exact rate limit delay values per model (tune to avoid 429s)
- APIResponse dataclass field design
- Internal streaming implementation details per SDK
- Error message formatting
- Test fixture design for API mocking

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experimental Design
- `docs/RDD_Linguistic_Tax_v4.md` — Authoritative spec for ALL experimental parameters. Key sections:
  - Section 5.3: Compression module design (dedup + condensation + validation)
  - Section 5.4: Prompt repetition mechanism and hypothesis
  - Section 6: Intervention definitions (Raw, Self-Correct, Pre-Proc Sanitize, Sanitize+Compress)
  - Section 8.3: Measurement architecture (TTFT, TTLT, cost instrumentation)
  - Section 9.2: Execution log schema (all fields the DB must capture)
  - Section 12: Optimizer overhead analysis (break-even, cost accounting)

### Project Conventions
- `CLAUDE.md` — Coding conventions (type hints, docstrings, logging module, American English, no print statements)
- `pyproject.toml` — Dependencies (NOTE: must replace `google-generativeai` with `google-genai`)

### Phase 1 and 2 Outputs (Dependencies)
- `src/config.py` — ExperimentConfig with pinned model versions, seeds, paths, temperature
- `src/db.py` — SQLite schema with all Phase 3 fields (intervention, preproc_*, cost_*, timing columns), insert_run(), query_runs()
- `src/noise_generator.py` — CLI pattern (argparse) and module structure to follow
- `src/grade_results.py` — grade_code(), grade_math() functions for inline grading
- `data/experiment_matrix.json` — Self-contained work items with prompt_id, noise_type, noise_level, intervention, model, repetition_num

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py`: ExperimentConfig with `claude_model`, `gemini_model`, `temperature`, `repetitions`, `base_seed` — all needed by execution engine
- `src/db.py`: Full schema already has intervention, preproc_model, preproc_*_tokens, preproc_*_ms, cost fields, status column — no schema changes needed
- `src/db.py`: `insert_run()` and `query_runs()` helpers for DB operations
- `src/grade_results.py`: `grade_code()`, `grade_math()` — import directly for inline grading
- `src/noise_generator.py`: argparse CLI pattern to follow for run_experiment.py

### Established Patterns
- Flat module layout in `src/` — one file per concern
- Python `logging` module for all output (no print statements)
- Type hints on all functions, docstrings on all public functions
- Frozen dataclass for configuration immutability
- Independent `random.Random(seed)` instances — no global random state
- argparse with subcommands for CLI tools

### Integration Points
- `data/experiment_matrix.json` — engine reads work items from here
- `results/results.db` — engine writes all results here via db.py helpers
- `experiment_runs.status` — engine reads/writes for resumability (pending -> completed/failed)
- `experiment_runs.raw_output` — engine writes LLM response, grader reads it
- `experiment_runs.pass_fail` — grader writes inline during execution

</code_context>

<specifics>
## Specific Ideas

- Pre-processor prompt text is intentionally minimal to reduce risk of changing meaning — the cheap model should fix errors, not rewrite
- The intervention router should use Python match/case for clean dispatch
- Progress logging format: `[N/total] prompt_id | noise_type | intervention | PASS/FAIL | latency | cost`
- Periodic summary every 100 items: accuracy %, total cost, ETA
- `--dry-run` flag should load the matrix, show how many items would be processed per model, estimate cost, then exit

</specifics>

<deferred>
## Deferred Ideas

- **OpenAI/GPT-4 as third model provider** — new capability, would change experimental design. Consider for v2 of the paper (see REQUIREMENTS.md EXT-01).
- **Context-aware pre-processor instruction** — variant that tells the cheap model it's fixing an LLM prompt specifically, preserving code/math notation. Compare against minimal instruction to see which is more accurate.
- **User-message-only pre-processor format** — variant without system prompt. Compare against system+user format to see if behavioral differences between Haiku and Flash affect results.
- **Triple prompt repetition** — test <QUERY><QUERY><QUERY> alongside double to measure diminishing returns of repetition.
- **Async concurrent API calls** — add asyncio with semaphore for higher throughput if sequential is too slow for full run.

</deferred>

---

*Phase: 03-interventions-and-execution-engine*
*Context gathered: 2026-03-20*
