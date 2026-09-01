# Ticket 033: Document auto-execute shell commands and CI hooks

- **ID**: ticket-033
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Document how Koru auto-executes shell commands (planfile queue, `koru ci run`,
`koru work next --run-gates`, `post_run_verify`) and clarify that `koru.yaml`
`when:` sections are brief-only except verification hooks.

## Acceptance criteria

- [x] AC-01: New guide `docs/auto-execute-commands.md` with execution-surface table.
- [x] AC-02: `docs/README.md`, `quickstart-10min.md`, and `cli-examples.md` link to the guide.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
