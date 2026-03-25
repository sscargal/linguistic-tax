# Phase 15: Pre-Execution Experiment Summary and Confirmation Gate - Research

**Researched:** 2026-03-25
**Domain:** CLI confirmation gate, cost estimation, progress reporting, argparse subcommands
**Confidence:** HIGH

## Summary

Phase 15 adds a pre-execution summary and confirmation gate to the experiment pipeline. The core work involves: (1) building a cost/runtime estimation engine from static token averages and PRICE_TABLE, (2) a three-way interactive prompt (Yes/No/Modify) with --yes and --budget bypass flags, (3) registering `propt run` and `propt pilot` as CLI subcommands with full flag parity, (4) a tqdm-based progress bar during execution, and (5) saving execution plans to JSON.

All building blocks exist in the codebase already. `_show_dry_run()` in run_experiment.py provides a skeleton summary. `compute_cost()` and `PRICE_TABLE` in config.py handle per-call pricing. `RATE_LIMIT_DELAYS` provides runtime estimation inputs. The CLI subparsers pattern in cli.py (with `set_defaults(func=handler)`) is well-established from Phase 14.

**Primary recommendation:** Build a standalone `execution_summary` module containing all summary/cost/runtime logic, then wire it into both run_experiment.py and pilot.py. Use tqdm for progress bars. Keep the interactive prompt simple with `input()` and a parameter-injectable input_fn for testability.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full breakdown: per-model, per-intervention, per-noise-type counts + cost estimates
- Structured sections format: Models, Interventions, Noise Conditions, Cost, Runtime -- with aligned columns
- Numbers only -- no ASCII bar charts or visual embellishments
- Show completed vs remaining when resuming a partial run (query DB for existing results, show "X of Y done, Z remaining" with adjusted cost for remaining only)
- Three-way prompt after summary: [Y]es to run, [N]o to abort, [M]odify to adjust parameters
- Modify allows changing filter flags only: --model, --limit, --intervention -- then re-displays summary
- Full config changes go through `propt set-config` (not inline modification)
- `--yes` flag: still prints the full summary (useful in CI logs) but auto-accepts without prompting
- `--budget` flag with configurable threshold: if estimated cost exceeds threshold, print warning and exit non-zero
- Cost estimated statically from PRICE_TABLE using average token counts per benchmark
- No pilot data required for cost estimation -- always available
- Pre-processor costs shown as separate line item
- Total cost = target model cost + pre-processor cost
- Runtime estimated from RATE_LIMIT_DELAYS x number of calls per model
- Both `propt run` subcommand AND confirmation gate in run_experiment.py
- `propt run` is the recommended entry point with full flag parity (--model, --limit, --retry-failed, --db, --yes, --budget)
- run_experiment.py also gets the confirmation gate for direct invocation
- `--dry-run` becomes summary-only mode (shows confirmation summary, always exits without running)
- `propt pilot` wraps pilot.py with the same confirmation gate and summary display
- After accepting, show a live progress bar during execution (tqdm-style)
- Display: completion %, items done/total, ETA, cost-so-far
- Write the pre-execution summary to `results/execution_plan.json` before running
- Records exactly what was planned: item counts, cost projection, models, filters, timestamp

### Claude's Discretion
- Progress bar library choice (tqdm vs custom ASCII)
- Exact structured section formatting and column widths
- Average token count assumptions per benchmark for cost estimation
- Execution plan JSON schema
- How modify mode re-prompts for flag changes

### Deferred Ideas (OUT OF SCOPE)
- Email/Slack notification on completion
- Config profiles (named presets)
- propt doctor (environment health check)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tqdm | 4.67.3 | Progress bar during execution | De facto Python progress bar; already installed; minimal API |
| tabulate | 0.9.0+ | Aligned column formatting for summary display | Already a project dependency; used in config_commands.py |
| argparse | stdlib | CLI subcommand registration | Already the project's CLI framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Execution plan serialization | Writing execution_plan.json |
| sqlite3 | stdlib | Query completed runs for resume detection | Checking existing results |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tqdm | Custom ASCII bar | tqdm is battle-tested, handles terminal width, ETA calculation; custom adds maintenance burden |
| tqdm | rich progress | rich is heavy; tqdm is simpler and already installed |

