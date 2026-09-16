# Ticket 149: Bound web dashboard shutdown so Ctrl+C cannot hang koru auto up --web

- **ID**: ticket-149
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

User session evidence (2026-09-16): `koru auto up --max-cycles 3 --web` hit
Ctrl+C and teardown deadlocked inside `_shutdown_web_dashboard`
(src/koru/autonomy/operator/operator_up.py:271):
`socketserver.BaseServer.shutdown()` blocks on `__is_shut_down.wait()` with no
timeout until the `serve_forever` loop exits. When that loop is stalled, the
interrupt hangs and only a second Ctrl+C (KeyboardInterrupt inside the finally
chain) recovers.

Fix: run `server.shutdown()`/`server.server_close()` on a helper daemon thread
joined with a 2s timeout, keeping the existing bounded join of the
`koru-serve-bg` serve thread (also a daemon). No serving, routing or port
behavior changes.

## Acceptance criteria

- [x] AC-01: `_shutdown_web_dashboard` returns within its bounded timeout even
      when `server.shutdown()` never completes (regression test with a blocking
      fake server).
- [x] AC-02: Normal teardown still calls `shutdown` then `server_close` and
      joins the serve thread with the existing 2s timeout; existing dashboard
      and serve suites stay green.

## Validation evidence

- `pytest tests/test_dashboard_logs.py tests/test_serve.py` — 65 passed;
  session governance gate GOV-PASS (0 errors, 0 warnings).
- `ruff check` on both changed files — clean.
- `python -m compileall` on both changed files — clean.
- `docker compose config -q` — clean.
- Standalone `./project/governance-check.sh` — GOV-PASS.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
