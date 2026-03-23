# Phase 7: Add OpenAI to the Supported Model Provider - Research

**Researched:** 2026-03-23
**Domain:** OpenAI Python SDK integration, GPT-4o API, streaming chat completions
**Confidence:** HIGH

## Summary

Adding OpenAI as a third model provider is a well-scoped extension. The existing codebase follows a clean provider-per-function pattern in `api_client.py` with dict-based config in `config.py`. The OpenAI Python SDK (`openai>=2.0`) uses a nearly identical streaming pattern to Anthropic: create a client, call `client.chat.completions.create(stream=True)`, iterate chunks. Token usage during streaming requires `stream_options={"include_usage": True}`, which appends a final chunk with usage stats (choices=[], usage populated).

GPT-4o's latest pinned version is `gpt-4o-2024-11-20`. GPT-4o-mini's latest pinned version is `gpt-4o-mini-2024-07-18`. Current pricing is $2.50/$10.00 per 1M tokens (input/output) for GPT-4o and $0.15/$0.60 for GPT-4o-mini. The OpenAI SDK auto-reads `OPENAI_API_KEY` from environment, matching the project's env-var convention.

**Primary recommendation:** Follow the exact existing provider pattern -- add `_call_openai()` in api_client.py, add config entries, extend routing. The streaming usage pattern requires careful handling of the final empty-choices chunk.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Primary target model: GPT-4o, pinned to latest available version at implementation time
- Pre-processor model: GPT-4o-mini, also pinned to a specific version
- Single OpenAI target model only (no o-series or additional models)
- Environment variable: OPENAI_API_KEY (standard convention)
- Dependency: `openai` Python package added as required dependency in pyproject.toml
- Determinism: temperature=0.0 only, no OpenAI-specific seed parameter
- GPT-4o becomes a full 3rd target model in the experiment matrix (all noise types x all interventions x 5 reps)
- Matrix generator auto-includes all models from the MODELS tuple
- Pilot module extended to validate OpenAI end-to-end before full runs
- Statistical analysis and figure generation modules updated to handle 3 models
- RDD stays as-is -- it's the finalized v1 paper spec
- Use official `openai` Python SDK
- Add `_call_openai()` function following existing `_call_anthropic`/`_call_google` pattern
- Streaming with `stream_options={"include_usage": true}` for TTFT/TTLT measurement AND token counts
- Model routing: `startswith("gpt")` check in `call_model()` dispatcher
- System messages: _call_openai handles conversion from system param to system role message internally
- Rate limit retry: identical pattern to Anthropic -- 4 attempts, exponential backoff, double delay on 429
- Rate limit error type: `openai.RateLimitError`
- Add GPT-4o and GPT-4o-mini to PRICE_TABLE
- Rate limit delays: GPT-4o at 0.2s, GPT-4o-mini at 0.1s

### Claude's Discretion
- Exact pinned version strings for GPT-4o and GPT-4o-mini (research latest stable at impl time)
- Exact current pricing for PRICE_TABLE entries
- Internal streaming implementation details for _call_openai
- Any OpenAI-specific error handling beyond rate limits

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=2.0.0 (latest: 2.29.0) | Official OpenAI Python SDK | Only supported SDK for OpenAI API; matches pattern of one SDK per provider |

### Supporting
No additional supporting libraries needed. The `openai` package is the only new dependency.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openai SDK | Raw HTTP requests | SDK handles auth, retries, types; no reason to go lower-level |
| Chat Completions API | Responses API | Chat Completions is the established API for GPT-4o; Responses API is newer but not needed here |

**Installation:**
```bash
pip install "openai>=2.0.0"
```

**Version verification:** `openai` latest on PyPI is 2.29.0 (verified 2026-03-23).

## Architecture Patterns

### Recommended Project Structure
No new files needed. All changes go into existing files:
```
src/
  api_client.py    # Add _call_openai(), extend call_model routing + retry
  config.py        # Add to MODELS, PRICE_TABLE, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS
pyproject.toml     # Add openai dependency
.env.example       # Add OPENAI_API_KEY
tests/
  test_api_client.py  # Add OpenAI routing, streaming, retry tests
  test_config.py      # Verify new config entries
```

