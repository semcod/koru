# koru local manager (`koru local-serve`)

## Purpose

koru stays **project-local** and usually talks to your IDE over the **autopilot Unix socket**
(request/response for driving the chat, typing, audits). Some tools are easier over **HTTP**
on the same machine: shell scripts, `curl`, small daemons, or a future MCP bridge. This command
starts a **tiny, stdlib-only** local manager that gives all koru versions one loopback entrypoint,
one event stream, one action queue, and one worker lifecycle policy.

It does **not** replace the socket: the socket remains the structured control plane for IDE
plugins; the local manager is the same-host service surface for fire-and-forget work items,
queue leasing, worker registration, and lifecycle decisions such as `continue`,
`drain-and-exit`, and `quarantine`.

## Bind address and port

- **Default host:** `127.0.0.1` (override with `--host` or `KORU_LOCAL_SERVICE_HOST`).
- **Default port:** `18766` if neither CLI nor env sets a port; this stays clear of
  `koru serve`'s default **8765**.
- **Ephemeral port:** pass `--port 0` (or set `KORU_LOCAL_SERVICE_PORT=0`). The OS assigns a
  free port; the process prints the resolved URL on startup.
- **Ring size:** `KORU_LOCAL_SERVICE_MAX_EVENTS` or `--max-events` (default **256**, hard cap
  **10000**). Oldest events and in-memory queue entries are dropped when full. **No disk
  persistence** in v1.

## Security

The service is meant for **loopback-only** use. Binding to `0.0.0.0` or a non-local address
would expose the manager to your network; do that only with your own access controls. There is
no authentication; anyone who can open the TCP port can POST events and queue work.

## Model

- **Event bus:** `POST /event` appends JSON to the in-memory event buffer; `GET /events`
  streams the buffer as NDJSON.
- **Action queue:** `POST /enqueue` appends the same JSON payload to the single local action
  queue. The payload may declare `type`, `action`, or `kind`; capability requirements can be
  listed under `requires`, `required_capabilities`, or `capability`.
- **Worker lifecycle:** versioned workers call `POST /workers/register` and then
  `POST /workers/heartbeat`. The manager chooses the newest healthy worker as active. Older
  healthy workers receive `drain-and-exit`; unhealthy workers receive `quarantine`.

This is intentionally a manager, not a package installer. Install/uninstall code should enqueue
typed actions and let a worker with the right capability claim them. That keeps self-upgrade
policy outside the worker that is currently doing work.

## CLI worker integration

`koru --queue` and `koru autopilot daemon` can register themselves with this manager. The client
side is **best-effort and opt-in** so short CLI invocations and tests do not wait on a localhost
connection when no manager is running.

Enable it with one of:

```bash
export KORU_LOCAL_MANAGER_URL=http://127.0.0.1:18766
# or
export KORU_LOCAL_MANAGER_ENABLED=1
```

When enabled:

- `koru --queue` registers as a `koru.queue` worker, tries to claim queued actions of type
  `koru.queue`, `koru.queue.run`, or `planfile.queue.run`, heartbeats after each iteration, and
  stops after the current iteration when the manager returns `drain-and-exit` or `quarantine`.
- `koru autopilot daemon` registers as `koru.autopilot.daemon`, starts a lightweight heartbeat,
  and calls `stop()` on itself when a later manager decision asks it to drain or quarantine.
- If a manager action was claimed, the worker completes that action with `completed` or `failed`
  after the local CLI run finishes.

## Endpoints

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/health` | `{"ok": true, "version": "<koru package version>", "service": "koru-local-manager", "active_worker_id": "...", "queue_counts": {...}}` |
| `POST` | `/event` | Body: JSON **object** (max ~64 KiB). Appends `id`, `received_at`, `payload`. Returns `{"id": "..."}`. |
| `POST` | `/enqueue` | Appends an event and one queue item. Returns `{"id": "...", "status": "queued", "item": {...}}`. |
| `GET` | `/events` | All buffered records, **NDJSON** (`application/x-ndjson`), one JSON object per line. |
| `GET` | `/queue` | Queue snapshot with `items` and `counts`. |
| `POST` | `/queue/claim` | Body: `{"worker_id": "...", "capabilities": [...], "action_types": [...], "lease_seconds": 300}`. Returns the first compatible queued item as `leased`, or `idle`. |
| `POST` | `/queue/complete` | Body: `{"action_id": "...", "worker_id": "...", "status": "completed"}`. Status can be `completed`, `failed`, or `canceled`. |
| `GET` | `/workers` | Active worker id plus all registered workers. |
| `POST` | `/workers/register` | Register or update a worker with `worker_id`, `version`, `capabilities`, `health`, `pid`, `path`. Returns worker state and decision. |
| `POST` | `/workers/heartbeat` | Update worker health/capabilities/conflict flag. Returns the current lifecycle decision. |
| `POST` | `/lifecycle/decision` | Alias for heartbeat-style lifecycle checks. |
| `GET` | `/state` | Combined queue and worker snapshot. |

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
curl -sS -X POST "http://127.0.0.1:18766/enqueue" \
  -H 'Content-Type: application/json' \
  -d '{"type":"upgrade","package":"koru","requires":["installer"]}'
curl -sS -X POST "http://127.0.0.1:18766/workers/register" \
  -H 'Content-Type: application/json' \
  -d '{"worker_id":"koru-0.1.168","version":"0.1.168","capabilities":["installer"],"health":"ok"}'
curl -sS -X POST "http://127.0.0.1:18766/queue/claim" \
  -H 'Content-Type: application/json' \
  -d '{"worker_id":"koru-0.1.168","capabilities":["installer"],"action_types":["upgrade"],"lease_seconds":300}'
curl -sS "http://127.0.0.1:18766/events"
```

## Tests

```bash
cd /path/to/koru && python -m pytest tests/test_local_service.py -q
```
