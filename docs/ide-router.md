# IDE router (`koru ide-router`)

Koru uses **two independent channels** to reach an editor:

1. **MCP** — the IDE agent calls `koru mcp-serve` tools (`koru_list_tickets`, …).
2. **Autopilot** — the autoloop pushes text into the IDE chat via the VSIX + daemon.

The **IDE router** (`koru.ide_router`) picks a **single coherent view** of the
current process environment: *GUI IDE shell* vs *headless*, and which
`--autopilot-ide` string `koru autonomous` should use after merging CLI +
`KORU_AUTOPILOT_IDE`.

## CLI

```bash
koru ide-router
koru ide-router --format json --cli-ide windsurf
```

## Environment

| Variable | Effect |
| --- | --- |
| `KORU_HEADLESS=1` | Headless route: `autopilot_ide` becomes `auto`, MCP/autopilot GUI **not recommended** for this shell. |
| `KORU_IDE_MODE=headless` | Same as explicit headless. |
| `SSH_CONNECTION` + no `DISPLAY` (Linux) | Treated as headless (SSH session without X forwarding). |
| `KORU_HEADLESS_ALLOW_AUTOPILOT=1` | Opt out: honor `KORU_AUTOPILOT_IDE` even when headless (e.g. XVFB + extension tests). |
| `KORU_AUTOPILOT_IDE` | When set to a concrete IDE (not `auto`), overrides CLI `--autopilot-ide` — **unless** headless short-circuit applies. |

## Integration

`koru autonomous` calls `resolve_ide_route()` via `_resolve_autopilot_ide()` so
autoloop, CI, and desktop sessions share one merge rule.

MCP bootstrap (`koru init-ide`) is unchanged: it still writes per-IDE config
files; the router does **not** auto-enable MCP in Cursor/Windsurf.

## Operator map

| Surface | Autoloop terminal | Chat / agent |
| --- | --- | --- |
| VS Code / VSCodium / Cursor / Windsurf | Autopilot plugin path | MCP + rules |
| JetBrains / Zed | Autopilot fallback path | IDE-native agent where available |
| Headless / CI | Queue + gates | Separate agent with MCP or API only |

## IDE lanes and sockets

Supported autopilot IDE ids are `vscode`, `vscodium`, `cursor`, `windsurf`,
`jetbrains`, and `zed`.

`vscode` and `vscodium` are intentionally separate lanes. If a terminal is
hosted by VSCodium, or if the operator passes `--ide vscodium`, koru uses
`KORU_AUTOPILOT_INSTANCE=vscodium`, VSCodium settings, and
`koru-autopilot-vscodium.sock`. VS Code uses `KORU_AUTOPILOT_INSTANCE=vscode`
and `koru-autopilot-vscode.sock`.

This separation matters when several editors are open at once: the router should
target the active/editor-specific lane instead of whichever VS Code-family
window connected first.

## Test coverage

The current smoke matrix covers:

- Docker Linux bases: `debian-slim`, `debian-bookworm`, `ubuntu-noble`,
  `fedora`, `alpine`
- Native GitHub runners: `ubuntu-latest`, `windows-latest`, `macos-latest`
- IDE lanes: `vscode`, `vscodium`, `cursor`, `windsurf`, `jetbrains`, `zed`

iOS is not part of the matrix because autopilot targets desktop IDE CLIs,
extension hosts, and local socket/process workflows.

For product-level agent lanes, see `koru agent --env-exports` and
`docs/agent-guide.md`.

## Further reading

- [mcp-ide-flow.md](mcp-ide-flow.md) — MCP `koru mcp-serve` and tool catalogue
- [autopilot-design.md](autopilot-design.md) — autopilot daemon and `drive` / `handoff`
- [ide-control-surfaces.md](ide-control-surfaces.md) — RPC, DAP/tasks, profiles, Neovim, OS fallback
