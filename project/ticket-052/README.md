# Ticket 052: Untrack final generated project analysis batch

- **ID**: ticket-052
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Remove the final nine generated project-analysis outputs from Git. All targets
are ignored, integration-owned and content-addressed by the ticket-045
registry. Update the lifecycle batch record without changing runtime code.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 slice.

## Acceptance criteria

- [x] AC-01: The nine declared project-analysis outputs are untracked and ignored.
- [x] AC-02: No generated analysis output from the registry remains tracked.
- [x] AC-03: Registry hashes and the lifecycle recovery procedure remain available.
- [x] AC-04: Governance, overlap, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent; ticket prose is not the
material outcome.
