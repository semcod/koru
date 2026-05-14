# IDE control surfaces — map beyond MCP + autopilot

Koru already combines **MCP** (IDE → Koru tools) and **autopilot** (Koru → IDE
chat injection via the VSIX + daemon). This page lists **additional** control
styles that stay useful without turning everything into “type into chat”.

See also: [ide-router.md](ide-router.md) (headless vs IDE shell merge for
`--autopilot-ide`).

[MCP IDE flow](mcp-ide-flow.md) — stdio tools (`koru mcp-serve`) wiring.  
[Autopilot design](autopilot-design.md) — terminal → chat injection architecture.

---

## 1. IDE plugin as a small RPC client (structured Koru → IDE)

Today the dominant Koru → IDE path is **prompt injection** (`drive` /
`handoff`). A complementary model is a **thin RPC** owned by the same (or a
sibling) extension:

- Endpoints or messages such as: open file, apply workspace edit, focus panel,
  show notification, run a named VS Code command.
- Koru calls the plugin over **HTTP loopback**, **WebSocket**, or **stdin JSON**
  — not raw GUI coordinates.

Why: **bidirectional, semantic** control (events from IDE, commands from Koru)
without fragile global GUI automation.

References:

- [Visual Studio Code Extension API](https://code.visualstudio.com/api) —
  `vscode.workspace`, `vscode.window`, `vscode.commands.executeCommand`.
- JetBrains: editor actions and plugin APIs (see IntelliJ Platform SDK docs on
  editor basics and actions).

This extends autopilot; it does **not** replace MCP.

---

## 2. Debug Adapter Protocol (DAP) / task runner (deterministic runs)

Much “autonomy” does not need the chat at all:

- Launch **tests**, **debug configurations**, or **tasks** through the IDE’s
  task/debug API (from the plugin), then stream **pass/fail** back to Koru.

Why: more **deterministic** than chat for “run pytest / compose / e2e” loops.

References:

- VS Code: [Debugging](https://code.visualstudio.com/api/extension-guides/debugger-extension)
  and tasks (`tasks.json` / programmatic task execution from extensions).

---

## 3. Filesystem + git as the control plane (“IDE as renderer”)

Sometimes the best IDE control is **no IDE control**:

- Koru applies patches, runs CLI gates, updates planfile; the IDE only **shows
  diffs** and diagnostics.
- Optional: a small **file watcher** or convention (e.g. append-only operator
  notes under `.planfile/.koru/`) that the plugin surfaces as banners or a tree
  view.

Why: **robust** across Cursor, Windsurf, JetBrains, Neovim — same repo truth.

---

## 4. IDE profiles in Koru (configuration, not one codepath)

`koru ide-router` + `koru agent --env-exports` are early pieces. A fuller model
is explicit **profiles** per editor family:

| Profile (concept) | Typical stack |
| --- | --- |
| `cursor` | MCP + `.cursorrules` + optional autopilot `drive` |
| `windsurf` | VSIX + MCP + optional autopilot |
| `jetbrains` | Plugin + action runner / tasks |
| `neovim` | RPC / `--listen` + remote client (e.g. `nvr`) |

Each profile would document: how to open a file, apply edits, run format/lint,
whether a “chat” exists and how it is driven.

References:

- Neovim: [remote](https://neovim.io/doc/user/remote.html) and `--listen` /
  remote-send patterns.

---

## 5. OS automation as a named fallback (`OsInjectorBackend`)

xdotool / ydotool / host injectors already exist in the autopilot stack. A
useful refactor is a **single backend** with explicit primitives:

- `focus_window`, `type_text`, `key_combo`, optional screenshot hooks.

Use only when **no** plugin RPC and **no** MCP-driven path is available.

---

## Suggested implementation order (next iterations)

1. **Neovim socket backend** — strong headless story, minimal GUI coupling.
2. **Plugin ↔ Koru RPC** — a short allowlist of commands (`open_file`,
   `apply_edits`, `show_message`) shared across VS Code–family and JetBrains.
3. **`OsInjectorBackend`** — consolidate injectors behind one interface and
   smoke-test against a trivial target window.

None of this replaces `koru ide-router`; the router stays focused on **which
shell class** you are in (headless vs IDE) and **which autopilot IDE string**
to merge — not on every delivery mechanism above.
