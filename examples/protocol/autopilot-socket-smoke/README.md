# Autopilot protocol — socket broker smoke (no IDE)

**What this shows**

- `koru autopilot doctor` and `koru autopilot ide-list` are safe in headless
  containers (no X11, no Cursor window).
- `koru autopilot --socket PATH daemon …` plus `status` / `shutdown` exercises
  the **Unix socket** protocol path without a real IDE plugin. Global `--socket`
  must appear **before** the subcommand (`daemon`, `status`, …).

**Limitation (by design)**

- `koru autopilot drive …` without `--direct` needs a running daemon **and**
  usually a connected plugin or a working injector (X11 / ydotool / …).
  This example **does not** validate typing into a real IDE chat panel.

## Run

```bash
./run-docker.sh
```
