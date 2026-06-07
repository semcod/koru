# koru autopilot — quickstart

> Drive your IDE's LLM chat from a terminal. Type into Cascade /
> Copilot Chat / Cursor / JetBrains AI Assistant with one command,
> from anywhere — another tmux pane, another TTY, even SSH.
>
> Architecture: [`autopilot-design.md`](./autopilot-design.md) ·
> Roadmap: [`autopilot-roadmap.md`](./autopilot-roadmap.md)

---

## 30-second start

```bash
# 0. choose the IDE instance when several editors are open
export KORU_AUTOPILOT_INSTANCE=vscode

# 1. (one-time, in any terminal) start the daemon
koru autopilot daemon --project "$(pwd)"

# 2. (from any terminal, even another tmux pane)
koru autopilot drive --ide vscode 'continue with the next ticket'
```

That's it. The text appears in your IDE's chat box and is submitted
automatically. If your IDE has the koru-autopilot extension installed,
the daemon will also type the next ticket brief back into the chat the
moment Cascade/Copilot signals it has finished its turn.

## After `koru autonomous up` (operator checklist)

Long-running autonomy prints a block **`co zrobić teraz (operator IDE)`** after
the autopilot daemon starts. Do this in the **same IDE** shown in the log
(`autopilot IDE=…`, `autopilot socket → …`):

1. Open the project root in Cursor / VS Code (not terminal-only).
2. Reload the window after `task koru:mcp:bootstrap`; enable MCP server **koru**.
3. Command Palette → **`koru: Connect autopilot daemon`** → status bar **`koru: on`**.
4. Set `koruAutopilot.socketPath` to the socket from the log (or leave empty and
   `export KORU_AUTOPILOT_INSTANCE=<ide>` in the shell).
5. Verify: `koru autopilot status` → **`plugins` must not be `[]`**.
   Then run `koru autopilot manage --ide <ide>` and check
   `connected/version`, `installed`, and `expected`.
6. Test: `koru autopilot drive --ide <ide> --require-plugin 'probe test'` →
   `ok: true` with `winning_*` fields (not `backend: ydotool`).

If `plugins` stays empty, run the IDE bridge doctor (replaces manual log hunting):

```bash
export KORU_AUTOPILOT_INSTANCE=cursor   # same lane as koru auto
koru ide doctor --ide cursor --fix --gc-sockets
koru autopilot status --explain
```

**Cursor 3.5+ / VS Code 1.105+:** VSIX install alone may not activate the extension
until you **Trust Publisher `semcod`** (Extensions panel → koru autopilot → Trust
Publisher) and **Reload Window**. `koru ide doctor` detects missing
`extensions.trustedPublishers` and can add `semcod` automatically when Cursor is
closed (`--fix`).

Use `--require-plugin` on drive while debugging so you never silently fall back to
keyboard injection.

See also: [`refactor/ide-bridge-2026.md`](./refactor/ide-bridge-2026.md).

If `installed=expected` but `connected=False`, the plugin is installed correctly
and only the runtime handshake is missing: start the daemon, reload the IDE
window, and run **`koru: Connect autopilot daemon`**. If the live `version`
differs from `expected`, re-run `koru autopilot manage --ide <ide> --fix` and
reload the IDE. Set `KORU_STRICT_PLUGIN_VERSION=1` when you want `drive` to
fail fast on stale live plugins instead of accepting a best-effort `message.sent`.
Strict mode is fail-closed: if the daemon cannot determine the expected plugin
version, plugin `drive` is blocked.

Monorepo guide: `maskservice/c2004/docs/autonomy-ide-cursor.md` (section *Po starcie*).

## Multiple IDE windows on one machine

Several editors can run koru against the **same** git checkout. Use
**different** automation endpoints so daemons and chat injection do not
fight each other:

| Concern | Mitigation |
|--------|------------|
| **Autopilot Unix socket** | Default is one socket per login (`$XDG_RUNTIME_DIR/koru-autopilot.sock`). Set **`KORU_AUTOPILOT_INSTANCE`** to a unique label per IDE window (e.g. `cursor-main`, `windsurf-2`); the socket becomes `koru-autopilot-<label>.sock`. Or set **`KORU_AUTOPILOT_SOCKET`** to an absolute path per instance. |
| **Planfile queue** | Koru takes an exclusive **`flock`** on `.planfile/.koru/queue-runner.lock` while running `run_next_planfile_task` (POSIX). A second drain **waits** instead of stealing the same ticket. Set **`KORU_QUEUE_RUNNER_LOCK=0`** only if you accept duplicate work. |
| **Ticket ownership** | Before `ticket start`, koru runs **`planfile ticket claim --assigned-to <actor> --lease-seconds …`**. Give each lane a distinct **`--actor`** name so ownership is visible. Tune lease with **`KORU_TICKET_LEASE_SECONDS`** (default 3600, clamped). |
| **Shell per lane** | Run `eval "$(koru agent --env-exports --lane cursor)"` (or `--agent cursor`) in each IDE terminal. For JSON (CI), use `koru agent --env-json --lane windsurf`. |

Helper script for strict IDE+instance binding:

```bash
# bind current shell to one lane
eval "$(koruenv env cursor cursor-main)"

# run one command in a pinned lane (without changing current shell)
koruenv run cursor cursor-main -- koru autopilot status --explain
```

Ergonomic shell shortcuts (source once per shell):

```bash
source scripts/koru-autopilot-lanes.sh
lane:cursor
lane:status
lane:run -- koru autopilot status --explain
```

PowerShell equivalent:

```powershell
koruenv env cursor cursor-main --shell powershell | Invoke-Expression
koruenv status cursor cursor-main
```

## What gets installed where

| Piece                              | Lives in                                            | Purpose                                  |
|------------------------------------|-----------------------------------------------------|------------------------------------------|
| `koru autopilot` CLI               | already in `pip install koru`                       | daemon + client + diagnostics            |
| VS Code / VSCodium / Windsurf / Cursor plugin | `plugins/koru-autopilot-vscode/` (this repo)        | preferred chat injection path            |
| JetBrains plugin                   | `plugins/koru-autopilot-jetbrains/` (stub, Phase 3) | currently keyboard-sim fallback only     |
| Keyboard backends                  | system packages (`xdotool` / `wtype` / `ydotool`)   | fallback when no plugin is loaded        |
| **OS injector (X11)**              | ``xdotool`` + ``.koru/ide-os-injector.json``         | optional click-to-focus chat before typing |

### OS injector (X11 coordinates)

When no autopilot plugin is connected, the daemon can use a **calibrated**
coordinate profile (window id + chat click point) before typing, instead of
blind ``xdotool type`` into whatever window is focused.

Config is merged JSON keyed by IDE id (``cursor``, ``windsurf``, ``vscode``,
…). Search order:

1. ``<daemon --project>/.koru/ide-os-injector.json``
2. ``$PWD/.koru/ide-os-injector.json``
3. ``~/.koru/ide-os-injector.json``

``koru autopilot drive --direct`` uses the same search (pass ``--project DIR``
to prepend ``DIR/.koru/…`` like ``koru autopilot daemon --project``).

**One command across IDEs (``--ide auto``, default):** ``koru autopilot drive --direct``
auto-selects the first IDE that has a saved profile in ``ide-os-injector.json``,
in order: **integrated terminal host** (``CURSOR_*`` / ``VSCODE_PID`` / parent walk)
→ **focused window** (X11) → **running match** → other detected editors.
When the terminal is Cursor but only Windsurf is calibrated, selection stays on
Cursor (``auto:terminal-no-profile``) instead of injecting Windsurf coordinates.
The CLI prints ``auto-selected <id> (…)`` on stderr. You do not need
``--os-profile windsurf`` unless the profile key must differ from the auto pick.
``koru autopilot calibrate --ide auto`` uses the same resolution before capture.

Behaviour:

- Profiles store only ``chat_x`` / ``chat_y`` (calibrate with the pointer over the chat input).
  No ``window_id`` is used for targeting (legacy keys in JSON are ignored).
