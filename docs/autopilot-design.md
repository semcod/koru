# koru autopilot — design

> Status: **shipped runtime, active hardening**
> Drives an IDE (Windsurf, VS Code, JetBrains) from a terminal-side koru
> process: types into the active LLM chat, takes over when an IDE-side
> session ends, and exposes a small set of operations through both a
> CLI and an IDE plugin. Current work focuses on installation management,
> version drift detection, and safer plugin runtime policy.

## Goals

1. **One command, zero clicks.** `koru autopilot drive '<text>'` types the given
   text directly into the active chat panel of whatever IDE is in
   focus and submits it.
2. **Session handoff.** When an in-IDE LLM session ends (Cascade reports
   "done", Copilot Chat closes, etc.) an IDE-side client can notify the
   koru daemon over a unix socket; koru can then continue the loop —
   read the next planfile ticket, build a brief, type it into the chat,
   submit, and watch for the next event.
3. **Headless reach.** From any terminal — even a different tmux pane,
   different TTY, or SSH session — `koru autopilot drive '...'` reaches the IDE
   running in the user's desktop session.
4. **Same UX as `goal`/`glon`.** Calling `koru` with no extra
   ceremony still works. New verbs are subcommands; defaults are safe.

## Non-goals (MVP)

- Headless IDE driving (no display). Autopilot assumes an active
  graphical session.
- Capturing the LLM's reply text out of the IDE. Reading reply contents
  is tracked separately as the closed-loop autonomy work in the roadmap.
- Cross-machine driving. The unix socket is local-only.

## Related documentation

- [ide-control-surfaces.md](ide-control-surfaces.md) — broader IDE control options
  beyond chat injection (RPC plugin, DAP/tasks, Neovim, OS injector backend).
- [ide-router.md](ide-router.md) — `koru ide-router` and headless vs IDE-shell merge
  for `--autopilot-ide` / `KORU_AUTOPILOT_IDE`.
- [IDE_PROTOCOL.md](IDE_PROTOCOL.md) — current daemon/plugin protocol,
  version policy, ACK metadata, and runtime safety gates.

## Components

```
any terminal
  └─ `export KORU_AUTOPILOT_INSTANCE=vscode`
      └─ `koru autopilot manage --ide vscode`
      └─ `koru autopilot drive --ide vscode --require-plugin '...'`
      └─ CLI client
          └─ unix socket
              └─ `koru autopilot daemon`
                  ├─ IDE plugin path: paste/submit through the extension
                  └─ fallback path: keyboard sim (`xdotool` / `wtype` / `ydotool`)

IDE plugin
  └─ unix socket
      └─ daemon-side `session.ended` routing
```

### Modules (`src/koruide/` + compatibility shims)

| Module / area                 | Role |
|-------------------------------|------|
| `src/koruide/protocol.py`     | Line-delimited JSON message types + (en/de)code. |
| `src/koruide/daemon.py`       | Unix-socket server: routes events to handlers. |
| `src/koruide/plugin_router.py`| Tracks connected plugin clients and reported runtime versions. |
| `src/koruide/drive_orchestrator.py` | Chooses plugin vs OS injector, applies ACK and plugin-version policy. |
| `src/koruide/plugin_installer.py` | Resolves VSIX, IDE CLIs, installed extension versions, and socket settings. |
| `src/koru/autopilot/*`        | CLI, install manager, and legacy compatibility import paths. |

### IDE plugins (`plugins/`)

| Plugin                          | IDEs                       | Status |
|---------------------------------|----------------------------|--------|
| `koru-autopilot-vscode/`        | VS Code, Windsurf, Cursor* | MVP    |
| `koru-autopilot-jetbrains/`     | IntelliJ family            | stub   |

\* Windsurf and Cursor are VS Code forks; the same VSIX works after
re-packaging or symlinking the extensions folder.

## Wire protocol

A single unix socket per IDE instance, normally:

