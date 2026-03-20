# Phase 3: Interventions and Execution Engine - Research

**Researched:** 2026-03-20
**Domain:** LLM API integration (Anthropic + Google), intervention strategies, execution orchestration
**Confidence:** HIGH

## Summary

Phase 3 builds four new modules: `prompt_repeater.py` (trivial string duplication), `prompt_compressor.py` (pre-processor calls via cheap models), `api_client.py` (unified streaming API wrapper for Claude and Gemini), and `run_experiment.py` (intervention router + execution engine + CLI). The existing Phase 1/2 infrastructure provides a complete DB schema, grading functions, experiment matrix (82,000 items), and configuration -- no schema changes needed.

The Anthropic SDK (v0.84.0, installed) supports synchronous streaming via `client.messages.stream()` with `.text_stream` iteration and `get_final_message()` for token counts. The Google GenAI SDK (v1.45.0, installed) replaces the deprecated `google-generativeai` package and uses `client.models.generate_content_stream()` with cumulative `usage_metadata` on the last chunk. Both SDKs are already installed; `pyproject.toml` must be updated to replace `google-generativeai` with `google-genai`.

**Primary recommendation:** Build `api_client.py` as a thin wrapper with a single `call_model()` function that internally routes to Anthropic or Google SDK, streams all responses for TTFT/TTLT measurement, and returns a unified `APIResponse` dataclass. Keep intervention modules as pure functions with no API knowledge.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Pre-processor Prompt Design:** Minimal, direct sanitize instruction. Combined sanitize+compress in single call. System prompt + user message format with `---` separator. Vendor-matched pre-processor models (Haiku for Claude, Flash for Gemini). Fallback to raw prompt if pre-processor returns empty or >1.5x original length.
- **Self-Correct Prefix:** Use RDD Section 6 wording exactly, prepended with `---` separator, ~15 token overhead.
- **Prompt Repetition:** Two newlines separator, user message only, repeat noisy version verbatim, double only.
- **Module Architecture:** Separate pure functions per intervention. Router uses match/case in `run_experiment.py`. `api_client.py` handles unified model routing.
- **Execution Ordering:** Group by model (all Claude first, then Gemini), randomized within each group. Sequential (one call at a time).
- **Resumability:** DB status field is single source of truth. Query completed run_ids on startup. Exponential backoff with 3 retries (1s, 4s, 16s). Mark failed after 4 attempts. `--retry-failed` CLI flag.
- **CLI Design:** `src/run_experiment.py` with argparse. Flags: `--model`, `--limit N`, `--retry-failed`, `--dry-run`.
- **API Instrumentation:** Streaming for TTFT/TTLT. Hardcoded price table in config.py. Fixed inter-call delay with 429-triggered doubling.
- **Max tokens:** HumanEval/MBPP: 2048, GSM8K: 1024. Pinned in config.py.
- **Gemini SDK:** Replace `google-generativeai` with `google-genai` in pyproject.toml.
- **API keys:** `os.environ.get()` with `EnvironmentError` if missing. No .env file loading.
- **Grading:** Inline -- grade each response immediately after receiving it.
- **Scope:** Apply pre-processing to ALL prompts including clean baselines (full factorial design).

### Claude's Discretion
- Exact rate limit delay values per model (tune to avoid 429s)
- APIResponse dataclass field design
- Internal streaming implementation details per SDK
- Error message formatting
- Test fixture design for API mocking

