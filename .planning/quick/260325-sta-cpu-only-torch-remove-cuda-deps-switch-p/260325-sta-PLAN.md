---
phase: quick-260325-sta
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - README.md
  - docs/getting-started.md
  - docs/contributing.md
  - uv.lock
autonomous: true
requirements: [QUICK-CPU-TORCH]
must_haves:
  truths:
    - "uv sync installs torch without CUDA packages"
    - "All docs reference uv sync instead of pip install -e ."
    - "bert-score remains a usable dependency"
  artifacts:
    - path: "pyproject.toml"
      provides: "uv source override for CPU-only torch"
      contains: "pytorch-cpu"
    - path: "README.md"
      provides: "Updated install instructions using uv"
      contains: "uv sync"
    - path: "docs/getting-started.md"
      provides: "Updated getting started with uv"
      contains: "uv sync"
    - path: "docs/contributing.md"
      provides: "Updated dev setup with uv"
      contains: "uv sync"
  key_links:
    - from: "pyproject.toml"
      to: "uv.lock"
      via: "uv sync regenerates lock file from updated sources"
      pattern: "pytorch-cpu"
---

<objective>
Configure CPU-only PyTorch via uv source overrides and update all documentation to use uv as the package manager.

Purpose: Eliminate ~6GB of unnecessary CUDA dependencies. This project uses cloud LLM APIs only -- no local GPU needed. torch is pulled in by bert-score but only needs CPU wheels.
Output: Updated pyproject.toml with uv source override, regenerated uv.lock without CUDA, all docs updated to uv workflow.
</objective>

<execution_context>
@/home/steve/linguistic-tax/.claude/get-shit-done/workflows/execute-plan.md
@/home/steve/linguistic-tax/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml
@README.md
@docs/getting-started.md
@docs/contributing.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add uv torch CPU-only source override to pyproject.toml</name>
  <files>pyproject.toml</files>
  <action>
Add the following two sections to the END of pyproject.toml (after the existing `[tool.uv]` section):

1. Add a `[tool.uv.sources]` section that maps torch to the pytorch-cpu index:
```toml
[tool.uv.sources]
torch = { index = "pytorch-cpu" }
```

2. Add a `[[tool.uv.index]]` entry for the PyTorch CPU-only wheel index:
```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

The `explicit = true` flag ensures this index is ONLY used for torch, not for any other package resolution.

Do NOT modify any existing sections of pyproject.toml. The existing `[tool.uv]` section with `package = true` stays as-is.

After editing pyproject.toml, run `uv sync` to regenerate uv.lock with CPU-only torch wheels. Verify the lock file does not contain nvidia/cuda packages by checking: `grep -i "nvidia\|cu121\|cu124\|cu118" uv.lock | head -5` should return no results.
  </action>
  <verify>
    <automated>grep "pytorch-cpu" /home/steve/linguistic-tax/pyproject.toml && grep -c "nvidia" /home/steve/linguistic-tax/uv.lock | grep -q "^0$" && echo "PASS: CPU-only torch configured"</automated>
  </verify>
  <done>pyproject.toml has uv source override for CPU-only torch. uv.lock regenerated without any CUDA/nvidia packages.</done>
</task>

<task type="auto">
  <name>Task 2: Update all documentation to use uv instead of pip</name>
  <files>README.md, docs/getting-started.md, docs/contributing.md</files>
  <action>
Update three documentation files to replace pip/venv workflow with uv.

**README.md** -- Two sections need updating:

1. Quick Start section (lines ~13-21): Replace the venv+pip commands with:
```bash
git clone https://github.com/sscargal/linguistic-tax.git
cd linguistic-tax
uv sync
export ANTHROPIC_API_KEY="sk-ant-..."   # At least one provider required
uv run propt setup
uv run propt pilot --dry-run
```

2. Installation > Setup section (lines ~33-42): Replace venv+pip commands with:
```bash
# Clone and install
git clone https://github.com/sscargal/linguistic-tax.git
cd linguistic-tax
uv sync
```
Remove the venv creation and activation lines -- uv manages its own virtual environment. Remove the Windows activate comment. Remove the "Install in editable mode" comment since `uv sync` handles everything.

3. Troubleshooting section near bottom: Change the "Import errors after install" entry from mentioning `pip install -e .` to `uv sync`. Remove mention of manually activating virtual environment since uv handles this. Keep the Python version entry as-is.

**docs/getting-started.md** -- Installation section (lines ~14-19):
Replace:
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e .
```
With:
```bash
uv sync
```
Remove the Windows activate comment. Update the "Import errors after install" troubleshooting entry at the bottom if present to reference `uv sync`.

**docs/contributing.md** -- Development Setup section (lines ~7-13):
Replace:
```bash
git clone https://github.com/sscargal/linguistic-tax.git
cd linguistic-tax
python -m venv .venv && source .venv/bin/activate
pip install -e .
pytest tests/ -x -q    # Quick smoke test
```
With:
```bash
git clone https://github.com/sscargal/linguistic-tax.git
cd linguistic-tax
uv sync
uv run pytest tests/ -x -q    # Quick smoke test
```

In all three files:
- Do NOT change any content unrelated to installation/setup commands
- Keep all API key instructions, configuration sections, and CLI examples exactly as they are
- The `propt` CLI command references stay as-is (uv makes them available via the project scripts)
- Add a note in README Prerequisites that uv is required: "**[uv](https://docs.astral.sh/uv/)** -- install with `curl -LsSf https://astral.sh/uv/install.sh | sh`"
  </action>
  <verify>
    <automated>grep -c "pip install" /home/steve/linguistic-tax/README.md /home/steve/linguistic-tax/docs/getting-started.md /home/steve/linguistic-tax/docs/contributing.md | grep -v ":0$" | wc -l | grep -q "^0$" && grep "uv sync" /home/steve/linguistic-tax/README.md && echo "PASS: All docs updated to uv"</automated>
  </verify>
  <done>All three doc files use `uv sync` for installation. No remaining `pip install -e .` references. README prerequisites list uv as a requirement.</done>
</task>

</tasks>

<verification>
1. `grep "pytorch-cpu" pyproject.toml` returns the source override
2. `grep -ci "nvidia\|cuda" uv.lock` returns 0
3. `grep -r "pip install" README.md docs/getting-started.md docs/contributing.md` returns no matches
4. `grep "uv sync" README.md docs/getting-started.md docs/contributing.md` returns matches in all three files
5. `uv run python -c "import torch; print(torch.__version__)"` succeeds (torch importable)
6. `uv run pytest tests/ -x -q` passes (existing tests still work)
</verification>

<success_criteria>
- pyproject.toml has [tool.uv.sources] and [[tool.uv.index]] for CPU-only torch
- uv.lock contains no CUDA/nvidia packages
- README.md, docs/getting-started.md, docs/contributing.md all use uv sync
- No remaining pip install -e . references in docs
- torch is importable via uv run
</success_criteria>

<output>
After completion, create `.planning/quick/260325-sta-cpu-only-torch-remove-cuda-deps-switch-p/260325-sta-SUMMARY.md`
</output>