**Recommendation:** Use tqdm. It is already installed (4.67.3), needs to be added to pyproject.toml dependencies, and provides built-in ETA, rate, and custom postfix (cost-so-far) support.

**Installation:**
```bash
# tqdm already installed but needs adding to pyproject.toml
# Add: "tqdm>=4.66.0" to dependencies list
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  execution_summary.py   # NEW: cost estimation, summary display, confirmation gate, plan saving
  run_experiment.py      # MODIFIED: import confirmation gate, add progress bar, new flags
  pilot.py               # MODIFIED: import confirmation gate, add progress bar
  cli.py                 # MODIFIED: add run + pilot subcommands
  config.py              # READ ONLY: PRICE_TABLE, RATE_LIMIT_DELAYS, compute_cost()
```

### Pattern 1: Standalone Summary Module
**What:** A new `src/execution_summary.py` module that encapsulates all pre-execution logic: cost estimation, runtime estimation, summary formatting, confirmation prompting, resume detection, and plan saving.
**When to use:** Any time experiment execution needs a pre-flight check.
**Why:** Avoids duplicating summary logic between run_experiment.py and pilot.py. Both call the same functions.

```python
# src/execution_summary.py

from typing import Any, Callable

AVG_TOKENS: dict[str, dict[str, int]] = {
    "humaneval": {"input": 500, "output": 200},
    "mbpp": {"input": 500, "output": 200},
    "gsm8k": {"input": 300, "output": 100},
}

def estimate_cost(items: list[dict[str, Any]]) -> dict[str, float]:
    """Estimate total cost from pending items using static token averages."""
    ...

def estimate_runtime(items: list[dict[str, Any]]) -> float:
    """Estimate wall-clock seconds from RATE_LIMIT_DELAYS x call counts per model."""
    ...

def format_summary(
    items: list[dict[str, Any]],
    completed_count: int,
    total_count: int,
) -> str:
    """Build the structured summary string with aligned columns."""
    ...

def confirm_execution(
    summary: str,
    yes: bool = False,
    budget: float | None = None,
    estimated_cost: float = 0.0,
    input_fn: Callable[[str], str] = input,
) -> str:
    """Display summary and prompt for Y/N/M. Returns 'yes', 'no', or 'modify'."""
    ...

def save_execution_plan(
    items: list[dict[str, Any]],
    cost_estimate: dict[str, float],
    runtime_estimate: float,
    output_path: str = "results/execution_plan.json",
) -> None:
    """Write pre-execution plan to JSON for reproducibility."""
    ...
```

### Pattern 2: CLI Subcommand Registration (Established)
**What:** Adding `run` and `pilot` subparsers in `build_cli()` following the existing pattern.
**When to use:** Standard pattern for all subcommands.

```python
# In cli.py build_cli()
run_parser = subparsers.add_parser("run", help="Run experiments with confirmation gate")
run_parser.add_argument("--model", choices=["claude", "gemini", "gpt", "openrouter", "all"], default="all")
run_parser.add_argument("--limit", type=int, default=None)
run_parser.add_argument("--retry-failed", action="store_true")
run_parser.add_argument("--db", type=str, default=None)
run_parser.add_argument("--yes", action="store_true", help="Auto-accept without prompting")
run_parser.add_argument("--budget", type=float, default=None, help="Exit non-zero if cost exceeds threshold")
run_parser.add_argument("--dry-run", action="store_true", help="Show summary only, do not execute")
run_parser.add_argument("--intervention", type=str, default=None, help="Filter to specific intervention")
run_parser.set_defaults(func=handle_run)
```

### Pattern 3: Injectable input_fn for Testability (Established)
**What:** Pass `input_fn: Callable = input` parameter for interactive prompts.
**When to use:** Any function that calls `input()`.
**Why:** Phase 13 established this pattern for the setup wizard. Avoids monkeypatching builtins.

