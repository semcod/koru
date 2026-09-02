# Ticket 076: Deduplicate Order 30 event replay

- **ID**: ticket-076
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace duplicated protobuf replay loops and event-store path construction in
canonical `dsl2koru` with shared private helpers. Preserve JSONL/protobuf bytes,
record ordering, compatibility paths and public `EventStore` behavior while
reducing Order 30 production lines.

The user's 2026-09-02 instruction to continue is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
      Order 30 slice.
- [x] AC-02: Project and compatibility constructors share one store factory
      without changing `.koru`/`.coru` locations or format selection.
- [x] AC-03: `read_all()` and `replay_pb()` share one protobuf decoder while
      preserving record order and truncated-tail behavior.
- [x] AC-04: A focused event-store matrix covers both locations, both formats,
      multi-record replay, empty stores and incomplete trailing frames.
- [x] AC-05: Focused suites, Ruff, compile, governance, overlap, Docker Compose
      and diff gates pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
