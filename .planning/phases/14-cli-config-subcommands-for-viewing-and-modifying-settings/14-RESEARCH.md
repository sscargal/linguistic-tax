# Phase 14: CLI Config Subcommands for Viewing and Modifying Settings - Research

**Researched:** 2026-03-25
**Domain:** Python CLI subcommands (argparse), config display/editing, shell tab completion
**Confidence:** HIGH

## Summary

Phase 14 extends the existing argparse-based CLI (`src/cli.py`) with six new subcommands: `show-config`, `set-config`, `reset-config`, `validate`, `diff`, and `list-models`. It also renames the CLI entry point to `propt` via pyproject.toml console_scripts. The existing codebase already has all the config infrastructure needed -- `config_manager.py` provides load/save/validate/get_full_config_dict, and `ExperimentConfig` is a frozen dataclass with 13 fields that can be introspected via `dataclasses.fields()`.

The `tabulate` library is already installed (0.10.0) and listed in pyproject.toml dependencies, making it the clear choice for table formatting. For tab completion, `argcomplete` is installed (3.6.3) and is the de facto standard for argparse-based completers. Both are lightweight and well-maintained.

**Primary recommendation:** Build all six subcommands as handler functions in a new `src/config_commands.py` module, register them in `cli.py`'s `build_cli()`, and use `tabulate` for table output and `argcomplete` for shell completions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Top-level command name: `propt` (registered as pyproject.toml console_scripts entry)
- Flat top-level subcommands (not nested under `config`): `setup`, `show-config`, `set-config`, `reset-config`, `validate`, `diff`, `list-models`
- Existing `setup` subcommand remains unchanged
- Existing scripts (`run_experiment.py`, `pilot.py`, etc.) continue to work as-is
- show-config: terminal table with Property/Value/Default columns, `*` for modified, `--json`, `--changed`, `--verbose`, single-property query
- set-config: auto-creates config, multiple key-value pairs, auto type coercion from ExperimentConfig defaults, immediate validation, change summary
- reset-config: removes key from sparse config, `--all` flag for full reset
- validate: runs validate_config, exit code 0/non-zero
- diff: shows properties differing from defaults in diff-like format
- list-models: prints PRICE_TABLE entries with pricing
- Tab completion for property names in bash and zsh

### Claude's Discretion
- Table formatting implementation (rich vs tabulate vs manual)
- Tab completion approach (argcomplete, custom, or shtab)
- Exact diff output format
- Property description text for --verbose mode
- Whether list-models groups by provider or shows flat list

### Deferred Ideas (OUT OF SCOPE)
- `propt doctor` -- standalone environment health check
- Config profiles (named parameter sets)
- `propt export --latex` -- LaTeX table export
- `propt run` / `propt pilot` -- wrapping scripts as subcommands
- Config file versioning / schema migration
- `propt cost-estimate` -- pre-execution cost estimation
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | CLI parsing, subcommands | Already used in cli.py; no reason to switch |
| tabulate | 0.10.0 | Terminal table formatting | Already in pyproject.toml deps; lightweight, supports multiple formats |
| argcomplete | 3.6.3 | Shell tab completion for argparse | De facto standard for argparse completion; already installed |
| dataclasses | stdlib | ExperimentConfig introspection | Already the config pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tabulate | rich | rich (14.2.0) is installed but heavyweight; tabulate is already a declared dep and sufficient for simple tables |
| argcomplete | shtab | shtab generates static completions from argparse; argcomplete is dynamic and already installed |
| argparse | click/typer | Would require rewriting existing CLI; not worth it for 6 subcommands |

**Recommendation:** Use `tabulate` for tables (already a dependency, simple API) and `argcomplete` for tab completion (already installed, dynamic completers for property names).

**Installation:**
```bash
pip install argcomplete  # Add to pyproject.toml dependencies
# tabulate already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  cli.py              # build_cli() -- add new subparsers, register propt entry point
  config_commands.py   # NEW: handler functions for all 6 config subcommands
  config_manager.py    # Existing: load/save/validate/get_full_config_dict
  config.py            # Existing: ExperimentConfig, PRICE_TABLE
  setup_wizard.py      # Existing: unchanged
```

