---
created: 2026-03-27T18:00:00.000Z
title: "Report output formats and multi-model comparison layout"
area: general
files:
  - src/execution_summary.py
  - src/cli.py
---

## Problem

1. **Multi-model layout**: With 2+ target models, the current report shows them stacked vertically. For comparison, a side-by-side tabular layout would be more useful — one column per model showing pass rates per noise/intervention.

2. **Output formats**: Terminal-only output limits usability. Researchers need to export data for papers, spreadsheets, and further analysis.

## Solution

### Multi-model comparison table
When multiple target models exist, add a cross-tabulation view:

```
Noise x Model Pass Rates:
                  gpt-5.1   gpt-5-nano   delta
clean              93.3%      78.2%      -15.1pp
type_a_5pct        93.4%      74.1%      -19.3pp
type_a_10pct       88.4%      65.3%      -23.1pp
type_a_20pct       88.0%      58.7%      -29.3pp
```

### Output format options
- `propt report` — default terminal display (current)
- `propt report --csv` — CSV output for spreadsheet import
- `propt report --json` — JSON for programmatic analysis
- `propt report --markdown` — markdown table for docs/papers
- `propt report --latex` — LaTeX tabular for ArXiv paper

### Implementation approach
- Add `--format` flag: `terminal` (default), `csv`, `json`, `markdown`, `latex`
- Refactor `format_post_run_report` to return structured data, then format at the end
- Multi-model comparison only shown when 2+ target models exist
