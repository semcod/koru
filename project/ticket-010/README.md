# Ticket 010: Fix MCP quality-gate CLI adapters for vallm and sumr

- **ID**: ticket-010
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-17

## Goal and scope

MCP `koru_run_quality_gates` invoked invalid `vallm <path>` and `sumr <path>`
argv shapes. Wire supported CLIs: `python -m vallm batch -r` and interpreter-
bound `sumd.cli.main_sumr`.

## Acceptance criteria

- [x] AC-01: `_gate_commands` emits supported vallm and sumr argv shapes.
- [x] AC-02: Focused MCP tests and governance pass.

## Participants

- Agent participant: [ai-gpt-5.6-sol.md](ai-gpt-5.6-sol.md)

## SESSION_EXECUTION_AUTHORIZATION

The user's instruction to continue outstanding work and push authorizes this
bounded quality-gate adapter fix.