### Deferred Ideas (OUT OF SCOPE)
- OpenAI/GPT-4 as third model provider
- Context-aware pre-processor instruction
- User-message-only pre-processor format
- Triple prompt repetition
- Async concurrent API calls

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTV-01 | Implement prompt compressor (sanitize + compress via cheap model) | `prompt_compressor.py` with `sanitize()` and `sanitize_and_compress()` using vendor-matched cheap models via `api_client.call_model()` |
| INTV-02 | Implement prompt repeater (<QUERY><QUERY> duplication) | `prompt_repeater.py` with `repeat_prompt()` -- pure string operation, two newlines separator |
| INTV-03 | Implement self-correct prompt prefix | Inline in router -- prepend RDD Section 6 text with `---` separator |
| INTV-04 | Implement pre-processor pipeline (sanitize noisy prompts via cheap model) | `prompt_compressor.py` `sanitize()` function with fallback logic for bad output |
| INTV-05 | Build intervention router dispatching to all 5 strategies | `run_experiment.py` match/case router dispatching to Raw/Self-Correct/Pre-Proc Sanitize/Sanitize+Compress/Repetition |
| EXEC-01 | Execute against Claude Sonnet and Gemini 1.5 Pro at temperature=0.0 | `api_client.py` unified `call_model()` with Anthropic and Google SDK streaming |
| EXEC-02 | Log TTFT, TTLT, token counts, cost, timestamp for every call | Streaming APIs provide timing; token counts from response metadata; cost from hardcoded price table |
| EXEC-03 | Run 5 repetitions per condition | Engine iterates experiment_matrix.json items which already include repetition_num 1-5 |
| EXEC-04 | Resumable execution -- skip completed items on restart | Query `experiment_runs WHERE status='completed'` on startup, skip matching run_ids |
| EXEC-05 | Proactive rate limiting | Fixed inter-call delay per model + 429 detection with delay doubling |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.84.0 (installed) | Claude API client with streaming | Official Anthropic SDK, supports `client.messages.stream()` |
| google-genai | 1.45.0 (installed) | Gemini API client with streaming | Official Google GenAI SDK, replaces deprecated `google-generativeai` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| time (stdlib) | -- | TTFT/TTLT measurement via `time.monotonic()` | All API calls for timing instrumentation |
| json (stdlib) | -- | Load experiment_matrix.json | Engine startup |
| random (stdlib) | -- | Shuffle matrix items within model groups | Execution ordering |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct SDK calls | LiteLLM unified wrapper | Adds dependency, abstracts away streaming details needed for TTFT |
| time.monotonic() | time.perf_counter() | Both work; monotonic() is standard for elapsed wall-clock |
| Hardcoded price table | Live pricing API | No pricing API exists; hardcoded is the only option |

**Installation:**
```bash
# In pyproject.toml, REPLACE google-generativeai with google-genai:
# "google-generativeai>=0.8.0"  ->  "google-genai>=1.0.0"
# anthropic is already correct at >=0.40.0
```

**Version verification:** Both `anthropic==0.84.0` and `google-genai==1.45.0` are already installed in the project environment. The `google-generativeai` package is also installed but should be removed from pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
src/
  config.py              # [exists] Add price table, max_tokens, pre-proc models, rate limit delays
  db.py                  # [exists] No changes needed -- schema already has all Phase 3 fields
  noise_generator.py     # [exists] Not modified
  grade_results.py       # [exists] Import grade_run() for inline grading
  prompt_repeater.py     # [NEW] Pure function: repeat_prompt()
  prompt_compressor.py   # [NEW] sanitize() and sanitize_and_compress() via api_client
  api_client.py          # [NEW] Unified call_model() with streaming TTFT/TTLT
  run_experiment.py      # [NEW] Intervention router + execution engine + CLI
```

### Pattern 1: Unified API Client with Streaming
**What:** Single `call_model()` function that internally routes to Anthropic or Google SDK based on model name, streams all responses, measures TTFT/TTLT, and returns a unified dataclass.
**When to use:** Every API call in the project -- both main model calls and pre-processor calls.
**Example:**
```python
import time
from dataclasses import dataclass

@dataclass(frozen=True)
class APIResponse:
    """Unified response from any model API call."""
    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float
    ttlt_ms: float
    model: str

def call_model(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float = 0.0,
) -> APIResponse:
    """Call an LLM via streaming, measure timing, return unified response."""
    if model.startswith("claude"):
        return _call_anthropic(model, system, user_message, max_tokens, temperature)
    elif model.startswith("gemini"):
        return _call_google(model, system, user_message, max_tokens, temperature)
    else:
        raise ValueError(f"Unknown model: {model}")
```

### Pattern 2: Anthropic Streaming with TTFT Measurement
**What:** Use synchronous `client.messages.stream()` context manager to iterate text chunks and measure timing.
**Example:**
```python
# Source: Anthropic SDK helpers.md + official docs
import anthropic
import time

