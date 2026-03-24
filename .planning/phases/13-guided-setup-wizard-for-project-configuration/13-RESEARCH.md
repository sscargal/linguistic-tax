# Phase 13: Guided Setup Wizard for Project Configuration - Research

**Researched:** 2026-03-24
**Domain:** Python CLI wizard, config file management, argparse subcommands
**Confidence:** HIGH

## Summary

Phase 13 builds a guided setup wizard as a CLI subcommand (`python src/cli.py setup`) that helps new users configure the Linguistic Tax toolkit through an interactive Q&A flow. The wizard creates a JSON config file in the project directory with all configurable properties from `ExperimentConfig`, using sensible defaults. It also establishes the CLI entry point (`src/cli.py`) with an extensible subcommand architecture that Phase 14 will build upon.

The technical domain is straightforward: Python's standard library provides everything needed. `argparse` with subparsers handles the CLI architecture, `json` handles config persistence, and `input()` handles the interactive wizard flow. The main complexity is in the design -- mapping the existing `ExperimentConfig` frozen dataclass to a file-based override system, structuring the wizard flow for good UX, and validating API keys with minimal test calls.

**Primary recommendation:** Use argparse subparsers for CLI, a dedicated `src/config_manager.py` module for config file I/O and merging with `ExperimentConfig` defaults, and keep the wizard logic in a separate `src/setup_wizard.py` module for testability.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Config file format: JSON (zero dependency -- Python `json` module handles read + write)
- Config file location: project directory (alongside `src/`, `data/`, etc.) -- NOT a global dotfile
- All configurable properties from `ExperimentConfig` are included in the config file with sensible defaults
- Runtime behavior: `ExperimentConfig` retains hardcoded defaults. On load, slicer checks for config file -- values present override dataclass defaults, missing keys fall back to hardcoded defaults
- Config file only needs to contain what the user changed (sparse override pattern)
- Essential config only in wizard: model provider, target model, preproc model, API key env var name, paths (prompts, matrix, results DB)
- Power users edit the JSON directly for advanced settings
- Model selection: pick provider -> auto-fills default target + preproc model -> user can accept or override
- API key validation: make a minimal test API call to confirm the key works
- New dedicated CLI entry point: `src/cli.py` with subcommand architecture (argparse subparsers)
- `setup` (or `init`) subcommand launches the wizard
- Existing scripts continue to work as-is -- CLI is additive
- If no config file exists when running experiment, print message guiding to `python src/cli.py setup` and exit
- Config validation on load: model strings match `PRICE_TABLE` keys, paths exist or are creatable, noise rates in valid ranges (0-1), repetitions > 0, temperature >= 0
- Environment check: Python version (3.11+), required packages installed, API key env vars are set and non-empty
- User refers to the toolkit as "the slicer"

### Claude's Discretion
- Exact config file name (avoiding confusion with `.planning/config.json`)
- Wizard UX details (colors, progress indicators, confirmation prompts)
- argparse vs click/typer for CLI framework (argparse preferred to match existing patterns)
- How to structure the config loading integration with ExperimentConfig
- Exact validation rules and error message formatting

### Deferred Ideas (OUT OF SCOPE)
- Config profiles (named profiles like "pilot", "full-run", "cheap")
- Dry-run / cost preview (relates to Phase 15)
- Config migration/versioning
- Multi-provider experiments
- Experiment templates
- Config diff (show changes from defaults)
- Export config to paper appendix

</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | CLI with subcommand routing | Already used in `run_experiment.py` and `pilot.py`; zero dependency |
| json | stdlib | Config file read/write | Locked decision; zero dependency |
| dataclasses | stdlib | Config dataclass integration | Already used for `ExperimentConfig` |
| importlib.metadata | stdlib | Package version detection for env check | Standard way to check installed packages |
| sys | stdlib | Python version check, exit codes | Standard library |
| os | stdlib | Path operations, env var checking | Already used throughout project |
| pathlib | stdlib | Path validation and creation | Cleaner than os.path for validation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anthropic | >=0.40.0 | API key validation test call (Anthropic) | During wizard setup when user selects Anthropic |
| google-genai | >=1.0.0 | API key validation test call (Google) | During wizard setup when user selects Google |
| openai | >=2.0.0 | API key validation test call (OpenAI/OpenRouter) | During wizard setup when user selects OpenAI or OpenRouter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click/typer | More ergonomic but adds dependency; project already uses argparse everywhere |
| input() | questionary/inquirer | Richer UX (autocomplete, selection lists) but adds dependency for minimal benefit |

