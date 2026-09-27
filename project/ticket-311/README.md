# Ticket 311: Stage-accurate names for the ide locals in ide doctor CLI

- **ID**: ticket-311
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Planfile**: PLF-045 (dedupe key
  `code2llm:smell:shotgun_surgery:src/koru/ide_doctor_cli.py:665:Shotgun Surgery: ide`)

## Goal and scope

code2llm reports `Shotgun Surgery: ide` at `src/koru/ide_doctor_cli.py:665`:
five functions in that file each assign a local named `ide`, so the detector's
`(file, variable) -> mutating scopes` grouping reaches the >= 5 threshold and
flags the name as logic coupled across many places. The five locals actually
carry deliberately different semantics (required diagnosis target, optional
history filter, reload target with raw fallback, catalog scope, scenario-prompt
scope), so the shared generic name is the defect, not a missing abstraction.

Fix: pure rename of each local to what it holds at its stage, matching the
pattern accepted for the same smell class in ticket-270
(src/koruapi/opencode_terminals.py, PR #480):

| Function | Old local | New local | Meaning |
|---|---|---|---|
| `action_ide_doctor` | `ide` | `target_ide` | single resolved IDE under diagnosis |
| `action_ide_history` | `ide` | `subject_ide` | optional repair-history subject selector (`None` = all) |
| `action_ide_reload` | `ide` | `reload_ide` | canonical IDE with raw-argument fallback |
| `action_ide_commands` | `ide` | `catalog_ide` | command-catalog scope selector (`None` = all) |
| `action_ide_scenario_prompt` | `ide` | `scenario_ide` | scenario-prompt target selector (`None` = all) |

`args.ide`, the `evaluate_bridge(ide=...)` keyword, the payload key `"ide"` and
all helper parameter names keep their names. No behavior change.

## Acceptance criteria

- [ ] AC-01: standalone code2llm DFGExtractor mutation grouping on the file
      reports the `ide` group at exactly the five ticket-reported functions
      before the rename and no `ide` group after it, with every other
      `(file, variable)` group unchanged.
- [ ] AC-02: `pytest tests/test_ide_doctor_cli.py tests/test_ide_command_catalog.py`
      and `ruff check src/koru/ide_doctor_cli.py` pass on the renamed file.
- [ ] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS 0 errors 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
