# Contributing

How to set up the development environment, run tests, and extend the toolkit with new models or interventions.

## Development Setup

```bash
git clone https://github.com/<user>/linguistic-tax.git
cd linguistic-tax
uv sync
uv run pytest tests/ -x -q    # Quick smoke test
```

**API keys** (set in your shell or `.env` file):

```bash
export ANTHROPIC_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="sk-or-..."
```

You only need the keys for providers you intend to use. The free OpenRouter/Nemotron models require only `OPENROUTER_API_KEY`.

## Project Structure Overview

```
src/
  config.py              # ExperimentConfig, MODELS, PRICE_TABLE, constants
  config_manager.py      # Config file I/O and validation
  cli.py                 # CLI entry point (propt command)
  noise_generator.py     # Type A (character) and Type B (syntactic) noise
  prompt_compressor.py   # Sanitization and compression via LLM pre-processor
  prompt_repeater.py     # Prompt repetition intervention
  run_experiment.py      # Execution engine (intervention routing, API calls, grading)
  api_client.py          # Unified API client (Anthropic, Google, OpenAI, OpenRouter)
  grade_results.py       # Auto-grading (HumanEval sandbox, GSM8K regex)
  db.py                  # SQLite schema, insert, query helpers
  compute_derived.py     # CR, quadrant classification, cost rollups
  analyze_results.py     # GLMM, bootstrap CIs, McNemar's, Kendall's tau
  generate_figures.py    # Publication figures (PDF + PNG)
  pilot.py               # Pilot validation
  execution_summary.py   # Pre-run cost/runtime estimates and confirmation gate
  config_commands.py     # Config display/set subcommand handlers
  setup_wizard.py        # Interactive setup wizard
```

See [Architecture](architecture.md) for detailed module descriptions, data flow diagrams, and database schema.

## Running Tests

```bash
# Quick check (stop on first failure)
pytest tests/ -x -q

# Full verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=term-missing

# By keyword (e.g., pilot tests only)
pytest tests/ -k pilot

# Skip slow tests
pytest tests/ -m "not slow"
```

**QA script** for comprehensive pre-release validation:

```bash
bash scripts/qa_script.sh             # Standard checks (6 sections)
bash scripts/qa_script.sh --live      # Include live API tests
bash scripts/qa_script.sh --section 2 # Run only pytest section
bash scripts/qa_script.sh --log       # Save output to timestamped log
```

## Code Conventions

- **Type hints** on all Python functions
- **Docstrings** on all public functions
- **American English** throughout
- **`src.` import prefix** for all internal imports (e.g., `from src.config import MODELS`)
- **Module-level logger**: `logger = logging.getLogger(__name__)`
- **No `print()` for logging** -- use the `logging` module. Exception: CLI user-facing output uses `print()`.
- **No hardcoded API keys** -- always use environment variables
- **Fixed random seeds** for reproducibility (base seed 42, deterministic derivation via `derive_seed()`)
- **Temperature 0.0** for all API calls

## Adding a New Model Provider

Follow these steps to add a new LLM provider (e.g., Mistral, Cohere):

### Step 1: Add model strings to MODELS

In `src/config.py`, add your model identifier to the `MODELS` tuple:

```python
MODELS: tuple[str, ...] = (
    "claude-sonnet-4-20250514",
    "gemini-1.5-pro",
    "gpt-4o-2024-11-20",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "mistral-large-latest",           # <-- new
)
```

### Step 2: Add pricing to PRICE_TABLE

```python
PRICE_TABLE: dict[str, dict[str, float]] = {
    # ... existing entries ...
    "mistral-large-latest": {"input_per_1m": 2.00, "output_per_1m": 6.00},
}
```

### Step 3: Add pre-processor mapping to PREPROC_MODEL_MAP

Map the main model to a cheaper model from the same provider for sanitization/compression:

```python
PREPROC_MODEL_MAP: dict[str, str] = {
    # ... existing entries ...
    "mistral-large-latest": "mistral-small-latest",
}
```

### Step 4: Add rate limit delay to RATE_LIMIT_DELAYS

```python
RATE_LIMIT_DELAYS: dict[str, float] = {
    # ... existing entries ...
    "mistral-large-latest": 0.2,
    "mistral-small-latest": 0.1,
}
```

