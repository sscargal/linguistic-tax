# Stack Research

**Domain:** Python research toolkit for LLM prompt noise/optimization experiments
**Researched:** 2026-03-19
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Already constrained by PROJECT.md. 3.11 has good typing support and `tomllib` built-in. No reason to require 3.12+. |
| uv | latest | Package management | Already in use (uv.lock exists). Fastest Python package manager, handles venvs and lockfiles. |
| SQLite (stdlib) | 3.x | Results storage | RDD mandates SQLite. No external dependency needed -- Python's `sqlite3` module is sufficient. Use WAL mode for concurrent reads during analysis. |

### LLM API Clients

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| anthropic | >=0.86.0 | Claude API calls | Official SDK. Pin minimum to current release. Provides structured response objects, automatic retries, token counting. |
| google-genai | >=1.66.0 | Gemini API calls | **CRITICAL: The `google-generativeai` package in pyproject.toml is DEPRECATED (support ended Nov 2025). Must migrate to `google-genai`.** This is the official replacement SDK. Pin to 1.66.0 (1.67.0 has a typing-extensions bug). |

### Statistical Analysis

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| statsmodels | >=0.14.4 | GLMM, logistic regression | RDD's primary analysis is GLMM via `BinomialBayesMixedGLM`. Also provides BH correction (`multipletests`). Current stable is 0.14.6. Limitation: statsmodels GLMM only supports independent random effects -- sufficient for this study's crossed design but worth noting. |
| scipy | >=1.14.0 | McNemar's test, bootstrap CIs | `scipy.stats` has `mcnemar` (added in 1.7+) and `bootstrap` (added in 1.9+). Mature, well-tested. |
| pandas | >=2.2.0 | Data manipulation | De facto standard for tabular data. Needed for aggregation, pivoting results from SQLite into analysis-ready form. |
| numpy | >=1.26.0 | Numerical computation | Transitive dependency of everything above, but pin explicitly for reproducibility. |

### Evaluation and Grading

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| bert-score | >=0.3.13 | Semantic similarity | RDD requires BERTScore for comparing clean vs. noisy outputs. Latest is 0.3.13. Pulls in PyTorch and transformers as dependencies -- this is the heaviest dependency in the stack but there is no lightweight alternative for contextual embedding similarity. |

### Token Counting

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| tiktoken | >=0.12.0 | Token counting for cost estimation | OpenAI's BPE tokenizer. Use for approximate token counts when estimating costs before API calls. Both Anthropic and Google SDKs also return actual token counts in responses -- use those for logged metrics. |

### Visualization

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| matplotlib | >=3.9.0 | Publication-quality figures | Standard for ArXiv papers. Supports LaTeX rendering in labels. |
| seaborn | >=0.13.0 | Statistical plots | Built on matplotlib. Excellent for heatmaps (experiment matrix), violin plots (distribution of scores), and pair plots. |

### Development and Testing

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | >=8.0 | Test runner | Use `pytest -v` for verbose, `pytest -k pilot` for pilot suite |
| ruff | latest | Linting + formatting | Replaces flake8 + black + isort. Single tool, fast. Configure in pyproject.toml. |
| mypy | latest | Type checking | Project requires type hints on all functions. Use `--strict` mode. |

## Installation