```bash
export KORU_AUTOPILOT_INSTANCE=vscode
# => $XDG_RUNTIME_DIR/koru-autopilot-vscode.sock
```

If no instance is configured, koru falls back to the legacy
`$XDG_RUNTIME_DIR/koru-autopilot.sock` path.

Messages are **newline-delimited JSON** ("NDJSON"). Each line is a
self-contained object with `type` and optional `id`.

### Plugin → daemon

```jsonc
{"type": "hello", "id": "h1", "ide": "vscode", "version": "0.1.13", "pid": 1234}
{"type": "session.started", "id": "ev1", "chat": "cascade"}
{"type": "session.ended",   "id": "ev2", "chat": "cascade", "reason": "user-stop"}
{"type": "ack", "id": "r1", "ok": true}
```

### CLI/daemon → plugin

```jsonc
{"type": "chat.send", "id": "r1", "text": "next ticket please", "submit": true}
{"type": "ping", "id": "p1"}
```

### CLI → daemon

```jsonc
{"type": "drive",   "text": "...", "submit": true, "ide": "auto"}
{"type": "status",  "id": "s1"}
{"type": "shutdown"}
```

Responses always carry the matching `id` and an `ok: bool`.
The daemon must reject any line larger than 1 MiB.

`hello.version` is plugin runtime metadata. `koru autopilot manage`
compares three separate layers:

- `connected/version`: live plugin connected to the daemon.
- `installed`: extension version installed in the IDE.
- `expected`: VSIX version bundled with the current koru package.

By default a connected-version drift is reported in status/drive ACKs.
With `KORU_STRICT_PLUGIN_VERSION=1`, the daemon blocks `drive` before
sending `chat.send` through a stale plugin.

## Injection backends

Detection order in `injector.py`:

1. **Plugin** — if a plugin is connected for the target IDE, send
   `chat.send` over the socket. Most reliable; works on Wayland.
   If the plugin acks with `submitted: false` (e.g. Windsurf changed its
   VS Code command IDs), the daemon now reports `ok: false` instead of a
   silent false-positive, so the caller can fall back or warn the user.
2. **VS Code CLI** — `code --command workbench.action.chat.sendMessage`
   (works on VS Code 1.93+, but text must already be in the chat box;
   used as a fallback if plugin is missing).
3. **Keyboard simulation** — type the text after focusing the IDE:
   - X11: `xdotool type --delay 5 --clearmodifiers -- <text>` then
     `xdotool key Return` (or `ctrl+Return` for multi-line).
   - Wayland (sway/Hyprland): `wtype -- <text>` then `wtype -k Return`.
   - Wayland (gnome) without `wtype`: requires `ydotool` daemon (needs
     uinput / root); we surface a doctor warning if it's missing.
4. **Clipboard + paste** — last resort: copy text to clipboard
   (`wl-copy` / `xclip`), then send `ctrl+v`. Loses any text already on
   the clipboard, so we save+restore.

`koru autopilot doctor` reports which backends are available.

## Triggers — when does koru "take over"?

The daemon accepts **session lifecycle events** from IDE-side clients.
The message type is `session.ended`; the real IDE chat lifecycle hook is
tracked as P2.3 in [`autopilot-roadmap.md`](./autopilot-roadmap.md).
The MVP path supports the same daemon-side routing once an event source
emits that frame:

| Source              | Description                                       |
|---------------------|---------------------------------------------------|
| **plugin event**    | Planned P2.3: the plugin listens to the IDE chat |
|                     | API and sends `session.ended`.                   |
| **explicit CLI**    | The user runs `koru autopilot drive '...'`; no   |
|                     | event needed.                                     |
| **protocol client** | Any trusted same-UID client can send an NDJSON    |
|                     | `session.ended` frame over the unix socket.       |

Routing handlers live in `daemon.py:_handle_session_event()` and decide
what to type next (typically: `koru` markdown brief for the active
ticket).