def _call_anthropic(
    model: str, system: str | None, user_message: str,
    max_tokens: int, temperature: float,
) -> APIResponse:
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages = [{"role": "user", "content": user_message}]
    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages, temperature=temperature)
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if not chunks:
                ttft_ms = (time.monotonic() - start) * 1000
            chunks.append(text)

    ttlt_ms = (time.monotonic() - start) * 1000
    final = stream.get_final_message()

    return APIResponse(
        text="".join(chunks),
        input_tokens=final.usage.input_tokens,
        output_tokens=final.usage.output_tokens,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )
```

### Pattern 3: Google GenAI Streaming with TTFT Measurement
**What:** Use `client.models.generate_content_stream()` to iterate chunks. The last chunk's `usage_metadata` contains cumulative token counts.
**Example:**
```python
# Source: Google GenAI SDK docs + GitHub issue #1204
from google import genai
from google.genai import types
import time

def _call_google(
    model: str, system: str | None, user_message: str,
    max_tokens: int, temperature: float,
) -> APIResponse:
    client = genai.Client()  # Uses GOOGLE_API_KEY env var (or GEMINI_API_KEY)
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []
    last_chunk = None

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    if system:
        config.system_instruction = system

    for chunk in client.models.generate_content_stream(
        model=model, contents=user_message, config=config,
    ):
        if chunk.text and not chunks:
            ttft_ms = (time.monotonic() - start) * 1000
        if chunk.text:
            chunks.append(chunk.text)
        last_chunk = chunk

    ttlt_ms = (time.monotonic() - start) * 1000

    # Last chunk has cumulative usage_metadata
    usage = last_chunk.usage_metadata if last_chunk else None
    return APIResponse(
        text="".join(chunks),
        input_tokens=usage.prompt_token_count if usage else 0,
        output_tokens=usage.candidates_token_count if usage else 0,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )
```

### Pattern 4: Intervention Router with match/case
**What:** Python 3.10+ structural pattern matching for clean dispatch.
**Example:**
```python
def apply_intervention(
    prompt_text: str,
    intervention: str,
    model: str,
    config: ExperimentConfig,
) -> tuple[str, dict]:
    """Apply intervention and return (processed_prompt, metadata)."""
    match intervention:
        case "raw":
            return prompt_text, {}
        case "self_correct":
            prefix = ("Note: my prompt below may contain spelling or grammar errors. "
                      "First, correct any errors you find, then execute the corrected "
                      "version of my request.")
            return f"{prefix}\n---\n{prompt_text}", {}
        case "pre_proc_sanitize":
            return _run_preproc(prompt_text, "sanitize", model, config)
        case "pre_proc_sanitize_compress":
            return _run_preproc(prompt_text, "sanitize_compress", model, config)
        case "prompt_repetition":
            return f"{prompt_text}\n\n{prompt_text}", {}
        case _:
            raise ValueError(f"Unknown intervention: {intervention}")
