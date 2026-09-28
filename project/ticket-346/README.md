# Ticket 346: Persist Markdown logs for wellmanifest project tickets and queue execution

- **ID**: ticket-346
- **Owner**: koru
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Persist Markdown formatted logs for projects with wellmanifest layout (`project/ticket-*/**`) during queue execution and autonomy cycles.
Support ticket identifiers from Planfile queue (`PLF-xxx`), GitHub issues, and canonical worktree directories.

## Acceptance criteria

- [x] AC-01: `src/koru/autonomy/cycle_trace.py` provides `find_ticket_dir` that resolves canonical wellmanifest directories for `PLF-xxx`, `ticket-xxx`, and numeric ticket IDs.
- [x] AC-02: `src/koru/autonomy/cycle_trace.py` provides `append_queue_ticket_markdown_log` to persist queue task executions to `project/ticket-*/koru.log.md`.
- [x] AC-03: `PlanfileQueueCommandService.run_next_task` appends markdown logs whenever a project adopts wellmanifest ticket directories.
- [x] AC-04: All unit tests in `tests/test_cycle_trace.py` and `tests/test_queue_log_markdown.py` pass and governance check passes.

## Scope limit

Changes confined to cycle_trace, queue application service, and unit tests.

## Validation

- Unit tests in `tests/test_cycle_trace.py` and `tests/test_queue_log_markdown.py` pass.
- Ruff check passes.
- Governance checks pass.
