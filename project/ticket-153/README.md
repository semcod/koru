# Ticket 153: scan-llm-executor-routing

- **ID**: ticket-153
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

`koru scan --apply` created each ticket with a full per-ticket planfile sync
(`sync_after_ticket_create` runs a whole `sync_integration` pass, not a
single-ticket push). With ~240 created tickets the first autonomous cycle
spent ~40 minutes in scan before reaching the queue.

This ticket batches the sync: `defer_sync_on_create()` suppresses per-ticket
sync inside the apply loop and `apply_scan_suggestions` runs one
`sync_planfile_integrations` pass afterwards. The `planfile ticket create
--sync` flag on the CLI runner path is removed for the same reason.

Executor routing is intentionally unchanged: `executor.kind=llm` would route
through `llm_runner` (SubLLM text answer) and bypass the
autopilot/tillm/OpenCode lane that actually edits code (see STARTER-577,
which completed through `human` → `waiting_input` → autopilot drive → verify
→ done).

## Acceptance criteria

- [ ] AC-01: Creating N scan tickets triggers one planfile sync, not N.
- [ ] AC-02: `sync_after_ticket_create` inside `defer_sync_on_create()` is a no-op and behavior restores after the block.
- [ ] AC-03: `pytest tests/test_planfile_sync.py tests/test_scan.py` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