```

### Anti-Patterns to Avoid
- **Global API client instances:** Create client per call or per model group. Do NOT share mutable state across calls.
- **Catching broad exceptions on API calls:** Catch specific `anthropic.RateLimitError` and `google.genai.errors.APIError` for proper retry logic.
- **Using non-monotonic clocks for timing:** Always use `time.monotonic()`, never `time.time()` (which can jump with NTP corrections).
- **Accumulating response text via string concatenation:** Use `list.append()` + `"".join()` instead of `+=` for O(n) instead of O(n^2).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API rate limiting | Custom token bucket | Fixed delay + 429 detection with backoff | Sequential execution makes token buckets unnecessary |
| Retry with backoff | Manual sleep loops | Structured retry function with configurable delays | Consistent retry behavior across all API calls |
| UUID generation | Custom ID scheme | `uuid.uuid4()` or existing run_id from matrix | DB requires unique run_id; uuid4 is standard |
| Token counting for cost | External tokenizer | API-reported token counts from response | SDKs return exact counts; tiktoken estimates may differ |
| Progress display | Custom progress bar | Logging with structured format string | Project convention: use logging module, no print() |

**Key insight:** Both SDKs handle streaming, token counting, and error classification internally. The wrapper should be thin -- just timing measurement and response normalization.

## Common Pitfalls

### Pitfall 1: google-generativeai vs google-genai Import Confusion
**What goes wrong:** Importing `import google.generativeai as genai` instead of `from google import genai` after SDK swap.
**Why it happens:** The old deprecated package is still referenced in pyproject.toml and may be installed alongside the new one.
**How to avoid:** Update pyproject.toml FIRST. Use `from google import genai` and `from google.genai import types`. Remove `google-generativeai` from dependencies.
**Warning signs:** ImportError or unexpected API shape (old SDK uses `genai.GenerativeModel()`, new uses `client.models.generate_content()`).

### Pitfall 2: Anthropic stream() vs create() with stream=True
**What goes wrong:** Using `client.messages.create(stream=True)` returns raw SSE events that need manual parsing. Using `client.messages.stream()` returns a helper that manages event parsing automatically.
**Why it happens:** Two streaming APIs exist; the helper is better.
**How to avoid:** Always use `client.messages.stream()` (the helper method), never `create(stream=True)`.
**Warning signs:** Getting raw `RawMessageStreamEvent` objects instead of text deltas.

### Pitfall 3: Google GenAI Streaming Token Counts on Empty Response
**What goes wrong:** If the model returns empty content, `last_chunk` may be None or `usage_metadata` may be missing.
**Why it happens:** Edge case when model refuses or returns empty.
**How to avoid:** Guard with `if last_chunk and last_chunk.usage_metadata` before accessing counts. Default to 0.
**Warning signs:** AttributeError on None object.

### Pitfall 4: Run ID Collision in Resumability
**What goes wrong:** If run_ids are generated fresh on each startup, completed items can't be matched for skipping.
**Why it happens:** Need deterministic run_ids derived from matrix item properties.
**How to avoid:** Generate run_id deterministically from `(prompt_id, noise_type, noise_level, intervention, model, repetition_num)` -- e.g., hash or concatenation. This ensures the same matrix item always produces the same run_id across restarts.
**Warning signs:** Duplicate key errors on INSERT, or completed work being re-executed.

### Pitfall 5: Pre-processor Fallback Not Logged
**What goes wrong:** Pre-processor returns garbage but the fallback to raw prompt is silent, making it impossible to analyze pre-processor failure rates.
**Why it happens:** Fallback is treated as success.
**How to avoid:** Log with WARNING level. Set `preproc_failed=True` in metadata. Store both the failed pre-processor output and the fact that fallback was used.
**Warning signs:** Unexpectedly high "sanitized" accuracy that matches raw accuracy.

### Pitfall 6: Anthropic API Key Environment Variable Name
**What goes wrong:** The Anthropic SDK expects `ANTHROPIC_API_KEY` by default. Google GenAI expects `GOOGLE_API_KEY` (or `GEMINI_API_KEY` for AI Studio).
**Why it happens:** Different vendors use different env var names.
**How to avoid:** Validate both keys exist at engine startup before processing any items. Raise `EnvironmentError` with clear message.
**Warning signs:** Cryptic authentication errors mid-run after processing all Claude items.

### Pitfall 7: Gemini System Instruction Format
**What goes wrong:** Google GenAI `system_instruction` in `GenerateContentConfig` may behave differently from Anthropic's `system` parameter.
**Why it happens:** Different APIs handle system prompts differently.
**How to avoid:** For pre-processor calls, use the system prompt + user message format specified in CONTEXT.md. Test both models with the same pre-processor prompt to verify equivalent behavior.
**Warning signs:** Pre-processor returns unexpected format or ignores the system instruction.

## Code Examples

### Deterministic Run ID Generation
```python
def make_run_id(item: dict) -> str:
    """Generate deterministic run_id from matrix item fields."""
    parts = [
        item["prompt_id"],
        item["noise_type"],
        str(item.get("noise_level", "none")),
        item["intervention"],
        item["model"],
        str(item["repetition_num"]),
    ]
    return "|".join(parts)
