# Phase 9: Add OpenRouter Support with Free Model Defaults (Nemotron) - Research

**Researched:** 2026-03-24
**Domain:** OpenRouter API integration, free model selection, OpenAI SDK reuse
**Confidence:** HIGH

## Summary

OpenRouter provides an OpenAI-compatible API at `https://openrouter.ai/api/v1`, meaning the existing `openai` Python SDK can be reused with a different `base_url` and API key. This is the strongest integration approach: no new dependency, proven streaming with `stream_options={"include_usage": True}`, and the existing `_call_openai` implementation serves as a near-identical template. The `_call_openrouter` function will be a thin variant of `_call_openai` that sets the base URL, uses `OPENROUTER_API_KEY`, adds project-identifying HTTP headers, and strips the `openrouter/` routing prefix before passing the model ID.

Two free NVIDIA Nemotron models are available on OpenRouter as of March 2026: **`nvidia/nemotron-3-super-120b-a12b:free`** (120B MoE, 12B active, 262K context) as the target model, and **`nvidia/nemotron-3-nano-30b-a3b:free`** (30B MoE, 3B active, 256K context) as the pre-processor. Both are $0/million tokens. Free models have rate limits of approximately 20 requests/minute and 50-1000 requests/day depending on credit balance, which the 0.5s inter-request delay accommodates.

**Primary recommendation:** Reuse the `openai` Python SDK with `base_url` override for OpenRouter integration. Use `nvidia/nemotron-3-super-120b-a12b:free` as target and `nvidia/nemotron-3-nano-30b-a3b:free` as pre-processor. No new pip dependencies needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New standalone `_call_openrouter()` function in api_client.py following existing `_call_anthropic`, `_call_google`, `_call_openai` pattern
- Streaming for TTFT/TTLT measurement, same pattern as all other providers
- Project-specific HTTP headers: HTTP-Referer and X-Title identifying the Linguistic Tax Research project
- Same retry pattern: 4 attempts, exponential backoff (1s/4s/16s), double delay on 429
- `openrouter/` prefix for routing in `call_model()` -- prefix stripping inside `_call_openrouter()`
- Models stored with full `openrouter/` prefix in MODELS tuple, PRICE_TABLE, etc.
- 1 free target model + 1 free pre-processor model via OpenRouter
- Named fields in ExperimentConfig: `openrouter_model` and `openrouter_preproc_model`
- OPENROUTER_API_KEY environment variable
- Exact $0 pricing in PRICE_TABLE (input_per_1m: 0.0, output_per_1m: 0.0)
- Conservative rate limit delay: 0.5s for both target and pre-proc free models
- OPENROUTER_BASE_URL as module-level constant in config.py, overridable via env var
- Full experiment matrix: all 8 noise conditions x 5 interventions x 5 reps
- Include in pilot runs
- Unit tests following Phase 8 pattern with conftest mock factories
- Full lifecycle integration test (mocked API)
- Maintain 80%+ line coverage
- Update QA script with OpenRouter-specific validation checks
- Auto-route on OpenRouter (no provider pinning)
- Standard logging only -- no OpenRouter-specific metadata
- No health check or pre-flight validation

### Claude's Discretion
- SDK choice for connecting to OpenRouter (OpenRouter SDK Beta, direct API, or OpenAI SDK reuse)
- Exact pinned model IDs for target and pre-processor (researched during planning)
- Internal streaming implementation details for _call_openrouter
- Any OpenRouter-specific error handling beyond standard rate limit retry

### Deferred Ideas (OUT OF SCOPE)
- Dynamic model discovery (Phase 13/14)
- Provider auto-detection based on configured API keys (Phase 13/14)
- Per-run model selection via CLI (Phase 14)
- Full config precedence system (Phase 14)
- OpenRouter model catalog browsing (Phase 13/14)
- Multi-provider model comparison (future phase)
- Free model comparison study (future phase)
- Model diversity study (future phase)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=2.0.0 (already installed) | OpenRouter API client via base_url override | OpenRouter is OpenAI-compatible; no new dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | - | No additional dependencies needed | - |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenAI SDK reuse | OpenRouter SDK Beta | Beta SDK is TypeScript-only, no Python support |
| OpenAI SDK reuse | Direct requests/httpx | Hand-rolling streaming SSE parsing; more code, more bugs |

