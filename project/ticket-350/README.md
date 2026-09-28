# Ticket 350: dynamic queue pipelining and in-process planfile sdk optimization

- **ID**: ticket-350
- **Owner**: agent:Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION ("zbadaj jak aktualnei wyglada sytuacja czy mozesz pomoc wypchnac czy scalic i wykonac wlasne zmiany w worktrees")

## Goal and scope

Optimize Koru ticket queue execution latency and parallel worker throughput:
1. Dynamic queue pipelining in `src/koru/queue/loop.py`: replace batch-barrier synchronization (`as_completed`) with continuous work-stealing (`wait(return_when=FIRST_COMPLETED)`). Whenever a worker finishes, it records results and immediately queries for the next runnable ticket using `Planfile.next_tickets(locked_files=..., exclude_ids=...)`.
2. Forward `dry_run` into `run_planfile_queue_loop` and worker execution so dry-run previews concurrent tasks safely.
3. Unwrap runner closures like `sprint_runner` in `runner.py` and `admission.py` so `koru ticket next` uses the in-process Planfile SDK instead of 2 slow subprocess spawns.
4. Fast-path empty queue detection directly in-process.
5. In `get_python_cmd`, prefer `sys.executable` before `python3`.
6. Expose `--concurrency` in root CLI `koru --queue`.
7. Split comma-separated file paths in `ticket_file_scope`.

## Acceptance criteria

- [x] AC-01: `run_planfile_queue_loop` implements dynamic pipelining with `FIRST_COMPLETED` and active file locks.
- [x] AC-02: `run_planfile_queue_loop` accepts and respects `dry_run`.
- [x] AC-03: `runner.py` and `admission.py` recognize in-process Planfile eligibility across wrapped runners.
- [x] AC-04: Empty queue check returns immediately without subprocess CLI fallback.
- [x] AC-05: `get_python_cmd` falls back to `sys.executable`.
- [x] AC-06: `--concurrency` is exposed in `_add_queue_arguments`.
- [x] AC-07: `ticket_file_scope` parses comma-separated file entries.
- [x] AC-08: Unit tests in `tests/test_queue_pipelining.py` verify dynamic pipelining and dry-run concurrency.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