```

### Cost Calculation from Token Counts
```python
# Price table to add to config.py
PRICE_TABLE: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
    },
    "claude-haiku-4-5-20250514": {
        "input_per_1m": 1.00,
        "output_per_1m": 5.00,
    },
    "gemini-1.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 5.00,
    },
    "gemini-2.0-flash": {
        "input_per_1m": 0.10,
        "output_per_1m": 0.40,
    },
}

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost from token counts and price table."""
    prices = PRICE_TABLE[model]
    return (
        input_tokens * prices["input_per_1m"] / 1_000_000
        + output_tokens * prices["output_per_1m"] / 1_000_000
    )
```

### Pre-processor with Fallback
```python
def sanitize(text: str, model: str, config: ExperimentConfig) -> tuple[str, dict]:
    """Sanitize noisy prompt via cheap model with fallback."""
    preproc_model = _get_preproc_model(model, config)
    system = "You are a text corrector."
    instruction = (
        "Fix all spelling and grammar errors in the following text. "
        "Return only the corrected text, no explanation.\n---\n"
    )
    user_msg = instruction + text

    response = call_model(
        model=preproc_model, system=system,
        user_message=user_msg, max_tokens=len(text) * 2,  # generous limit
        temperature=0.0,
    )

    result = response.text.strip()
    metadata = {
        "preproc_model": preproc_model,
        "preproc_input_tokens": response.input_tokens,
        "preproc_output_tokens": response.output_tokens,
        "preproc_ttft_ms": response.ttft_ms,
        "preproc_ttlt_ms": response.ttlt_ms,
    }

    # Fallback: empty or bloated output
    if not result or len(result) > len(text) * 1.5:
        logger.warning("Pre-processor fallback for model=%s, output_len=%d, input_len=%d",
                       preproc_model, len(result), len(text))
        metadata["preproc_failed"] = True
        return text, metadata

    return result, metadata
```

### Execution Engine Main Loop
```python
def run_engine(args) -> None:
    """Main execution loop: load matrix, skip completed, process items."""
    config = ExperimentConfig()
    conn = init_database(config.results_db_path)
    prompts = load_prompts(config.prompts_path)

    # Load matrix and filter
    matrix = load_matrix(config.matrix_path)
    if args.model != "all":
        matrix = [m for m in matrix if _model_matches(m["model"], args.model)]

    # Resumability: get completed run_ids
    completed = {r["run_id"] for r in query_runs(conn, status="completed")}
    pending = [m for m in matrix if make_run_id(m) not in completed]

    if args.retry_failed:
        failed = {r["run_id"] for r in query_runs(conn, status="failed")}
        pending.extend([m for m in matrix if make_run_id(m) in failed])

    # Group by model, randomize within
    pending = _order_by_model(pending, config.base_seed)

    if args.limit:
        pending = pending[:args.limit]

    if args.dry_run:
        _show_dry_run(pending)
        return

    # Process
    for i, item in enumerate(pending):
        _process_item(item, conn, prompts, config, i, len(pending))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `google-generativeai` SDK | `google-genai` SDK | 2025 (deprecated Aug 2025) | MUST update pyproject.toml; entirely different API shape |
| `genai.GenerativeModel().generate_content()` | `client.models.generate_content()` | 2025 | Client-based pattern, not module-level functions |
| `client.messages.create(stream=True)` | `client.messages.stream()` | Anthropic SDK ~0.25+ | Helper manages event parsing, provides `.text_stream` |
| Anthropic `claude-3-5-sonnet` | `claude-sonnet-4-20250514` | 2025 | Model name format changed; use pinned version from config.py |

**Deprecated/outdated:**
- `google-generativeai` package: Sunset August 31, 2025. Must use `google-genai` instead.
- `genai.configure(api_key=...)` pattern: Old SDK pattern. New SDK uses `genai.Client(api_key=...)`.

## Open Questions

1. **Claude Haiku 4.5 exact model string**
   - What we know: The model is `claude-haiku-4-5-20250514` based on Anthropic naming conventions.
   - What's unclear: Need to verify exact model string accepted by the API.
   - Recommendation: Verify during implementation by checking `anthropic` SDK model list or making a test call. Add to config.py once confirmed.

2. **Gemini Flash 2.0 exact model string**
   - What we know: Likely `gemini-2.0-flash` or `gemini-2.0-flash-001`. Note: Gemini 2.0 Flash is deprecated with shutdown June 1, 2026.
   - What's unclear: Exact string and whether a newer Flash model should be used.
   - Recommendation: Use `gemini-2.0-flash` for now (matches research timeline). Pin in config.py. Consider upgrading if deprecation becomes urgent.

3. **Google GenAI environment variable name**
   - What we know: SDK accepts `GOOGLE_API_KEY` or can use `GEMINI_API_KEY` via explicit `genai.Client(api_key=os.environ["GEMINI_API_KEY"])`.
   - What's unclear: Which env var the `genai.Client()` auto-detects.
   - Recommendation: Use explicit `api_key=os.environ.get("GOOGLE_API_KEY")` for clarity. Document in .env.example.

4. **Pre-processor max_tokens calculation**
   - What we know: CONTEXT.md says max_tokens for main model calls are benchmark-specific (2048/1024).
   - What's unclear: What max_tokens to use for pre-processor calls (sanitize/compress).
   - Recommendation: Use the length of the input text as a rough guide. A generous limit like `max(512, len(prompt_text) * 2)` should suffice -- the pre-processor should return text shorter than or equal to input.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTV-01 | prompt_compressor sanitize + sanitize_and_compress | unit (mock API) | `pytest tests/test_prompt_compressor.py -x` | No -- Wave 0 |
| INTV-02 | prompt_repeater repeat_prompt | unit | `pytest tests/test_prompt_repeater.py -x` | No -- Wave 0 |
| INTV-03 | Self-correct prefix prepended correctly | unit | `pytest tests/test_run_experiment.py::test_self_correct -x` | No -- Wave 0 |
| INTV-04 | Pre-processor pipeline with fallback | unit (mock API) | `pytest tests/test_prompt_compressor.py::test_fallback -x` | No -- Wave 0 |
| INTV-05 | Intervention router dispatches all 5 types | unit | `pytest tests/test_run_experiment.py::test_router -x` | No -- Wave 0 |
| EXEC-01 | API calls to Claude and Gemini succeed | integration (mock SDK) | `pytest tests/test_api_client.py -x` | No -- Wave 0 |
| EXEC-02 | TTFT, TTLT, token counts, cost logged | unit | `pytest tests/test_api_client.py::test_timing -x` | No -- Wave 0 |
| EXEC-03 | 5 repetitions stored | unit | `pytest tests/test_run_experiment.py::test_repetitions -x` | No -- Wave 0 |
| EXEC-04 | Resumability skips completed items | unit | `pytest tests/test_run_experiment.py::test_resumability -x` | No -- Wave 0 |
| EXEC-05 | Rate limiting with delay and 429 handling | unit | `pytest tests/test_api_client.py::test_rate_limit -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_prompt_repeater.py` -- covers INTV-02
- [ ] `tests/test_prompt_compressor.py` -- covers INTV-01, INTV-04 (mock API calls)
- [ ] `tests/test_api_client.py` -- covers EXEC-01, EXEC-02, EXEC-05 (mock SDK clients)
- [ ] `tests/test_run_experiment.py` -- covers INTV-03, INTV-05, EXEC-03, EXEC-04
- [ ] Update `tests/conftest.py` -- add fixtures for mock API responses, sample matrix items

**Mock strategy:** All API tests must use `unittest.mock.patch` to mock the Anthropic and Google SDK clients. No real API calls in tests. Create fixture classes that simulate streaming behavior (yield text chunks, provide usage metadata).

## Sources

### Primary (HIGH confidence)
- Anthropic SDK helpers.md (GitHub) -- streaming API usage, `.stream()`, `.text_stream`, `.get_final_message()`, usage fields
- Google GenAI SDK documentation (googleapis.github.io/python-genai) -- `generate_content_stream()`, `GenerateContentConfig`, client creation
- Google GenAI GitHub issue #1204 -- confirmed last chunk has cumulative `usage_metadata`
- Existing codebase: `src/config.py`, `src/db.py`, `src/grade_results.py` -- established patterns and schema

### Secondary (MEDIUM confidence)
- Anthropic pricing page -- Claude Sonnet 4 at $3/$15 per 1M, Haiku 4.5 at $1/$5 per 1M
- Google Gemini pricing page -- Gemini 1.5 Pro at $1.25/$5 per 1M, Flash 2.0 at $0.10/$0.40 per 1M
- Anthropic model naming: `claude-sonnet-4-20250514`, `claude-haiku-4-5-20250514` (from docs)

### Tertiary (LOW confidence)
- Gemini Flash 2.0 exact model string (may need verification during implementation)
- Google GenAI default environment variable auto-detection behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- both SDKs installed and verified, APIs documented
- Architecture: HIGH -- patterns derived from official SDK docs and existing codebase conventions
- Pitfalls: HIGH -- based on actual SDK differences and known issues
- Pricing: MEDIUM -- prices may change; hardcoded table should be verified before full run

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (30 days -- SDKs and pricing are relatively stable)
