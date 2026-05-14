# Koru MCP IDE Integration Flow

> Status: **operational**
> Target: Windsurf, Cursor, VS Code
> Version: 2026-05-14

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    IDE (Windsurf/Cursor/VS Code)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Cascade    │  │   Cursor     │  │  Copilot     │           │
│  │   Agent      │  │   Agent      │  │  Chat        │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                   │
│                           │                                     │
│                           ▼                                     │
│              ┌──────────────────────────┐                       │
│              │    MCP Client (stdio)    │                       │
│              └───────────┬──────────────┘                       │
└──────────────────────────┼──────────────────────────────────────┘
                           │ stdio (JSON-RPC 2.0)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              koru mcp-serve (MCP Server)                         │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  koru_list_tickets     (read-only queue query)            │   │
│  │  koru_run_ticket       (queue mode execution)             │   │
│  │  koru_job_status       (job state polling)                │   │
│  │  koru_run_quality_gates (gate binaries)                   │   │
│  │  koru_propose_edits    (context + file metadata)          │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ├─────────────────┬──────────────────┐
                           ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Koru Backend Layers                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐    │
│  │  Queue Mode      │  │  Autopilot       │  │  Autonomous     │    │
│  │  (CLI wrapper)   │  │  (unix socket)   │  │  (orchestrator) │    │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Mapping

### MCP Layer (stdio transport)

**Transport**: JSON-RPC 2.0 over stdio (no unix socket)

**Tools**:
- `koru_list_tickets`: Query planfile queue (headless-friendly)
- `koru_run_ticket`: Execute next runnable ticket (requires CLI queue mode)
- `koru_job_status`: Poll job state (in-memory, ephemeral)
- `koru_run_quality_gates`: Run gate binaries (regix, redup, vallm, testql, bandit)
- `koru_propose_edits`: Read context + file metadata (safe, no writes)

**Configuration**:
```json
{
  "mcpServers": {
    "koru": {
      "command": "koru",
      "args": ["mcp-serve"],
      "env": {
        "KORU_PROJECT_ROOT": "/path/to/project"
      }
    }
  }
}
```

**Capabilities**:
- **Headless**: Yes (no display required)
- **Session stability**: High (stdio is reliable)
- **Fallback**: None (stdio is the only transport)

### Autopilot Layer (unix socket)

**Transport**: NDJSON over unix socket

**Socket path**: `$XDG_RUNTIME_DIR/koru-autopilot.sock` (fallback: `/tmp/koru-autopilot-$UID.sock`)

**Protocol**:
```jsonc
// Plugin → daemon
{"type": "hello", "ide": "vscode", "version": "0.1.0"}
{"type": "session.ended", "chat": "cascade", "reason": "user-stop"}

// Daemon → plugin
{"type": "chat.send", "text": "...", "submit": true}
```

**Injection backends** (priority order):
1. **Plugin**: IDE extension API (most reliable, Wayland-safe)
2. **VS Code CLI**: `code --command workbench.action.chat.sendMessage`
3. **Keyboard sim**: `xdotool` (X11) / `wtype` (sway) / `ydotool` (gnome)
4. **Clipboard**: `wl-copy` / `xclip` + `ctrl+v` (last resort)

**Capabilities**:
- **Headless**: No (requires graphical session)
- **Session stability**: Medium (depends on IDE focus, Wayland restrictions)
- **Fallback**: Yes (4-tier injection backends)

### Autonomous Layer (CLI orchestration)

**Mode**: `koru queue loop` or `koru autonomous up`

**Components**:
- Planfile queue runner
- Scan (filesystem watcher)
- WUP (work unit processor)
- Optional autopilot daemon

**OOM protection**: Not implemented in current codebase (future work)

**Capabilities**:
- **Headless**: Yes (CLI-only)
- **Session stability**: High (no UI dependencies)
- **Fallback**: None (CLI is the interface)

## Concrete Flows

### Flow 1: MCP-only (no autopilot)

**Use case**: Agent IDE queries queue, runs gates, proposes edits without autopilot

**Steps**:
1. IDE starts `koru mcp-serve` via MCP config
2. Agent calls `koru_list_tickets` to see open tickets
3. Agent calls `koru_propose_edits` to get context
4. Agent generates edits using its own LLM
5. Agent calls `koru_run_quality_gates` to validate
6. (Optional) Agent calls `koru_run_ticket` to execute via CLI queue mode

**Requirements**:
- MCP config in IDE
- `koru` in PATH
- Planfile queue initialized
- Gate binaries (regix, redup, vallm, testql, bandit) for validation

**Session stability**: High (stdio only)

**Autonomy blockers**: None (pure MCP, no autopilot)

### Flow 2: MCP + Autopilot (hybrid)

**Use case**: Agent IDE uses MCP for data, autopilot for IDE injection

**Steps**:
1. Terminal: `koru autopilot daemon --project "$(pwd)"` (start daemon)
2. IDE plugin connects to daemon socket, sends `hello`
3. IDE agent calls `koru_list_tickets` via MCP
4. IDE agent calls `koru_propose_edits` via MCP
5. IDE agent generates edits
6. IDE agent calls `koru_run_quality_gates` via MCP
7. If gates pass, IDE agent calls `koru autopilot drive '<text>'` to inject
8. Daemon routes to plugin (preferred) or keyboard sim (fallback)
9. Plugin sends `session.ended` when LLM finishes
10. Daemon handoff builds next brief and sends `chat.send`

