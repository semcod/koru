# koru autopilot — VS Code / Windsurf / Cursor extension

Bridge between the editor (VS Code 1.85+, Windsurf, Cursor — all share
the same extension API) and the koru autopilot daemon.

## What it does

1. Opens the unix socket exposed by `koru autopilot daemon`
   (default: `$XDG_RUNTIME_DIR/koru-autopilot.sock`).
2. Sends a `hello` so the daemon knows which IDE is connected.
3. Listens for `chat.send` messages and pastes the supplied text into
   the active chat panel (Copilot Chat / Cascade / Cursor Chat).
4. (Phase 2) Forwards `session.started` / `session.ended` events.

## Build

```bash
npm install
npm run compile
```

To use it locally without packaging:

```bash
# inside this folder:
code --extensionDevelopmentPath=$(pwd)
# or for Windsurf:
windsurf --extensionDevelopmentPath=$(pwd)
```

## Configuration

| Setting                           | Default | Purpose                              |
|-----------------------------------|---------|--------------------------------------|
| `koruAutopilot.socketPath`        | `""`    | Override unix-socket path.           |
| `koruAutopilot.autoConnect`       | `true`  | Connect automatically on startup.    |

## Status bar

The extension adds a small status item:

| Indicator           | Meaning                              |
|---------------------|--------------------------------------|
| `🔌 koru: off`      | Not connected (click to retry).      |
| `🔌 koru: on`       | Connected to the daemon.             |
| `⚠ koru: err`       | Last connection failed; will retry.  |
