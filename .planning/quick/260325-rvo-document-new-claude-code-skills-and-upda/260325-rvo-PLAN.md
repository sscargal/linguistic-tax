---
phase: quick
plan: 260325-rvo
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
  - docs/README.md
autonomous: true
requirements: [quick-task]
must_haves:
  truths:
    - "README.md documents all 7 Claude Code skills with descriptions and trigger phrases"
    - "docs/README.md links to the skills section or lists skills"
    - "Users can discover what Claude Code skills are available without browsing .claude/skills/"
  artifacts:
    - path: "README.md"
      provides: "Claude Code Skills section"
      contains: "Claude Code Skills"
    - path: "docs/README.md"
      provides: "Link to skills documentation"
      contains: "Claude Code"
  key_links: []
---

<objective>
Add documentation of the 7 Claude Code skills to README.md and update docs/README.md to reference them.

Purpose: Users who clone this repo and use Claude Code have no way to discover the available skills (check-results, validate-rdd, run-pilot, analyze, run-experiment, generate-figures, write-section) without browsing .claude/skills/ manually. Documenting them in the README makes them discoverable.

Output: Updated README.md with a Claude Code Skills section, updated docs/README.md with a reference.
</objective>

<execution_context>
@/home/steve/linguistic-tax/.claude/get-shit-done/workflows/execute-plan.md
@/home/steve/linguistic-tax/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@README.md
@docs/README.md
@.claude/skills/check-results/SKILL.md
@.claude/skills/validate-rdd/SKILL.md
@.claude/skills/run-pilot/SKILL.md
@.claude/skills/analyze/SKILL.md
@.claude/skills/run-experiment/SKILL.md
@.claude/skills/generate-figures/SKILL.md
@.claude/skills/write-section/SKILL.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Claude Code Skills section to README.md</name>
  <files>README.md</files>
  <action>
Add a new section "## Claude Code Skills" to README.md, placed between the "## Documentation" section and the "## Glossary" section (i.e., after line 333 and before line 334 in the current file).

The section should:

1. Open with a brief intro paragraph: "This project includes 7 Claude Code skills that automate common research workflows. These skills are triggered automatically when you ask Claude Code about relevant topics."

2. Include a summary table with columns: Skill, Description, Example Triggers. Populate from each SKILL.md frontmatter description field and the "Also trigger when" phrases:

| Skill | Description | Example Triggers |
|-------|-------------|------------------|
| `check-results` | Inspect experiment progress, data quality, and cost tracking | "how's the experiment going", "check progress", "how much have we spent" |
| `run-pilot` | Run the 20-prompt pilot experiment to validate the pipeline | "run pilot", "test run", "validate the pipeline" |
| `run-experiment` | Execute the full experiment matrix or targeted subsets | "run experiments", "start the full run", "retry failed" |
| `analyze` | Run the statistical analysis pipeline and interpret results against H1-H5 | "analyze results", "run the stats", "are the hypotheses supported" |
| `generate-figures` | Generate publication-quality figures for the ArXiv paper | "make the figures", "generate plots", "accuracy curve" |
| `validate-rdd` | Verify codebase implements the RDD specification correctly | "validate against RDD", "check RDD compliance" |
| `write-section` | Draft LaTeX sections for the ArXiv paper from experiment data | "write the paper", "draft the intro", "generate LaTeX" |

3. Add a note: "Skills are defined in `.claude/skills/` and each has a detailed SKILL.md with full process documentation."

Do NOT change any other section of README.md. Preserve all existing content exactly.
  </action>
  <verify>grep -c "Claude Code Skills" README.md returns 1; grep -c "check-results" README.md returns at least 2 (table row + existing or new mention); the file has valid markdown structure</verify>
  <done>README.md contains a Claude Code Skills section between Documentation and Glossary, listing all 7 skills with descriptions and example trigger phrases</done>
</task>

<task type="auto">
  <name>Task 2: Update docs/README.md with skills reference</name>
  <files>docs/README.md</files>
  <action>
Add a new section to docs/README.md after the "## Research" section and before the "## Quick Links" section.

Add:

```markdown
## Claude Code Skills

This project includes automated skills for Claude Code. See the [main README](../README.md#claude-code-skills) for a summary table, or browse `.claude/skills/` for detailed process documentation.

| Skill | SKILL.md |
|-------|----------|
| check-results | [.claude/skills/check-results/SKILL.md](../.claude/skills/check-results/SKILL.md) |
| run-pilot | [.claude/skills/run-pilot/SKILL.md](../.claude/skills/run-pilot/SKILL.md) |
| run-experiment | [.claude/skills/run-experiment/SKILL.md](../.claude/skills/run-experiment/SKILL.md) |
| analyze | [.claude/skills/analyze/SKILL.md](../.claude/skills/analyze/SKILL.md) |
| generate-figures | [.claude/skills/generate-figures/SKILL.md](../.claude/skills/generate-figures/SKILL.md) |
| validate-rdd | [.claude/skills/validate-rdd/SKILL.md](../.claude/skills/validate-rdd/SKILL.md) |
| write-section | [.claude/skills/write-section/SKILL.md](../.claude/skills/write-section/SKILL.md) |
```

Also add a quick link entry: "- **Using Claude Code?** See [Claude Code Skills](../README.md#claude-code-skills)" in the Quick Links section.

Do NOT change any other content in the file.
  </action>
  <verify>grep -c "Claude Code Skills" docs/README.md returns at least 1; grep -c "SKILL.md" docs/README.md returns at least 7</verify>
  <done>docs/README.md has a Claude Code Skills section with links to each SKILL.md and a quick link entry</done>
</task>

</tasks>

<verification>
- `grep "Claude Code Skills" README.md docs/README.md` shows matches in both files
- All 7 skill names appear in README.md: check-results, run-pilot, run-experiment, analyze, generate-figures, validate-rdd, write-section
- No existing content in either file was modified or removed
</verification>

<success_criteria>
- README.md has a new "Claude Code Skills" section listing all 7 skills with descriptions and trigger examples
- docs/README.md references the skills with links to individual SKILL.md files
- Both files maintain valid markdown structure with no broken formatting
</success_criteria>

<output>
After completion, create `.planning/quick/260325-rvo-document-new-claude-code-skills-and-upda/260325-rvo-SUMMARY.md`
</output>