**Requirements**:
- Autopilot daemon running
- IDE plugin installed and connected
- MCP config in IDE
- `koru` in PATH
- Planfile queue initialized
- Gate binaries for validation
- Keyboard sim tools (xdotool/wtype/ydotool) for fallback

**Session stability**: Medium (depends on IDE focus, Wayland restrictions)

**Autonomy blockers**:
- IDE must be focused (keyboard sim)
- Wayland focus stealing restrictions (some compositors)
- Plugin must be connected (for preferred path)

### Flow 3: Autonomous-only (no IDE)

**Use case**: Background automation running planfile queue without IDE

**Steps**:
1. Terminal: `koru queue loop --project "$(pwd)"` or `koru autonomous up`
2. Koru runs planfile queue in loop
3. Each ticket executes via its executor (CLI/autopilot/LLM/API)
4. If ticket has `executor.kind=autopilot`, requires daemon + IDE
5. Scan watches filesystem changes
6. WUP processes work units
7. Loop continues until queue empty or max iterations

**Requirements**:
- Planfile queue initialized
- `koru` in PATH
- (Optional) Autopilot daemon if tickets use autopilot executor
- (Optional) Gate binaries if tickets include gates

**Session stability**: High (CLI-only)

**Autonomy blockers**:
- None if executor is CLI/LLM/API
- IDE focus required if executor is autopilot

## OOM Protection Flags

**Current status**: Not implemented in codebase

**Planned flags** (future work):
- `--oom-kill-threshold`: Memory limit before killing subprocess (MB)
- `--oom-monitor-interval`: Polling interval for memory stats (seconds)
- `--oom-action`: Action on OOM (kill | warn | continue)

**Integration points**:
- `koru_run_ticket`: Wrap subprocess with memory monitoring
- `koru_run_quality_gates`: Apply per-gate memory limits
- `autonomous queue loop`: Global memory budget enforcement

## Operational Commands

### MCP setup

```bash
# Provision MCP config for Windsurf
koru init-ide --target windsurf

# Provision MCP config for Cursor
koru init-ide --target cursor

# Provision MCP config for VS Code
koru init-ide --target vscode

# Dry-run to preview
koru init-ide --target windsurf --dry-run
```

### Autopilot daemon

```bash
# Start daemon (foreground)
koru autopilot daemon --project "$(pwd)"

# Start daemon with handoff enabled
koru autopilot daemon --project "$(pwd)" --handoff

# Check daemon status
koru autopilot status

# Diagnose backends
koru autopilot doctor

# List detected IDEs
koru autopilot ide-list

# Drive text to IDE
koru autopilot drive 'next ticket please'

# Force specific IDE
koru autopilot drive --ide vscode 'force VS Code'
```

### Autonomous mode

```bash
# Run planfile queue loop
koru queue loop --project "$(pwd)"

# Run with interactive prompts
koru queue loop --project "$(pwd)" --interactive

# Limit iterations
koru queue loop --project "$(pwd)" --max-iterations 10

# Dry-run
koru queue loop --project "$(pwd)" --dry-run
```

## Troubleshooting

### MCP tools not appearing in IDE

**Check**:
```bash
# Verify MCP config exists
cat ~/.windsurf/mcp_config.json  # Windsurf
cat ~/.cursor/mcp_config.json    # Cursor
cat ~/.config/Code/User/globalStorage/mcp.json  # VS Code

# Verify koru in PATH
which koru

# Test MCP server manually
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | koru mcp-serve
```

### Autopilot daemon not connecting

**Check**:
```bash
# Verify daemon running
koru autopilot status

# Check socket path
ls -la $XDG_RUNTIME_DIR/koru-autopilot.sock
# or
ls -la /tmp/koru-autopilot-$UID.sock

# Verify plugin installed
code --list-extensions | grep koru
```

### Keyboard sim not working

**Check**:
```bash
# Run diagnostics
koru autopilot doctor

# Install missing tools
apt install xdotool          # X11
apt install wtype             # Wayland (sway)
apt install ydotool           # Wayland (gnome)
apt install wl-clipboard xclip  # Clipboard
```

### Wayland focus stealing

**Symptoms**: `drive` command types text but IDE doesn't receive focus

**Solutions**:
- Use plugin path (preferred): IDE plugin must be connected
- Manually focus IDE before running `drive`
- Use Wayland compositor that allows focus changes (sway/Hyprland)

## Summary Table

| Flow                | Headless | Session Stability | Autopilot Required | MCP Required | IDE Required |
|---------------------|----------|------------------|--------------------|---------------|--------------|
| MCP-only            | Yes      | High             | No                 | Yes           | Yes          |
| MCP + Autopilot     | No       | Medium           | Yes                | Yes           | Yes          |
| Autonomous-only     | Yes      | High             | Optional*          | No            | No           |

*Only if tickets have `executor.kind=autopilot`

**Recommendation**: Start with MCP-only flow for maximum stability. Add autopilot only if IDE injection is required.