- If a profile exists for the resolved IDE and ``xdotool`` is on ``PATH``, that path runs automatically.
- ``KORU_OS_INJECTOR_FOCUS=click`` (default): move, then left-click to focus; ``return``: move, then Return (no click).
- ``KORU_OS_INJECTOR_INPUT=auto`` (default): paste via ``xclip``/``xsel`` + Ctrl+V when available, else ``xdotool type``; set ``type`` or ``paste`` to force.
- ``KORU_OS_INJECTOR_POST_FOCUS_DELAY`` (seconds, default ``0.12``): sleep after the focus click/Return before paste/type; Electron chat fields often need this. Set ``0`` to disable.
- Set ``KORU_OS_INJECTOR=0`` to disable and always use the plain keyboard injector.
- On **Wayland**, a saved profile in ``ide-os-injector.json`` is used automatically
  (after ``calibrate``). Without a profile, ``drive --direct`` falls back to
  ``ydotool``/``wtype`` into whichever window has focus — click the IDE chat first.
- ``KORU_OS_INJECTOR_DRY_RUN=1`` logs the planned injection without running ``xdotool``.

Injection uses ``xdotool`` (X11 / XWayland). On Wayland, ``koru autopilot drive``
may still use the keyboard injector unless ``KORU_OS_INJECTOR=1`` — many setups
still run IDE windows under XWayland, so forcing the profile is opt-in. For a
full calibration workflow in a monorepo, see the c2004 doc
``.koru/workflows/ide-os-injector.md`` and ``task koru:ide-os:calibrate``.

## Full setup checklist

### 1. Verify your machine has at least one injection backend

```bash
koru autopilot doctor
koru autopilot doctor --fix
```

If you want guided host remediation (including optional apt auto-install
for missing `xdotool`/`wtype`/`ydotool` on Debian/Ubuntu), run:

```bash
koru autopilot setup-host
koru autopilot setup-host --install --dry-run
koru autopilot setup-host --install

# inspect and repair plugin/socket/version state for the target IDE
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot manage --ide vscode
koru autopilot manage --ide vscode --fix --dry-run
koru autopilot manage --ide vscode --fix
```

Expected output looks like:

```
session: wayland
selected backend: ydotool
backends:
  ✗ xdotool    requires x11 session, current is 'wayland'
  ✓ ydotool    /usr/bin/ydotool
  ✓ wl-copy    /usr/bin/wl-copy
  ...
running IDEs (3):
  · Windsurf (pid=56097)
  · Cursor (pid=387966)
  · JetBrains IDE (pid=1357647)
```

The doctor exits **0** when at least one backend is usable.
If everything is `✗`, install one of:

| Session  | Install                                | Notes                                |
|----------|----------------------------------------|--------------------------------------|
| X11      | `sudo apt install xdotool`             | most reliable, no extra setup        |
| Wayland (sway/Hyprland) | `sudo apt install wtype`  | no permissions needed                |
| Wayland (GNOME / KDE)   | `sudo apt install ydotool` + start `ydotoold` service | needs uinput / a daemon — see below |

#### ``wtype`` and “Compositor does not support the virtual keyboard protocol”

``wtype`` talks to the Wayland **virtual-keyboard-v1** protocol. **Mutter (GNOME),
many KDE sessions, and several other compositors do not expose it**, so you can
get:

```text
Compositor does not support the virtual keyboard protocol
```

That is expected on those desktops — ``wtype`` is not broken; the compositor
simply does not offer that API. Prefer **ydotool** (above), run the IDE on
**XWayland** so ``xdotool`` / the OS-injector path can work, or use the **koru
autopilot editor extension** (best on Wayland).

#### ydotool one-time setup (Wayland on GNOME/KDE)

`ydotool` writes to `/dev/uinput`, which is root-only by default.
Either:

```bash
# (a) run ydotoold as your user with a setuid socket
sudo systemctl enable --now ydotool        # ships with apt package
sudo usermod -aG input "$USER"             # then log out / log in once
```

or

```bash
# (b) chmod the device — quickest, less safe (resets on reboot)
sudo chmod 0660 /dev/uinput
sudo chgrp input /dev/uinput
```

Re-run `koru autopilot doctor` until `ydotool` is `✓`.

### 2. Start the daemon

```bash
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot daemon --project "$(pwd)"
```

