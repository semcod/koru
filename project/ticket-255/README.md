# Ticket 255: Integrate Taskand process runner adapter into Koru queue

- **ID**: ticket-255
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Integrate the Taskand process execution framework with Koru's queue system (`koru --queue` and `run_next_planfile_task`).
Enable Koru to execute Planfile tickets whose `executor.kind` is `taskand` or `process`.
The integration supports:
1. Direct process execution via `proc://` URIs and payload data.
2. DAG orchestrator execution via declarative step blueprints (`plan`).
3. Dual-mode transport: Gateway HTTP (`/api/proc/call`, `/api/orchestrator`) when online, with fallback to local `taskand` CLI.
4. Strict enforcement of the zero cross-package imports boundary between Koru and Taskand.

## Acceptance criteria

- [x] AC-01: Introduce `TaskandRunResult` in `src/koru/queue/types.py` adhering to `CommandResult`.
- [x] AC-02: Support `ticket_taskand_request` in `src/koru/queue/ticket.py`.
- [x] AC-03: Implement `run_taskand_request` in `src/koru/queue/runners.py` with gateway HTTP and local CLI fallback.
- [x] AC-04: Wire `taskand` executor kind into `src/koru/queue/runner.py` and CQRS commands/application service.
- [x] AC-05: Comprehensive test coverage in `tests/test_queue_runners.py` and `tests/test_taskand_runner.py`.
- [x] AC-06: Pass `./project/governance-check.sh` cleanly.