**Installation:**
```bash
# No new dependencies needed -- all stdlib + existing project deps
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  cli.py                # CLI entry point with argparse subparsers
  setup_wizard.py       # Interactive wizard flow (Q&A logic)
  config_manager.py     # Config file I/O, merge with ExperimentConfig, validation
  config.py             # Existing -- ExperimentConfig frozen dataclass (unchanged)
  run_experiment.py     # Existing -- add config-missing check at startup
```

### Pattern 1: Argparse Subparsers for Extensible CLI
**What:** Use `argparse.add_subparsers()` to create a command hierarchy that Phase 14 can extend
**When to use:** Always -- this is the locked decision for CLI architecture
**Example:**
```python
# src/cli.py
import argparse
import logging
import sys

from src.setup_wizard import run_setup_wizard


def build_cli() -> argparse.ArgumentParser:
    """Build the main CLI parser with subcommand routing."""
    parser = argparse.ArgumentParser(
        prog="linguistic-tax",
        description="Linguistic Tax research toolkit CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup wizard subcommand
    setup_parser = subparsers.add_parser(
        "setup",
        help="Run the guided setup wizard to configure the toolkit",
    )
    setup_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Write default config without prompting (for CI/scripting)",
    )
    setup_parser.set_defaults(func=run_setup_wizard)

    # Phase 14 will add: config show, config set, config list, etc.

    return parser


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_cli()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
```

### Pattern 2: Sparse Override Config Loading
**What:** Config file contains only user-changed values; missing keys fall back to `ExperimentConfig` defaults
**When to use:** Config load at experiment startup
**Example:**
```python
# src/config_manager.py
import json
from dataclasses import fields, asdict
from pathlib import Path
from src.config import ExperimentConfig

CONFIG_FILENAME = "experiment_config.json"


def find_config_path(start_dir: str = ".") -> Path | None:
    """Find config file in the given directory."""
    path = Path(start_dir) / CONFIG_FILENAME
    return path if path.exists() else None


def load_config(config_path: Path | None = None) -> ExperimentConfig:
    """Load config from file, merging with ExperimentConfig defaults.

    Missing keys fall back to dataclass defaults. Unknown keys are ignored.
    """
    if config_path is None:
        config_path = find_config_path()
    if config_path is None:
        return ExperimentConfig()

    with open(config_path) as f:
        overrides = json.load(f)

    # Filter to valid ExperimentConfig fields only
    valid_fields = {field.name for field in fields(ExperimentConfig)}
    filtered = {k: v for k, v in overrides.items() if k in valid_fields}

    # Convert lists back to tuples for tuple fields
    for field in fields(ExperimentConfig):
        if field.name in filtered and field.type.startswith("tuple"):
            filtered[field.name] = tuple(filtered[field.name])

    return ExperimentConfig(**filtered)


def save_config(config: dict, config_path: Path | None = None) -> Path:
    """Write config dict to JSON file."""
    if config_path is None:
        config_path = Path(".") / CONFIG_FILENAME
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return config_path


def get_full_config_dict() -> dict:
    """Return all ExperimentConfig fields with their defaults as a dict."""
    config = ExperimentConfig()
    d = asdict(config)
    # Convert tuples to lists for JSON serialization
    for k, v in d.items():
        if isinstance(v, tuple):
            d[k] = list(v)
    return d
```

### Pattern 3: Provider-Based Model Selection
**What:** User picks provider, wizard auto-fills target + preproc model from existing config maps
**When to use:** During wizard model selection step
**Example:**
```python
from src.config import MODELS, PREPROC_MODEL_MAP

PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": [m for m in MODELS if m.startswith("claude")],
        "env_var": "ANTHROPIC_API_KEY",
    },
    "google": {
        "name": "Google (Gemini)",
        "models": [m for m in MODELS if m.startswith("gemini")],
        "env_var": "GOOGLE_API_KEY",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "models": [m for m in MODELS if m.startswith("gpt")],
        "env_var": "OPENAI_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter (free models)",
        "models": [m for m in MODELS if m.startswith("openrouter/")],
        "env_var": "OPENROUTER_API_KEY",
    },
}
```

