# Ticket 345: fast living status update and waves routing

- **ID**: ticket-345
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Route `koru ticket waves` to the Planfile queue CLI handler alongside `auto`, `list`, and `next`.
2. Add native Python SDK fast-path to `update_living_status` in `src/koru/queue/living_status.py` to eliminate 1-2s subprocess boot overhead on each living status transition.

## Acceptance criteria

- [x] AC-01: `koru ticket waves` is routed to `koru.cli_ticket_queue` instead of being rejected as a non-existent URL.
- [x] AC-02: `update_living_status` attempts in-process `Planfile.update_ticket` update first before falling back to subprocess.
- [x] AC-03: Subprocess fallback remains functional if `planfile` is not directly importable or raises an error.
- [x] AC-04: Unit tests verify `waves` routing and `update_living_status` fast-path execution.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
