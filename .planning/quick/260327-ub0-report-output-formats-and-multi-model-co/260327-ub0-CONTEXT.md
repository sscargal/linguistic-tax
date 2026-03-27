# Quick Task 260327-ub0: Report output formats and multi-model comparison layout - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Task Boundary

Add multi-model comparison tables and export format flags (--json, --csv, --markdown) to `propt report`. Keep existing sections, add pivot comparison at top.

</domain>

<decisions>
## Implementation Decisions

### Multi-model comparison layout
- Add pivot summary table at top: intervention rows x model columns showing pass rate
- Also add noise_type x model pivot table
- Keep existing per-model detail sections below for drill-down
- Both pivot summary + per-model detail = most complete view

### Export formats
- Add `--json` flag: outputs entire report as structured JSON (all sections as nested dict)
- Add `--csv` flag: outputs key tables as CSV (one per section, separated by headers, or written to separate files)
- Add `--markdown` flag: outputs report as GitHub-flavored markdown tables (copy-pasteable)
- Default remains plain-text terminal output (no flag)

### Report sections
- Keep all current sections: models, fallback, timing, interventions, noise, benchmarks, costs
- Add multi-model pivot comparison tables at the top (before per-model detail)
- No restructuring around hypotheses

### Claude's Discretion
- CSV output strategy (single file with section headers vs multiple files)
- JSON structure (flat vs nested)
- How to handle single-model case (skip pivot tables, show existing layout)

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<canonical_refs>
## Canonical References

- `src/execution_summary.py` lines 495-818 -- Current `format_post_run_report()` implementation
- `src/cli.py` lines 206-220 -- Current `report` subcommand argument parsing
- `.planning/todos/pending/2026-03-27-report-output-formats-and-multi-model-layout.md` -- Original TODO

</canonical_refs>
