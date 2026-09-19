# Ticket 170: reduce CC: profile load, source snapshot, verify inference

- **ID**: ticket-170
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-18

## Goal and scope

To be completed from human-owned input.

## Acceptance criteria

- [ ] AC-01: Scope is approved by a human owner.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Verification
- lizard: zero functions >15 in touched files (was: 30, 26, 25, 21, 17, 17)
- `pytest` poa/todo2code/profile suites → 108 pass
- `ruff check` clean; `governance-check.sh` → GOV-PASS
