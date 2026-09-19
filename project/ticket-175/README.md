# Ticket 175: decompose god function get_vql_chat_target_from_photo

- **ID**: ticket-175
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Remove the code2llm `God Function: get_vql_chat_target_from_photo` smell
(STARTER-578) from `src/koru/integrations/vdisplay_client.py` by extracting
the nested closures and selection stages into module-level helpers, without
behavior change.

## Acceptance criteria

- [ ] AC-01: `get_vql_chat_target_from_photo` no longer trips the code2llm
  god-function thresholds (CC<=12, fan-out<=10, mutations<=6).
- [ ] AC-02: Existing VQL chat-target tests pass unchanged.
- [ ] AC-03: Ruff and the governance gate pass.
