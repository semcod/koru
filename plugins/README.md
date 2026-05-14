# koru autopilot — IDE plugins

These are the editor-side counterparts of `koru autopilot daemon`. Each
plugin opens the daemon's unix socket, sends a `hello`, then forwards
LLM session lifecycle events (`session.started`, `session.ended`) where
the IDE API exposes them so koru can take over and type the next ticket
brief into the chat panel.

| Plugin                          | IDE family                  | Status |
|---------------------------------|-----------------------------|--------|
| `koru-autopilot-vscode/`        | VS Code, Windsurf, Cursor   | MVP    |
| `koru-autopilot-jetbrains/`     | IntelliJ family             | scaffold |

Wire protocol: see [`docs/autopilot-design.md`](../docs/autopilot-design.md#wire-protocol).
TL;DR — newline-delimited JSON over `$XDG_RUNTIME_DIR/koru-autopilot.sock`.
