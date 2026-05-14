# Koru examples (Docker E2E)

Each runnable sample lives under **`examples/<category>/<name>/`** and ships:

- **`README.md`** — what is being demonstrated and known limits
- **`e2e.sh`** — non-interactive smoke (copied into the image at build time)
- **`docker-compose.yml`** — isolated build (`context` = koru repo root)
- **`run-docker.sh`** — local wrapper around `docker compose build && run`

Shared image layers are defined once in **`examples/docker/koru-e2e.Dockerfile`**
( `python:3.12-slim`, editable `pip install -e .`, plus `planfile` and `uvicorn`).

The large flat pipeline sample **`examples/bootstrap.planfile.yaml`** stays at its
historic path (referenced from CLI help and docs).

## Index

| Path | One-line purpose |
|------|------------------|
| `examples/ci/headless-autonomous-jsonl` | CI-style `koru autonomous up` with `--no-autopilot` + NDJSON events |
| `examples/env/autopilot-ide-auto` | `KORU_AUTOPILOT_IDE=auto` does not override explicit `--autopilot-ide` |
| `examples/env/autopilot-ide-cursor` | `KORU_AUTOPILOT_IDE=cursor` overrides CLI when CLI uses `auto` |
| `examples/protocol/autopilot-socket-smoke` | Autopilot daemon + `status` + `shutdown` on a Unix socket (no IDE) |
| `examples/planfile/queue-cli-dryrun` | `koru --queue --dry-run` + `planfile --version` (no HTTP server) |
| `examples/planfile/http-api-curl` | `uvicorn planfile.api.server:app` + `curl /health` (skips if API layout missing) |
| `examples/runtime/koru-serve-health` | `koru serve --no-open` + `curl /health` |

## Run all (from repo root)

```bash
./examples/run-e2e.sh
```

If `docker` is not installed, the script **exits 0** so optional CI jobs can reuse
it without failing non-Docker hosts.

## Run one example

```bash
./examples/ci/headless-autonomous-jsonl/run-docker.sh
```

Equivalent manual invocation:

```bash
docker compose -f examples/ci/headless-autonomous-jsonl/docker-compose.yml build
docker compose -f examples/ci/headless-autonomous-jsonl/docker-compose.yml run --rm e2e
```