### Pattern 1: Subcommand Handler Module
**What:** Each subcommand gets a handler function in `config_commands.py` that receives the parsed `args` namespace. Registration happens in `build_cli()`.
**When to use:** Always -- matches existing `setup` subcommand pattern.
**Example:**
```python
# src/config_commands.py
import json
import logging
from dataclasses import fields
from tabulate import tabulate

from src.config import ExperimentConfig, PRICE_TABLE
from src.config_manager import (
    find_config_path, load_config, save_config, validate_config,
)

logger = logging.getLogger(__name__)

def handle_show_config(args) -> None:
    """Display current configuration."""
    defaults = ExperimentConfig()
    current = load_config()
    # ... build table, format output
```

### Pattern 2: Sparse Config Read-Modify-Write
**What:** For `set-config` and `reset-config`, read the raw JSON (not the merged ExperimentConfig), modify the sparse dict, validate the merged result, then write back.
**When to use:** Every write operation.
**Why:** The config file only stores overrides. Reading the merged config and writing it back would convert all defaults to explicit values, defeating the sparse pattern.
**Example:**
```python
def _load_raw_overrides(config_path=None) -> tuple[dict, Path]:
    """Load the raw JSON overrides (not merged with defaults)."""
    path = find_config_path() if config_path is None else config_path
    if path is None or not path.exists():
        return {}, Path(".") / "experiment_config.json"
    with open(path) as f:
        return json.load(f), path

def handle_set_config(args) -> None:
    raw, path = _load_raw_overrides()
    # Parse key-value pairs from args.pairs
    # Type-coerce based on ExperimentConfig field type
    # Merge into raw, validate merged result, save raw
```

### Pattern 3: Type Coercion from Dataclass Introspection
**What:** Determine the target type for a property by inspecting the default value of the corresponding ExperimentConfig field, then coerce the string input.
**When to use:** `set-config` command.
**Example:**
```python
def _coerce_value(field_name: str, raw_value: str):
    """Coerce a string value to the type of the ExperimentConfig field."""
    defaults = ExperimentConfig()
    default_val = getattr(defaults, field_name)
    if isinstance(default_val, int):
        return int(raw_value)
    elif isinstance(default_val, float):
        return float(raw_value)
    elif isinstance(default_val, tuple):
        # Parse comma-separated values, coerce element types
        parts = raw_value.split(",")
        if all(isinstance(x, float) for x in default_val):
            return tuple(float(p) for p in parts)
        return tuple(parts)
    return raw_value  # str
```

### Pattern 4: pyproject.toml Console Scripts Entry
**What:** Register `propt` as a command-line tool via pyproject.toml.
**When to use:** Once, during setup.
**Example:**
```toml
[project.scripts]
propt = "src.cli:main"
```
After adding this, `pip install -e .` (or reinstall) makes `propt` available system-wide. The existing `python src/cli.py` invocation still works.

### Pattern 5: argcomplete Dynamic Completers
**What:** Register custom completers for property names in set-config/show-config/reset-config.
**When to use:** Tab completion for property names.
**Example:**
```python
import argcomplete

def _property_name_completer(prefix, parsed_args, **kwargs):
    """Complete property names from ExperimentConfig fields."""
    from src.config import ExperimentConfig
    from dataclasses import fields as dc_fields
    names = [f.name for f in dc_fields(ExperimentConfig)]
    return [n for n in names if n.startswith(prefix)]

# In build_cli():
show_parser.add_argument("property", nargs="?").completer = _property_name_completer
argcomplete.autocomplete(parser)  # Must be called before parse_args
```