### Pattern 4: Config-Missing Guard
**What:** Early check in `run_experiment.py` that prints guidance and exits if no config file exists
**When to use:** At the top of `run_engine()` or in `main()`
**Example:**
```python
from src.config_manager import find_config_path, CONFIG_FILENAME

def _check_config_exists() -> None:
    """Exit with guidance if no config file is found."""
    if find_config_path() is None:
        logger.error(
            "No config found. Run `python src/cli.py setup` to configure "
            "the slicer before running experiments."
        )
        sys.exit(1)
```

### Anti-Patterns to Avoid
- **Modifying ExperimentConfig class itself:** The frozen dataclass should remain unchanged. Config loading creates a new instance with overrides, not mutating the class.
- **Using print() for wizard output:** CLAUDE.md requires `logging` module. However, for interactive wizard prompts, `print()` is acceptable since logging adds timestamps/levels that clutter user-facing Q&A. Recommendation: use `print()` for wizard-specific interactive prompts, `logging` for everything else.
- **Auto-launching wizard on missing config:** Locked decision says NO -- just print a message and exit. Safe for CI.
- **Storing secrets in config file:** API keys stay in environment variables. Config stores the env var NAME (e.g., `"api_key_env_var": "ANTHROPIC_API_KEY"`), never the key value.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Custom arg parsing | `argparse` subparsers | Battle-tested, already used in project |
| JSON serialization | Custom config format | `json` stdlib | Zero dependency, human-readable |
| Python version check | String parsing sys.version | `sys.version_info` tuple comparison | Clean, reliable |
| Package availability check | try/import each package | `importlib.metadata.distributions()` or `importlib.metadata.version()` | Standard, handles version checking |
| API key validation | Custom HTTP calls | Existing SDK clients from `api_client.py` | Already imported, handles auth correctly |

**Key insight:** This phase uses entirely stdlib tools. The only external dependencies are the existing API SDKs for validation test calls.

## Common Pitfalls

### Pitfall 1: Frozen Dataclass with Tuple Fields and JSON
**What goes wrong:** JSON doesn't have tuples -- `json.dump` converts tuples to lists, `json.load` returns lists. If you pass lists to `ExperimentConfig(type_a_rates=[0.05, 0.10, 0.20])`, it works (Python accepts list for tuple-typed field) but `asdict()` then returns lists not tuples.
**Why it happens:** JSON only has arrays, Python has both lists and tuples.
**How to avoid:** On config load, explicitly convert list values back to tuples for fields typed as `tuple`. On save, convert tuples to lists.
**Warning signs:** Type checker warnings about list vs tuple.

### Pitfall 2: Config File Name Collision
**What goes wrong:** Naming the config file `config.json` collides with `.planning/config.json` (the GSD config).
**Why it happens:** Generic naming in a project that already has a `config.json`.
**How to avoid:** Use a distinct name like `experiment_config.json` or `slicer_config.json`. Recommendation: `experiment_config.json` -- clear, specific, matches `ExperimentConfig` class name.
**Warning signs:** User confusion about which config file is which.

### Pitfall 3: Interactive Input in Tests
**What goes wrong:** Tests that call wizard functions hang waiting for `input()`.
**Why it happens:** `input()` blocks on stdin.
**How to avoid:** Design wizard functions to accept an `input_fn` parameter (defaulting to `input`) that tests can replace with a mock/lambda. Or use `unittest.mock.patch("builtins.input")`.
**Warning signs:** Tests hanging indefinitely.

### Pitfall 4: API Validation Call Failure Modes
**What goes wrong:** Validation call fails due to network issues, rate limiting, or model unavailability -- wizard treats this as "bad key" when it's actually a transient error.
**Why it happens:** Multiple failure modes for API calls beyond auth.
**How to avoid:** Distinguish between auth errors (401/403) and other errors (network, rate limit, server error). Report specific failure type to user.
**Warning signs:** User has valid key but wizard says it's invalid.

