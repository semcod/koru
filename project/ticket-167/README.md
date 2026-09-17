# Ticket 167: split god module queue_clean.py (STARTER-672)

- **ID**: ticket-167
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Split `src/koru/queue_clean.py` (592L, 21 functions) into a `queue_clean/`
package: `cleanup.py` (fixture sweep) + `legacy_skipped.py` (status migration),
`__init__.py` re-exports the full surface for back-compat.

To be completed from human-owned input.

## Acceptance criteria

- [ ] AC-01: Scope is approved by a human owner.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
