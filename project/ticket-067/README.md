# Ticket 067: Consolidate DSL command-line interface

- **ID**: ticket-067
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Continue order 30 of the volume-reduction plan by making `dsl2koru` the only
implementation of the shared command-line interface. Preserve both command
names, their context flags and their native versus compatibility event-store
semantics through one dialect-aware canonical parser.

## Acceptance criteria

- [x] AC-01: The user's instruction to continue executing the plan in `docs/*`
  is recorded as `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: One canonical CLI accepts the Koru `--project` and Coru `--file`
  dialects, including legacy mode and every existing subcommand.
- [x] AC-03: Encode, roundtrip, run, exec and replay preserve the selected
  dialect's context and `.koru` versus `.coru` event-store behavior.
- [x] AC-04: `dsl2coru.cli` contains only compatibility aliases to the
  canonical CLI and the public callable identities are tested.
- [x] AC-05: Both DSL package suites plus changed-file Ruff, compile,
  governance, Docker Compose and diff gates pass before protected exact-head
  publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