### Pitfall 5: Logging vs Print for Interactive Wizard
**What goes wrong:** Using `logging.info()` for wizard prompts adds ugly timestamps and log levels to user-facing Q&A flow.
**Why it happens:** CLAUDE.md says "Do NOT use print() for logging."
**How to avoid:** The rule is about logging (debug info, errors, progress). For interactive user prompts and wizard output, `print()` is the right tool. Use `logging` for status messages, errors, and non-interactive output.
**Warning signs:** Wizard output cluttered with `2026-03-24 INFO src.setup_wizard: Choose your provider:`.

### Pitfall 6: Relative Path Resolution
**What goes wrong:** Config file stores paths like `data/prompts.json` but the working directory when running may differ from the project root.
**Why it happens:** Relative paths are relative to CWD, not to config file location.
**How to avoid:** Document that paths in config are relative to project root. The config loader can resolve them relative to the config file's parent directory.
**Warning signs:** FileNotFoundError when running from a subdirectory.

## Code Examples

### Config Validation
```python
def validate_config(config_dict: dict) -> list[str]:
    """Validate config values, returning list of error messages."""
    errors = []
    from src.config import PRICE_TABLE

    # Model validation
    for key in ("claude_model", "gemini_model", "openai_model", "openrouter_model"):
        if key in config_dict:
            model = config_dict[key]
            if model not in PRICE_TABLE:
                errors.append(f"Unknown model '{model}' for {key}. "
                             f"Valid: {', '.join(PRICE_TABLE.keys())}")

    # Noise rate validation
    if "type_a_rates" in config_dict:
        for rate in config_dict["type_a_rates"]:
            if not 0 <= rate <= 1:
                errors.append(f"Noise rate {rate} not in range [0, 1]")

    # Repetitions
    if "repetitions" in config_dict:
        if config_dict["repetitions"] < 1:
            errors.append("Repetitions must be >= 1")

    # Temperature
    if "temperature" in config_dict:
        if config_dict["temperature"] < 0:
            errors.append("Temperature must be >= 0")

    # Path existence (warn, don't error -- paths may be created later)
    for key in ("prompts_path", "matrix_path"):
        if key in config_dict and not Path(config_dict[key]).exists():
            errors.append(f"Path '{config_dict[key]}' for {key} does not exist")

    return errors
```

### Environment Check
```python
import sys
import importlib.metadata

REQUIRED_PACKAGES = [
    "anthropic", "google-genai", "openai", "scipy",
    "statsmodels", "pandas", "matplotlib", "pytest",
]

def check_environment() -> list[tuple[str, bool, str]]:
    """Check environment prerequisites. Returns list of (check_name, passed, detail)."""
    results = []

    # Python version
    py_ok = sys.version_info >= (3, 11)
    results.append((
        "Python >= 3.11",
        py_ok,
        f"Found {sys.version_info.major}.{sys.version_info.minor}",
    ))

    # Required packages
    for pkg in REQUIRED_PACKAGES:
        try:
            ver = importlib.metadata.version(pkg)
            results.append((f"Package: {pkg}", True, f"v{ver}"))
        except importlib.metadata.PackageNotFoundError:
            results.append((f"Package: {pkg}", False, "Not installed"))

    return results
```

