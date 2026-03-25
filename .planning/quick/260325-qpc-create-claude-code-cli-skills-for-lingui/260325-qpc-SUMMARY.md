# Quick Task 260325-qpc: Create Claude Code CLI Skills

## What was done

Created 7 Claude Code skills for the Linguistic Tax research project, each with SKILL.md, evals, and reference files where needed. Used the skill-creator plugin for full eval loops (with-skill vs without-skill benchmarking).

## Skills created

| # | Skill | Purpose | Eval Result |
|---|-------|---------|-------------|
| 1 | check-results | Inspect experiment progress, data quality, cost tracking | 73% vs 57% baseline, -5.8% tokens |
| 2 | validate-rdd | Verify code implements RDD specification | 100% vs 95% baseline, -17% tokens |
| 3 | run-pilot | Run 20-prompt pilot experiment | 48% fewer tokens vs baseline |
| 4 | analyze | Run statistical analysis pipeline, interpret H1-H5 | 46% fewer tool calls vs baseline |
| 5 | run-experiment | Execute full matrix with filters and budget gates | Structured execution order guidance |
| 6 | generate-figures | Generate 4 publication-quality figure types | 35% fewer tokens vs baseline |
| 7 | write-section | Draft LaTeX paper sections from results | Paper outline reference included |

## Key findings from evals

- Skills consistently reduce token usage (17-48% reduction) by providing structured process guidance
- Skills reduce tool calls by directing agents to the right files instead of requiring codebase exploration
- The validate-rdd skill surfaced real bugs: GLMM noise_type/noise_level conflation, 4-model vs 2-model RDD mismatch
- Without-skill baseline occasionally found things skills missed (e.g., bootstrap resampling unit bug), suggesting skills should not over-constrain exploration

## Files

- `.claude/skills/check-results/` — SKILL.md + references/ + evals/
- `.claude/skills/validate-rdd/` — SKILL.md + evals/
- `.claude/skills/run-pilot/` — SKILL.md + evals/
- `.claude/skills/analyze/` — SKILL.md + evals/
- `.claude/skills/run-experiment/` — SKILL.md + evals/
- `.claude/skills/generate-figures/` — SKILL.md + evals/
- `.claude/skills/write-section/` — SKILL.md + references/ + evals/

## Commits

- `65eda2b` — check-results skill
- `419f94d` — validate-rdd skill
- `edaad8a` — run-pilot skill
- `1c48092` — analyze skill
- `d3da7fc` — run-experiment skill
- `ebb0e47` — generate-figures skill
- `63cee47` — write-section skill