## CLI surface

```bash
# start daemon in the foreground
export KORU_AUTOPILOT_INSTANCE=vscode
koru autopilot daemon --project "$(pwd)"
koru autopilot daemon --idempotent --no-handoff

# install/repair/inventory for the active IDE
koru autopilot manage --ide vscode
koru autopilot manage --ide vscode --fix --dry-run
koru autopilot manage --ide vscode --fix

# type text into the focused IDE's chat
koru autopilot drive --ide vscode --require-plugin 'continue with the next ticket'
koru autopilot drive --prompt 'TAK'
koru autopilot drive -p "multi word answer"
koru autopilot drive --no-submit 'partial line, do not press Enter'
koru autopilot drive --ide vscode 'force VS Code'

# fail fast if the live plugin version is stale
KORU_STRICT_PLUGIN_VERSION=1 koru autopilot drive --ide vscode --require-plugin 'probe'

# diagnostics
koru autopilot status         # is daemon up? plugin connected? backends?
koru autopilot manage --ide vscode
koru autopilot doctor         # detailed backend / dependency report
koru autopilot ide-list       # detected running IDEs

# end-to-end shortcut: paste the active koru brief into the IDE
koru autopilot handoff        # = koru --context --format markdown | koru autopilot drive
```

`koru autopilot daemon` is **idempotent**: if the socket already
serves a healthy daemon, it exits 0 with `daemon already running`.

## Phases

| Phase | Scope                                                             |
|-------|-------------------------------------------------------------------|
| 1 MVP | protocol, daemon, client, keyboard-sim injector, `drive`/`status`/`doctor`. VS Code extension stub that connects + sends `hello`. |
| 2     | Real VS Code/Windsurf chat injection through extension API; `handoff`; install manager; runtime version policy. |
| 3     | JetBrains plugin (Kotlin); `session.ended` events from Cascade for Windsurf. |
| 4     | Capture LLM reply text → feed back into koru loop closure.        |

Current implementation ships Phase 1 plus the major Phase 2 runtime
pieces: VS Code-family plugin path, VSIX packaging/install/reassert via
`koru autopilot manage`, one-shot `handoff`, systemd unit, audit log,
`tail`, live plugin version reporting, and strict stale-plugin blocking.
Reply capture and real IDE chat lifecycle events remain open.

## Security model

- Socket is created with mode `0600` and owned by the running user.
- The daemon refuses connections from a different UID (verified via
  `SO_PEERCRED`).
- No network listener. `koru autopilot daemon --tcp` is intentionally
  not implemented.
- All injected text is logged to `~/.local/state/koru/autopilot.log`
  with a 10 MiB rotation, so the user can audit what was typed on
  their behalf.
- `--dry-run` on `drive` prints what would be typed and exits without
  touching the keyboard.

## System dependencies (Linux)

| Stack         | Required for                  | Install                            |
|---------------|-------------------------------|------------------------------------|
| X11           | xdotool                       | `apt install xdotool`              |
| Wayland (sway)| wtype                         | `apt install wtype`                |
| Wayland (gnome)| ydotool + uinput            | `apt install ydotool` + service    |
| any           | wl-copy / xclip (clipboard)   | `apt install wl-clipboard xclip`   |

`koru autopilot doctor` checks all of these and prints copy-pasteable
install commands when something is missing.

## Open questions

1. **Multi-IDE focus arbitration.** If both VS Code *and* IntelliJ
   are running, which one receives `drive`? MVP: focused window wins;
   `--ide` can force.
2. **Wayland focus stealing.** Some compositors refuse focus changes
   from CLI. Mitigation: rely on plugin path on Wayland.
3. **Submit shortcut differences.** VS Code chat: `Enter` submits,
   `Shift+Enter` newline. JetBrains AI Assistant: `Ctrl+Enter`. The
   injector keeps a per-IDE keymap.