### API Key Validation Test Call
```python
def validate_api_key(provider: str, env_var: str) -> tuple[bool, str]:
    """Make a minimal API call to verify the key works.

    Returns (success, message).
    """
    import os
    key = os.environ.get(env_var)
    if not key:
        return False, f"Environment variable {env_var} is not set"

    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model="claude-haiku-4-5-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "google":
            from google import genai
            client = genai.Client(api_key=key)
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Hi",
                config={"max_output_tokens": 1},
            )
        elif provider == "openai":
            import openai
            client = openai.OpenAI(api_key=key)
            client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        elif provider == "openrouter":
            import openai
            from src.config import OPENROUTER_BASE_URL
            client = openai.OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)
            client.chat.completions.create(
                model="nvidia/nemotron-3-nano-30b-a3b:free",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        return True, "API key validated successfully"
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "403" in err_str or "invalid" in err_str or "auth" in err_str:
            return False, f"Authentication failed: {e}"
        return False, f"API call failed (key may be valid, but got error): {e}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual config editing only | Interactive wizard + manual fallback | This phase | Reduces onboarding friction |
| Direct ExperimentConfig() construction | Config file + ExperimentConfig merge | This phase | Persistent user preferences |
| Individual script entry points | Unified CLI with subcommands | This phase | Extensible command surface for Phase 14+ |

**Note:** argparse subparsers is the standard Python approach. click/typer are popular alternatives but add dependencies. For this project with existing argparse patterns, argparse is the right choice.

## Open Questions

1. **Print vs logging for wizard prompts**
   - What we know: CLAUDE.md says no print() for logging. Interactive prompts are not logging.
   - What's unclear: Whether the project owner considers wizard output as "logging."
   - Recommendation: Use `print()` for interactive wizard I/O (prompts, choices, confirmations). Use `logging` for non-interactive status messages and errors. Document this distinction in a code comment.

2. **Config file name**
   - What we know: Must avoid collision with `.planning/config.json`. Must be intuitive.
   - Options: `experiment_config.json`, `slicer_config.json`, `lt_config.json`
   - Recommendation: `experiment_config.json` -- matches `ExperimentConfig` class name, clearly describes purpose, no collision risk.

3. **Where to add the config-missing guard**
   - What we know: Only `run_experiment.py` is mentioned, but `pilot.py` and other scripts also need config.
   - Recommendation: Add the guard to `run_experiment.py` and `pilot.py` initially. Other scripts (`analyze_results.py`, `grade_results.py`) work on existing data and don't need API config.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_cli.py tests/test_setup_wizard.py tests/test_config_manager.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P13-01 | CLI entry point with subcommand routing | unit | `pytest tests/test_cli.py -x` | No -- Wave 0 |
| P13-02 | Setup wizard interactive flow | unit | `pytest tests/test_setup_wizard.py -x` | No -- Wave 0 |
| P13-03 | Config file save/load with sparse override | unit | `pytest tests/test_config_manager.py -x` | No -- Wave 0 |
| P13-04 | Config validation (models, paths, ranges) | unit | `pytest tests/test_config_manager.py -x` | No -- Wave 0 |
| P13-05 | Environment check (Python, packages, keys) | unit | `pytest tests/test_setup_wizard.py -x` | No -- Wave 0 |
| P13-06 | API key validation test call | unit (mocked) | `pytest tests/test_setup_wizard.py -x` | No -- Wave 0 |
| P13-07 | Config-missing guard in run_experiment | unit | `pytest tests/test_run_experiment.py -x` | Partial -- existing file |
| P13-08 | ExperimentConfig merge with file overrides | unit | `pytest tests/test_config_manager.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_cli.py tests/test_setup_wizard.py tests/test_config_manager.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli.py` -- CLI entry point, subparser routing, help output
- [ ] `tests/test_setup_wizard.py` -- wizard flow with mocked input, env checks, API validation
- [ ] `tests/test_config_manager.py` -- config save/load, sparse override merge, validation rules
- [ ] Mock `input()` strategy: use `unittest.mock.patch("builtins.input")` with side_effect lists

## Sources

### Primary (HIGH confidence)
- `src/config.py` -- ExperimentConfig frozen dataclass, MODELS, PRICE_TABLE, PREPROC_MODEL_MAP (direct code inspection)
- `src/run_experiment.py` -- `_build_parser()` argparse pattern, `run_engine()` config usage (direct code inspection)
- `src/api_client.py` -- API call patterns, `_validate_api_keys()` (direct code inspection)
- `src/pilot.py` -- Additional argparse CLI pattern (direct code inspection)
- `tests/conftest.py` -- Existing test fixtures and patterns (direct code inspection)
- `pyproject.toml` -- Project dependencies and pytest config (direct code inspection)

### Secondary (MEDIUM confidence)
- Python argparse documentation -- subparsers, set_defaults for command routing
- Python json module -- standard serialization behavior (tuples become lists)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no external dependencies needed, patterns established in codebase
- Architecture: HIGH -- clear mapping from CONTEXT.md decisions to implementation structure
- Pitfalls: HIGH -- based on direct code inspection of ExperimentConfig, JSON serialization behavior, and existing patterns

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain -- Python stdlib doesn't change)
