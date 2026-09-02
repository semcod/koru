# Ticket 050: Untrack generated plugin analysis batch one

- **ID**: ticket-050
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Remove the first fourteen files from the generated `.tmp/code2llm-plugins`
artifact group. The group is ignored, content-addressed in the ticket-045
registry and integration-owned after ticket-049. Update the lifecycle document
with the delivered batch boundary.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 slice.

## Acceptance criteria

- [x] AC-01: The fourteen declared plugin-analysis outputs are untracked and
  remain ignored.
- [x] AC-02: The registry still binds the complete pre-cleanup plugin group.
- [x] AC-03: The lifecycle document identifies the delivered and remaining
  plugin batches.
- [x] AC-04: Governance, overlap, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
