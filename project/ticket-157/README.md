# Ticket 157: terminals prompt_async model schema fix

- **ID**: ticket-157
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Follow-up to merged ticket-156. Live verification against
`opencode serve` 1.17.8 showed the opencode API is inconsistent:

- `POST /api/session` (create) accepts `model: {"id", "providerID"}`.
- `POST /session/{id}/prompt_async` rejects that shape — it requires
  `model: {"providerID", "modelID"}` (HTTP 400
  `Missing key at ["model"]["modelID"]`).

Dashboard prompts carrying an explicit model therefore failed with 400.

## Changes

- `_normalize_model(model, style=...)`: `style="create"` emits
  `{id, providerID}` (session create), `style="prompt"` emits
  `{providerID, modelID}` (prompt_async). Caller input may use either
  `id`/`modelID` and `providerID`/`providerId`.
- `send_prompt` uses `style="prompt"`; `create_session` keeps the default
  `style="create"`.
- `stop_instance` falls back to discovered (unpersisted) instances so
  adopted unmanaged servers get the `not koru-managed` refusal instead of
  "unknown instance".

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_terminals.py -q` — all pass.
- [x] AC-02: live `prompt_async` with `{"providerID","modelID"}` →
      HTTP 204, assistant reply produced.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
