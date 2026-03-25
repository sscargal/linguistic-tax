# Phase 15: Pre-Execution Experiment Summary and Confirmation Gate - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Before running experiments, display a comprehensive pre-execution summary (cost projection, experiment count, estimated runtime, models, noise conditions, interventions) with a confirmation gate. Researcher can accept, reject, or modify filter parameters before execution proceeds. Includes `--yes` flag for scripted/CI runs and `--budget` threshold for automated cost gates. Also adds `propt run` and `propt pilot` CLI subcommands, execution progress bar, and execution plan saving.

</domain>

<decisions>
## Implementation Decisions

### Summary display
- Full breakdown: per-model, per-intervention, per-noise-type counts + cost estimates
- Structured sections format: Models, Interventions, Noise Conditions, Cost, Runtime — with aligned columns
- Numbers only — no ASCII bar charts or visual embellishments
- Show completed vs remaining when resuming a partial run (query DB for existing results, show "X of Y done, Z remaining" with adjusted cost for remaining only)

### Accept/reject/modify flow
- Three-way prompt after summary: [Y]es to run, [N]o to abort, [M]odify to adjust parameters
- Modify allows changing filter flags only: --model, --limit, --intervention — then re-displays summary
- Full config changes go through `propt set-config` (not inline modification)
- `--yes` flag: still prints the full summary (useful in CI logs) but auto-accepts without prompting
- `--budget` flag with configurable threshold: if estimated cost exceeds threshold, print warning and exit non-zero. Useful for CI budget gates.

### Cost & runtime estimation
- Cost estimated statically from PRICE_TABLE using average token counts per benchmark (HumanEval ~500 in/200 out, GSM8K ~300 in/100 out)
- No pilot data required for cost estimation — always available
- Pre-processor costs shown as separate line item (sanitize/compress calls to cheap models via PREPROC_MODEL_MAP pricing)
- Total cost = target model cost + pre-processor cost
- Runtime estimated from RATE_LIMIT_DELAYS x number of calls per model — gives wall-clock lower bound

### Integration
- Both `propt run` subcommand AND confirmation gate in run_experiment.py
- `propt run` is the recommended entry point with full flag parity (--model, --limit, --retry-failed, --db, --yes, --budget)
- run_experiment.py also gets the confirmation gate for direct invocation
- `--dry-run` becomes summary-only mode (shows confirmation summary, always exits without running)
- `propt pilot` wraps pilot.py with the same confirmation gate and summary display

### Execution progress bar
- After accepting, show a live progress bar during execution (tqdm-style)
- Display: completion %, items done/total, ETA, cost-so-far
- Part of Phase 15 — natural extension of the confirmation gate

### Execution plan saving
- Write the pre-execution summary to `results/execution_plan.json` before running
- Records exactly what was planned: item counts, cost projection, models, filters, timestamp
- Supports reproducibility — can compare plan vs actual after execution

### Claude's Discretion
- Progress bar library choice (tqdm vs custom ASCII)
- Exact structured section formatting and column widths
- Average token count assumptions per benchmark for cost estimation
- Execution plan JSON schema
- How modify mode re-prompts for flag changes

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Execution engine
- `src/run_experiment.py` — Current execution engine with `run_engine()`, `_show_dry_run()`, `_build_parser()`, `--dry-run` flag. Phase 15 enhances this with confirmation gate.
- `src/pilot.py` — Pilot validation with `run_pilot()`, `compute_cost_projection()`, `_build_parser()`. Phase 15 wraps this as `propt pilot`.

### CLI architecture
- `src/cli.py` — `build_cli()` with argparse subparsers, `main()` routing. Add `run` and `pilot` subcommands here.
- `src/config_commands.py` — Pattern for CLI subcommand handlers (Phase 14).

### Configuration and pricing
- `src/config.py` — `ExperimentConfig`, `PRICE_TABLE`, `MODELS`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`, `compute_cost()`
- `src/config_manager.py` — `load_config()`, `find_config_path()` for loading current settings

### Database
- `src/db.py` — `query_runs()` for checking existing results (resume detection)

### Prior phase context
- `.planning/phases/04-pilot-validation/04-CONTEXT.md` — Pilot cost projection decisions, budget gate pattern ($200 default)
- `.planning/phases/14-cli-config-subcommands-for-viewing-and-modifying-settings/14-CONTEXT.md` — CLI naming (`propt`), print() for output, deferred `propt run` idea

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_show_dry_run()` in run_experiment.py: basic model/intervention breakdown — replace/enhance with full summary display
- `compute_cost_projection()` in pilot.py: bootstrap CI logic for pilot cost — reference for cost calculation patterns
- `compute_cost()` in config.py: per-call cost from token counts + PRICE_TABLE — core cost calculation
- `RATE_LIMIT_DELAYS` in config.py: per-model delay between calls — basis for runtime estimation
- `PREPROC_MODEL_MAP` in config.py: maps target model to pre-processor model — needed for pre-processor cost line item
- `build_cli()` in cli.py: argparse subparsers pattern — add `run` and `pilot` subcommands

### Established Patterns
- argparse subparsers in cli.py with `set_defaults(func=handler)` routing
- `print()` for user-facing CLI output (Phase 14 decision)
- `_check_config_exists()` guard at entry points
- JSON output files in `results/` directory

### Integration Points
- `cli.py build_cli()` — add `run` and `pilot` subparser entries
- `run_experiment.py run_engine()` — insert confirmation gate before execution loop
- `run_experiment.py _show_dry_run()` — replace with enhanced summary display
- `pilot.py run_pilot()` — insert confirmation gate before pilot execution
- `results/execution_plan.json` — new file, pre-execution summary saved here

</code_context>

<specifics>
## Specific Ideas

- The deferred `propt run` and `propt pilot` ideas from Phase 14 context are now in scope
- Budget gate mirrors the pilot's `--budget` flag pattern but applies to any execution
- Progress bar should show cost-so-far alongside completion % — researcher cares about spend during long runs
- Execution plan JSON enables post-hoc comparison: "did we actually run what we planned?"

</specifics>

<deferred>
## Deferred Ideas

- **Email/Slack notification on completion** — For long runs, optionally notify when done. Too niche for now.
- **Config profiles** — Named profiles (e.g., "pilot", "full-run", "cheap") for quick parameter switching. From Phase 13 deferred list.
- **propt doctor** — Standalone environment health check. From Phase 14 deferred list.

</deferred>

---

*Phase: 15-pre-execution-experiment-summary-and-confirmation-gate*
*Context gathered: 2026-03-25*
