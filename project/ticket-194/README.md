# Ticket 194: Preserve Flash model identity across Tillm fallback

- **ID**: ticket-194
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

Preserve the provider-qualified Flash model identity when Koru delegates a
bounded lint task through Tillm, including provider fallback, so a requested
`zai/glm-5.3-flash` cannot silently become the full `glm-5.3` model.

The user's `wykonaj` instruction is the session execution authorization for
this bounded repair, validation and pilot deployment.

## Acceptance criteria

- [x] AC-01: Koru normalizes provider-qualified model ids without changing the
  requested routing receipt and delegates the exact model family to Tillm.
- [x] AC-02: Focused tests cover the adapter boundary and pass.
- [ ] AC-03: The deployed pilot records the configured Flash selector and its
  effective model or a sanitized provider rejection reason.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