### Anti-Patterns to Avoid
- **Writing full config on set-config:** Never write the merged (defaults + overrides) config back. Always read/modify/write the sparse overrides only.
- **Using print() directly:** Per CLAUDE.md, use the logging module for diagnostic output. However, for user-facing command output (tables, JSON), `print()` is appropriate since it IS the command output, not logging.
- **Hardcoding property names:** Always introspect ExperimentConfig via `dataclasses.fields()` so new fields auto-propagate.
- **Importing setup_wizard dependencies in config_commands:** Keep config_commands lightweight. It should not import API clients (anthropic, openai, google).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal table formatting | Manual column alignment with string padding | `tabulate` | Handles unicode widths, alignment, multiple output formats |
| Shell tab completion | Custom bash/zsh script generation | `argcomplete` | Handles escaping, prefix matching, integration with argparse |
| Type coercion | Manual if/elif chains per field name | `isinstance()` on default value | Automatically handles new fields without code changes |
| JSON pretty printing | Manual formatting | `json.dumps(indent=2)` | Handles all edge cases |

**Key insight:** The ExperimentConfig dataclass is the single source of truth. All property listing, type detection, and default comparison should derive from `dataclasses.fields(ExperimentConfig)` and `ExperimentConfig()` defaults -- never from hardcoded lists.

## Common Pitfalls

### Pitfall 1: Destroying Sparse Config on Write
**What goes wrong:** `set-config` loads the merged config (defaults + overrides), modifies one field, writes the entire merged dict back. Now ALL fields are explicit overrides and `reset-config` cannot distinguish user changes from defaults.
**Why it happens:** Using `load_config()` (which returns a full ExperimentConfig) instead of reading the raw JSON.
**How to avoid:** Always read the raw JSON file for write operations. Only the sparse overrides dict gets modified and written back.
**Warning signs:** Config file suddenly has all 13 fields after a single `set-config` call.

### Pitfall 2: Frozen Dataclass Prevents Modification
**What goes wrong:** Trying to modify an ExperimentConfig instance directly fails because it is frozen.
**Why it happens:** ExperimentConfig is `@dataclass(frozen=True)`.
**How to avoid:** Work with plain dicts for config manipulation. Use ExperimentConfig only for validation (construct a new instance with the merged dict).
**Warning signs:** `FrozenInstanceError` at runtime.

### Pitfall 3: Tuple Round-Trip Through JSON
**What goes wrong:** JSON has no tuple type. Saving tuples as lists then loading them back produces lists, not tuples.
**Why it happens:** `json.dump` converts tuples to lists.
**How to avoid:** `load_config()` already handles this conversion (lists back to tuples based on default type). For the sparse config file, `save_config()` handles tuple-to-list conversion. The pattern is established and works.
**Warning signs:** Type mismatch when constructing ExperimentConfig from loaded dict.

### Pitfall 4: argcomplete.autocomplete() Placement
**What goes wrong:** Tab completion does not work.
**Why it happens:** `argcomplete.autocomplete(parser)` must be called BEFORE `parser.parse_args()` in `main()`. If called after, it never activates.
**How to avoid:** Place `argcomplete.autocomplete(parser)` immediately after `build_cli()` returns the parser, before any `parse_args()` call.
**Warning signs:** Completion works for subcommand names but not property names.

### Pitfall 5: set-config Positional Argument Parsing
**What goes wrong:** argparse treats `--json` or negative numbers as flags, not values.
**Why it happens:** `set-config temperature -0.5` -- argparse sees `-0.5` as an unknown flag.
**How to avoid:** Use `nargs='*'` for the pairs argument and parse key-value pairs manually. Or use `--` separator convention. For this project, negative temperature is invalid (must be >= 0), so this is less of a concern, but tuple values with negative floats could trigger it.
**Warning signs:** "unrecognized arguments" errors for numeric values.

### Pitfall 6: Console Scripts Entry Point Module Path
**What goes wrong:** `propt` command fails with ImportError.
**Why it happens:** The entry point `src.cli:main` requires the project to be installed (pip install -e .) since `src` is a package, not a top-level module.
**How to avoid:** Ensure pyproject.toml has the correct entry and the user runs `pip install -e .` after changes. Document this in the setup instructions.
**Warning signs:** `ModuleNotFoundError: No module named 'src'` when running `propt`.

