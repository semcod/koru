# Autodiagnostics and Auto-Repair

This page documents what Koru can diagnose automatically, what it can repair
automatically, and which commands a human operator should run.

## What is implemented

| Area | Status | Commands |
| --- | --- | --- |
| Project health doctor | implemented, read-only | `koru --doctor`, `koru --doctor --format json` |
| Guided project repair hints | implemented, read-only | `koru --doctor --fix`, `koru --doctor --fix --format json` |
| IDE / injector diagnostics | implemented | `koru autopilot doctor`, `koru autopilot doctor --fix` |
| Host injector auto-install | implemented for apt-based hosts | `koru autopilot setup-host --install` |
| IDE plugin/version management | implemented for VS Code family lanes | `koru autopilot manage --ide vscode`, `koru autopilot manage --ide vscode --fix` |
| Persistent daemon unit | implemented | `koru autopilot install-unit` + `systemctl --user enable --now koru-autopilot.service` |
| Idle diagnostic tickets | implemented | `koru autonomous safe-up` |
| Full IDE LLM reply capture | not implemented yet | tracked in the autopilot roadmap |
| Fully autonomous code repair without tickets / gates | not implemented intentionally | use queue, diagnostics, tests, and an IDE/LLM lane |

## Fast diagnostic sequence

Run these first when autonomy, queue execution, or IDE control feels stuck:

```bash
cd /path/to/project

koru --doctor
koru --doctor --format json

export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot status
koru autopilot manage --ide vscode
koru autopilot doctor --fix
koru autopilot ide-list
```

`koru --doctor` never writes to the repository. Its JSON output is intended for
LLM agents and CI wrappers.

`koru --doctor --fix` is also read-only. It prints the explicit repair commands
that may write to the host or project.

## Host and IDE auto-repair

For the autopilot channel, Koru already has guided and partially automated
repair:

```bash
# See missing keyboard / clipboard injector tools and human actions.
koru autopilot setup-host

# Preview apt changes.
koru autopilot setup-host --install --dry-run

# Install missing apt packages such as xdotool, wtype, or ydotool.
koru autopilot setup-host --install

# Install / reassert the VS Code-family extension and socket setting.
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot manage --ide vscode --fix --dry-run
koru autopilot manage --ide vscode --fix

# Install a user-level daemon unit.
koru autopilot install-unit
systemctl --user daemon-reload
systemctl --user enable --now koru-autopilot.service
```

After that, verify the active socket and plugin path:

```bash
KORU_AUTOPILOT_INSTANCE=vscode koru autopilot status
KORU_AUTOPILOT_INSTANCE=vscode koru autopilot manage --ide vscode
KORU_AUTOPILOT_INSTANCE=vscode koru autopilot drive \
  --ide vscode --require-plugin --prompt "KORU smoke test"
```

If `drive` returns `ok=true`, `backend=plugin`, and `delivered=true`, the Koru
daemon reached the IDE plugin. `submitted=false` means the IDE/plugin did not
confirm the final chat submit.

`manage` reports `connected/version`, `installed`, and `expected`. If
`installed=expected` but `connected=False`, installation is healthy and the IDE
runtime handshake is missing: start the daemon, reload the IDE window, and run
`koru: Connect autopilot daemon`. Set `KORU_STRICT_PLUGIN_VERSION=1` to block
drive through stale live plugins.

## Autonomous diagnostic tickets

Koru can turn failed diagnostics into planfile tickets. This is the current
safe auto-repair pattern: diagnose, create a deduplicated ticket, let the queue
and IDE/LLM lane handle the actual edit, then validate with tests.

Safe one-cycle diagnostic pass:

```bash
koru autonomous safe-up --project .
```

`safe-up` expands to a one-cycle queue-only diagnostic run:
`--ticket-sources queue`, `--idle-diagnostics quick`, `--diagnostic-tickets`,
`--autopilot-action off`, `--no-autopilot`, `--no-semcod-artifacts`, and
`--max-cycles 1`. Extra flags after `safe-up` still override normal `up`
options where argparse supports it.

Longer supervised loop:

```bash
koru autonomous up \
  --project . \
  --ticket-sources queue \
  --idle-diagnostics quick \
  --diagnostic-tickets \
  --keep-waiting-input \
  --autopilot-on-idle-only \
  --scan-skip-if-clean \
  --no-semcod-artifacts \
  --sleep-seconds 60 \
  --autopilot-ide vscode
```

Avoid starting a bare `koru autonomous up` in a production project unless you
really want `scan + all queues + autopilot` with the default iteration limit.
For smoke tests, prefer `--max-cycles 1`, `--ticket-sources queue`, and a test
queue or fixture project.

## Reset diagnostic dedup markers

When a diagnostic issue has been fixed and you want Koru to create fresh
diagnostic tickets again:

```bash
task queue:autoloop:reset-diag-markers
task queue:autoloop:reset-diag-markers CLOSE_TICKETS=true
```

## Recommended operator checklist

1. Run `koru --doctor --fix`.
2. Run `koru autopilot doctor --fix`.
3. Repair host tools with `koru autopilot setup-host --install --dry-run`, then
   `koru autopilot setup-host --install` if the preview is acceptable.
4. Reassert the IDE plugin with `koru autopilot manage --ide vscode --fix`.
5. Start or reassert the daemon with `koru autopilot install-unit` and
   `systemctl --user enable --now koru-autopilot.service`, or run
   `koru autopilot daemon --project "$(pwd)"` in a terminal.
6. Smoke test `koru autopilot drive --ide vscode --require-plugin`.
7. Use `koru autonomous up` with explicit safety flags for longer sessions.
