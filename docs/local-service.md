# koru local HTTP hub (`koru local-serve`)

## Purpose

koru stays **project-local** and usually talks to your IDE over the **autopilot Unix socket**
(request/response for driving the chat, typing, audits). Some tools are easier over **HTTP**
on the same machine: shell scripts, `curl`, small daemons, or a future MCP bridge. This command
starts a **tiny, stdlib-only** server that accepts JSON events and exposes them as **NDJSON**
for trivial `curl` pipelines.

It does **not** replace the socket: the socket remains the structured control plane for IDE
plugins; the HTTP hub is an optional **same-host side channel** for fire-and-forget work items
and observability-style dumps.

## Bind address and port

- **Default host:** `127.0.0.1` (override with `--host` or `KORU_LOCAL_SERVICE_HOST`).
- **Default port:** `18766` if neither CLI nor env sets a port — chosen to stay clear of
  `koru serve`’s default **8765**.
- **Ephemeral port:** pass `--port 0` (or set `KORU_LOCAL_SERVICE_PORT=0`). The OS assigns a
  free port; the process prints the resolved URL on startup.
- **Ring size:** `KORU_LOCAL_SERVICE_MAX_EVENTS` or `--max-events` (default **256**, hard cap
  **10000**). Oldest entries are dropped when full. **No disk persistence** in v1.

## Security

The service is meant for **loopback-only** use. Binding to `0.0.0.0` or a non-local address
would expose the hub to your network — **do not** unless you add your own access controls.
There is no authentication; anyone who can open the TCP port can POST events.

## Endpoints

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/health` | `{"ok": true, "version": "<koru package version>"}` |
| `POST` | `/event` or `/enqueue` | Body: JSON **object** (max ~64 KiB). Appends `id`, `received_at`, `payload`. Returns `{"id": "…"}`. |
| `GET` | `/events` | All buffered records, **NDJSON** (`application/x-ndjson`), one JSON object per line. |

## Run

```bash
koru local-serve --port 0
# or
python -m koru local-serve --port 0
```

Examples:

```bash
curl -sS "http://127.0.0.1:18766/health"
curl -sS -X POST "http://127.0.0.1:18766/event" \
  -H 'Content-Type: application/json' \
  -d '{"kind":"note","text":"from script"}'
curl -sS "http://127.0.0.1:18766/events"
```

## Tests

```bash
cd /path/to/koru && python -m pytest tests/test_local_service.py -q
```
