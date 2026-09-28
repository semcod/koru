# Ticket 322: Add koru ticket next command

- **ID**: ticket-322
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

1. Add `koru ticket next` CLI subcommand alongside `koru ticket auto` and `koru ticket list`.
2. Inspect the project queue (defaulting to current or specified `--project`, `--queue`, `--sprint`) to determine the exact next runnable Planfile ticket.
3. Support formats:
   - `text` (default): formatted terminal card with ID, Title, Status, Priority, Executor, Labels, Files, and action hints.
   - `brief`: compact single-line `<ID>: <Title>` for scripts and quick overview.
   - `json`: raw JSON representation of the next ticket.
   - `markdown`: clean markdown block.
4. Gracefully report idle queue when no runnable tickets remain.

## Acceptance criteria

- [x] AC-01: `koru ticket next` outputs the next runnable ticket in text, brief, json, and markdown formats.
- [x] AC-02: `koru ticket next` reports idle status when no runnable ticket is found.
- [x] AC-03: Full test suite in `tests/test_ticket_command_queue.py` passes.
- [x] AC-04: `./project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.

## Continuation and validation

User explicitly handed off ticket-322 after the previous session ended; resumed 2026-09-28 with a new controller-issued lease after clean HEAD and scope observation. The preview scopes candidate queries to the requested sprint and keeps native readiness across archived dependencies. Explicit project directories are respected. Invalid transport/JSON returns a nonzero error; JSON output retains raw fields. 69 focused CLI, selection and admission tests pass; scoped Ruff and governance pass. Independent protected publication is still required.