Leave it running. The daemon binds a unix socket at
`$XDG_RUNTIME_DIR/koru-autopilot-<instance>.sock` when
`KORU_AUTOPILOT_INSTANCE` is set, otherwise `$XDG_RUNTIME_DIR/koru-autopilot.sock`
(mode `0600`, same-UID only).
It prints one line per event so you can watch what is happening:

```
koru autopilot daemon: listening on /run/user/1000/koru-autopilot.sock
koru autopilot daemon: handoff enabled for project=/home/tom/work/myproj
plugin connected: ide=windsurf version='0.1.0'
event session.ended ide=windsurf chat=cascade reason='user-stop'
handoff → plugin/windsurf (5388 chars)
```

To run it in the background once you trust it:

```bash
nohup koru autopilot daemon --project "$(pwd)" >/tmp/koru-autopilot.log 2>&1 &
```

(`nohup` works, but the `systemd --user` unit below is the recommended
long-running setup.)

#### Recommended: install a `systemd --user` unit (P2.6)

```bash
koru autopilot install-unit
systemctl --user daemon-reload
systemctl --user enable --now koru-autopilot.service
journalctl --user -u koru-autopilot -f
```

This keeps the daemon alive across terminal closes and user logins.
The generated unit defaults to `--idempotent --no-handoff`; if you want
automatic handoff for a specific project, override `ExecStart` via:

```bash
systemctl --user edit koru-autopilot.service
```

### 3. Install or reassert the VS Code / VSCodium / Windsurf / Cursor plugin

The plugin makes injection 100 % reliable (no focus-stealing race) and
emits `session.ended` events that drive the auto-handoff.

#### Fastest path — use `manage`

```bash
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot manage --ide vscode --fix --dry-run
koru autopilot manage --ide vscode --fix
```

Verify:

```bash
code --list-extensions --show-versions | grep semcod.koru-autopilot-vscode
koru autopilot manage --ide vscode
```

`manage` reports three version layers:

- `connected` / `version` — live plugin attached to the daemon,
- `installed` — extension version from the editor CLI,
- `expected` — bundled VSIX/package version in the koru checkout.

After `--fix`, reload the IDE window and run **`koru: Connect autopilot daemon`**
from the Command Palette.

#### Developer fallback — build a `.vsix` manually

```bash
cd plugins/koru-autopilot-vscode
npm install
npm run package

code --install-extension koru-autopilot-*.vsix --force
windsurf --install-extension koru-autopilot-*.vsix --force
cursor --install-extension koru-autopilot-*.vsix --force
```

#### Alternative — run from source (no packaging)

```bash
cd plugins/koru-autopilot-vscode
npm install && npm run compile
code     --extensionDevelopmentPath="$(pwd)"
windsurf --extensionDevelopmentPath="$(pwd)"
cursor   --extensionDevelopmentPath="$(pwd)"
```

A status bar item `🔌 koru: on` appears in the bottom-right when the
plugin successfully connects to the daemon.

> JetBrains plugin: stub only — see [`autopilot-roadmap.md`](./autopilot-roadmap.md).
> JetBrains users get keyboard-sim through `ydotool`.

### 3b. `coru calibration` (works from IDE integrated terminal)

[`coru calibration`](../packages/coru/README.md) runs the same end-to-end
plugin probe as step 4 below, but chains socket alignment, optional testql
preflights, and a strict `drive --require-plugin` in one command. Use it
after reloading the IDE window or upgrading a VSIX.

```bash
export KORU_AUTOPILOT_INSTANCE=antigravity   # or cursor, vscode, windsurf, …
coru calibration --skip-desktop --skip-bridge   # plugin-only probe (recommended on Wayland)
coru calibration                                # full preflight (desktop is advisory)
```

Success ends with `calibration: PASS — focus/paste/submit path verified`.
Desktop `DESKTOP_*` steps may fail on GNOME/Wayland (wmctrl cannot see Electron
titles) — that does **not** block the plugin probe. Templates live in
`testql-scenarios/{ide}-desktop-calibration.oql` and are materialized under
`.planfile/.koru/`. See also [`docs/README.md`](./README.md).

### 4. Verify end-to-end

