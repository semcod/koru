# Ticket 165: terminals: dynamic provider failover without server restart

- **ID**: ticket-165
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

When an OpenCode serve instance is driving tasks and encounters provider rate limits or quota exhaustion (e.g. `Usage limit reached for 5 hour` / `AI_APICallError` on `zai/glm-5.3`), the session remains blocked unless manually restarted.
This ticket implements dynamic provider failover without server restart:
- Detect provider exhaustion from server errors / session messages.
- Dynamically resolve unexhausted models from the running instance's `/config` provider catalog.
- Automatically steer prompts and stuck sessions to the working fallback model (e.g. `deepseek/deepseek-v4-pro`).

## Acceptance criteria

- [x] AC-01: Provider exhaustion tracking (`mark_provider_exhausted`, `is_provider_exhausted`) respects cooldown TTL.
- [x] AC-02: `resolve_active_terminal_model` picks the fallback model when the primary provider is exhausted.
- [x] AC-03: `terminal_prompt` uses the resolved active model and fails over on provider exhaustion.
- [x] AC-04: `opencode_supervisor` detects sessions with stream errors and auto-switches to unexhausted model.
- [x] AC-05: Unit tests pass in `tests/test_dashboard_terminals.py`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
