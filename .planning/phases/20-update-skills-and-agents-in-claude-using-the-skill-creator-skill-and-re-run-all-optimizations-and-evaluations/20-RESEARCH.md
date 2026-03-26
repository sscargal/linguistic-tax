# Phase 20: Update Skills and Agents - Research

**Researched:** 2026-03-26
**Domain:** Claude Code skills maintenance, eval regeneration, workspace management
**Confidence:** HIGH

## Summary

This phase updates 7 existing `.claude/skills/` to reflect the v2.0 codebase changes made in phases 16-19. The core change is that hardcoded model constants (`MODELS`, `PRICE_TABLE`, `PREPROC_MODEL_MAP`, `RATE_LIMIT_DELAYS`) were removed from `config.py` and replaced by `model_registry.py` (ModelRegistry singleton), `config_manager.py` (ExperimentConfig v2 with JSON persistence), `env_manager.py` (.env management), `model_discovery.py` (live model listing), and a fully rewritten `setup_wizard.py` (multi-provider wizard). Skills currently reference stale interfaces and need content updates, fresh evals, and regenerated workspaces.

The work is primarily content editing (SKILL.md updates) plus automated eval/workspace regeneration via the skill-creator tool. No new code modules are being written. The risk is low -- this is documentation maintenance with automated verification via eval pass rates.

**Primary recommendation:** Update each skill's SKILL.md to reference v2.0 module paths and APIs, then use `/skill-creator:skill-creator` to regenerate evals, workspaces, and re-optimize trigger descriptions. Process skills in impact order: most-affected first (validate-rdd, run-experiment, run-pilot, check-results), then less-affected (analyze, generate-figures, write-section).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Update all 7 skills in-place: analyze, check-results, generate-figures, run-experiment, run-pilot, validate-rdd, write-section
- Preserve working trigger descriptions as starting points (re-optimize after content updates)
- All skills are affected by v2.0 changes: model_registry replaces hardcoded constants, config_manager replaces flat config, setup_wizard is fully rewritten, env_manager and model_discovery are new modules
- Skill content (SKILL.md) must reference correct module paths, function signatures, and CLI commands
- Regenerate all evals from current codebase state (old evals reference stale interfaces)
- Regenerate all workspace directories (contain snapshot data from pre-v2.0 state)
- Clean up old workspace directories before regenerating to avoid stale data conflicts
- Use `/skill-creator:skill-creator` to regenerate evals and run optimization loops
- Use skill-creator's built-in optimization loop and default passing thresholds
- Re-optimize trigger descriptions -- new CLI commands need updated triggers
- Each skill must pass its eval suite before the phase is considered complete
- Delete existing `-workspace` directories before regeneration

### Claude's Discretion
- Exact SKILL.md wording and structure updates
- Which specific interface changes per skill need the most attention
- Order of skill updates (can be parallelized)
- Eval case design for testing new module interactions

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Architecture Patterns

### Skill Directory Structure (unchanged)
```
.claude/skills/
  {skill-name}/
    SKILL.md              -- Skill content (trigger description in YAML frontmatter + instructions)
    evals/
      evals.json          -- Eval cases with prompts, expected outputs, expectations
    references/           -- (optional) Reference docs for the skill
      *.md
  {skill-name}-workspace/
    iteration-1/          -- Workspace snapshot for eval runs
      ...
```

### SKILL.md Format
Each skill has YAML frontmatter with `name` and `description` (the trigger description), followed by markdown instructions. The `description` field is what Claude Code uses for routing -- it must mention relevant keywords and natural-language triggers.

### Eval Format
```json
{
  "skill_name": "check-results",
  "evals": [
    {
      "id": 1,
      "prompt": "natural language user request",
      "expected_output": "what should happen",
      "files": [],
      "expectations": [
        "Specific verifiable behavior 1",
        "Specific verifiable behavior 2"
      ]
    }
  ]
}
```

### Pattern: Skill Update Workflow
For each skill:
1. Audit SKILL.md for stale references (old module paths, removed constants, changed APIs)
2. Update SKILL.md content to reference v2.0 modules and APIs
3. Delete the `-workspace` directory
4. Use `/skill-creator:skill-creator` to regenerate evals and workspace
5. Run optimization loop until eval pass rate meets threshold
6. Re-optimize trigger description if CLI commands or concepts changed

## Stale Reference Audit

### HIGH Impact Skills (direct references to removed/changed APIs)

#### validate-rdd
- References `config.py:MODELS` (removed -- now `registry.target_models()`)
- References `config.py:PREPROC_MODEL_MAP` (removed -- now `registry.get_preproc()`)
- References `config.py:temperature` (still in ExperimentConfig, OK)
- References `config.py:type_a_rates` (still in ExperimentConfig, OK)
- References `config.py:derive_seed()` (still in config.py, OK)
- References `config.py:NOISE_TYPES` (still in config.py, OK)
- References `config.py:INTERVENTIONS` (still in config.py, OK)
- References `config.py:compute_cost()` (removed -- now `registry.compute_cost()`)
- References `config.py:repetitions` (still in ExperimentConfig, OK)
- Says "Models under test: Claude Sonnet + Gemini 1.5 Pro (2 models)" -- now configurable, up to 4+ models
- Must add: model_registry.py, config_manager.py, setup_wizard.py as validation targets
- Must update: model configuration checks to validate against registry, not hardcoded MODELS

