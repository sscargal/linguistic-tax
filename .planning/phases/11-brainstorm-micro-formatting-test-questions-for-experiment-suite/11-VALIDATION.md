---
phase: 11
slug: brainstorm-micro-formatting-test-questions-for-experiment-suite
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual file verification (pure documentation phase — no code changes) |
| **Config file** | none — no test framework needed |
| **Quick run command** | `ls docs/experiments/*.md \| wc -l` |
| **Full suite command** | `ls docs/experiments/*.md && head -5 docs/experiments/README.md` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Verify output file exists and has expected sections
- **After every plan wave:** Verify all expected files created with correct structure
- **Before `/gsd:verify-work`:** All 6 docs/experiments/ files present with complete content
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/token_efficiency.md` | ❌ W0 | ⬜ pending |
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/structural_markup.md` | ❌ W0 | ⬜ pending |
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/punctuation_micro.md` | ❌ W0 | ⬜ pending |
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/format_noise_interaction.md` | ❌ W0 | ⬜ pending |
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/novel_hypotheses.md` | ❌ W0 | ⬜ pending |
| 11-01-XX | 01 | 1 | TBD | file-check | `test -f docs/experiments/README.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/experiments/` directory — create if not exists

*Existing infrastructure covers all phase requirements — this is a pure documentation phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Atomic experiment specs are self-contained | TBD | Requires reading comprehension | Each spec must have: claim, variables, benchmarks, sample size, cost, pilot protocol |
| Tiered execution plan is coherent | TBD | Requires judgment | Tiers ordered by cost/signal ratio; cumulative costs calculated |
| All 6 hypotheses from Phase 10 covered | TBD | Requires cross-reference | grep for H-FMT-01 through H-FMT-06 across all files |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
