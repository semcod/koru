# Headless CI — autonomous + JSONL

Demonstrates a **non-interactive** autonomous smoke run suitable for CI:

- `koru autonomous up` with `--no-autopilot` (no IDE control)
- `--emit-events jsonl` for structured stdout (stderr keeps human hints)
- `--ticket-sources queue` and `--max-cycles 1` for a bounded run

## Run (from this directory)

```bash
./run-docker.sh
```

## Run (from koru repository root)

```bash
docker compose -f examples/ci/headless-autonomous-jsonl/docker-compose.yml build
docker compose -f examples/ci/headless-autonomous-jsonl/docker-compose.yml run --rm e2e
```

Build context is always the **koru repo root** so the image installs koru from source.