### Pattern 4: tqdm with Custom Postfix for Cost Tracking
**What:** Use tqdm's `set_postfix()` to display running cost during execution.

```python
from tqdm import tqdm

with tqdm(total=len(pending), desc="Running experiments", unit="item") as pbar:
    for i, item in enumerate(pending):
        _process_item(item, conn, prompts_by_id, config, i, len(pending))
        cost_so_far += item_cost  # track from DB or return value
        pbar.set_postfix(cost=f"${cost_so_far:.2f}")
        pbar.update(1)
```

### Anti-Patterns to Avoid
- **Duplicating summary logic in run_experiment.py and pilot.py:** Extract to execution_summary.py and import.
- **Using logger.info() for user-facing summary output:** Phase 14 established `print()` for CLI output. The summary is user-facing, so use print(). Keep logger for debug/internal messages only.
- **Hardcoding token averages in multiple places:** Define AVG_TOKENS once in execution_summary.py.
- **Blocking on input() in --yes mode:** Still print summary, skip the prompt entirely.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar with ETA | Custom ASCII progress + ETA calc | tqdm | Handles terminal width, rate smoothing, thread safety |
| Aligned column output | Manual string formatting | tabulate | Already a dependency; handles column alignment automatically |
| Cost calculation | New pricing logic | config.compute_cost() | Already correct and tested |
| Resume detection | Custom DB queries | db.query_runs(status="completed") | Already implements the query pattern |

**Key insight:** Nearly all infrastructure exists. This phase is primarily about composition and UI, not new algorithms.

## Common Pitfalls

### Pitfall 1: Forgetting Pre-Processor Costs
**What goes wrong:** Cost estimate only includes target model calls, under-reporting by 10-30% for sanitize/compress interventions.
**Why it happens:** Easy to compute `compute_cost(model, avg_in, avg_out) * count` and forget that pre_proc_sanitize and pre_proc_sanitize_compress also make a separate API call to the cheap model.
**How to avoid:** For each item with intervention in ("pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only"), add a second cost line using `PREPROC_MODEL_MAP[model]` and appropriate token estimates.
**Warning signs:** Cost estimate seems too low for runs with many pre-processor interventions.

### Pitfall 2: Not Handling Empty Pending List
**What goes wrong:** Division by zero or confusing output when all items are already completed.
**Why it happens:** Resume scenario where 100% of items are done.
**How to avoid:** Check `len(pending) == 0` early, display "All items complete" message, and return cleanly.

### Pitfall 3: Modify Loop Not Re-Computing Summary
**What goes wrong:** User selects [M]odify, changes filters, but sees stale cost/count numbers.
**Why it happens:** Summary string is computed once and not refreshed after filter change.
**How to avoid:** The modify flow must re-filter the item list AND re-compute the summary before re-displaying.

### Pitfall 4: Budget Gate with --yes Still Prompting
**What goes wrong:** `--yes --budget 50` should auto-fail if cost > $50, not prompt.
**Why it happens:** Budget check and --yes flag handled in wrong order.
**How to avoid:** Check budget BEFORE the interactive prompt. If budget exceeded, print warning and `sys.exit(1)` regardless of --yes.

### Pitfall 5: tqdm Output Conflicting with print()
**What goes wrong:** Summary prints and tqdm bar interleave, garbling terminal output.
**Why it happens:** tqdm writes to stderr by default; print() goes to stdout.
**How to avoid:** Print summary to stdout, then start tqdm on stderr (default). This is actually fine since terminals interleave them correctly. Alternatively, flush stdout before starting tqdm.

### Pitfall 6: Intervention Filter Not Matching Matrix Values
**What goes wrong:** User passes `--intervention sanitize` but matrix uses `pre_proc_sanitize`.
**Why it happens:** Mismatch between user-friendly names and internal matrix strings.
**How to avoid:** Either use exact matrix strings in the CLI or provide a mapping. Recommend using exact strings with `choices=INTERVENTIONS` from config.py.

