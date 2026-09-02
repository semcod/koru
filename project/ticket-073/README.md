# Ticket 073: Collapse Order 30 DSL CLI dispatch

- **ID**: ticket-073
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace repeated canonical `dsl2koru` CLI argument declarations and input
dispatch branches with immutable shared specifications and one execution path.
Preserve both console dialects, context precedence, exit codes and byte/text
output while reducing Order 30's remaining production surface.

The user's 2026-09-02 instruction to continue is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
      Order 30 slice.
- [x] AC-02: Shared immutable argument specifications replace repeated context,
      format and output option declarations.
- [x] AC-03: Legacy and subcommand execution share one input dispatcher without
      changing empty-input or context behavior.
- [x] AC-04: A CLI matrix covers parser shape, both dialects, command routing,
      outputs and failure paths.
- [x] AC-05: Focused suites, Ruff, compile, governance, overlap, Docker Compose
      and diff gates pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
