# Planfile HTTP API — `curl` health (optional skip)

Starts **`uvicorn planfile.api.server:app`** (same pattern as the koru README)
and curls **`/health`**.

The shared example image installs **`fastapi`** alongside `planfile` because
`planfile.api.server` imports it. If import still fails in a custom image, the
script **exits 0** with a skip message so CI stays green.

## Run

```bash
./run-docker.sh
```

## Pairing with koru

When you run a real planfile API locally, `koru --watch --ws-url ws://localhost:8000/ws`
consumes WebSocket events — this example only covers the **HTTP `/health`**
smoke.
