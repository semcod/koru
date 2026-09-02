# Ticket 068: Complete namespace compatibility conformance

- **ID**: ticket-068
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Complete order 30's executable compatibility boundary. Move the last protobuf
text helpers into canonical `dsl2koru` so `dsl2coru.pb_codec` contains direct
aliases only, and add one conformance suite covering every legacy/canonical
adapter pair declared by the volume-reduction plan.

The user's 2026-09-02 instruction to continue and push the changes is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected exact-head publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
  order-30 slice.
- [x] AC-02: Canonical protobuf text helpers support both project and file
  context without a legacy behavioral wrapper.
- [x] AC-03: Every `*2coru` production module contains only warnings,
  imports, aliases/re-exports, module forwarding and console guards.
- [x] AC-04: One parameterized suite proves warning and CLI identity across
  all six `coru`/`koru` adapter pairs.
- [x] AC-05: Focused Python, Ruff, compile, governance, overlap, Docker
  Compose and diff gates pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
