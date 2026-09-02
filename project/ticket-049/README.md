# Ticket 049: Route generated artifacts to integration workstream

- **ID**: ticket-049
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Assign the exact generated-analysis, coverage, tree and release-media paths from
the governed VOL-1 artifact registry to the integration workstream. These paths
were previously unowned, so the managed gate correctly rejected ticket-048's
first deletion attempt with `GOV-WORKSTREAM-003`.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded governance prerequisite.

## Acceptance criteria

- [x] AC-01: Every path in `config/artifact-registry.json` resolves to the
  integration workstream.
- [x] AC-02: Governance carriers and executable `project/readme.sh` remain
  governance-owned and outside the generated-artifact route.
- [x] AC-03: The managed governance, overlap, Docker Compose and diff gates
  pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
