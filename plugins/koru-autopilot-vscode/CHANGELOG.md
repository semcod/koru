# Changelog — koru autopilot (VS Code extension)

All notable changes to this extension will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.6] — 2026-05-14

### Fixed
- **Windsurf command drift**: added speculative Windsurf / Cascade command IDs
  (`windsurf.chat.open`, `windsurf.cascade.submit`, `windsurf.chat.typeText`, …)
  to cover IDE versions where the older `windsurf.action.*` namespace no longer
  exists.
- **`console.warn` diagnostics**: every failed `focusChat`, `pasteText`, and
  `submitChat` command is now logged to the browser console so users can see
  exactly which VS Code command IDs are missing and configure
  `koruAutopilot.chatOpenCommands` accordingly.

## [0.1.5] — 2026-05-14

### Fixed
- **Windsurf / Cascade**: open Cascade **before** generic `workbench.action.chat.open`
  so `chat.send` targets the built-in agent, not a no-op web panel.
- **Submit**: try Cascade-specific submit command IDs **before** generic
  `workbench.action.chat.*` (those often resolve without throwing but do not
  submit in Windsurf).
- **`executeCommand` false**: treat resolved `false` as failure and try the
  next candidate command.

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
