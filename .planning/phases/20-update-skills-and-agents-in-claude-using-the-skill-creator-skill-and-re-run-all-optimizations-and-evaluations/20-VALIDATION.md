---
phase: 20
slug: update-skills-and-agents-in-claude-using-the-skill-creator-skill-and-re-run-all-optimizations-and-evaluations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python3 -m pytest tests/test_setup_wizard.py -x -q` |
| **Full suite command** | `.venv/bin/python3 -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3 -m pytest tests/ -x -q --timeout=60`
- **After every plan wave:** Run `.venv/bin/python3 -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | N/A | content | `grep -c "model_registry\|ModelRegistry\|registry" .claude/skills/validate-rdd/SKILL.md` | N/A | pending |
| 20-01-02 | 01 | 1 | N/A | content | `grep -c "model_registry\|config_manager" .claude/skills/run-experiment/SKILL.md` | N/A | pending |
| 20-02-01 | 02 | 1 | N/A | content | `grep -c "model_registry\|config_manager" .claude/skills/check-results/SKILL.md` | N/A | pending |
| 20-02-02 | 02 | 1 | N/A | content | `python3 -c "import json; d=json.load(open('.claude/skills/validate-rdd/evals/evals.json')); print(len(d))"` | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files or frameworks needed — this phase updates skill content (SKILL.md files), not source code.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Skill triggers correctly | N/A | Requires Claude Code runtime | Invoke each skill by name, verify it routes correctly |
| Eval pass rate | N/A | Requires skill-creator tool | Run skill-creator evals for each updated skill |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
