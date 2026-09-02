# Ticket 071: Collapse protobuf verb codecs

- **ID**: ticket-071
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace the per-verb protobuf setter and extractor functions in canonical
`dsl2koru` with one descriptor-driven codec and explicit default-value policy.
Preserve byte, dictionary and text round trips for both Koru and compatibility
Coru verbs while reducing Order 30's remaining production surface.

The user's 2026-09-02 instruction to continue is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
      Order 30 slice.
- [x] AC-02: One descriptor-driven encoder handles every protobuf body field,
      repeated value and scalar conversion without per-verb setter functions.
- [x] AC-03: One descriptor-driven decoder preserves the intentional defaults
      and omission semantics of every supported verb.
- [x] AC-04: A parameterized matrix proves dict/protobuf round-trip parity for
      all native and compatibility body messages.
- [x] AC-05: The source-line reduction, focused suites, Ruff, compile,
      governance, overlap, Docker Compose and diff gates pass before protected
      publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