```bash
# from a second terminal
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot status
koru autopilot manage --ide vscode
koru autopilot drive --ide vscode --require-plugin 'hello from koru'
```

`drive` should produce JSON with `"ok": true` and one of:
- `"backend": "stub"` / `"backend": "ydotool"` etc. → keyboard-sim path was used,
- `"delivered": true` → the plugin injected via its own API.

To force exact live plugin version matching:

```bash
KORU_STRICT_PLUGIN_VERSION=1 koru autopilot drive --ide vscode --require-plugin \
  'strict version probe'
```

## Common pitfalls (read these before filing a bug)

### "daemon not running"

`koru autopilot drive` requires either a running daemon or `--direct`:

```bash
koru autopilot drive --direct 'inject from this terminal only'
```

`--direct` skips the daemon entirely and uses keyboard-sim. It is
useful for one-off scripts, but loses the plugin path and the
handoff cooldown.

### Daemon was killed but the socket file lingers

Symptoms: `cannot remove stale socket … Permission denied`.

```bash
rm "$XDG_RUNTIME_DIR/koru-autopilot-vscode.sock"      # or wherever your socket is
koru autopilot daemon
```

(The daemon does this automatically when it owns the file, but a
hard kill from a different user / container can leave a stray.)

### Keyboard-sim types into the wrong window

