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
| Cursor / Windsurf / VS Code | Autopilot optional | MCP + rules |
| Headless / CI | Queue + gates | Separate agent with MCP or API only |

For product-level agent lanes, see `koru agent --env-exports` and
`docs/agent-guide.md`.

## Further reading

- [mcp-ide-flow.md](mcp-ide-flow.md) — MCP `koru mcp-serve` and tool catalogue
- [autopilot-design.md](autopilot-design.md) — autopilot daemon and `drive` / `handoff`
- [ide-control-surfaces.md](ide-control-surfaces.md) — RPC, DAP/tasks, profiles, Neovim, OS fallback
