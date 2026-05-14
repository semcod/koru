# koru autopilot — VS Code / Windsurf / Cursor extension

Bridge between the editor (VS Code 1.85+, Windsurf, Cursor — all share
the same extension API) and the koru autopilot daemon.

## What it does

1. Opens the unix socket exposed by `koru autopilot daemon`
   (default: `$XDG_RUNTIME_DIR/koru-autopilot.sock`).
2. Sends a `hello` so the daemon knows which IDE is connected.
3. Listens for `chat.send` messages and pastes the supplied text into
   the IDE chat agent (Windsurf **Cascade** first when detected, else
   Copilot Chat / Cursor Chat — not external browser windows).
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
npm run package        # produces koru-autopilot-0.1.6.vsix
```

`npm run package` invokes `vsce package` and writes the file next to
`package.json`. Behind the scenes the script runs `tsc -p ./` first
(via `vscode:prepublish`).

## Install the `.vsix`

For everyday users who don't want to clone this repo:

```bash
# Cascade / Windsurf:
windsurf --install-extension koru-autopilot-0.1.6.vsix

# VS Code:
code --install-extension koru-autopilot-0.1.6.vsix

# Cursor:
cursor --install-extension koru-autopilot-0.1.6.vsix
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

| IDE        | Open commands (auto-detected)                                                                                                                                    | Submit commands (auto-detected)                                                                                                        |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| VS Code    | `workbench.action.chat.open`                                                                                                                                     | `workbench.action.chat.submit`                                                                                                         |
| Cursor     | `workbench.action.chat.open`                                                                                                                                     | `workbench.action.chat.submit`                                                                                                         |
| **Windsurf** | `windsurf.chat.open`, `windsurf.cascade.open`, `windsurf.action.openChat`, `windsurf.action.openCascade`, `cascade.focus`, `windsurf.panel.chat`, `composer.showComposer` | `windsurf.chat.submit`, `windsurf.cascade.submit`, `windsurf.action.submitChat`, `windsurf.action.cascade.submit`, `cascade.submit`, `workbench.action.chat.submit` |

Windsurf is a fast-moving fork; command IDs change between releases. The extension
maintains a speculative list and tries every candidate until one succeeds. If you
see `opened: false, submitted: false` in the daemon logs, the commands for your
Windsurf build have drifted again.

### Customising chat commands

Override the auto-detected commands via `settings.json`:

```json
{
  "koruAutopilot.chatOpenCommands": [
    "windsurf.chat.open",
    "windsurf.action.openCascade"
  ]
}
```

Then reload the window (`Developer: Reload Window`).

## Troubleshooting

### Plugin connects but messages never appear in Windsurf Cascade

1. **Open the browser console** (Windsurf: `Ctrl+Shift+P` → `Developer: Toggle Developer Tools` → Console tab).
2. Look for yellow warnings starting with `koru autopilot: ... command not available`. These list the exact VS Code command IDs that Windsurf rejected.
3. Find the working ones by running in the Console:

   ```js
   vscode.commands.getCommands().then(c =>
     c.filter(x => x.includes('chat') || x.includes('cascade'))
   )
   ```

4. Add the working commands to `koruAutopilot.chatOpenCommands` in your `settings.json` (see *Customising chat commands* above) and reload the window.

### Daemon reports `autopilot: ok` but nothing was sent

Since 0.1.6 the koru daemon detects when the plugin returns `submitted: false` and reports `ok: false` instead of a silent false-positive. If you see:

```text
plugin connected but could not submit to chat (outdated IDE commands)
```

…it means the plugin socket is alive but the IDE command IDs have drifted. Follow the console-debug steps above.

## Status bar

The extension adds a small status item:

| Indicator           | Meaning                              |
|---------------------|--------------------------------------|
| `🔌 koru: off`      | Not connected (click to retry).      |
| `🔌 koru: on`       | Connected to the daemon.             |
| `⚠ koru: err`       | Last connection failed; will retry.  |
