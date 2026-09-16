# Ticket 146: dashboard-web-ws-log-streaming

- **ID**: ticket-146
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Add a `--web` flag to `koru auto up` that starts the dashboard HTTP server
(`koru serve`) in a background thread before the autonomous loop begins,
auto-opening the default browser. Add a WebSocket endpoint
(`/api/logs/stream`) to the dashboard that tails the autonomous log
(`.planfile/.koru/nfo-events.jsonl`) and the cycle log, streaming structured
log events with severity levels (ERROR, WARNING, INFO, DEBUG) to the
browser in real time. Add a "Logs" tab to the dashboard with live-stream
display and level filters.

## Acceptance criteria

- [ ] AC-01: `koru auto up --web` starts the dashboard server in a background
      thread and opens the browser before the autonomous loop runs.
- [ ] AC-02: Dashboard exposes `/api/logs/stream` WebSocket endpoint that
      streams structured log events with `level` field (error/warning/info/debug).
- [ ] AC-03: Dashboard "Logs" tab shows live log stream with level filter
      buttons (ERROR / WARNING / INFO / DEBUG) and auto-scroll.
- [ ] AC-04: Existing "Create ticket" NL form remains functional.
- [ ] AC-05: Tests cover the WS endpoint and the `--web` flag wiring.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
