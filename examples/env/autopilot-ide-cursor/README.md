# Env matrix — explicit `KORU_AUTOPILOT_IDE=cursor`

Shows how **`KORU_AUTOPILOT_IDE`** (when set to a concrete IDE slug, not `auto`)
overrides the `--autopilot-ide` CLI value inside `koru autonomous up`
(see `autonomous._resolve_autopilot_ide`).

This container has **no Cursor / VS Code UI**; the example still uses
`--no-autopilot` so nothing tries to drive a real IDE. The point is the
**configuration surface** you would set in CI or a wrapper script.

## Run

```bash
./run-docker.sh
```

## Compare with default

See `examples/ci/headless-autonomous-jsonl/` for the same smoke without forcing
`KORU_AUTOPILOT_IDE`.
