# Ticket 158: terminals messages endpoint path

- **ID**: ticket-158
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Follow-up to ticket-156/157. `session_messages` queried
`/api/session/{id}/message`, which on opencode serve 1.17.8 returns an
event projection (`agent-switched` entries) instead of conversation
messages — the dashboard Messages view was empty for live sessions. The
conversation route is mounted unprefixed: `/session/{id}/message`.

## Changes

- `session_messages` → `GET /session/{id}/message` (unprefixed).

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_terminals.py -q` — all pass.
- [x] AC-02: live `/session/{id}/message` returns user+assistant messages
      with parts; `/api/...` variant returned only `agent-switched`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
