# Ticket 058: Replace uri2coru with uri2koru aliases

- **ID**: ticket-058
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Replace the duplicated `uri2coru` implementation with a one-release
compatibility namespace over `uri2koru`. Preserve legacy Python symbol and
console names as direct aliases while canonical `koru://` behavior has one
implementation.

This is the second bounded source slice of order 30,
`namespaces.coru_koru_pairs`, in `docs/architecture/volume-reduction-plan.yaml`.
The user's 2026-09-02 instruction to continue executing the plan under
`docs/*` is `SESSION_EXECUTION_AUTHORIZATION` for this ticket.

## Acceptance criteria

- [x] AC-01: Importing `uri2coru` emits a one-release deprecation warning.
- [x] AC-02: Every legacy URI module contains aliases/re-exports and no business logic.
- [x] AC-03: Legacy public symbols are identical to their canonical counterparts.
- [x] AC-04: Both console module names execute the same canonical behavior.
- [x] AC-05: Python, governance, overlap, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
