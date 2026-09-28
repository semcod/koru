# Ticket 342: fast in process planfile sdk for queue listing and admission

- **ID**: ticket-342
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

Accelerate queue loop iteration latency by eliminating redundant CLI subprocess execution (`planfile ticket list` and `planfile ticket next`) in favor of direct in-process `Planfile` SDK calls when available, while preserving CLI compatibility fallbacks.

## Acceptance criteria

- [x] AC-01: `src/koru/queue/runner.py` uses in-process `Planfile.auto_discover(project).list_tickets(status="open")` fast path when available.
- [x] AC-02: `src/koru/queue/admission.py` uses native in-process `pf.runnable_report(queue=...)` when available.
- [x] AC-03: All unit tests in `tests/test_planfile_queue.py` pass cleanly.
- [x] AC-04: Full governance check passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
