# Ticket 066: Consolidate DSL dispatch and handlers

- **ID**: ticket-066
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Continue order 30 of the volume-reduction plan by making `dsl2koru` the only
implementation of the shared dispatch bus and Coru-compatible CLI/UI handlers.
`dsl2coru` retains one-release import and console compatibility through direct
aliases to the canonical implementation.

## Acceptance criteria

- [x] AC-01: The user's instruction to continue executing the plan in `docs/*`
  is recorded as `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: The canonical bus dispatches both Koru-native and legacy Coru
  query, command and UI verbs while preserving input-codec parity, runner
  injection and event-store locations.
- [x] AC-03: `dsl2koru` owns argv construction, CLI runner and UI handler
  implementations without importing `dsl2coru`.
- [x] AC-04: The legacy bus and handler modules contain only compatibility
  imports and aliases to `dsl2koru`, with identity assertions covering the
  public compatibility boundary.
- [x] AC-05: Both DSL package suites plus changed-file Ruff, compile,
  governance, Docker Compose and diff gates pass before protected exact-head
  publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
