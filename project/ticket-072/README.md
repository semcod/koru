# Ticket 072: Collapse Order 30 DSL grammar tables

- **ID**: ticket-072
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace the per-verb text parser and serializer wrappers in canonical
`dsl2koru` with declarative field tables plus a small set of exceptional
handlers. Preserve every native and compatibility spelling, default and text
round trip while reducing Order 30's remaining production surface.

The user's 2026-09-02 instruction to continue is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
      Order 30 slice.
- [x] AC-02: Shared field tables replace repeated flag parsing and serialization
      without changing verb aliases or context defaults.
- [x] AC-03: Exceptional repair and UI forms retain their current canonical and
      compatibility semantics.
- [x] AC-04: A parameterized grammar matrix covers every supported verb and
      verifies stable parse/serialize/parse behavior.
- [x] AC-05: The source-line reduction, focused suites, Ruff, compile,
      governance, overlap, Docker Compose and diff gates pass before protected
      publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
