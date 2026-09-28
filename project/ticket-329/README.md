# Ticket 329: Parallel ticket batching and execution waves in koru queue

- **ID**: ticket-329
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

Integrate Planfile native dependency acceleration, disjoint ticket batching, and execution waves into Koru:
1. `koru.queue.ticket.parse_next_tickets` and `koru.queue.runner._next_tickets_or_result`:
   - Batch resolution supporting `count=N` and `disjoint_files=True`.
   - Prefer native Python `Planfile.next_tickets` (critical-path weighted, disjoint-file guaranteed) with graceful fallback.
2. Parallel queue loop execution in `koru.queue.loop.run_planfile_queue_loop`:
   - Add `concurrency: int = 1` parameter.
   - Run up to `concurrency` independent workers simultaneously via `ThreadPoolExecutor` on disjoint tickets.
   - Scoped locking: restrict `queue_runner_lock` to claim and status finalization phases so long-running LLM/tool steps run concurrently.
3. CLI enhancements in `koru.cli_ticket_queue`:
   - Add `--concurrency -c` to `koru ticket auto`.
   - Add `--count -c` and `--disjoint-files` to `koru ticket next`.
   - Add `koru ticket waves` command to visualize parallel execution waves.
4. Comprehensive test coverage in `tests/test_queue_concurrency.py`.

## Acceptance criteria

- [ ] AC-01: `parse_next_tickets` filters and returns disjoint file sets when `disjoint_files=True`.
- [ ] AC-02: `_next_tickets_or_result` leverages native `Planfile.next_tickets` when available and falls back cleanly.
- [ ] AC-03: `run_planfile_queue_loop` executes tasks concurrently when `concurrency > 1`.
- [ ] AC-04: `koru ticket auto --concurrency N` and `koru ticket next --count N` CLI options parse correctly.
- [ ] AC-05: `tests/test_queue_concurrency.py` passes all unit and integration assertions.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
