# Antigravity plan: Integrate Taskand process runner adapter into Koru queue

## Context and goal

Enable deep integration between Koru and the Taskand process execution framework.
Tickets in Koru with `executor.kind: taskand` or `executor.kind: process` can now run
Taskand process URIs (e.g. `proc://taskand.dev/...`) and DAG orchestrator plans (`plan`).

## Approach

1. **Protocol and Data Types**:
   - Added `TaskandRunResult` to `src/koru/queue/types.py` adhering to `CommandResult`.
2. **Ticket Parsing**:
   - Added `ticket_taskand_request` in `src/koru/queue/ticket.py` to extract `uri`, `plan`, `data`, and execution options.
3. **Execution Runners**:
   - Implemented `run_taskand_request` in `src/koru/queue/runners.py` with dual-mode execution:
     - Gateway HTTP (`/api/proc/call`, `/api/orchestrator`) with health probe and bearer authentication.
     - Local CLI fallback (`taskand call <uri> '<data>' --json`) if Gateway HTTP is offline.
     - Zero cross-package imports preserved.
4. **Queue Runner & CQRS Integration**:
   - Wired `taskand` and `process` executor kinds into `_resolve_ticket_action`, `_execute_action`, `_run_next_planfile_task_impl`, and `run_next_planfile_task` in `src/koru/queue/runner.py`.
   - Updated `RunNextPlanfileTaskCommand` and `PlanfileQueueCommandService` to support `taskand_runner`.
5. **Testing & Verification**:
   - Unit tests in `tests/test_queue_runners.py`.
   - Comprehensive integration tests in `tests/test_taskand_runner.py`.
