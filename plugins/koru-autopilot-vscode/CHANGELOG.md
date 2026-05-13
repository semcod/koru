# Changelog — koru autopilot (VS Code extension)

All notable changes to this extension will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.1] — 2026-05-13

### Added
- **Windsurf Cascade support**: IDE detection (`detectIde()`) now recognises
  Windsurf and tries Cascade-specific chat commands:
  - Open: `windsurf.action.openChat`, `windsurf.action.openCascade`, `cascade.focus`
  - Submit: `windsurf.action.submitChat`, `windsurf.action.cascade.submit`
- `focusChat()` and `submitChat()` dynamically append IDE-specific commands
  based on `detectIde()` instead of relying solely on generic VS Code commands.

## [0.1.0] — 2026-05-11

### Added
- Initial scaffolding: unix-socket bridge to `koru autopilot daemon`.
- Sends `hello`, listens for `chat.send`, pastes text into the active
  chat panel (Copilot Chat, Cascade, Cursor Chat).
- Status-bar item showing connection state.
- Configuration: `koruAutopilot.socketPath`, `koruAutopilot.autoConnect`.
- Reconnect loop with ±500 ms jitter.
- Clipboard restored in a `finally` so injection never strands payloads.
- `runCommand()` helper that wraps `vscode.commands.executeCommand`
  in `Promise.resolve(...)` so failures are catchable.

### Known limitations
- `session.ended` events from the chat lifecycle are not yet emitted
  (Phase 2.3 — depends on the VS Code Chat API stabilising).
- LLM reply text is not captured (Phase 4).
