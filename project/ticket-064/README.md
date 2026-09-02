# Ticket 064: Consolidate DSL text and schema registry

- **ID**: ticket-064
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Continue order 30 of the volume-reduction plan by making `dsl2koru` the only
implementation of the shared text grammar, JSON-schema registry, validation
codec and schema model generator. `dsl2coru` retains one-release import and
console compatibility through warning/re-export facades.

## Acceptance criteria

- [x] AC-01: The user's instruction to continue executing the plan in `docs/*`
  is recorded as `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: Canonical text parsing and serialization preserve both Koru and
  legacy Coru verbs, defaults and round trips.
- [x] AC-03: `dsl2koru` owns the combined schema registry, validation codec and
  generated-model behavior without importing `dsl2coru`.
- [x] AC-04: Legacy grammar, parser, serializer, schema registry, codec and
  codegen modules contain only compatibility imports, aliases and thin
  signature wrappers where required.
- [x] AC-05: Both DSL package suites plus changed-file Ruff, compile,
  governance, Docker Compose and diff gates pass before protected exact-head
  publication. Fourteen Ruff findings in files unchanged from the accepted
  base remain outside this ticket.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