### Pattern 1: OpenAI Streaming with Usage Tracking
**What:** Stream chat completions while capturing TTFT, TTLT, and token usage in a single call
**When to use:** Every `_call_openai()` invocation
**Example:**
```python
# Source: OpenAI API docs + cookbook
import openai

def _call_openai(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    client = openai.OpenAI()
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages: list[dict] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )

    usage = None
    for chunk in stream:
        # Final chunk has usage but empty choices
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta.content:
            if not chunks:
                ttft_ms = (time.monotonic() - start) * 1000
            chunks.append(chunk.choices[0].delta.content)

    ttlt_ms = (time.monotonic() - start) * 1000

    return APIResponse(
        text="".join(chunks),
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        ttft_ms=ttft_ms,
        ttlt_ms=ttlt_ms,
        model=model,
    )
```

### Pattern 2: System Message Conversion
**What:** Convert the `system` parameter to a message with role "system" in the messages array
**When to use:** In `_call_openai()` before sending to the API
**Key detail:** GPT-4o supports both "system" and "developer" roles. Use "system" for consistency -- it auto-converts for newer models. The `call_model()` signature remains unchanged; conversion is internal to `_call_openai()`.

### Pattern 3: Rate Limit Handling
**What:** Catch `openai.RateLimitError` in `call_model()` retry loop
**When to use:** Alongside existing Anthropic and Google error handlers
**Example:**
```python
import openai

# In call_model() retry loop, add:
except openai.RateLimitError as e:
    last_error = e
    _rate_delays[model] = _rate_delays.get(model, 0.2) * 2
    logger.warning(
        "Rate limited on %s (attempt %d/4), delay now %.1fs",
        model, attempt + 1, _rate_delays[model],
    )
    if attempt < 3:
        time.sleep(retry_delays[attempt])
```

### Anti-Patterns to Avoid
- **Using the Responses API instead of Chat Completions:** The Responses API is OpenAI's newer interface but the Chat Completions API is what GPT-4o uses and matches our existing pattern. Do not mix APIs.
- **Using `"developer"` role for system messages:** While newer models support it, `"system"` role works for GPT-4o and is more universally understood. Stick with `"system"`.
- **Forgetting `stream_options`:** Without `stream_options={"include_usage": True}`, streaming responses do NOT include token counts. This would break our logging requirement.
- **Creating a new OpenAI client per call:** The `openai.OpenAI()` constructor reads env vars each time. This is fine for our use case (matches Anthropic pattern which also creates per-call), but be aware of it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI API communication | Custom HTTP client | `openai` SDK | Handles auth, retries, streaming, types |
| Token counting | Manual tokenizer calls | `stream_options={"include_usage": True}` | Server-side count is authoritative |
| Rate limit detection | HTTP status parsing | `openai.RateLimitError` exception | SDK raises typed exceptions |

**Key insight:** The openai SDK provides the same level of abstraction as Anthropic's SDK -- typed exceptions, streaming iterators, auto-auth from env vars. Follow the existing pattern exactly.

## Common Pitfalls

### Pitfall 1: Missing Usage on Final Stream Chunk
**What goes wrong:** The final streaming chunk has `choices=[]` (empty) but contains `usage`. If code only processes chunks with non-empty choices, it misses usage data.
**Why it happens:** OpenAI appends an extra chunk solely for usage stats when `stream_options={"include_usage": True}`.
**How to avoid:** Check `chunk.usage is not None` separately from content extraction. Store usage when found.
**Warning signs:** `input_tokens=0` and `output_tokens=0` in results despite successful responses.

### Pitfall 2: Delta Content Can Be None
**What goes wrong:** `chunk.choices[0].delta.content` can be `None` on some chunks (e.g., role-only deltas at the start).
**Why it happens:** The first chunk typically contains only the role assignment, not content.
**How to avoid:** Always check `chunk.choices[0].delta.content is not None` before appending.
**Warning signs:** `TypeError: can only concatenate str (not NoneType) to str`.

