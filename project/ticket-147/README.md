# Ticket 147: web-flag-stdio-fmt-fix

- **ID**: ticket-147
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Fix TypeError crash in `koru auto up --web`: `stdio_info` requires
keyword-only `fmt` argument (regression from ticket-146).

## Acceptance criteria

- [x] AC-01: `koru auto up --web` starts dashboard without TypeError
- [x] AC-02: fmt regression covered by tests

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