### Step 5: Create the API call function

In `src/api_client.py`, add a `_call_mistral()` function following the `_call_openai` pattern:

- Accept `model`, `prompt`, `max_tokens` parameters
- Use streaming to measure TTFT (time to first token) and TTLT (time to last token)
- Extract input/output token counts from the response
- Return an `APIResponse` dataclass

### Step 6: Add routing in call_model()

In `src/api_client.py`, add prefix-based routing in the `call_model()` function:

```python
if model.startswith("mistral"):
    return _call_mistral(model, prompt, max_tokens)
```

### Step 7: Add environment variable

Add `MISTRAL_API_KEY` to your `.env` file and add validation in `_validate_api_keys()`.

### Step 8: Add tests

Create test cases in `tests/test_api_client.py` following the `TestCallOpenRouter` pattern:
- Mock the provider SDK
- Verify streaming behavior
- Verify token extraction
- Verify TTFT/TTLT measurement

### Step 9: Update QA script if needed

If the provider requires special environment checks, add them to `scripts/qa_script.sh`.

## Adding a New Intervention

### Step 1: Add intervention string to INTERVENTIONS

In `src/config.py`:

```python
INTERVENTIONS: tuple[str, ...] = (
    "raw",
    "self_correct",
    "pre_proc_sanitize",
    "pre_proc_sanitize_compress",
    "prompt_repetition",
    "my_new_intervention",            # <-- new
)
```

### Step 2: Implement the intervention function

Create a pure function (no side effects, no global state). If it needs an API call (like sanitization), accept a `call_fn` callable parameter instead of importing `api_client` directly:

```python
def my_new_intervention(prompt: str, call_fn: Callable = None) -> str:
    """Apply the new intervention to a prompt."""
    # Transform the prompt
    return transformed_prompt
```

### Step 3: Add routing in run_experiment.py

In the intervention dispatch section of `run_experiment.py`, add a case for your new intervention string.

### Step 4: Add tests

Write tests verifying:
- The transformation is correct for representative inputs
- Edge cases (empty prompt, very long prompt, prompts with special characters)
- Determinism if applicable (same input = same output)

### Step 5: Update experiment matrix generation

In `scripts/generate_matrix.py`, ensure the new intervention is included in the factorial design.

## Test Patterns

### File naming

Test files mirror source modules: `src/foo.py` has tests in `tests/test_foo.py`.

### Shared fixtures

`tests/conftest.py` provides reusable fixtures:

- `sample_config` -- A pre-configured `ExperimentConfig` instance
- `tmp_db_path` -- Temporary SQLite database path with schema initialized
- Mock factory fixtures: `mock_anthropic_response`, `mock_google_response`, `mock_openai_response`, `mock_openrouter_response` -- Create realistic mock API responses for each provider

### Argparse mocking

Use `SimpleNamespace` with the `make_args()` helper for testing CLI handlers:

```python
from types import SimpleNamespace

def make_args(**kwargs):
    defaults = {"db": "test.db", "output_dir": "results/"}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)

args = make_args(model="claude-sonnet-4-20250514")
```

### Noise determinism

Noise generator tests verify that the same seed always produces the same output. This is critical for reproducibility.

### API response mocking

Use the mock factory fixtures from `conftest.py` rather than building mock responses from scratch. This ensures mocks stay consistent with actual API response formats.

## CI and QA

The QA script (`scripts/qa_script.sh`) runs 6 validation sections:

1. **Environment** -- Python version, venv activation, API keys present
2. **Pytest** -- Full test suite
3. **CLI** -- `propt` command availability and subcommand help
4. **Data** -- Prompt files exist and are valid JSON
5. **Config** -- Default config validation
6. **API** -- Live API smoke tests (only with `--live` flag)

Flags:
- `--live`: Enable Section 6 live API tests
- `--section N`: Run only one section (e.g., `--section 2` for pytest only)
- `--log`: Save results to a timestamped log file

## Commit Conventions

This project follows conventional commit style:

| Prefix | Use for |
|--------|---------|
| `test()` | New or modified tests |
| `feat()` | New features or capabilities |
| `fix()` | Bug fixes |
| `docs()` | Documentation changes |
| `refactor()` | Code cleanup with no behavior change |
| `chore()` | Config, tooling, dependencies |
