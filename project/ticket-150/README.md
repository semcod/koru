# Ticket 150: terminals-tab-opencode-grid-supervisor

- **ID**: ticket-150
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Add a **Terminals** tab to the koru dashboard: a grid of `opencode serve`
instances (koru-spawned and user-started, discovered via a registry file plus a
`/proc` scan). Clicking a card shows that instance's sessions, live messages,
and pending permission/question requests — which the user can answer with
buttons, or leave to the koru supervisor.

The supervisor is a daemon thread started alongside the dashboard (`koru serve`
and `koru auto --web`). For instances with `auto_answer` it polls the opencode
HTTP API and replies: permissions → `once`; questions → answered by SubLLM,
which picks the best option labels (fallback: leave pending for the human).

Interaction uses the documented `opencode serve` HTTP API (`/api/session`,
`/api/session/{id}/prompt`, `/api/permission/request` + reply,
`/api/question/request` + reply) — no TUI scraping, no extra dependencies.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_terminals.py -q` passes.
- [x] AC-02: `pytest tests/test_dashboard_logs.py -q` still passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
