# Ticket 156: terminals prompt_async execution path

- **ID**: ticket-156
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Live testing of the Terminals tab against unmanaged `opencode serve`
instances (ticket-155) showed that dashboard prompts never execute:

- `send_prompt` posted `{"prompt": {"text": ...}}` to
  `/api/session/{id}/prompt`, which only *steer-queues* text for a running
  agent loop (`delivery: "steer"`). An idle session admits the prompt
  (`admittedSeq`) but nothing ever runs.
- `create_session` forwarded caller model dicts verbatim; the server schema
  is `{"id": ..., "providerID": ...}`, so `{"providerID", "modelID"}`
  returned HTTP 400 — and the exception escaped `terminal_prompt`, killing
  the dashboard handler (empty reply).
- `stop_instance` on a discovered-but-unpersisted instance reported
  "unknown instance" instead of the intended not-koru-managed refusal.

## Changes

- `send_prompt` → `POST /session/{id}/prompt_async` with
  `{"parts": [{"type": "text", ...}]}` plus optional normalized
  `model`/`agent`. `prompt_async` is mounted without the `/api` prefix.
- `_normalize_model` translates `{providerID, modelID}` →
  `{id, providerID}` for session create and prompt bodies.
- `terminal_prompt` catches `create_session` failures and returns an error
  dict; `model`/`agent` are forwarded to `send_prompt` too.
- `stop_instance` falls back to discovered (unpersisted) instances so the
  unmanaged refusal applies.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_terminals.py -q` — 28 passed.
- [x] AC-02: live verification on `opencode serve :4101` — session created,
      `prompt_async` produced an assistant reply (`finish: stop`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