#### run-experiment
- References `config.py:RATE_LIMIT_DELAYS` in troubleshooting table (removed -- now `registry.get_delay()`)
- Model filter examples are correct (`--model claude`, etc.) but may need updating if CLI flags changed
- Should mention `config_manager.load_config()` flow for model resolution
- Should reference `registry.compute_cost()` for cost estimation instead of old `compute_cost()`

#### run-pilot
- References `config.py:RATE_LIMIT_DELAYS` in troubleshooting table (removed)
- Should mention multi-provider setup via `propt setup`
- Prerequisites should reference `config_manager.load_config()` and `env_manager.check_keys()`

#### check-results
- Already references `config_manager.find_config_path` (partially updated!)
- db-context.md reference file has hardcoded price table (needs update -- prices now from registry)
- db-context.md says "Models: Up to 4" -- still correct but should mention dynamic configuration
- Recommendations section references correct CLI commands

### LOW Impact Skills (no direct references to changed APIs)

#### analyze
- No references to model configuration, registry, or config management
- Pipeline commands (`python -m src.compute_derived`, `python -m src.analyze_results`) unchanged
- Hypothesis interpretation framework unchanged
- Main update: ensure any mention of "models" acknowledges dynamic configuration

#### generate-figures
- No references to model configuration or changed APIs
- Figure generation commands unchanged
- Style specifications unchanged
- Main update: figures should handle variable number of models (not assume exactly 2 or 4)

#### write-section
- No references to model configuration or changed APIs
- Paper structure and LaTeX conventions unchanged
- Main update: methodology section guidance should mention configurable models

## V2.0 Module Reference (what skills should cite)

| Old Reference | New Reference | Module |
|---------------|---------------|--------|
| `config.py:MODELS` | `registry.target_models()` | `src/model_registry.py` |
| `config.py:PRICE_TABLE` | `registry.get_price(model_id)` | `src/model_registry.py` |
| `config.py:PREPROC_MODEL_MAP` | `registry.get_preproc(model_id)` | `src/model_registry.py` |
| `config.py:RATE_LIMIT_DELAYS` | `registry.get_delay(model_id)` | `src/model_registry.py` |
| `config.py:compute_cost()` | `registry.compute_cost(model_id, in_tok, out_tok)` | `src/model_registry.py` |
| flat config fields (`claude_model`, etc.) | `ExperimentConfig.models` list | `src/config.py` + `src/config_manager.py` |
| manual .env editing | `env_manager.write_env()` / `env_manager.check_keys()` | `src/env_manager.py` |
| N/A (new) | `discover_all_models()` | `src/model_discovery.py` |
| old setup wizard | `run_setup_wizard()` (16 functions, multi-provider) | `src/setup_wizard.py` |
| N/A (new) | `propt list-models` CLI command | `src/cli.py` |

### What Remains in config.py (unchanged)
- `ExperimentConfig` dataclass (with `models` list field, v2 format)
- `derive_seed()` function
- `NOISE_TYPES` tuple
- `INTERVENTIONS` tuple
- `OPENROUTER_BASE_URL`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Eval generation | Manual eval JSON editing | `/skill-creator:skill-creator` | Automated eval generation ensures consistency and coverage |
| Workspace creation | Manual file copying | `/skill-creator:skill-creator` | Workspace snapshots must match current codebase state |
| Trigger optimization | Manual description tweaking | Skill-creator optimization loop | Data-driven trigger descriptions outperform manual tuning |

## Common Pitfalls

### Pitfall 1: Updating Content but Not Evals
**What goes wrong:** SKILL.md is updated but evals still test old behaviors/references
**Why it happens:** Evals are regenerated separately and easy to forget
**How to avoid:** Always regenerate evals AFTER updating SKILL.md content
**Warning signs:** Evals reference old module names or expect old behaviors

### Pitfall 2: Stale Workspace Data
**What goes wrong:** Eval runs pass against old workspace snapshots that don't reflect v2.0 code
**Why it happens:** Workspace directories contain frozen file copies from pre-v2.0
**How to avoid:** Delete workspace directories before regenerating (as CONTEXT.md specifies)
**Warning signs:** Eval passes but skill fails in real use because workspace had old interfaces

### Pitfall 3: Partial Reference Updates
**What goes wrong:** Some references to `config.py:MODELS` updated but others missed
**Why it happens:** Skills have multiple sections that may reference the same old API
**How to avoid:** Do a full grep for stale references after each skill update
**Warning signs:** Mixed old/new references in the same SKILL.md