### Pitfall 3: OpenAI Uses "system" Role Not a Separate Parameter
**What goes wrong:** Passing system instructions as a top-level parameter (like Anthropic's `system=` kwarg) instead of as a message.
**Why it happens:** Anthropic has `system` as a top-level API parameter; OpenAI embeds it in the messages array.
**How to avoid:** In `_call_openai()`, prepend `{"role": "system", "content": system}` to the messages list when system is not None.
**Warning signs:** System instructions being ignored silently.

### Pitfall 4: Model Routing Collision with Future Models
**What goes wrong:** Using `startswith("gpt")` might collide if other model names start with "gpt".
**Why it happens:** Overly broad prefix matching.
**How to avoid:** This is acceptable per the user's decision. GPT is distinctly OpenAI's namespace. If issues arise later, tighten the prefix.
**Warning signs:** N/A -- low risk for this project's scope.

### Pitfall 5: Import at Module Level Causes Failure Without SDK
**What goes wrong:** If `import openai` is at the top of api_client.py and the package isn't installed, ALL model calls fail.
**Why it happens:** Module-level imports execute on first import.
**How to avoid:** This is the correct pattern (matches Anthropic/Google imports). Just ensure `openai` is in pyproject.toml dependencies.
**Warning signs:** `ModuleNotFoundError: No module named 'openai'` even when only using Anthropic.

## Code Examples

### Config Entries to Add
```python
# In config.py

# Add to MODELS tuple:
MODELS: tuple[str, ...] = (
    "claude-sonnet-4-20250514",
    "gemini-1.5-pro",
    "gpt-4o-2024-11-20",
)

# Add to ExperimentConfig:
@dataclass(frozen=True)
class ExperimentConfig:
    # ... existing fields ...
    openai_model: str = "gpt-4o-2024-11-20"

# Add to PRICE_TABLE:
PRICE_TABLE: dict[str, dict[str, float]] = {
    # ... existing entries ...
    "gpt-4o-2024-11-20": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-4o-mini-2024-07-18": {"input_per_1m": 0.15, "output_per_1m": 0.60},
}

# Add to PREPROC_MODEL_MAP:
PREPROC_MODEL_MAP: dict[str, str] = {
    # ... existing entries ...
    "gpt-4o-2024-11-20": "gpt-4o-mini-2024-07-18",
}

# Add to RATE_LIMIT_DELAYS:
RATE_LIMIT_DELAYS: dict[str, float] = {
    # ... existing entries ...
    "gpt-4o-2024-11-20": 0.2,
    "gpt-4o-mini-2024-07-18": 0.1,
}
```

### API Key Validation Extension
```python
# In api_client.py _validate_api_keys():
elif model.startswith("gpt"):
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not set")
```

### Call Model Routing Extension
```python
# In call_model() dispatch:
elif model.startswith("gpt"):
    return _call_openai(model, system, user_message, max_tokens, temperature)
```

### Test Mock Pattern for OpenAI Streaming
```python
def _make_openai_stream_chunks(text_chunks: list[str], prompt_tokens: int, completion_tokens: int):
    """Create mock OpenAI streaming chunks."""
    chunks = []
    for text in text_chunks:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = text
        chunk.usage = None
        chunks.append(chunk)

    # Final usage-only chunk
    usage_chunk = MagicMock()
    usage_chunk.choices = []
    usage_mock = MagicMock()
    usage_mock.prompt_tokens = prompt_tokens
    usage_mock.completion_tokens = completion_tokens
    usage_chunk.usage = usage_mock
    chunks.append(usage_chunk)

    return chunks
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| openai v0.x (openai.ChatCompletion.create) | openai v2.x (client.chat.completions.create) | v1.0 (Nov 2023) | Completely different API surface; must use v2+ |
| No streaming usage stats | stream_options={"include_usage": True} | Mid-2024 | Can now get token counts without a separate API call |
| "system" role only | "developer" role (newer models) | 2025 | "system" still works for GPT-4o; "developer" is for o-series |
| Chat Completions API only | Responses API (newer) | 2025 | Chat Completions remains fully supported for GPT-4o |

**Deprecated/outdated:**
- `openai.ChatCompletion.create()`: Old v0.x API surface. Use `client.chat.completions.create()`.
- `openai.error.RateLimitError`: Old exception path. Use `openai.RateLimitError` directly.

## Open Questions

1. **GPT-4o model version freshness**
   - What we know: `gpt-4o-2024-11-20` is the latest pinned snapshot as of March 2026
   - What's unclear: OpenAI may release newer snapshots; the alias `gpt-4o` points to latest but we want pinned
   - Recommendation: Use `gpt-4o-2024-11-20` as pinned version. Document that it can be updated later.

2. **OpenAI `max_tokens` vs `max_completion_tokens`**
   - What we know: OpenAI renamed `max_tokens` to `max_completion_tokens` for newer models (o-series). For GPT-4o via Chat Completions, `max_tokens` still works.
   - What's unclear: Whether `max_tokens` will be deprecated for GPT-4o in the future
   - Recommendation: Use `max_tokens` for now -- it works and matches the existing `call_model()` signature.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_api_client.py tests/test_config.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N/A-01 | _call_openai streaming returns APIResponse | unit | `pytest tests/test_api_client.py::TestCallOpenAI -x` | No -- Wave 0 |
| N/A-02 | call_model routes gpt-* to _call_openai | unit | `pytest tests/test_api_client.py::TestCallModelRouting -x` | Partial -- extend existing |
| N/A-03 | OpenAI rate limit retry with backoff | unit | `pytest tests/test_api_client.py::TestRetryAndRateLimiting -x` | Partial -- extend existing |
| N/A-04 | OPENAI_API_KEY validation | unit | `pytest tests/test_api_client.py::TestAPIKeyValidation -x` | No -- Wave 0 |
| N/A-05 | Config entries (MODELS, PRICE_TABLE, etc.) | unit | `pytest tests/test_config.py -x` | Partial -- verify new entries |
| N/A-06 | TTFT/TTLT timing for OpenAI stream | unit | `pytest tests/test_api_client.py::TestTiming -x` | Partial -- extend |

### Sampling Rate
- **Per task commit:** `pytest tests/test_api_client.py tests/test_config.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_client.py::TestCallOpenAI` -- new test class for _call_openai streaming
- [ ] `tests/test_api_client.py` -- extend TestCallModelRouting with gpt-* routing test
- [ ] `tests/test_api_client.py` -- extend TestRetryAndRateLimiting with openai.RateLimitError test
- [ ] `tests/test_api_client.py` -- extend TestAPIKeyValidation with OPENAI_API_KEY test

## Sources

### Primary (HIGH confidence)
- [OpenAI API models page](https://developers.openai.com/api/docs/models/gpt-4o) -- GPT-4o pinned versions: gpt-4o-2024-11-20
- [OpenAI API models page](https://developers.openai.com/api/docs/models/gpt-4o-mini) -- GPT-4o-mini pinned version: gpt-4o-mini-2024-07-18
- [OpenAI pricing page](https://developers.openai.com/api/docs/pricing) -- GPT-4o: $2.50/$10.00, GPT-4o-mini: $0.15/$0.60
- [OpenAI streaming docs](https://developers.openai.com/api/docs/guides/streaming-responses) -- Streaming pattern and stream_options
- [OpenAI cookbook - streaming](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb) -- stream_options={"include_usage": True} pattern
- [openai PyPI](https://pypi.org/project/openai/) -- Latest version 2.29.0, verified 2026-03-23

### Secondary (MEDIUM confidence)
- [OpenAI community forum](https://community.openai.com/t/usage-stats-now-available-when-using-streaming-with-the-chat-completions-api-or-completions-api/738156) -- Usage stats streaming details
- [OpenAI community forum](https://community.openai.com/t/system-vs-developer-role-in-4o-model/1119179) -- system vs developer role for GPT-4o

### Tertiary (LOW confidence)
- None -- all findings verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- single official SDK, verified version on PyPI
- Architecture: HIGH -- follows exact existing pattern in codebase, SDK API verified
- Pitfalls: HIGH -- documented in official SDK docs and cookbook
- Pricing: MEDIUM -- verified via multiple sources but prices can change

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (pricing may change; model versions stable once pinned)
