# IDE Command API Map for Koru Autonomy

Status: draft, 2026-05-25. Machine-readable companion:
[ide-command-api-map.yaml](ide-command-api-map.yaml).

## Runtime Diagnosis

The current autonomy failure had two separate causes:

1. The VS Code autopilot daemon was not running on
   `/run/user/1000/koru-autopilot-vscode.sock`, so Koru had no live bridge for
   pushing prompts into IDE chat.
2. The latest autonomy trace skipped with `chat_activity` for `STARTER-281`
   because a recent `message.sent` event was still inside the cooldown window.

After starting `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot daemon --idempotent`,
`koru autopilot status --explain` reports `ok=true`, daemon `0.1.279`, VS Code
plugin `0.1.78`, protocol `1`, and these plugin capabilities:

- `ide.commands`
- `chat.focus`
- `chat.paste`
- `chat.submit`
- `chat.events`
- `chat.history`
- `probe.ladder`

The plugin also reported 404 matching IDE commands. Today those commands are
used internally by the probe ladder; the gap is that they are not exported as a
stable API that an OpenRouter planner, an IDE LLM, or deterministic heuristics
can inspect.

## Control Layers

Koru should treat IDE control as a layered API, not as one magic "wake LLM"
operation:

| Layer | Direction | Best Use | Current Entry |
| --- | --- | --- | --- |
| Planfile | Koru/LLM -> work queue | choose and close work | `planfile ticket ...` |
| MCP | IDE LLM -> Koru | read queue, run gates, get context | `koru mcp-serve` |
| Plugin socket | Koru -> IDE | push prompt to chat with trace | `koru autopilot drive` |
| IDE native commands | plugin -> IDE | focus/open/paste/submit/tasks | `vscode.commands.executeCommand`, JetBrains `ActionManager` |
| OS injector | Koru -> desktop | last-resort typing/keys | `wtype`, `ydotool`, `xdotool`, clipboard |
| OpenRouter | Koru -> hosted LLM | planning, semantic review | `OPENROUTER_API_KEY`, strategy prompt |

The strategy rule is simple: use the most semantic and observable layer that can
do the job, then fall back only when diagnostics explain why the preferred layer
cannot work.

## Stable Facade

The command facade exposed to LLMs and heuristics should be small and stable,
even if each IDE has many native command IDs behind it.

| API command | State | Purpose |
| --- | --- | --- |
| `koru.autonomy.status.explain` | stable | read daemon/plugin/backend health before drive |
| `koru.autonomy.trace` | stable | explain `skip_code`, decision, evidence, next step |
| `koru.planfile.queue.list` | stable | find runnable tickets |
| `koru.planfile.ticket.transition` | stable | mark done/input/fail after verification |
| `koru.ide.chat.drive` | stable | push text to IDE chat through daemon/plugin |
| `koru.ide.chat.handoff` | stable | build current Koru brief and send it to chat |
| `koru.mcp.list_tickets` | stable | IDE LLM reads queue via MCP |
| `koru.mcp.run_quality_gates` | stable | IDE LLM runs bounded gates via MCP |
| `koru.ide.commands.list` | proposed | expose plugin-observed IDE commands as an allowlist |
| `koru.ide.command.execute` | proposed | execute one allowlisted native IDE command |
| `koru.ide.workspace.open_file` | proposed | open a file/range in the IDE |
| `koru.ide.workspace.apply_edit` | proposed | apply structured workspace edits through IDE APIs |
| `koru.ide.diagnostics.list` | proposed | return IDE diagnostics without shell probing |
| `koru.ide.task.run` | proposed | run IDE task/debug configuration deterministically |

The YAML companion records parameters, side effects, and provider audience for
each command.

## Per-IDE Map

### VS Code

Preferred transport: VS Code-family plugin socket.

Important native commands:

- Open chat: `workbench.action.chat.open`
- Focus input: `workbench.action.chat.focusInput`, `chat.action.focus`,
  `workbench.chat.action.focusLastFocused`
- Paste/type: `workbench.action.chat.insertText`,
  `workbench.action.chat.typeText`, `aichat.typeText`, clipboard paste, `type`
- Submit: `workbench.action.chat.submit`, `workbench.action.chat.acceptInput`,
  `workbench.action.chat.send`, `workbench.action.chat.sendMessage`,
  `workbench.action.interactive.accept`
- Repair: `workbench.action.reloadWindow`, `koruAutopilot.connect`

Gap: `message.received` is not universally available, so Koru cannot always
read the IDE LLM's answer.

### Cursor

Preferred transport: Cursor VSIX/plugin socket.

Important native commands:

- Open/focus Composer: `composer.openComposer`, `composer.openAsPane`,
  `composer.focusComposer`, `cursor.composer.open`, `cursor.composer.focus`
- Paste/type: `cursor.action.chat.typeText`, `composer.typeText`, `aichat.typeText`
- Submit: `composer.sendToAgent`, `composer.acceptComposerStep`,
  `composer.startComposerPrompt`, `composer.startComposerPrompt2`,
  `composer.submit`, `aichat.submit`
- Host fallback: prefer `Ctrl+Return`; plain `Return` can insert a newline.

