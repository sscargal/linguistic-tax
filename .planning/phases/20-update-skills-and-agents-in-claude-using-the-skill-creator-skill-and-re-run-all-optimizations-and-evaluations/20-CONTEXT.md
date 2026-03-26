# Phase 20: Update Skills and Agents - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all 7 `.claude/skills/` to reflect v2.0 codebase changes (phases 16-19 rewrote core modules), regenerate evals and workspaces, re-optimize trigger descriptions, and verify all skills pass evals against the current codebase. No new skills are created — this is maintenance of existing skills.

</domain>

<decisions>
## Implementation Decisions

### Skill update scope
- Update all 7 skills in-place: analyze, check-results, generate-figures, run-experiment, run-pilot, validate-rdd, write-section
- Preserve working trigger descriptions as starting points (re-optimize after content updates)
- All skills are affected by v2.0 changes: model_registry replaces hardcoded constants, config_manager replaces flat config, setup_wizard is fully rewritten, env_manager and model_discovery are new modules
- Skill content (SKILL.md) must reference correct module paths, function signatures, and CLI commands

### Eval refresh strategy
- Regenerate all evals from current codebase state (old evals reference stale interfaces)
- Regenerate all workspace directories (contain snapshot data from pre-v2.0 state)
- Clean up old workspace directories before regenerating to avoid stale data conflicts
- Use `/skill-creator:skill-creator` to regenerate evals and run optimization loops

### Optimization criteria
- Use skill-creator's built-in optimization loop and default passing thresholds
- Re-optimize trigger descriptions — new CLI commands (reconfigured `propt setup`, `propt list-models` with new flags) need updated triggers
- Each skill must pass its eval suite before the phase is considered complete

### Workspace handling
- Delete existing `-workspace` directories before regeneration
- Workspace dirs: analyze-workspace, check-results-workspace, generate-figures-workspace, run-experiment-workspace, run-pilot-workspace, validate-rdd-workspace, write-section-workspace

### Claude's Discretion
- Exact SKILL.md wording and structure updates
- Which specific interface changes per skill need the most attention
- Order of skill updates (can be parallelized)
- Eval case design for testing new module interactions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Skills to update
- `.claude/skills/analyze/SKILL.md` — Statistical analysis pipeline skill
- `.claude/skills/check-results/SKILL.md` — Experiment progress and data quality skill
- `.claude/skills/generate-figures/SKILL.md` — Publication figure generation skill
- `.claude/skills/run-experiment/SKILL.md` — Full experiment matrix execution skill
- `.claude/skills/run-pilot/SKILL.md` — 20-prompt pilot validation skill
- `.claude/skills/validate-rdd/SKILL.md` — RDD compliance checking skill
- `.claude/skills/write-section/SKILL.md` — LaTeX paper section drafting skill

### Key v2.0 module changes (what skills must reference correctly)
- `src/model_registry.py` — ModelConfig, ModelRegistry singleton, replaces hardcoded MODELS/PRICE_TABLE/PREPROC_MODEL_MAP
- `src/config_manager.py` — ExperimentConfig v2, save_config/load_config/validate_config
- `src/env_manager.py` — .env read/write, PROVIDER_KEY_MAP, check_keys
- `src/model_discovery.py` — Live model listing from 4 providers, _query_* functions
- `src/setup_wizard.py` — Fully rewritten multi-provider wizard (Phase 19)
- `src/execution_summary.py` — estimate_cost() with registry-backed pricing

### Skill creation tool
- Use `/skill-creator:skill-creator` for eval generation, optimization, and benchmarking

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 7 skills have existing SKILL.md, evals/evals.json, and -workspace directories
- Skill-creator skill is available for automated eval generation and optimization
- Each skill already has trigger descriptions in the system (listed in CLAUDE.md skill section)

### Established Patterns
- Skills follow SKILL.md format with trigger conditions, steps, and references
- Evals stored as evals/evals.json within each skill directory
- Workspace directories provide isolated test environments for eval runs
- Trigger descriptions defined in skill metadata for Claude Code routing

### Integration Points
- Skills reference src/ modules by import path — these paths changed in v2.0
- Skills reference CLI commands (`propt setup`, `propt run`, etc.) — some flags/behavior changed
- Skills reference data formats (ExperimentConfig, results.db schema) — config format is now v2

</code_context>

<specifics>
## Specific Ideas

- The primary concern is that skills reference old interfaces (e.g., hardcoded `MODELS` tuple instead of `registry.target_models()`, old flat config fields instead of ExperimentConfig v2)
- Skills like run-pilot and run-experiment are most affected since they directly orchestrate experiment execution
- The validate-rdd skill needs to know about new config schema and model registry
- The check-results skill needs to handle results from dynamically configured models, not just the original 4

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-update-skills-and-agents-in-claude-using-the-skill-creator-skill-and-re-run-all-optimizations-and-evaluations*
*Context gathered: 2026-03-26*
