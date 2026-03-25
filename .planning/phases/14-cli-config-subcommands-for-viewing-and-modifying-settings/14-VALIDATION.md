---
phase: 14
slug: cli-config-subcommands-for-viewing-and-modifying-settings
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0+ |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_cli.py tests/test_config_commands.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cli.py tests/test_config_commands.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | show-config table | unit | `pytest tests/test_config_commands.py::test_show_config_table -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | show-config --json | unit | `pytest tests/test_config_commands.py::test_show_config_json -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | show-config --changed | unit | `pytest tests/test_config_commands.py::test_show_config_changed -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | show-config single property | unit | `pytest tests/test_config_commands.py::test_show_config_single -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | set-config coercion | unit | `pytest tests/test_config_commands.py::test_set_config_coercion -x` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 1 | set-config validation | unit | `pytest tests/test_config_commands.py::test_set_config_validation -x` | ❌ W0 | ⬜ pending |
| 14-02-03 | 02 | 1 | set-config auto-create | unit | `pytest tests/test_config_commands.py::test_set_config_auto_create -x` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 1 | reset-config single key | unit | `pytest tests/test_config_commands.py::test_reset_config_single -x` | ❌ W0 | ⬜ pending |
| 14-03-02 | 03 | 1 | reset-config --all | unit | `pytest tests/test_config_commands.py::test_reset_config_all -x` | ❌ W0 | ⬜ pending |
| 14-04-01 | 04 | 1 | validate valid config | unit | `pytest tests/test_config_commands.py::test_validate_valid -x` | ❌ W0 | ⬜ pending |
| 14-04-02 | 04 | 1 | validate invalid config | unit | `pytest tests/test_config_commands.py::test_validate_invalid -x` | ❌ W0 | ⬜ pending |
| 14-05-01 | 05 | 1 | diff output | unit | `pytest tests/test_config_commands.py::test_diff_output -x` | ❌ W0 | ⬜ pending |
| 14-06-01 | 06 | 1 | list-models | unit | `pytest tests/test_config_commands.py::test_list_models -x` | ❌ W0 | ⬜ pending |
| 14-07-01 | 07 | 1 | entry point registered | unit | `pytest tests/test_cli.py::test_propt_entry_point -x` | ❌ W0 | ⬜ pending |
| 14-07-02 | 07 | 1 | all subcommands present | unit | `pytest tests/test_cli.py::test_all_subcommands -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config_commands.py` — stubs for all config subcommand tests
- [ ] `tests/test_cli.py` — update with entry point and subcommand tests (file may already exist)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal table renders correctly with colors | show-config table formatting | Terminal-dependent ANSI rendering | Run `propt show-config` in terminal, verify alignment and color |
| Tab completion works | argcomplete integration | Requires shell activation | Run `eval "$(register-python-argcomplete propt)"` then test tab completion |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
