# Ticket 358: fix queue runner assert on empty queue and operator guard EPERM

- **ID**: ticket-358
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user asked to continue Koru autopilot
repair ("kontynuuj"); the cluster systemd lane crash-loops on two defects
in this repo.

1. `src/koru/queue/runner.py`: the planfile fast path returns
   `(None, None)` when the queue has no open tickets; the caller then hits
   `assert ticket is not None` and the autonomous daemon exits non-zero
   once the queue is drained. Return an `idle` QueueRunResult instead.
2. `src/koru/autonomy/operator/operator_processes.py`:
   `_terminate_existing_processes` crashes with PermissionError when
   `os.kill(pid, 0)` probes a process owned by another user. Only wait on
   processes that were actually signaled and tolerate EPERM in probes.

## Acceptance criteria

- [ ] AC-01: Empty-queue fast path returns QueueRunResult(status=idle).
- [ ] AC-02: EPERM during SIGTERM/probe never raises out of the guard.
- [ ] AC-03: governance-check.sh passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
