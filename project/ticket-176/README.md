# Ticket 176: decompose god function jetbrains_chat_target_from_surface

- **ID**: ticket-176
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Remove the code2llm `God Function: jetbrains_chat_target_from_surface` smell
(STARTER-579) from `packages/koruide/src/koruide/chat_target.py` — the
function moved there from `src/koru/integrations/photo_vql_target.py` on
2026-07-22, which the ticket's stale evidence still references — by splitting
the inline surface-validation, coordinate-map, clamping and payload stages
into small module-level helpers, without behavior change.

Authorization: the requesting session asked to execute this ticket
autonomously (SESSION_EXECUTION_AUTHORIZATION).

## Acceptance criteria

- [ ] AC-01: `jetbrains_chat_target_from_surface` no longer trips the code2llm
  god-function thresholds (CC<=12, fan-out<=10, mutations<=6), and no new
  god-function smell is introduced in the module.
- [ ] AC-02: Existing VQL chat-target tests pass unchanged.
- [ ] AC-03: Ruff and the governance gate pass.
