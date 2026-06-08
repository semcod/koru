# Agent backends — layered IDE / LLM control (koru)

There is **no single API** that wakes or drives the embedded LLM across
all editors. Koru already splits the problem into **transports**; this
document names the layers, maps popular IDEs to them, and points to code.
For the LLM/heuristic-facing command facade, see
[ide-command-api-map.md](ide-command-api-map.md).

For the full control stack (koruide vs nlp2uri vs plugins), see
[ide-control-architecture.md](ide-control-architecture.md) and the refactor plan
[plans/nlp2uri-koruide-integration-refactor-plan.md](plans/nlp2uri-koruide-integration-refactor-plan.md).

## Design rule

> `koru autonomous` / queue runners should eventually call a **small
> stable interface** (e.g. “push prompt to the active agent UI”). Each
> **backend** implements that interface using one transport: unix socket +
> editor plugin, MCP-only, OS-level injector, or vendor CLI.

Today, **push-to-chat** is implemented by **`koru autopilot`** (daemon +
`koru autopilot drive`) and editor-specific plugins / injectors — not by
MCP. MCP is the inverse direction: **IDE agent → koru tools**.

## Layer matrix

| Layer | Role | Typical entry | Works for |
| --- | --- | --- | --- |
| **A. Plugin + socket** | Daemon sends `drive` / `chat.send`; extension opens chat, types, submits | `koru autopilot daemon`, `koru autopilot drive` | VS Code, Windsurf, Cursor (VSIX), JetBrains (Kotlin plugin, stub→grow) |
| **B. MCP server** | LLM in IDE calls `koru_*` tools; no server→client push | `koru mcp-serve`, IDE `mcp.json` | Cursor, Windsurf, VS Code, Claude Code host |
| **C. TILLM shell client** | External `tillm` plugin controls vendor CLIs | `tillm drive --client aider`, `claude`, `devin`, … | Headless / CI; less UI coupling |
| **D. OS injector** | Keyboard / clipboard when plugin missing | `koru autopilot drive --direct`, `Injector` | X11 / Wayland with focus caveats |
| **E. HTTP / SaaS API** | Koru talks to provider directly | OpenRouter, Anthropic, … | No IDE chat; separate from “wake IDE LLM” |

## IDE / provider cheat sheet

| Product | Prefer (push “TAK” / prompt into **IDE** chat) | Tool / pull (IDE → koru) | Notes |
| --- | --- | --- | --- |
| **Windsurf** | A — `koru-autopilot-vscode` + Cascade-first commands | B — MCP `koru` | Browser / Perplexity webview ≠ VS Code API |
| **Cursor** | A — same VSIX lane + socket | B — MCP; optional **C** — `cursor agent` CLI | CLI path = different binary contract |
| **VS Code** | A — VSIX + Copilot / built-in chat | B — MCP | Same extension host as Windsurf |
| **JetBrains** | A — `koru-autopilot-jetbrains` (`ChatInjector`) | B if host adds MCP later | Plugin maturity varies |
| **Zed** | A (experimental) or D | B when available | `koru autopilot drive --ide zed` hits injector/plugin path |
| **Neovim** | Custom Lua bridge (same **socket protocol** as VSIX) or D | B via external MCP client | Not shipped; pattern matches A |
| **Claude Code** | C — TILLM shell lane | B — MCP in supported hosts | No single “chat panel” |
| **SaaS (OpenAI, Anthropic, Perplexity web)** | **E** — HTTP from koru | — | Koru cannot drive their DOM from a VS Code extension |

## Code map (this repo)

| Piece | Path |
| --- | --- |
| Autopilot daemon + protocol (canonical) | `src/koruide/daemon/`, `src/koruide/protocol.py` |
| Autopilot shims (legacy imports) | `src/koru/autopilot/daemon.py`, `protocol.py` |
| CLI `drive` / `daemon` | `src/koru/autopilot/cli_command.py` |
| VS Code / VSCodium / Windsurf / Cursor extension | `plugins/koru-autopilot-vscode/` |
| JetBrains scaffold | `plugins/koru-autopilot-jetbrains/` |
| MCP tools | `src/koru/mcp_server.py`, `mcp_provision.py` |
| OS injector | `src/koru/autopilot/injector.py` |
| Experimental registry (core profiles + TILLM-exported shell profile) | `src/koru/agent_backends.py`, `koru agent-backends`, `/home/tom/github/semcod/tillm` |
| Runtime ``AgentBackend`` (socket ``drive`` + TILLM shell backend) | `src/koru/agent_backend_runtime.py` |
| Shell LLM control plugin | `/home/tom/github/semcod/tillm` |
| Tool registry YAML | `docs/ai-tool-registry-2026.yaml` |

## Roadmap (incremental)

1. **Keep A stable** — one protocol string (`hello`, `chat.send`, …) per
   socket client; editor-specific command lists live in each plugin.
2. **Treat B as default for “agent does work”** — tickets, scan, gates via
   MCP; document that MCP does **not** push text into the chat.
3. **Add C per vendor in TILLM** — shell client specs and prompt contracts live
   in `/home/tom/github/semcod/tillm`, not in Koru.
4. **Optional Python façade** — `koru.agent_backends` exposes **profiles**
   only (CLI: `koru agent-backends`, doctor: `agent_backends_registry`);
   `koru.agent_backend_runtime` exposes **AgentBackend** + `PluginSocketBackend`
   (autopilot ``drive``); real `send_chat` from :mod:`koru.autonomous` should
   converge on these types as more backends land.

## Project config

`koru.yaml` may declare the durable IDE / LLM lane map under
`ide_integration`. This does not replace generated IDE files yet; it gives
`koru --doctor` and future `autonomous` refactors one project-level contract:

```yaml
ide_integration:
  default_lane: windsurf
  lanes:
    windsurf:
      backend: plugin_socket
      ide: windsurf
      socket: /run/user/1000/koru-autopilot-windsurf.sock
      prompt_mode: continue_ticket
    cursor:
      backend: mcp_tool
      mcp_server: koru
```

Backend aliases are normalized by `koru.agent_backends`: `plugin_socket` maps
to `vscode_family_plugin_socket`, and `mcp_tool` maps to `mcp_stdio_server`.
The `tillm_shell` and legacy `cursor_cli` aliases are supplied by TILLM and map
to `vendor_agent_cli`. `koru --doctor` reports invalid lane/backend
combinations as `agent_integration_config` failures.

## References (external)

- [Cursor MCP](https://cursor.com/docs/mcp)
- [Cursor CLI](https://cursor.com/docs/cli)

These URLs describe **vendor contracts**; koru does not control when they
change.
