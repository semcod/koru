# Ticket 286: normalize-taskand-orchestrator-plan-and-evidence-logging

- **ID**: ticket-286
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Normalize Taskand orchestrator DAG plans in `src/koru/queue/runners.py` so that planfile tickets specifying steps with `uri`, `inputs`/`input`, or string identifiers conform seamlessly to Taskand Orchestrator's execution contract (`id: int`, `process: uri`, `params: dict`, `deps: list`). Furthermore, ensure `src/koru/queue/runner.py` persists taskand/process and api execution outputs as evidence notes on the ticket upon completion.

## Acceptance criteria

- [x] AC-01: `_normalize_taskand_plan` in `src/koru/queue/runners.py` maps step `uri` -> `process`, ensures integer `id`, generates default step names, guarantees `deps` is a list, and maps `inputs`/`input`/`data` -> `params`.
- [x] AC-02: `run_taskand_request` transparently normalizes any provided plan before sending it to `/api/orchestrator`.
- [x] AC-03: `_finalize_ticket` in `src/koru/queue/runner.py` records execution evidence notes for `taskand` and `api` executor kinds.
- [x] AC-04: Unit test suite passes with full test coverage for normalization and runner evidence.
- [x] AC-05: `./project/governance-check.sh` passes with 0 errors and 0 warnings (GOV-PASS).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