```bash
# Using uv (already set up)
uv add anthropic google-genai statsmodels scipy pandas numpy
uv add bert-score tiktoken matplotlib seaborn
uv add --dev pytest ruff mypy

# CRITICAL: Remove deprecated package
uv remove google-generativeai
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| statsmodels GLMM | R's lme4 via rpy2 | If statsmodels GLMM fails to converge (RDD risk register mentions this). lme4 has more robust optimization. But adds R as a dependency -- only use as fallback. |
| statsmodels GLMM | pymer4 (Python wrapper for lme4) | Same as above but slightly easier interface. Still requires R installation. |
| subprocess sandbox for HumanEval | Docker containers | If running on a shared machine or need stronger isolation. For a single-researcher local setup, subprocess with timeout + resource limits is sufficient. |
| bert-score | sentence-transformers cosine similarity | If BERTScore is too slow. Lighter weight but less established in the literature. RDD specifically requires BERTScore, so not recommended. |
| google-genai | litellm | If you want a unified API across providers. Adds abstraction overhead and a third-party dependency for only 2 providers. Not worth it. |
| tiktoken | anthropic SDK's built-in counting | Anthropic SDK returns token counts in responses. tiktoken is only needed for pre-call estimation and cost projection. Could skip if you only need post-call counts. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `google-generativeai` | **Deprecated. Support ended Nov 30, 2025.** No access to recent Gemini features. Will not receive security patches. | `google-genai` (the official replacement SDK) |
| LangChain | Massive dependency tree, unnecessary abstraction for direct API calls. This project sends prompts and logs responses -- no chains, agents, or RAG needed. | Direct `anthropic` and `google-genai` SDK calls |
| OpenAI SDK | Not in scope. RDD specifies Claude and Gemini only. Adding a third provider increases experiment matrix without adding to the paper's contribution. | N/A |
| RestrictedPython | CVE-2025-22153 (critical sandbox escape). Not designed for full code execution. | `subprocess` with timeout, resource limits, and temp directories for HumanEval execution |
| Jupyter notebooks for experiments | Non-reproducible, hard to version control, can't be run by autonomous agent. | Python scripts with `logging` module, results in SQLite |
| `print()` for logging | PROJECT.md explicitly forbids it. No log levels, no file output, no structured logging. | Python `logging` module |
| JSON files for results | PROJECT.md and RDD forbid it. Cannot query, no ACID guarantees, doesn't scale to 20K runs. | SQLite with schema from RDD |
| black / flake8 / isort (separately) | Three tools doing what one tool does. Configuration sprawl. | ruff (single tool, faster, compatible settings) |

## Stack Patterns by Domain

**For HumanEval code execution (sandboxing):**
- Use `subprocess.run()` with `timeout=30` seconds
- Execute in a temporary directory (`tempfile.mkdtemp()`)
- Redirect stdout/stderr to capture test results
- Kill process group on timeout (`os.killpg`)
- Do NOT use `exec()` or `eval()` -- always subprocess

**For GSM8K math grading:**
- Regex extraction of final numerical answer
- Normalize: strip commas, whitespace, dollar signs, percent signs
- Compare as floats with tolerance (e.g., `abs(a - b) < 0.001`)
- Log both extracted and expected values for debugging

**For API call retry/resilience:**
- Both SDKs have built-in retry with exponential backoff
- Set `max_retries=3` on client initialization
- Log every retry attempt with the `logging` module
- Implement a global rate limiter if hitting API limits (use `time.sleep` with jitter)

**For GLMM convergence issues (RDD risk):**
- Start with `BinomialBayesMixedGLM` from statsmodels
- If convergence fails, fall back to `MixedLM` (linear approximation)
- If that fails, fall back to logistic regression with clustered standard errors
- Document which method was used in the results

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| bert-score >=0.3.13 | torch >=1.0, transformers >=4.0 | Pulls in ~2GB of dependencies. Install once, cache the model. First run downloads DeBERTa by default. |
| statsmodels >=0.14.4 | scipy >=1.8, pandas >=1.4, numpy >=1.22 | All compatible with our pinned versions. |
| google-genai >=1.66.0 | Python >=3.9 | Avoid 1.67.0 (typing-extensions bug). |
| anthropic >=0.86.0 | Python >=3.9 | httpx-based, no requests dependency. |

## Critical Migration Note

The existing `pyproject.toml` uses `google-generativeai>=0.8.0`. This package was **permanently discontinued on November 30, 2025**. The migration to `google-genai` involves:

1. Change the import from `import google.generativeai as genai` to `from google import genai`
2. Client initialization changes from `genai.configure(api_key=...)` to `client = genai.Client(api_key=...)`
3. Model calls change from `model.generate_content(...)` to `client.models.generate_content(model=..., contents=...)`
4. Response structure differs -- test thoroughly during migration

Since no code exists yet (src/ only has `__init__.py`), this is a clean start -- use `google-genai` from day one.

## Sources

- [Anthropic Python SDK releases](https://github.com/anthropics/anthropic-sdk-python/releases) -- version 0.86.0 confirmed (2026-03-18)
- [google-generativeai deprecation notice](https://ai.google.dev/gemini-api/docs/libraries) -- support ended Nov 30, 2025, migrate to google-genai
- [google-genai PyPI](https://pypi.org/project/google-genai/) -- version 1.67.0 current, 1.66.0 recommended due to bug
- [statsmodels GLMM docs](https://www.statsmodels.org/stable/mixed_glm.html) -- BinomialBayesMixedGLM for binary outcomes, version 0.14.6
- [bert-score PyPI](https://pypi.org/project/bert-score/) -- version 0.3.13 latest
- [tiktoken PyPI](https://pypi.org/project/tiktoken/) -- version 0.12.0 latest
- [RestrictedPython CVE-2025-22153](https://www.sentinelone.com/vulnerability-database/cve-2025-22153/) -- critical sandbox escape, avoid for code execution
- [Migrating to google-genai SDK](https://medium.com/google-cloud/migrating-to-the-new-google-gen-ai-sdk-python-074d583c2350) -- migration guide
- RDD v4.0 Section 18 (Tools & Infrastructure) -- statsmodels, scipy, scikit-learn, bert-score specified

---
*Stack research for: LLM prompt noise/optimization research toolkit*
*Researched: 2026-03-19*
