---
phase: 12
slug: comprehensive-documentation-and-readme-for-new-users
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | N/A | manual | `test -f README.md && grep -q "install" README.md` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | N/A | manual | `test -f docs/getting-started.md` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 1 | N/A | manual | `test -f docs/architecture.md` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 1 | N/A | manual | `test -f docs/analysis-guide.md` | ❌ W0 | ⬜ pending |
| 12-05-01 | 05 | 1 | N/A | manual | `test -f docs/contributing.md` | ❌ W0 | ⬜ pending |
| 12-06-01 | 06 | 1 | N/A | manual | `test -f docs/README.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Documentation files are verified by file existence checks and content grep.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mermaid diagrams render | N/A | GitHub rendering | View architecture.md on GitHub, confirm diagrams render |
| Cross-links resolve | N/A | Link validation | Click all internal links in docs, confirm targets exist |
| CLI examples accurate | N/A | Runtime output | Run `propt --help` and compare against README CLI reference |
| Glossary completeness | N/A | Domain knowledge | Review glossary against RDD terms |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