**SDK Decision (Claude's Discretion): Use OpenAI SDK reuse.** OpenRouter explicitly documents this as a supported approach. The SDK handles streaming SSE parsing, retry logic (though we use our own), and proper error types. The existing `_call_openai` code is a near-identical template. No new dependency needed since `openai>=2.0.0` is already in `pyproject.toml`.

**Installation:**
```bash
# No new packages needed -- openai is already a dependency
```

## Architecture Patterns

### Recommended Changes by File

```
src/
  config.py          # Add OPENROUTER_BASE_URL, model entries to all config dicts
  api_client.py      # Add _call_openrouter(), extend call_model routing + key validation
.env.example         # Add OPENROUTER_API_KEY
tests/
  conftest.py        # Add mock_openrouter_response fixture
  test_api_client.py # Add TestCallOpenRouter class, routing test, retry test
  test_config.py     # Verify new config entries
  test_integration.py# Add OpenRouter lifecycle test
scripts/
  qa_script.sh       # Add OpenRouter env/API checks
```

### Pattern 1: OpenAI SDK with base_url Override
**What:** Instantiate `openai.OpenAI` with `base_url` pointing to OpenRouter and `api_key` from `OPENROUTER_API_KEY`
**When to use:** Every `_call_openrouter` invocation
**Example:**
```python
# Source: https://openrouter.ai/docs/quickstart
import openai

client = openai.OpenAI(
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://github.com/linguistic-tax",
        "X-Title": "Linguistic Tax Research",
    },
)
```

### Pattern 2: Prefix-Based Routing with Stripping
**What:** `call_model` routes on `openrouter/` prefix; `_call_openrouter` strips it before passing to the API
**When to use:** All OpenRouter model calls
**Example:**
```python
# In call_model():
elif model.startswith("openrouter/"):
    return _call_openrouter(model, system, user_message, max_tokens, temperature)

# In _call_openrouter():
api_model = model.removeprefix("openrouter/")
# Pass api_model to client.chat.completions.create(model=api_model, ...)
```

### Pattern 3: Streaming with stream_options (Identical to OpenAI)
**What:** OpenRouter supports `stream_options={"include_usage": True}` exactly like OpenAI, providing token counts in the final streaming chunk
**When to use:** All streaming calls through _call_openrouter
**Example:**
```python
stream = client.chat.completions.create(
    model=api_model,
    messages=messages,
    max_tokens=max_tokens,
    temperature=temperature,
    stream=True,
    stream_options={"include_usage": True},
)
# Iterate exactly like _call_openai -- same chunk structure
```

### Pattern 4: Rate Limit Error Handling via openai.RateLimitError
**What:** Since we use the OpenAI SDK, rate limit errors from OpenRouter arrive as `openai.RateLimitError` -- the same exception type as direct OpenAI calls
**When to use:** In call_model retry logic
**Note:** The existing `except openai.RateLimitError` block in `call_model()` will catch OpenRouter 429s automatically because the OpenAI SDK raises this for any 429 from any base_url. However, the rate delay doubling uses the full model ID (with `openrouter/` prefix) as the dict key, which is correct.

### Anti-Patterns to Avoid
- **Creating a new OpenAI client per call without base_url:** The base_url MUST be set, otherwise calls go to OpenAI's API
- **Stripping prefix in call_model instead of _call_openrouter:** Keep routing and transformation separate per CONTEXT.md decision
- **Using epsilon values (0.001) instead of exact 0.0 for free pricing:** CONTEXT.md explicitly requires exact $0

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE streaming parser | Custom HTTP streaming | `openai` SDK with `stream=True` | Handles SSE comments, reconnection, chunk parsing |
| Token counting from streams | Manual chunk aggregation | `stream_options={"include_usage": True}` | OpenRouter returns usage in final chunk like OpenAI |
| Rate limit error detection | HTTP status code parsing | `openai.RateLimitError` exception | SDK raises typed exceptions from any base_url |

**Key insight:** OpenRouter's OpenAI compatibility means the entire streaming + error handling infrastructure from `_call_openai` transfers directly. The only differences are: base_url, API key source, extra headers, and prefix stripping.

## Common Pitfalls

### Pitfall 1: Forgetting base_url Leads to OpenAI Charges
**What goes wrong:** If `_call_openrouter` creates an `openai.OpenAI()` client without `base_url`, it hits OpenAI's API with an invalid key (or worse, with a valid OPENAI_API_KEY if env vars are polluted)
**Why it happens:** Copy-paste from `_call_openai` without changing the constructor
**How to avoid:** Always pass `base_url` from the config constant; test verifies base_url is set
**Warning signs:** Unexpected charges on OpenAI account; "invalid API key" errors

### Pitfall 2: Free Model Rate Limits Are Much Stricter
**What goes wrong:** 429 errors during experiment runs, especially with daily limit exhaustion (50/day without credits, 1000/day with $10+ credits)
**Why it happens:** Free models have ~20 RPM and daily caps vs. paid models' much higher limits
**How to avoid:** 0.5s delay (per CONTEXT.md), but also document that full experiment matrix (200 prompts x 8 noise x 5 interventions x 5 reps = 40,000 calls per model) will take multiple days at 1000/day
**Warning signs:** Increasing 429 rate after ~50 or ~1000 calls in a day

### Pitfall 3: Free Model Prompts Are Logged by Provider
**What goes wrong:** Not a code issue, but the free endpoints log all prompts/outputs to improve the provider's model
**Why it happens:** This is how free inference is subsidized
**How to avoid:** Document in comments; only use benchmark prompts (no sensitive data)
**Warning signs:** N/A -- this is expected behavior for `:free` model variants

### Pitfall 4: compute_cost Returning 0.0 for All OpenRouter Calculations
**What goes wrong:** Zero-cost calculations could mask bugs (e.g., cost_projection returning $0 total might seem like an error)
**Why it happens:** $0 pricing is legitimate for free models
**How to avoid:** Ensure cost rollup and projection code handles 0.0 gracefully (no division-by-zero in per-dollar metrics); add explicit test for zero-cost model
**Warning signs:** Division by zero in cost-per-correct-answer calculations

### Pitfall 5: OPENROUTER_BASE_URL Constant vs. Environment Override
**What goes wrong:** Inconsistency between where the base URL is read
**Why it happens:** CONTEXT.md says module-level constant in config.py, overridable via env var
**How to avoid:** Define in config.py: `OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")`. Import in api_client.py
**Warning signs:** Tests that hardcode the URL instead of using the config constant

## Code Examples

### _call_openrouter Implementation Pattern
```python
# Source: https://openrouter.ai/docs/quickstart + existing _call_openai pattern
def _call_openrouter(
    model: str,
    system: str | None,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> APIResponse:
    """Call OpenRouter API with streaming for TTFT/TTLT measurement.

    Uses the OpenAI SDK with base_url override. Strips the 'openrouter/'
    prefix from the model ID before sending to the API.
    """
    from src.config import OPENROUTER_BASE_URL

    api_model = model.removeprefix("openrouter/")

    client = openai.OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "https://github.com/linguistic-tax",
            "X-Title": "Linguistic Tax Research",
        },
    )
    start = time.monotonic()
    ttft_ms = 0.0
    chunks: list[str] = []

    messages: list[dict] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    stream = client.chat.completions.create(
        model=api_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )

    usage = None
    for chunk in stream:
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta.content is not None:
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
        model=model,  # Keep full prefixed model ID for consistency
    )
```

### Config Entries Pattern
```python
# config.py additions

import os

OPENROUTER_BASE_URL: str = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)

# In ExperimentConfig:
openrouter_model: str = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
openrouter_preproc_model: str = "openrouter/nvidia/nemotron-3-nano-30b-a3b:free"

# In MODELS tuple -- add:
"openrouter/nvidia/nemotron-3-super-120b-a12b:free",

# In PRICE_TABLE -- add both:
"openrouter/nvidia/nemotron-3-super-120b-a12b:free": {"input_per_1m": 0.0, "output_per_1m": 0.0},
"openrouter/nvidia/nemotron-3-nano-30b-a3b:free": {"input_per_1m": 0.0, "output_per_1m": 0.0},

# In PREPROC_MODEL_MAP:
"openrouter/nvidia/nemotron-3-super-120b-a12b:free": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",

# In RATE_LIMIT_DELAYS:
"openrouter/nvidia/nemotron-3-super-120b-a12b:free": 0.5,
"openrouter/nvidia/nemotron-3-nano-30b-a3b:free": 0.5,
```

### call_model Routing Extension
```python
# In call_model(), add before the else/ValueError branch:
elif model.startswith("openrouter/"):
    return _call_openrouter(model, system, user_message, max_tokens, temperature)

# In _validate_api_keys(), add:
elif model.startswith("openrouter/"):
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise EnvironmentError("OPENROUTER_API_KEY not set")
```

### Rate Limit Retry -- No New Exception Type Needed
```python
# The existing openai.RateLimitError catch in call_model() handles OpenRouter 429s
# because OpenRouter returns standard HTTP 429 and the openai SDK converts to
# openai.RateLimitError regardless of base_url.
# No code change needed in the retry loop.
```

## Model Selection Research

### Target Model: nvidia/nemotron-3-super-120b-a12b:free
| Property | Value |
|----------|-------|
| OpenRouter ID | `nvidia/nemotron-3-super-120b-a12b:free` |
| Full routing ID | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` |
| Parameters | 120B total, 12B active (MoE) |
| Architecture | Hybrid Mamba-Transformer |
| Context window | 262,144 tokens |
| Pricing | $0 input, $0 output |
| Reasoning | Supports `<think>` tags for extended reasoning |

### Pre-processor Model: nvidia/nemotron-3-nano-30b-a3b:free
| Property | Value |
|----------|-------|
| OpenRouter ID | `nvidia/nemotron-3-nano-30b-a3b:free` |
| Full routing ID | `openrouter/nvidia/nemotron-3-nano-30b-a3b:free` |
| Parameters | 30B total, 3B active (MoE) |
| Architecture | MoE, agentic-focused |
| Context window | 256,000 tokens |
| Pricing | $0 input, $0 output |

### Rate Limits for Free Models
| Metric | Value | Source |
|--------|-------|--------|
| Requests/minute | ~20 RPM | WebSearch (multiple sources) |
| Requests/day (no credits) | ~50 RPD | WebSearch (multiple sources) |
| Requests/day ($10+ credits) | ~1,000 RPD | WebSearch (multiple sources) |

**Experiment feasibility note:** The full matrix for one model is 200 prompts x 8 noise x 5 interventions x 5 reps = 40,000 calls. At 1,000/day (with credits), this would take ~40 days for the target model alone, plus pre-processor calls. This is fine for a cost-free background run but not for quick turnaround. The pilot (20 prompts = ~4,000 calls) would take ~4 days.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OpenRouter SDK (Python) | No Python SDK exists | N/A | Must use OpenAI SDK or direct HTTP |
| OpenRouter SDK Beta (TS) | Beta, TypeScript-only | 2025 | Not usable for Python projects |
| Direct HTTP requests | OpenAI SDK base_url override | OpenAI SDK v1+ (2023) | Zero new dependencies, full streaming support |

**Deprecated/outdated:**
- OpenRouter had a Python SDK attempt but it was never officially released; the recommended Python approach is OpenAI SDK reuse

## Open Questions

1. **Free model availability stability**
   - What we know: These models are available as of March 2026
   - What's unclear: How long free tiers persist; NVIDIA could remove free access
   - Recommendation: Per CONTEXT.md, manual swap if model disappears -- just update config.py with new model ID

2. **Daily rate limit with $10 credits**
   - What we know: $10+ credits unlocks 1,000 RPD for free models
   - What's unclear: Whether purchasing credits is worthwhile given experiment timeline
   - Recommendation: Document the tradeoff; researcher decides based on timeline needs

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_api_client.py tests/test_config.py -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OR-01 | _call_openrouter streams and returns APIResponse | unit | `pytest tests/test_api_client.py::TestCallOpenRouter -x` | No -- Wave 0 |
| OR-02 | call_model routes openrouter/ prefix correctly | unit | `pytest tests/test_api_client.py::TestCallModelRouting -x` | Partially (needs new test) |
| OR-03 | OPENROUTER_API_KEY validation | unit | `pytest tests/test_api_client.py::TestAPIKeyValidation -x` | Partially (needs new test) |
| OR-04 | Config entries (MODELS, PRICE_TABLE, etc.) correct | unit | `pytest tests/test_config.py -x` | Partially (needs new assertions) |
| OR-05 | Zero-cost compute_cost returns 0.0 | unit | `pytest tests/test_config.py -x` | No -- Wave 0 |
| OR-06 | Prefix stripping in _call_openrouter | unit | `pytest tests/test_api_client.py::TestCallOpenRouter -x` | No -- Wave 0 |
| OR-07 | Rate limit retry works for OpenRouter (openai.RateLimitError) | unit | `pytest tests/test_api_client.py::TestRetryAndRateLimiting -x` | Partially (same exception type) |
| OR-08 | Full lifecycle: config -> MODELS -> matrix -> routing -> response | integration | `pytest tests/test_integration.py -x` | Partially (needs OpenRouter path) |
| OR-09 | QA script validates OpenRouter entries | manual | `bash scripts/qa_script.sh --section config` | No -- must update script |

### Sampling Rate
- **Per task commit:** `pytest tests/test_api_client.py tests/test_config.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_client.py::TestCallOpenRouter` -- new test class for _call_openrouter streaming, prefix stripping, headers
- [ ] `tests/conftest.py::mock_openrouter_response` -- factory fixture (can reuse _make_openai_stream_chunks pattern since same SDK)
- [ ] `tests/test_config.py` -- assertions for new MODELS entry, PRICE_TABLE entries, PREPROC_MODEL_MAP entry
- [ ] `tests/test_integration.py` -- OpenRouter lifecycle test path

## Sources

### Primary (HIGH confidence)
- [OpenRouter Quickstart](https://openrouter.ai/docs/quickstart) -- Python integration with OpenAI SDK, authentication, headers
- [OpenRouter Streaming](https://openrouter.ai/docs/api/reference/streaming) -- stream_options support, usage in final chunk
- [OpenRouter Chat Completion API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request) -- stream_options parameter confirmed, response schema
- Existing codebase: `src/api_client.py` `_call_openai` -- proven streaming pattern with identical SDK

### Secondary (MEDIUM confidence)
- [OpenRouter Nemotron 3 Super](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free) -- model specs, $0 pricing, context window
- [OpenRouter Nemotron 3 Nano](https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b:free) -- pre-proc model specs, $0 pricing
- [OpenRouter Rate Limits](https://openrouter.ai/docs/api/reference/limits) -- rate limit structure (exact numbers from WebSearch)

### Tertiary (LOW confidence)
- WebSearch rate limit numbers (20 RPM, 50/1000 RPD) -- multiple sources agree but official docs use template variables

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- OpenAI SDK reuse is officially documented by OpenRouter
- Architecture: HIGH -- follows proven pattern from Phase 7 (OpenAI integration)
- Model selection: MEDIUM -- free models available now but availability can change
- Rate limits: MEDIUM -- approximate numbers from multiple WebSearch sources; official docs use template variables
- Pitfalls: HIGH -- based on direct code analysis and API documentation

**Research date:** 2026-03-24
**Valid until:** 2026-04-07 (free model availability may change; rate limits may be adjusted)
