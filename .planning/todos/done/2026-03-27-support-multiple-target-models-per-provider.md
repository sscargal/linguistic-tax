---
created: 2026-03-27T04:30:00.000Z
title: "Support multiple target models per provider in setup wizard"
area: general
files:
  - src/setup_wizard.py
  - src/cli.py
---

## Problem

The setup wizard currently supports one target + one preproc per provider. To test both gpt-5.1 (capable) and gpt-5-nano (small) as target models under OpenAI, the user has no way to configure this. The research needs multiple models to compare noise robustness across model sizes.

## Solution

1. **Allow multiple target models per provider** — after entering the first target, ask "Add another target model for this provider? (y/N)"
2. **Each target gets its own preproc assignment** — smaller models may use themselves as preproc
3. **Update experiment matrix remapping** — when multiple targets exist for a provider, expand the matrix accordingly
4. **Alternative approach**: allow the same provider to be selected multiple times in the provider selection step (simpler, no wizard changes needed — just remove the deduplication)