### Pitfall 4: Trigger Description Regression
**What goes wrong:** Re-optimized trigger descriptions lose routing accuracy for existing use cases
**Why it happens:** Optimization focuses on new capabilities and forgets old triggers
**How to avoid:** Preserve working trigger phrases as starting points (per CONTEXT.md decision)
**Warning signs:** Skill stops triggering for previously-working prompts

### Pitfall 5: check-results db-context.md Reference File
**What goes wrong:** The `references/db-context.md` file has a hardcoded price table that won't match registry-backed pricing
**Why it happens:** Reference files are separate from SKILL.md and easy to overlook
**How to avoid:** Update reference files alongside SKILL.md
**Warning signs:** check-results skill gives wrong cost information

## Skill Impact Assessment and Update Order

| Skill | Impact | Key Changes Needed | Priority |
|-------|--------|-------------------|----------|
| validate-rdd | HIGH | 6+ stale references to removed config.py constants; must add model_registry, config_manager, setup_wizard as validation targets | 1 |
| run-experiment | HIGH | RATE_LIMIT_DELAYS reference, cost estimation flow, model resolution via registry | 2 |
| run-pilot | HIGH | RATE_LIMIT_DELAYS reference, prerequisites mentioning new setup flow | 3 |
| check-results | MEDIUM | db-context.md price table update, dynamic model acknowledgment; already partially updated (uses config_manager) | 4 |
| analyze | LOW | Minor wording to acknowledge dynamic model sets | 5 |
| generate-figures | LOW | Minor wording about variable model counts | 6 |
| write-section | LOW | Methodology guidance for configurable models | 7 |

**Recommended approach:** Process HIGH-impact skills first where stale references could cause real failures, then MEDIUM, then LOW. Each skill follows: audit -> update SKILL.md -> delete workspace -> regenerate evals+workspace via skill-creator -> optimize triggers -> verify pass rate.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | skill-creator eval system (via `/skill-creator:skill-creator`) |
| Config file | Each skill's `evals/evals.json` |
| Quick run command | `/skill-creator:skill-creator` run evals for single skill |
| Full suite command | Run evals for all 7 skills sequentially |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKL-01 | validate-rdd references v2.0 modules correctly | skill eval | skill-creator eval for validate-rdd | Regenerate in Wave 0 |
| SKL-02 | run-experiment references registry APIs | skill eval | skill-creator eval for run-experiment | Regenerate in Wave 0 |
| SKL-03 | run-pilot references new setup flow | skill eval | skill-creator eval for run-pilot | Regenerate in Wave 0 |
| SKL-04 | check-results handles dynamic models | skill eval | skill-creator eval for check-results | Regenerate in Wave 0 |
| SKL-05 | analyze skill functional with v2.0 | skill eval | skill-creator eval for analyze | Regenerate in Wave 0 |
| SKL-06 | generate-figures skill functional | skill eval | skill-creator eval for generate-figures | Regenerate in Wave 0 |
| SKL-07 | write-section skill functional | skill eval | skill-creator eval for write-section | Regenerate in Wave 0 |

### Sampling Rate
- **Per task commit:** Run eval for the specific skill being updated
- **Per wave merge:** Run evals for all skills updated in that wave
- **Phase gate:** All 7 skills pass their eval suites

### Wave 0 Gaps
- [ ] All 7 `evals/evals.json` files need regeneration (current evals reference pre-v2.0 state)
- [ ] All 7 `-workspace/` directories need deletion and regeneration
- [ ] `check-results/references/db-context.md` needs price table update

## Open Questions

1. **Skill-creator availability and invocation**
   - What we know: CONTEXT.md says to use `/skill-creator:skill-creator`
   - What's unclear: The skill-creator tool is not present in the `.claude/skills/` directory of this project -- it may be a system-level Claude Code skill or MCP tool
   - Recommendation: The implementer should verify the skill-creator is available in their Claude Code session before starting. If unavailable, evals can be manually updated following the existing JSON format.

2. **Eval pass threshold**
   - What we know: CONTEXT.md says "use skill-creator's built-in optimization loop and default passing thresholds"
   - What's unclear: The exact default threshold percentage
   - Recommendation: Use whatever default the skill-creator provides; if manual, aim for all expectations met on all eval cases

## Sources

### Primary (HIGH confidence)
- Direct file reads of all 7 SKILL.md files in `.claude/skills/`
- Direct file reads of `src/model_registry.py`, `src/config_manager.py`, `src/config.py`
- Direct file reads of `src/env_manager.py`, `src/model_discovery.py`, `src/setup_wizard.py`
- grep audit of stale references across all skill files
- Eval JSON format from existing `evals/evals.json` files
- CONTEXT.md decisions from user discussion session

### Secondary (MEDIUM confidence)
- Workspace directory structure inferred from `ls` of existing workspaces

## Metadata

**Confidence breakdown:**
- Stale reference audit: HIGH - direct grep against source files
- Impact assessment: HIGH - based on actual file contents
- Update workflow: HIGH - follows established skill-creator pattern from CONTEXT.md
- Eval regeneration: MEDIUM - skill-creator tool not inspected directly (external tool)

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- skill format unlikely to change)
