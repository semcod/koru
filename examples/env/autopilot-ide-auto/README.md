# Env matrix — `KORU_AUTOPILOT_IDE=auto`

When `KORU_AUTOPILOT_IDE` is **`auto`** (or unset), it does **not** override the
`--autopilot-ide` CLI flag — the explicit CLI value (`cursor` in the script) is
used for autopilot targeting.

Compare with `examples/env/autopilot-ide-cursor/`, where the environment is set
to a **non-auto** slug and therefore **wins** over CLI `auto`.

## Run

```bash
./run-docker.sh
```
