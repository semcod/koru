# Ticket 151: serve-shutdown-sse-daemon-threads

- **ID**: ticket-151
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Ctrl+C on `koru auto up --web` / `koru serve` hangs in `server.shutdown()` /
`server_close()` because `ThreadingHTTPServer` defaults keep non-daemon
handler threads and `block_on_close=True`: an open `/api/logs/stream` SSE
connection (or any keep-alive request) blocks teardown forever. After the
forced kill the browser tab keeps polling a dead port, producing a flood of
`ERR_CONNECTION_REFUSED`.

Fix: a `DashboardHTTPServer` subclass with `daemon_threads=True`,
`block_on_close=False`, a `shutdown_event` observed by the SSE generator, and
`handle_error` that suppresses expected client-disconnect noise
(ConnectionResetError/BrokenPipeError).

SESSION_EXECUTION_AUTHORIZATION: user-reported incident log in session
(requested dashboard reliability for `koru auto --web`).

## Acceptance criteria

- [x] AC-01: `server.shutdown()` + `server_close()` return promptly with an
  open SSE client connected.
- [x] AC-02: SSE generator exits when the server shutdown event is set.
- [x] AC-03: Client disconnects no longer print socketserver tracebacks.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