Cursor has the best partial observation story because the plugin can poll
Cursor chat-history SQLite and verify new user bubbles in `cursorDiskKV`.

Hazards:

- `composer.openAsPane` can toggle the panel hidden.
- Clipboard-reading commands can paste stale user clipboard content.
- Host-key success can be a false positive on Wayland.

### VSCodium

Preferred transport: VSCodium plugin socket, with host clipboard/key fallbacks.

Current strategy trusts fewer registered submit commands. It prefers
host-level `Ctrl+Return` before plain `Return` because `workbench.action.chat.submit`
and plain host keys can report success without sending.

### Windsurf

Preferred transport: Windsurf native plugin path.

Important native commands:

- Atomic send: `windsurf.sendTextToChat`
- Open/focus Cascade: `windsurf.cascadePanel.open`,
  `windsurf.cascadePanel.focus`, `windsurf.action.openChat`,
  `windsurf.chat.open`, `windsurf.cascade.open`, `windsurf.panel.chat`,
  `cascade.focus`, `windsurf.action.showCascade`
- Focus input: `windsurf.action.focusChatInput`, `windsurf.chat.focusInput`,
  `windsurf.cascade.focusInput`, `cascade.focusInput`
- Paste/type: `windsurf.action.chat.typeText`,
  `windsurf.action.cascade.typeText`, `windsurf.chat.typeText`,
  `windsurf.cascade.typeText`, `cascade.typeText`
- Submit: `windsurf.action.cascade.submit`, `windsurf.action.submitCascade`,
  `windsurf.action.submitChat`, `windsurf.action.chat.submit`,
  `windsurf.chat.submit`, `windsurf.cascade.submit`, `cascade.submit`

Best path: use `windsurf.sendTextToChat` as an atomic send when registered.

### Antigravity

Preferred transport: Antigravity native plugin path.

Important native commands:

- Atomic send: `antigravity.sendPromptToAgentPanel`
- Open agent: `antigravity.openAgent`, `antigravity.agentSidePanel.open`,
  `antigravity.agentSidePanel.focus`

Best path: require the atomic send command for submit. If it is absent, report
the missing capability rather than trying unsafe generic paste loops.

### JetBrains

Preferred transport: JetBrains plugin socket when installed; otherwise OS
injector.

Current scaffold:

- Opens AI Assistant with `ActionManager` action IDs:
  `AIAssistant.OpenAIAssistantToolWindow`, `AIAssistant.Chat.OpenChat`,
  `AiAssistant.OpenAiAssistantToolWindow`, `Grazie.OpenAssistant`
- Pastes by system clipboard plus AWT `Ctrl+V`
- Submits by AWT `Enter`

Gaps to close:

- Use a real JSON encoder for `hello.capabilities`.
- Add command list/introspection for JetBrains action IDs.
- Add diagnostics/task APIs and stable chat lifecycle events.

### Zed

Preferred current transport: OS injector. Koru has process detection and keyboard
policy, but no native plugin bridge in this repo.

The better integration is a small Zed extension/RPC that implements the same
facade: open chat, paste/send, observe result, list diagnostics, run task.

## Provider Strategy

OpenRouter should not attempt GUI control. It should consume the command map as
context and produce one of these outputs:

- a planfile ticket plan,
- a proposed `koru.yaml` strategy patch,
- a semantic review of a patch,
- a recommendation to use IDE LLM/MCP/plugin only when local status says the
  bridge is healthy.

IDE-side LLMs should prefer MCP for pull operations and plugin socket for push
operations:

1. Use MCP to read tickets/context and run quality gates.
2. Use filesystem edits or IDE edit APIs for code changes.
3. Use `koru.ide.chat.drive` only for handoff/prompt continuation.
4. Use native IDE commands only through an allowlist exported by the plugin.

## Heuristics

1. Always run `koru.autonomy.status.explain` before `koru.ide.chat.drive`.
2. If the trace says `chat_activity`, do not paste again; wait for cooldown or
   change the policy explicitly.
3. Prefer planfile tickets over broad discovery while runnable tickets exist.
4. Prefer MCP for IDE LLM pull, plugin socket for Koru-to-chat push, and OS
   injector only as fallback.
5. Prefer atomic vendor send commands where available:
   `windsurf.sendTextToChat`, `antigravity.sendPromptToAgentPanel`.
6. Never retry submit blindly. Require `operation_trace`, `winning_submit`, or a
   known observation event.
7. If `message.received` is absent, treat IDE LLM completion as uncertain and
   rely on ticket state, file diffs, gates, and explicit operator/LLM handoff.
8. OpenRouter stays headless: planning, review, strategy, not GUI drive.

## Recommended Next Protocol

Extend KIDE v2 with a KIDE-004 capability layer:

- `command.ide.commands.list`
- `command.ide.command.execute`
- `command.workspace.open_file`
- `command.workspace.apply_edit`
- `command.diagnostics.list`
- `command.task.run`
- `event.chat.message.received`

The plugin already sees native commands through `vscode.commands.getCommands(false)`.
The next step is to export a safe, categorized allowlist with schemas and
verification requirements instead of sending only a raw count in `hello`.