## Code Examples

### show-config Table Output
```python
from dataclasses import fields as dc_fields
from tabulate import tabulate

def handle_show_config(args) -> None:
    defaults = ExperimentConfig()
    current = load_config()

    if hasattr(args, 'property') and args.property:
        # Single property query
        val = getattr(current, args.property)
        if args.json:
            print(json.dumps({args.property: val}))
        else:
            print(val)
        return

    rows = []
    for f in dc_fields(ExperimentConfig):
        cur_val = getattr(current, f.name)
        def_val = getattr(defaults, f.name)
        modified = "*" if cur_val != def_val else ""
        rows.append([f"{modified}{f.name}", _format_value(cur_val), _format_value(def_val)])

    if args.changed:
        rows = [r for r in rows if r[0].startswith("*")]

    headers = ["Property", "Value", "Default"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))
```

### set-config with Type Coercion and Validation
```python
def handle_set_config(args) -> None:
    pairs = args.pairs  # List like ["temperature", "0.5", "repetitions", "3"]
    if len(pairs) % 2 != 0:
        print("Error: set-config requires key-value pairs")
        sys.exit(1)

    raw, config_path = _load_raw_overrides()
    defaults = ExperimentConfig()
    valid_names = {f.name for f in dc_fields(ExperimentConfig)}

    changes = {}
    for i in range(0, len(pairs), 2):
        key, value = pairs[i], pairs[i + 1]
        if key not in valid_names:
            print(f"Error: unknown property '{key}'")
            sys.exit(1)
        coerced = _coerce_value(key, value)
        changes[key] = coerced

    # Merge and validate
    merged = {**raw, **changes}
    errors = validate_config(merged)
    if errors:
        for e in errors:
            print(f"Error: {e}")
        sys.exit(1)

    # Show change summary
    for key, new_val in changes.items():
        old_val = raw.get(key, getattr(defaults, key))
        print(f"{key}: {old_val} -> {new_val}")

    save_config(merged, config_path)
```

### reset-config
```python
def handle_reset_config(args) -> None:
    raw, config_path = _load_raw_overrides()

    if args.all:
        if config_path.exists():
            config_path.unlink()
            print("Config reset to defaults")
        return

    for prop in args.properties:
        if prop in raw:
            del raw[prop]
            print(f"{prop}: reset to default")
        else:
            print(f"{prop}: already at default")

    save_config(raw, config_path)
```

### list-models with Pricing
```python
def handle_list_models(args) -> None:
    rows = []
    for model, prices in sorted(PRICE_TABLE.items()):
        inp = prices["input_per_1m"]
        out = prices["output_per_1m"]
        cost_str = "free" if inp == 0 and out == 0 else f"${inp:.2f} / ${out:.2f}"
        rows.append([model, cost_str])

    headers = ["Model", "Input / Output (per 1M tokens)"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))
```

