# Koru Autonomy Interface Surface

Date: 2026-05-25

This document describes the full set of interfaces available to Koru for
controlling or observing a development environment while executing
programming and testing tasks.

The goal is not only documentation, but a usable control model:

> every automation capability should be classifiable as an interface with:
> direction, transport, trust level, side effects, verification mode, and
> ideal use cases.

## Design principle

Koru does not have one universal “agent API”.

Instead it operates across several interface families:

1. **tool invocation**
2. **IDE control**
3. **desktop / OS input**
4. **browser / dashboard control**
5. **filesystem and artifact exchange**
6. **provider / service APIs**
7. **history / trace / event observation**

These should be treated as one control plane with multiple transports.

## Interface inventory

### A. MCP tools

Direction:

- IDE-hosted LLM or MCP client -> Koru

Transport:

- stdio MCP server

Code:

- `src/koru/mcp_server.py`
- `src/koruapi/mcp_server.py`
- `.vscode/mcp.json`

Role:

- structured tool execution
- ticket listing/running
- quality gates
- project-aware helper calls

Strengths:

- explicit
- structured
- safe for coding workflows
- best interface for “agent asks Koru to do something”

Limitations:

- not a push channel from Koru into the IDE chat

Best use:

- code tasks
- queue/ticket operations
- repo inspection
- reproducible LLM tool use

### B. Dashboard REST API

Direction:

- browser/operator/automation -> Koru

Transport:

- local HTTP

Code:

- `src/koruapi/dashboard_routes.py`
- `src/koruapi/dashboard_tickets.py`
- `src/koruapi/dashboard_serve_utils.py`

Examples:

- `/api/dashboard`
- `/api/autonomy/trace`
- `/llm/action/create-ticket-for-project`

Role:

- lightweight operator actions
- read/write ticket operations
- runtime inspection
- quick links from shell

Strengths:

- clickable
- easy to script with `curl`
- good for operator recovery actions

Limitations:

- mostly request/response
- not suitable as the only live IDE-control transport

Best use:

- accept/reject/reopen/annotate tasks
- inspect decision trace
- trigger lightweight workflow actions

### C. Plugin + Unix socket protocol

Direction:

- Koru daemon <-> IDE plugin

Transport:

- local Unix domain socket
- NDJSON protocol

Code:

- `src/koruide/protocol.py`
- `src/koruide/daemon/`
- `plugins/koru-autopilot-vscode/`
- `plugins/koru-autopilot-jetbrains/`

Role:

- chat drive
- focus/open commands
- paste/submit
- session lifecycle
- plugin hello / capabilities / acknowledgements

Strengths:

- primary high-trust control path for IDE chat automation
- verifiable
- versioned
- IDE-aware

Limitations:

- plugin/session drift
- IDE reload/version mismatch issues

Best use:

- push prompt into IDE chat
- detect plugin capabilities
- receive structured drive acknowledgements and events

### D. Native IDE commands

Direction:

- plugin -> IDE internals

Transport:

- VS Code command registry / JetBrains action APIs

Code:

- `plugins/koru-autopilot-vscode/src/extension.ts`
- `plugins/koru-autopilot-vscode/src/ides/`
- `plugins/koru-autopilot-vscode/src/antigravity-fastpath.ts`

Role:

- open/focus agent/chat panes
- use IDE-native send commands when available

Antigravity note:

- Antigravity has a special native path:
  `antigravity.sendPromptToAgentPanel`
- this is preferable to generic paste/submit when available

Strengths:

- less fragile than keyboard injection
- can be atomic

Limitations:

- vendor-specific
- commands can change across IDE versions

Best use:

- native send/focus operations
- product-specific fast paths

### E. Desktop / OS injectors

Direction:

- Koru -> desktop session

Transport:

- keyboard/mouse/clipboard injection

Code:

- `src/koruide/injector_backends.py`
- injector logic in `koruide`

Backends:

- `xdotool`
- `wtype`
- `ydotool`

Role:

- fallback when plugin/native command cannot complete the drive

Strengths:

- broad fallback coverage
- works even when IDE APIs are incomplete

Limitations:

- focus-sensitive
- compositor/session dependent
- weaker verification than native plugin paths

Best use:

- fallback submit
- fallback paste
- desktop recovery in Linux GUI sessions

### F. Browser / dashboard surface

Direction:

- operator or automation -> browser UI -> Koru HTTP routes

Transport:

- local browser
- dashboard frontend

Code:

- `src/koruapi/dashboard_template.html`
- dashboard routes and runtime payloads

Role:

- visualize runtime state
- navigate queue/tickets quickly
- click actions instead of manual shell commands

Strengths:

- human-friendly control plane

Limitations:

- mostly operator-facing today
- not yet a general browser-automation backend

Best use:

- quick remediation
- visibility
- lightweight approvals

