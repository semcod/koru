# Ticket 474: Restore koru.queue lower-layer import contract (#731)

- **ID**: ticket-474
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Closes semcod/koru#731. `ci.yml` on main had failed for 200+ consecutive runs at the
"Import contracts" step: `koru.queue is a lower layer: no autonomy or daemon imports` was
broken through three chains (queue.runner -> activity_log / planfile_queue.application ->
autonomy.cycle_trace; queue.runners -> task_model_policy -> autonomy.verification_engine).

The stdlib-only helpers those lower layers need move to neutral modules:
`koru.ticket_logs` (find_ticket_dir, append_ticket_markdown_log,
append_queue_ticket_markdown_log) and `koru.drive_budget` (per-ticket drive budget).
`koru.autonomy.cycle_trace` and `koru.autonomy.verification_engine.budget` re-export them, so
every existing import keeps working; the three lower-layer callers import the neutral modules.

## Acceptance criteria

- [x] AC-01: `lint-imports` (import-linter, `PYTHONPATH=src:packages/koruide/src`): 3 kept, 0 broken.
- [x] AC-02: `tests/test_queue_layer_contract.py` (AST guard + re-export identity + budget
  behaviour) and the existing cycle_trace / queue log / retry-guard tests pass (24).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
