# IDE bridge refactor (2026)

## Problem

Autopilot paste failures (`plugins: []`) had many root causes but one generic error message. Common cases:

- **Cursor 1.105+**: `extensions.trustedPublishers` blocks VSIX-installed extensions until the publisher is trusted.
- **Workspace settings** override user `koruAutopilot.socketPath` (e.g. `.cursor/settings.json` vs `KORU_AUTOPILOT_INSTANCE=cursor`).
- **Stale Unix sockets** after `koru auto` exits leave `Connection refused` while the socket file exists.

## Solution

### `koru ide doctor`

Single diagnostic entry point:

```bash
export KORU_AUTOPILOT_INSTANCE=cursor
koru ide doctor --ide cursor --fix --gc-sockets
```

- Enumerates **hypotheses** with confidence and remediation steps.
- **`--fix`**: safe auto-fixes (workspace socket path; `trustedPublishers` when IDE is closed).
- **`--gc-sockets`**: remove dead `koru-autopilot-*.sock` files.

### `koru autopilot status --explain`

When `plugins` is empty, prints bridge diagnostics to stderr after the JSON status.

### Operator pipeline

Step `autopilot_plugin` uses bridge diagnostics in ticket detail and points to `koru ide doctor --ide … --fix`.

### Daemon start

`koru autopilot daemon` garbage-collects stale sockets (keeps the target socket path) before binding.

## Architecture

```
koru ide doctor
    → ide_adapters/bridge.evaluate_bridge()
    → ide_adapters/registry.get_adapter(ide)
    → ide_adapters/vscode_family.VSCodeFamilyAdapter
    → ide_adapters/shared.py (vscdb, exthost logs, settings)
```

## Cursor trusted publisher (manual if IDE open)

1. Extensions → **koru autopilot** → **Trust Publisher 'semcod'**
2. **Developer: Reload Window**
3. Command Palette → **koru: Connect autopilot daemon**
4. `koru autopilot status` → `plugins` not empty

Or close Cursor and run `koru ide doctor --ide cursor --fix`.

## Follow-up (not in this phase)

- Plugin handshake contract v3
- End-to-end echo probe in chat input
- Headless CI matrix per IDE version
