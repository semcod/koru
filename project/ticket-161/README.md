# Ticket 161: terminals: fix message rendering + show ticket/project/model per opencode instance

- **ID**: ticket-161
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user asked to fix the
  detected terminals-tab problems and extend the opencode list view with
  ticket/project/LLM/API info.

## Goal and scope

The Terminals tab rendered every conversation message as `?` with an empty
body: `termMessagesHtml()` expected `{role|type, text|content|command}` while
`/api/terminals/messages` proxies raw opencode `{info:{role}, parts:[...]}`
messages (see ticket-158 for the endpoint fix). Additionally the instance grid
showed no working context — which planfile ticket a session drives, which
project directory it runs in, which LLM model and provider API it uses.

## Changes

- `terminal_messages` normalizes `{info,parts}` to
  `{role, text, agent, model, provider, created}`; the template renderer also
  accepts the raw shape as a fallback.
- `instance_status` session rows gain `directory` (from `location.directory`),
  `model`, `provider`, `agent`, `updated`, `ticket` — the ticket id is scanned
  from user prompts of the 8 most recently updated sessions (72h window,
  cached per `(url, sid, updated)`).
- Instance rows gain `project_dirs`, `models`, `active_ticket` and a sanitized
  `providers` catalog from `/api/provider` (request bodies / apiKeys never
  leave the process).
- Cards show ticket/project/llm/api lines; session buttons show ticket +
  model badges.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_terminals.py -q` — all pass.
- [x] AC-02: live `/api/terminals/messages` returns normalized
      `{role:"user","text":"say ok"}` rows; cards expose ticket/model/api.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
