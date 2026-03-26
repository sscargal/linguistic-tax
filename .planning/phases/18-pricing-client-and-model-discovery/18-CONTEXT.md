# Phase 18: Pricing Client and Model Discovery - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Query live model availability and pricing from provider APIs. Enhance `propt list-models` to display real model IDs, context windows, and pricing where available. Fall back gracefully when provider APIs are unreachable. This phase does NOT add free-text model entry (Phase 19) or modify the setup wizard.

Requirements: DSC-01, DSC-02, PRC-02.

</domain>

<decisions>
## Implementation Decisions

### Provider API querying
- Query all 4 configured providers (Anthropic, Google, OpenAI, OpenRouter) for live model listing
- Use each provider's SDK `models.list()` endpoint where available; HTTP GET for OpenRouter `/api/v1/models`
- Show ALL available models from each provider, with configured models marked/highlighted (aids model discovery)
- Query providers in parallel (threading or asyncio) for faster CLI response

### Output format
- Columns: Model ID, Provider, Context Window, Input Price (per 1M tokens), Output Price (per 1M tokens), Status (configured/available)
- Group output by provider with provider headers
- Pricing format: `$X.XX / $Y.YY` per 1M tokens, `free` for zero-cost, `--` for unknown
- Add `--json` flag for programmatic JSON output (consistent with existing config commands' `--format json`)

### Fallback behavior
- When a provider API is unreachable: show fallback pricing from registry with a `fallback` indicator, log a warning identifying which provider failed
- 5-second timeout per provider API query
- Missing API keys: warn that provider was skipped (e.g., "Skipping anthropic: ANTHROPIC_API_KEY not set"), do not crash

### Pricing source priority
- Live pricing displayed when available; fallback pricing from registry shown only when live query fails
- Display-only -- live pricing does NOT update the registry or config (preserves reproducibility)
- No caching of live pricing across invocations (CLI command, not a hot path)

### Claude's Discretion
- Internal implementation of provider query abstraction (shared interface vs per-provider functions)
- Threading vs asyncio for parallel queries
- Exact table formatting and column widths
- How to detect and parse context window from each provider's response schema

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specification
- `docs/RDD_Linguistic_Tax_v4.md` -- Research Design Document defining experimental parameters and model requirements

### Requirements
- `.planning/REQUIREMENTS.md` -- v2.0 requirements DSC-01, DSC-02, PRC-02 (all mapped to Phase 18)

### Out of scope documentation
- `.planning/REQUIREMENTS.md` "Out of Scope" table -- confirms Anthropic/Google/OpenAI do NOT expose pricing via SDKs; only model IDs and capabilities

### Existing implementation
- `src/model_registry.py` -- ModelRegistry class, get_price(), compute_cost(), target_models(), check_provider()
- `src/config_commands.py` `handle_list_models()` (line 319) -- current list-models implementation reading from registry
- `src/api_client.py` -- existing SDK imports for anthropic, google.genai, openai (provider SDK patterns)
- `data/default_models.json` -- curated fallback pricing for all 8 default models
- `src/cli.py` line 146 -- argparse setup for list-models subcommand

### Phase 16 context (foundation)
- `.planning/phases/16-config-schema-and-defensive-fallbacks/16-CONTEXT.md` -- ModelConfig dataclass design, null vs 0.0 pricing semantics

### STATE.md research flag
- `.planning/STATE.md` -- "OpenRouter /api/v1/models pricing schema is MEDIUM confidence -- verify live before writing parser"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ModelRegistry` in `model_registry.py` -- provides fallback pricing via `get_price()` and model enumeration via `target_models()`
- `registry.check_provider()` -- already checks if API key exists for a provider (groundwork from Phase 16)
- `_PROVIDER_KEY_MAP` in `model_registry.py` -- maps provider names to env var names
- `handle_list_models()` in `config_commands.py` -- existing table display using `tabulate`; will be enhanced
- Provider SDK clients already imported in `api_client.py` -- `anthropic`, `google.genai`, `openai`

### Established Patterns
- `tabulate` library used for all CLI table output (config_commands.py)
- `--format json` flag pattern established in config show/diff commands
- `print()` for CLI user-facing output (Phase 14 decision)
- `logging` module for warnings/errors
- Registry singleton pattern: `from src.model_registry import registry`

### Integration Points
- `handle_list_models()` in `config_commands.py` -- main enhancement target
- `cli.py` argparse for list-models -- add `--json` flag
- `model_registry.py` -- may need new methods for provider enumeration or a separate `model_discovery.py` module
- Provider SDKs already in `requirements.txt` -- no new dependencies needed for SDK-based listing

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. Auto-selected recommended defaults throughout.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 18-pricing-client-and-model-discovery*
*Context gathered: 2026-03-26*