Two causes:
1. **Wayland focus stealing** — some compositors refuse focus changes
   from a CLI tool. Mitigation: install the IDE plugin (the plugin
   path doesn't touch focus).
2. **Multiple IDEs running** — pass `--ide` to disambiguate:
   ```bash
   koru autopilot drive --ide vscode --require-plugin 'rerun failing test'
   ```
   `koru autopilot ide-list` shows everything detected.

### Auto-handoff loops on me

If `session.ended` fires every time we type (because the LLM emits
"done" immediately), we have a cooldown to break the loop:

```bash
koru autopilot daemon --handoff-cooldown 10   # seconds (default: 2)
```

Bumping the cooldown to 10 s is safe; the only cost is a slower
takeover after an *intentional* session end.

Or disable the takeover entirely:

```bash
koru autopilot daemon --no-handoff
```

In that mode the daemon still routes `drive` requests but ignores
session events.

### Submit goes to the wrong key in JetBrains

JetBrains AI Assistant uses `Ctrl+Enter`; we ship a per-IDE keymap
for this in `injector.py:_SUBMIT_KEY`. If a future JetBrains version
changes the binding, override the IDE id when driving:

```bash
koru autopilot drive --no-submit 'paste only, I will press enter myself'
```

### Multi-line text gets submitted prematurely

`xdotool` and `wtype` send a real `Enter` for every newline in the
text, which most chat panels treat as "submit". Workarounds:

```bash
# (a) use --no-submit and press Ctrl+Enter yourself when ready
koru autopilot drive --no-submit "$(cat my-prompt.md)"

# (b) pipe through the plugin path; the plugin uses paste + submit
#     (one Enter at the end), which is what you almost always want.
```

The plugin path is the long-term answer; install the extension.

## CLI cheat-sheet

```bash
koru autopilot daemon                # start the broker
koru autopilot daemon --no-handoff   # broker without auto-takeover
koru autopilot daemon --idempotent   # exit 0 if already running

koru autopilot drive 'text'          # send through daemon (preferred)
koru autopilot drive --prompt 'TAK'  # same, explicit string (shell-friendly)
koru autopilot drive --direct 'x'    # skip daemon, inject locally
koru autopilot drive --dry-run 'y'   # print what would happen, no keystrokes
koru autopilot drive --ide vscode --require-plugin 'z'   # force target IDE/plugin

koru autopilot status                # daemon health + connected plugins
koru autopilot manage --ide vscode   # binary/socket/plugin version inventory
koru autopilot manage --ide vscode --fix --dry-run
koru autopilot manage --ide vscode --fix
koru autopilot ide-list              # IDEs detected on /proc
koru autopilot doctor                # backend availability
koru autopilot doctor --fix          # print guided next steps
koru autopilot doctor --format json  # machine-readable

koru autopilot setup-host            # guided host readiness report
koru autopilot setup-host --install --dry-run
koru autopilot setup-host --install
KORU_STRICT_PLUGIN_VERSION=1 koru autopilot drive --ide vscode --require-plugin 'probe'

koru autopilot shutdown              # ask the daemon to stop

# P2.6 — systemd --user installation helper
koru autopilot install-unit
koru autopilot install-unit --print
koru autopilot install-unit --force

# P2.5 — one-shot brief injection (build koru brief + type into chat)
koru autopilot handoff               # uses cwd as project
koru autopilot handoff --project ~/path/to/repo --ide windsurf
koru autopilot handoff --dry-run     # print the brief, don't drive

# P2.7/P2.8 — persistent audit log
koru autopilot tail                  # last 20 entries, human-readable
koru autopilot tail -n 100           # more entries
koru autopilot tail --format json    # machine-readable
```

## Audit log

Every injection request, plugin handshake, handoff, and shutdown is
appended as one NDJSON line to
`$XDG_STATE_HOME/koru/autopilot.log` (defaults to
`~/.local/state/koru/autopilot.log`). The file is `0600`, the
directory is `0700`, and the file rotates at 10 MiB with 5 archived
backups.

Example entry:

```json
{"ts":"2026-05-11T18:36:05.327Z","event":"drive","ide":"windsurf",
 "backend":"plugin","chars":29,"submit":true,"ok":true}
```

`koru autopilot tail` is the convenience renderer — use `--format json`
if you'd rather pipe to `jq`. The schema is append-only, so future
fields land alongside the existing ones without breaking old tail
output.

## Configuration (`~/.config/koru/autopilot.toml`)

The config file is **optional**. Without it, autopilot uses safe
built-in defaults: `Return` for VS Code / VSCodium / Windsurf / Cursor / Zed,
`ctrl+Return` for JetBrains.

You only need to write a config if you want to override the submit
shortcut for an IDE or teach autopilot about a new one.

```toml
# ~/.config/koru/autopilot.toml

[submit_keys]
# IDE id matches what `koru autopilot ide-list` prints.
windsurf  = "Return"
vscode    = "Return"
cursor    = "Return"
jetbrains = "ctrl+Return"
# Adding a new editor only requires this line — no code change:
fleet     = "alt+Return"
```

Rules:

- Missing file → defaults, silently.
- Malformed TOML → defaults + one warning on stderr (autopilot **never
  crashes** because of a bad config).
- Non-string values inside `[submit_keys]` are ignored.
- Multi-modifier combos (e.g. `"ctrl+shift+Return"`) are rejected at
  injection time with a clear error — only `Mod+Key` is supported by
  the keyboard backends today (R3).

The config is loaded once per process and cached. If you edit the file
while the daemon is running, restart the daemon (`koru autopilot
shutdown` + `koru autopilot daemon`) to pick up the change.

## Security model — what you are trusting

- **Same UID only.** The unix socket is `0600` and the daemon
  verifies `SO_PEERCRED` on each accept. A different user (or root in
  another namespace) cannot drive your IDE.
- **No network listener.** There is intentionally no TCP mode.
- **All meaningful events are persisted** to
  `~/.local/state/koru/autopilot.log` (or `$XDG_STATE_HOME/koru/`),
  plus mirrored to daemon stdout.
- **The plugin can refuse.** A VS Code-side extension can choose not
  to paste, e.g. when the chat view is not focused — the daemon
  receives `ack ok:false` and surfaces it to the CLI caller.

If any of these guarantees are *not* good enough for your environment,
prefer `--direct` invocations (no daemon, no socket) and keep the
plugin uninstalled.

## When to use autopilot vs. plain `koru`

| Situation                                              | Use                              |
|--------------------------------------------------------|----------------------------------|
| First-time setup of a project                          | `koru --init` then `koru`        |
| Want to paste a brief into a chat                      | `koru \| xclip` (manual)         |
| Want to *type* the brief into a chat without focus     | `koru autopilot handoff` |
| Want koru to take over when an IDE session ends        | `koru autopilot daemon --handoff` |
| Want a one-shot text injection from a script           | `koru autopilot drive --direct`  |

Autopilot is **additive** — it never replaces the existing `koru` CLI;
it just adds a delivery channel.