### G. Browser capture / mesh side channels

Direction:

- browser or external capture -> Koru

Transport:

- HTTP side endpoints

Code:

- `korumesh.browser_capture`
- routes under dashboard server

Role:

- observational interface
- browser upload / external view state ingestion

Strengths:

- useful for observing real browser state

Limitations:

- not the main control path yet

### H. Filesystem + artifacts

Direction:

- shared between Koru, tools, IDE, and operator

Transport:

- files on disk

Examples:

- `.planfile/`
- `project/analysis.toon.yaml`
- `.planfile/.koru/autonomy-telemetry.json`
- checkpoints
- IDE settings files

Role:

- stable state handoff
- queue/ticket persistence
- scan artifacts
- telemetry

Strengths:

- durable
- debuggable
- tool-agnostic

Limitations:

- stale artifact risk
- locking / dedupe / freshness policy needed

Best use:

- authoritative workflow state
- discovery inputs
- operator debugging

### I. CLI / subprocess interfaces

Direction:

- Koru -> local command-line tools

Transport:

- subprocess

Examples:

- `planfile`
- `pytest`
- `wup`
- `git`
- IDE CLIs like `codium --install-extension`

Role:

- glue layer for real environment changes and checks

Strengths:

- simple
- composable
- easy to log

Limitations:

- inconsistent contracts across tools

Best use:

- build/test/doctor flows
- installation and verification

### J. Provider / external service APIs

Direction:

- Koru -> remote service

Transport:

- HTTP / SDK / vendor CLI

Examples:

- model providers
- future CI or issue tracker integrations

Role:

- external compute / hosted workflow support

Strengths:

- does not depend on local GUI

Limitations:

- separate from IDE-native control

### K. Chat-history / event observation

Direction:

- IDE plugin / local artifacts -> Koru

Transport:

- socket events
- SQLite / file polling
- product-specific stores

Examples:

- Cursor DB watcher
- session/message events
- Antigravity conversation `.pb` files (currently observational/stubbed in plugin docs)

Role:

- detect replies
- infer task completion / needs-input
- avoid blind re-driving

Strengths:

- crucial for closed-loop autonomy

Limitations:

- store formats vary by IDE
- some histories are encrypted or protobuf-based and not safely writable

## About protobuf / `.pb` surfaces

Antigravity-related history mentions `.pb` conversation files under:

- `~/.gemini/antigravity/conversations/*.pb`

These should be treated as an **observation interface**, not a control
interface, unless Koru owns a stable schema and safe writer.

Recommended rule:

- **read-only unless a formal schema contract exists**
- if read support lands, expose it behind a narrow adapter
- never treat raw protobuf stores as the primary write path for chat drive

## Cursor control vs browser control

Two concepts should stay separate:

1. **cursor control**
   - moving keyboard focus
   - sending keys/mouse
   - desktop automation
2. **browser control**
   - controlling an in-browser application or dashboard
   - potentially via dedicated browser automation in the future

Today Koru has stronger primitives for desktop/IDE control than for
general browser automation. If browser control becomes first-class, it
should be introduced as its own backend family rather than smuggled into
OS injectors.

## Proposed canonical interface schema

Every interface should be describable by the same fields:

```yaml
id: plugin_socket
family: ide_control
direction: bidirectional
transport: unix_socket_ndjson
surface: ide_chat
authority: high
verification:
  mode: strict_ack
  can_confirm_submit: true
blocking_modes:
  - plugin_missing
  - version_mismatch
  - chat_busy
artifacts:
  - .planfile/.koru/autonomy-telemetry.json
operator_recovery:
  - reload_window
  - reconnect_plugin
```

Suggested top-level families:

- `tool_invocation`
- `ide_control`
- `desktop_control`
- `browser_control`
- `artifact_exchange`
- `remote_service`
- `observation`

## Recommended next implementation step

Create a machine-readable registry, for example:

- `docs/interfaces/koru-interface-registry.yaml`

and describe each concrete interface instance:

- `mcp_stdio_server`
- `dashboard_rest`
- `plugin_socket_vscode_family`
- `plugin_socket_jetbrains`
- `antigravity_native_send`
- `os_injector_xdotool`
- `os_injector_wtype`
- `os_injector_ydotool`
- `filesystem_planfile`
- `chat_history_cursor_sqlite`
- `chat_history_antigravity_pb_readonly`

That registry can then drive:

- doctor output
- dashboard runtime introspection
- blocker classification
- future agent planning

## Why this matters for programming and testing

When Koru is executing real engineering work, it needs to know:

- which interfaces are available
- which are authoritative
- which are safe to write
- which are only observational
- how to recover when one fails

Without that model, autonomy becomes a pile of special cases.
With that model, Koru can choose the best path for:

- coding
- running tests
- reading IDE feedback
- opening tickets
- coordinating with the operator
