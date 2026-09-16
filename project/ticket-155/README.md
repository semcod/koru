# Ticket 155: terminals-adopt-unmanaged-serve

- **ID**: ticket-155
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Manually started `opencode serve` processes appear in the Terminals grid with
`id: null`, so the detail/prompt/reply endpoints and the auto-answer toggle
cannot address them (`_find_instance` and `set_auto_answer` only match
registry ids). The supervisor can therefore never operate a terminal the
user launched by hand.

- `_scan_serve_processes` now stamps a stable `proc-<port>` id on discovered
  processes, making them addressable by all `/api/terminals/*` endpoints.
- `set_auto_answer` falls back to adopting a discovered process into the
  registry with `managed=False`, so the supervisor answers its questions and
  permissions; stop stays refused for unmanaged instances.

## Acceptance criteria

- [ ] AC-01: discovered `opencode serve` rows expose a non-null stable id.
- [ ] AC-02: `set_auto_answer` on a discovered id registers it (managed=False) and persists the flag.
- [ ] AC-03: `pytest tests/test_dashboard_terminals.py` passes.

- [ ] AC-01: Scope is approved by a human owner.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
