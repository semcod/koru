# Ticket 228: split-god-module-coru-cli

- **ID**: ticket-228
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

code2llm reports `God Module: packages.coru.src.coru.cli` (180 top-level
functions, 3 classes; detector threshold `f_count > 40`). Split the module by
responsibility into six new `cli_*` modules plus the existing `cli_terminal.py`,
keeping `coru.cli` as a stable facade so every existing import and monkeypatch
target keeps working. Planfile ticket PLF-054. Base: origin/main `5cb5bac5`.

SESSION_EXECUTION_AUTHORIZATION: the planfile handoff for PLF-054 asks to
execute this refactor autonomously and close it with `planfile ticket done`.

## Acceptance criteria

- [ ] AC-01: Scope is approved by a human owner (planfile PLF-054 handoff).
- [ ] AC-02: `packages/coru` tests pass unchanged (no test edits).
- [ ] AC-03: code2llm reports no God Module for `coru.cli` or any new module.
- [ ] AC-04: Patch-heavy tests that monkeypatch `coru.cli` attributes still
  pass (call-time facade late binding preserved).
- [ ] AC-05: `project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