## Code Examples

### Cost Estimation from Static Token Averages
```python
from collections import Counter
from src.config import compute_cost, PREPROC_MODEL_MAP, RATE_LIMIT_DELAYS

AVG_TOKENS: dict[str, dict[str, int]] = {
    "humaneval": {"input": 500, "output": 200},
    "mbpp": {"input": 500, "output": 200},
    "gsm8k": {"input": 300, "output": 100},
}

PREPROC_INTERVENTIONS = {"pre_proc_sanitize", "pre_proc_sanitize_compress", "compress_only"}

def estimate_cost(items: list[dict]) -> dict[str, float]:
    """Return dict with 'target_cost', 'preproc_cost', 'total_cost'."""
    target_cost = 0.0
    preproc_cost = 0.0
    for item in items:
        benchmark = _get_benchmark(item["prompt_id"])
        tokens = AVG_TOKENS.get(benchmark, {"input": 500, "output": 200})
        target_cost += compute_cost(item["model"], tokens["input"], tokens["output"])
        if item["intervention"] in PREPROC_INTERVENTIONS:
            preproc_model = PREPROC_MODEL_MAP.get(item["model"], item["model"])
            # Pre-proc input ~ same as target input; output ~ 80% of input (compressed)
            preproc_cost += compute_cost(preproc_model, tokens["input"], int(tokens["input"] * 0.8))
    return {
        "target_cost": target_cost,
        "preproc_cost": preproc_cost,
        "total_cost": target_cost + preproc_cost,
    }
```

### Runtime Estimation
```python
def estimate_runtime_seconds(items: list[dict]) -> float:
    """Estimate wall-clock time from rate limit delays."""
    model_counts = Counter(item["model"] for item in items)
    total_seconds = 0.0
    for model, count in model_counts.items():
        delay = RATE_LIMIT_DELAYS.get(model, 0.5)
        total_seconds += count * delay
    return total_seconds
```

### Confirmation Gate with input_fn Injection
```python
def confirm_execution(
    summary: str,
    yes: bool = False,
    budget: float | None = None,
    estimated_cost: float = 0.0,
    input_fn: Callable[[str], str] = input,
) -> str:
    print(summary)

    # Budget gate (checked before --yes)
    if budget is not None and estimated_cost > budget:
        print(f"WARNING: Estimated cost ${estimated_cost:.2f} exceeds budget ${budget:.2f}")
        sys.exit(1)

    if yes:
        return "yes"

    while True:
        choice = input_fn("[Y]es to run, [N]o to abort, [M]odify filters: ").strip().lower()
        if choice in ("y", "yes"):
            return "yes"
        elif choice in ("n", "no"):
            return "no"
        elif choice in ("m", "modify"):
            return "modify"
        print("Invalid choice. Enter Y, N, or M.")
```

### Progress Bar with Cost Tracking
```python
from tqdm import tqdm

def run_with_progress(pending, conn, prompts_by_id, config):
    cost_so_far = 0.0
    with tqdm(total=len(pending), desc="Experiments", unit="item") as pbar:
        for i, item in enumerate(pending):
            _process_item(item, conn, prompts_by_id, config, i, len(pending))
            # Retrieve cost from last inserted row
            row = conn.execute(
                "SELECT total_cost_usd FROM experiment_runs WHERE run_id = ?",
                (make_run_id(item),)
            ).fetchone()
            if row and row[0]:
                cost_so_far += row[0]
            pbar.set_postfix(cost=f"${cost_so_far:.2f}")
            pbar.update(1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_show_dry_run()` with logger.info | Full summary with print(), cost, runtime | Phase 15 | User-facing output, not log messages |
| No confirmation before execution | Three-way gate (Y/N/M) | Phase 15 | Prevents accidental expensive runs |
| No progress indicator | tqdm with cost tracking | Phase 15 | Researcher sees real-time execution state |

