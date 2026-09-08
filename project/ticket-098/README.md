# Ticket 098: Acknowledge persisted verification transitions

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Goal and scope
Refactor post-run command verification and acknowledge persisted failure transitions.

## Acceptance criteria
- [x] AC-01: Single-command execution is separated without changing deadline, output or short-circuit behavior.
- [x] AC-02: Failed writes and missing/mismatched readback yield persistence_failed; confirmed transitions occur once and report reopened/blocked.
- [x] AC-03: Focused regressions, Ruff, managed governance and Docker checks pass; execute verification through koru.

Validation: koru single-repository runs passed 55 focused and 11 slow-marked offline integration tests. Ruff, managed governance, Docker Compose and whitespace checks pass. Fresh code2llm report removes run_verify_commands from high-CC methods (18 to 17 in autonomy). Publication authorized on 2026-09-08; protected validation and merge required.