### argcomplete Registration
```python
# In build_cli(), after creating all subparsers:
try:
    import argcomplete
    argcomplete.autocomplete(parser)
except ImportError:
    pass  # argcomplete optional for basic functionality
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python src/cli.py | propt (console_scripts) | This phase | Standard CLI invocation |
| Manual config file editing | propt set-config key value | This phase | Lower friction for researchers |
| Reading source code for models | propt list-models | This phase | Self-service model discovery |

**Deprecated/outdated:**
- Nothing deprecated in this phase. The `python src/cli.py` invocation continues to work alongside `propt`.

## Open Questions

1. **Property descriptions for --verbose mode**
   - What we know: ExperimentConfig fields have no docstring/description metadata
   - What's unclear: Where to define per-field descriptions
   - Recommendation: Define a `FIELD_DESCRIPTIONS: dict[str, str]` constant in `config_commands.py` mapping field names to human-readable descriptions. This is simpler than adding metadata to the frozen dataclass.

2. **argcomplete activation by users**
   - What we know: argcomplete requires a one-time `activate-global-python-argcomplete` or per-script eval in .bashrc
   - What's unclear: How to communicate this to users
   - Recommendation: Have `propt` print a hint on first run if argcomplete is not activated, or provide a `propt completions` helper that outputs the activation command.

3. **Diff output format**
   - What we know: User wants "diff-like format" with old/new side by side
   - What's unclear: Exact format (unified diff, two-column, colored)
   - Recommendation: Simple two-column format: `property: default_value -> current_value` for each changed property. Matches the set-config change summary style.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_cli.py tests/test_config_commands.py -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

Since no formal requirement IDs are assigned for Phase 14, tests map to the subcommands:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| show-config displays table with all properties | unit | `pytest tests/test_config_commands.py::test_show_config_table -x` | No - Wave 0 |
| show-config --json outputs valid JSON | unit | `pytest tests/test_config_commands.py::test_show_config_json -x` | No - Wave 0 |
| show-config --changed filters to overrides only | unit | `pytest tests/test_config_commands.py::test_show_config_changed -x` | No - Wave 0 |
| show-config single property query | unit | `pytest tests/test_config_commands.py::test_show_config_single -x` | No - Wave 0 |
| set-config writes sparse override with type coercion | unit | `pytest tests/test_config_commands.py::test_set_config_coercion -x` | No - Wave 0 |
| set-config validates before saving | unit | `pytest tests/test_config_commands.py::test_set_config_validation -x` | No - Wave 0 |
| set-config auto-creates config file | unit | `pytest tests/test_config_commands.py::test_set_config_auto_create -x` | No - Wave 0 |
| reset-config removes single key | unit | `pytest tests/test_config_commands.py::test_reset_config_single -x` | No - Wave 0 |
| reset-config --all clears all overrides | unit | `pytest tests/test_config_commands.py::test_reset_config_all -x` | No - Wave 0 |
| validate exits 0 for valid config | unit | `pytest tests/test_config_commands.py::test_validate_valid -x` | No - Wave 0 |
| validate exits non-zero for invalid config | unit | `pytest tests/test_config_commands.py::test_validate_invalid -x` | No - Wave 0 |
| diff shows only changed properties | unit | `pytest tests/test_config_commands.py::test_diff_output -x` | No - Wave 0 |
| list-models shows all PRICE_TABLE entries | unit | `pytest tests/test_config_commands.py::test_list_models -x` | No - Wave 0 |
| propt entry point registered in pyproject.toml | unit | `pytest tests/test_cli.py::test_propt_entry_point -x` | No - Wave 0 |
| build_cli has all subcommands | unit | `pytest tests/test_cli.py::test_all_subcommands -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_cli.py tests/test_config_commands.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config_commands.py` -- new test file for all config subcommand handlers
- [ ] Additional tests in `tests/test_cli.py` for new subcommand registration and `propt` entry point
- [ ] `argcomplete` added to pyproject.toml dependencies

## Sources

### Primary (HIGH confidence)
- `src/cli.py` -- current CLI structure, build_cli pattern
- `src/config_manager.py` -- all config I/O functions (load, save, validate, get_full_config_dict)
- `src/config.py` -- ExperimentConfig (13 fields), PRICE_TABLE (8 models)
- `pyproject.toml` -- current dependencies (tabulate 0.10.0 already listed)
- `tests/test_cli.py` -- existing CLI test patterns
- `tests/test_config_manager.py` -- existing config test patterns

### Secondary (MEDIUM confidence)
- tabulate 0.10.0 API -- `tabulate(rows, headers, tablefmt)` pattern, verified installed
- argcomplete 3.6.3 -- dynamic completer registration, verified installed

### Tertiary (LOW confidence)
- None -- all findings verified against installed packages and existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- tabulate already in deps, argcomplete already installed, all APIs verified
- Architecture: HIGH -- extends well-established patterns from Phase 13 (argparse subparsers, config_manager functions)
- Pitfalls: HIGH -- based on direct code inspection of ExperimentConfig (frozen), save_config (sparse), and JSON round-trip behavior

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain, no fast-moving dependencies)
