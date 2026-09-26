# Ticket 249: address code smell shotgun surgery cmd in healing webhook app

- **ID**: ticket-249
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm smell `Shotgun Surgery: cmd` in
`services/healing-webhook/app.py` (planfile ticket PLF-039): the variable
`cmd` is assigned/mutated across 7 functions (`_build_planfile_command`,
`create_planfile_ticket`, `heal_redsl_improve`, `heal_rebuild_restore`,
`_run_vallm_check`, `_run_vallm_validate`, `_run_redup_check`), each
hand-rolling the same "argv list, then conditionally append/extend flags"
pattern. Consolidate that pattern into one `_build_command` helper so
command assembly logic lives in a single place; each call site passes its
base argv plus optional flag bundles.

Prerequisite already merged: PR #458 (ticket-247) assigned
`services/**/*.py` to the application workstream, unblocking this work.

## Acceptance criteria

- [ ] AC-01: A single `_build_command(base, *flags)` helper owns argv
      assembly with conditional flag extension; no call site builds and
      mutates its own `cmd` list.
- [ ] AC-02: Existing behaviour is unchanged — the planfile, docker
      (redsl/rebuild), vallm and redup argv shapes are identical for the
      same inputs (covered by `tests/test_healing_webhook_split.py`).
- [ ] AC-03: code2llm no longer reports `Shotgun Surgery: cmd` for
      `services/healing-webhook/app.py`, and `tests/` stays green.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
