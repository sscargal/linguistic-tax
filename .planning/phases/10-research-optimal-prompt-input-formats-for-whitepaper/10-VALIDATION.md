---
phase: 10
slug: research-optimal-prompt-input-formats-for-whitepaper
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | Research doc | manual review | N/A — research output | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | Hypotheses | manual review | N/A — research output | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Phase 10 is a research/documentation phase — outputs are markdown documents, not code. Existing test suite validates no regressions from any incidental changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Research document quality | Literature survey completeness | Subjective quality assessment | Review docs/ output for coverage of all format categories in CONTEXT.md |
| Hypothesis feasibility | Testable hypotheses ranked | Requires domain judgment | Verify each hypothesis specifies: what to test, expected effect, measurement method, estimated cost |
| Integration with experiment suite | Format compatibility | Requires architecture review | Verify proposed formats could map to existing INTERVENTIONS tuple pattern |

*Research phases produce knowledge artifacts, not testable code.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
