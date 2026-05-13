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

## Run locally (no install required)

```bash
# inside this folder:
code --extensionDevelopmentPath=$(pwd)
# or for Windsurf / Cursor (they share the VS Code extension API):
windsurf --extensionDevelopmentPath=$(pwd)
cursor   --extensionDevelopmentPath=$(pwd)
```

## Package a `.vsix` for distribution

```bash
npm install
npm run package        # produces koru-autopilot-0.1.0.vsix
```

`npm run package` invokes `vsce package` and writes the file next to
`package.json`. Behind the scenes the script runs `tsc -p ./` first
(via `vscode:prepublish`).

## Install the `.vsix`

For everyday users who don't want to clone this repo:

```bash
# Cascade / Windsurf:
windsurf --install-extension koru-autopilot-0.1.0.vsix

# VS Code:
code --install-extension koru-autopilot-0.1.0.vsix

# Cursor:
cursor --install-extension koru-autopilot-0.1.0.vsix
```

After install, the IDE shows a `🔌 koru: on` indicator in its status
bar as soon as `koru autopilot daemon` is running.

## Clean rebuild

```bash
npm run clean && npm install && npm run package
```

## Configuration

| Setting                          | Default | Purpose                               |
|----------------------------------|---------|---------------------------------------|
| `koruAutopilot.socketPath`       | `""`    | Override unix-socket path.            |
| `koruAutopilot.autoConnect`      | `true`  | Connect automatically on startup.     |
| `koruAutopilot.chatOpenCommands` | `[]`    | Custom commands to open chat panel.   |

### IDE-specific chat commands

The extension detects the IDE (`windsurf`, `cursor`, or `vscode`) and automatically
tries the right commands to open and submit the chat panel.

| IDE        | Open commands (auto-detected)                                              | Submit commands (auto-detected)                                |
|------------|----------------------------------------------------------------------------|----------------------------------------------------------------|
| VS Code    | `workbench.action.chat.open`                                               | `workbench.action.chat.submit`                               |
| Cursor     | `workbench.action.chat.open`                                               | `workbench.action.chat.submit`                               |
| **Windsurf** | `windsurf.action.openChat`, `windsurf.action.openCascade`, `cascade.focus` | `windsurf.action.submitChat`, `windsurf.action.cascade.submit` |

If the auto-detected commands fail, you can override them via the
`koruAutopilot.chatOpenCommands` setting in your IDE's `settings.json`.

## Status bar

The extension adds a small status item:

| Indicator           | Meaning                              |
|---------------------|--------------------------------------|
| `🔌 koru: off`      | Not connected (click to retry).      |
| `🔌 koru: on`       | Connected to the daemon.             |
| `⚠ koru: err`       | Last connection failed; will retry.  |
