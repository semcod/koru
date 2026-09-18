# Ticket 169: reduce CC: scan mirrors, model router, ticket hygiene

- **ID**: ticket-169
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
- lizard: all four target functions <=15 (`_layers_dup_modules_are_extern_mirrors`, `load_model_registry`, `route`, `run_ticket_hygiene`); `_todo2code_plan_suggestion` also reduced to <=15
- `pytest tests/test_repair_model_router.py test_repair_router.py test_ticket_hygiene.py test_scan.py test_scan_split.py test_scan_phase.py` → 110+99 pass
- `ruff check` clean; `./project/governance-check.sh` → GOV-PASS