## Open Questions

1. **Token averages per benchmark**
   - What we know: CONTEXT.md suggests ~500 in/200 out for HumanEval, ~300 in/100 out for GSM8K
   - What's unclear: MBPP averages not specified; likely similar to HumanEval
   - Recommendation: Use 500/200 for HumanEval and MBPP, 300/100 for GSM8K. These are estimates for cost projection, not exact values.

2. **Pre-processor token assumptions**
   - What we know: Pre-proc input tokens = similar to target input. Output tokens = compressed result.
   - What's unclear: Exact ratio of input-to-output for pre-processor calls
   - Recommendation: Assume pre-proc output tokens ~ 80% of input tokens (sanitize) or ~60% (sanitize+compress). These are rough estimates.

3. **_process_item return value for cost tracking**
   - What we know: Currently _process_item returns None; cost is written to DB
   - What's unclear: Whether to modify _process_item to return cost or query DB after each item
   - Recommendation: Query DB after each item (simple, no signature change) or have _process_item return cost (cleaner). Either works; querying DB is lower-risk.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_execution_summary.py tests/test_cli.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P15-01 | Cost estimation from static token averages | unit | `pytest tests/test_execution_summary.py::TestCostEstimation -x` | No - Wave 0 |
| P15-02 | Runtime estimation from rate limits | unit | `pytest tests/test_execution_summary.py::TestRuntimeEstimation -x` | No - Wave 0 |
| P15-03 | Summary display formatting | unit | `pytest tests/test_execution_summary.py::TestSummaryFormat -x` | No - Wave 0 |
| P15-04 | Confirmation gate (Y/N/M with --yes/--budget) | unit | `pytest tests/test_execution_summary.py::TestConfirmation -x` | No - Wave 0 |
| P15-05 | Resume detection (completed vs remaining) | unit | `pytest tests/test_execution_summary.py::TestResumeDetection -x` | No - Wave 0 |
| P15-06 | Execution plan JSON saving | unit | `pytest tests/test_execution_summary.py::TestExecutionPlan -x` | No - Wave 0 |
| P15-07 | `propt run` subcommand registration | unit | `pytest tests/test_cli.py::TestRunSubcommand -x` | No - Wave 0 |
| P15-08 | `propt pilot` subcommand registration | unit | `pytest tests/test_cli.py::TestPilotSubcommand -x` | No - Wave 0 |
| P15-09 | --budget exit code on threshold exceeded | unit | `pytest tests/test_execution_summary.py::TestBudgetGate -x` | No - Wave 0 |
| P15-10 | tqdm progress bar integration | integration | Manual verification -- tqdm display is terminal-dependent | N/A |

### Sampling Rate
- **Per task commit:** `pytest tests/test_execution_summary.py tests/test_cli.py -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_execution_summary.py` -- covers P15-01 through P15-09
- [ ] Add tqdm to pyproject.toml dependencies
- [ ] Extend `tests/test_cli.py` with run/pilot subcommand tests

## Sources

### Primary (HIGH confidence)
- `src/config.py` -- PRICE_TABLE, RATE_LIMIT_DELAYS, compute_cost(), PREPROC_MODEL_MAP (read directly)
- `src/run_experiment.py` -- _show_dry_run(), run_engine(), _build_parser() (read directly)
- `src/cli.py` -- build_cli() subparser pattern, main() routing (read directly)
- `src/pilot.py` -- run_pilot(), compute_cost_projection() signatures (read directly)
- `src/config_commands.py` -- handler pattern with print() output (read directly)
- `15-CONTEXT.md` -- all locked decisions and canonical references

### Secondary (MEDIUM confidence)
- tqdm 4.67.3 -- installed on system, API well-known from training data (set_postfix, context manager)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use or installed; only tqdm needs pyproject.toml addition
- Architecture: HIGH - extends well-established CLI and execution patterns from Phases 13-14
- Pitfalls: HIGH - identified from reading actual code; cost estimation edge cases are concrete

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain, no external API changes expected)
