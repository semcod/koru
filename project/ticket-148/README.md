# Ticket 148: logs-tab-sse-reconnect-churn

- **ID**: ticket-148
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Fix the Logs tab loading slowly: the 5-second dashboard refresh re-created the
SSE `EventSource` on every cycle. Each reconnect made the server re-read and
re-parse the whole `nfo-events.jsonl` (~4.7 MB) and re-send 50 history entries,
while the re-render wiped the entries DOM — the tab never reached a stable live
state.

Fix: keep the existing open/connecting stream across refreshes, repopulate
displayed entries from the cached array after a re-render, dedupe history
re-sent on reconnect, and give the Logs tab a fast first paint (it does not
need the slow context/topology/config endpoints).

## Acceptance criteria

- [x] AC-01: `pytest tests/test_dashboard_logs.py -q` passes, including
  reconnect-guard regression tests.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
