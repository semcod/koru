# Ticket 060: Consolidate DSL result and event aliases

- **ID**: ticket-060
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Continue order 30 of the volume-reduction plan by making `dsl2koru` the only
implementation of the shared DSL result, protobuf envelope and event-store
foundation. `dsl2coru` retains import-compatible aliases and text-codec wrappers
while its command grammar and bus remain unchanged for this bounded slice.

## Acceptance criteria

- [x] AC-01: The user's instruction to continue executing the plan in `docs/*`
  is recorded as `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: Canonical `dsl2koru` protobuf models encode and decode both current
  Koru verbs and the legacy Coru compatibility verbs.
- [x] AC-03: `dsl2koru.DslResult` and `EventStore` preserve both public APIs;
  legacy result, event and generated protobuf modules are aliases.
- [x] AC-04: Both DSL package suites pass, including protobuf and replay tests,
  and legacy/canonical symbols have explicit identity coverage.
- [x] AC-05: Ruff, compile, governance, Docker Compose and diff checks pass
  before protected exact-head publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
