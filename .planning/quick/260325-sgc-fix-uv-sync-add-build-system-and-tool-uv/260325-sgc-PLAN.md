---
phase: quick
plan: 260325-sgc
type: execute
wave: 1
depends_on: []
files_modified: [pyproject.toml]
autonomous: true
requirements: [fix-uv-sync-entry-points]

must_haves:
  truths:
    - "`uv sync` completes without entry point warnings"
    - "`propt` entry point is installed and callable after `uv sync`"
  artifacts:
    - path: "pyproject.toml"
      provides: "build-system configuration"
      contains: "build-system"
  key_links:
    - from: "pyproject.toml [build-system]"
      to: "pyproject.toml [project.scripts]"
      via: "hatchling build backend enables entry point installation"
---

<objective>
Add [build-system] section to pyproject.toml so uv can install the `propt` entry point defined in [project.scripts].

Purpose: Without a build-system, uv skips entry point installation and warns. Adding hatchling as the build backend resolves this.
Output: Updated pyproject.toml with working build configuration.
</objective>

<execution_context>
@/home/steve/linguistic-tax/.claude/get-shit-done/workflows/execute-plan.md
@/home/steve/linguistic-tax/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add build-system and package flag to pyproject.toml</name>
  <files>pyproject.toml</files>
  <action>
Add two sections to pyproject.toml:

1. Add `[build-system]` section at the TOP of the file (before [project]), using hatchling:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. Add `[tool.uv]` section (after [tool.pytest.ini_options]) with:
```toml
[tool.uv]
package = true
```

Since `src/` is the package directory and is imported as `src.cli:main`, hatchling's default source discovery should find it automatically (it looks for directories with `__init__.py`). No additional `[tool.hatch.build]` configuration should be needed.

Do NOT change any existing sections or dependencies.
  </action>
  <verify>
    <automated>cd /home/steve/linguistic-tax && uv sync 2>&1 | grep -v "Skipping installation of entry points" && which propt && propt --help | head -5</automated>
  </verify>
  <done>
- `uv sync` produces no "Skipping installation of entry points" warning
- `propt` command is available on PATH after sync
- `propt --help` shows CLI help output
  </done>
</task>

</tasks>

<verification>
Run `uv sync` and confirm:
1. No warning about skipping entry points
2. `propt --help` works
</verification>

<success_criteria>
- pyproject.toml has [build-system] with hatchling
- `uv sync` installs entry points without warnings
- `propt` CLI command is functional
</success_criteria>

<output>
After completion, create `.planning/quick/260325-sgc-fix-uv-sync-add-build-system-and-tool-uv/260325-sgc-SUMMARY.md`
</output>
