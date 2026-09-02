# Ticket 056: Prepare legacy adapters for canonical namespace shims

- **ID**: ticket-056
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Prepare four legacy adapter distributions for thin compatibility shims by
declaring their canonical `*2koru` counterparts as runtime dependencies. Keep
the existing dependencies during this prerequisite so the current legacy
implementations remain installable until the application-owned shim slice
lands.

The user's 2026-09-02 instruction to continue executing the plan under
`docs/*` is `SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-3 slice.

## Acceptance criteria

- [x] AC-01: Each selected legacy distribution depends on its canonical peer.
- [x] AC-02: Existing legacy dependencies remain intact during the transition.
- [x] AC-03: All four package manifests parse and build wheels without dependencies.
- [x] AC-04: Governance, overlap, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
