# Changelog — koru autopilot (VS Code extension)

All notable changes to this extension will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.58] — 2026-05-24

### Fixed
- **VSCodium: submit with the Codium host-key strategy.** The Codium submit
  path now passes ``ide=vscodium`` into the host-key ladder, so auto mode
  prefers ``Ctrl+Return`` before plain ``Return``. Plain ``Return`` can report
  success while leaving the pasted prompt in the chat input, which produced
  ``verification=submit_unverified``.

## [0.1.57] — 2026-05-24

### Fixed
- **VS Code: focus chat input after opening the Chat panel.** When an explicit
  focus-open command such as ``workbench.panel.chat`` only opens the panel and
  leaves the active file editor unchanged, the plugin now immediately runs the
  chat-input focus ladder and accepts the open step only when a specific
  chat/composer/cascade input command wins. This prevents `koru auto` from
  stopping at `chat input is not focused/open` while still avoiding generic
  panel/sidebar focus as proof of chat readiness.

## [0.1.56] — 2026-05-23

### Fixed
- **VS Code/Cursor: recover from stale Koru chat drafts.** The pre-paste
  busy-input guard now distinguishes user text from known Koru leftovers:
  if the chat input already contains the exact prompt, the plugin submits it
  instead of pasting a duplicate; if it contains a short command-like
  ``koru auto`` draft, the plugin replaces it with the requested autonomous
  prompt. Arbitrary user text still blocks drive to avoid clobbering replies.

## [0.1.55] — 2026-05-23

### Changed
- **Post-submit verification for all plugin-ladder IDEs.** The submit
  input probe (select-all + copy, tail-match via ``decideSubmitCleared``)
  now runs after every submit candidate on Cursor, VS Code, VSCodium, and
  generic fallbacks — not only Cursor. Policy lives in new module
  ``step-decisions.ts`` (``shouldVerifyPostSubmit``, ``interpretPostSubmitProbe``,
  ``shouldVerifyPrePasteBusy``) so focus → busy → paste → submit steps share
  one decision tree. Setting renamed to ``koruAutopilot.verifySubmit``
  (``verifySubmitOnCursor`` kept as deprecated alias). VS Code host-key
  ladder and type-submit fallbacks are verified the same way.

### Fixed
- **Autonomous: llm-ready tickets no longer redrive on stale message.sent.**
  Redrive when ``message.sent`` lacks ``message.received`` is limited to
  non-``llm-ready`` tickets (false-positive Wayland submits). ``llm-ready``
  tickets keep the chat-activity cooldown while the IDE LLM works.

## [0.1.54] — 2026-05-23

### Fixed
- **Cursor: post-submit verification of the chat input.** Cursor's
  ``composer.sendToAgent`` (and its sibling commands ``composer.acceptComposerStep``,
  ``composer.startComposerPrompt`` …) returned ``ok=true`` from the VS Code
  command host even when they no-oped — wrong focus surface, agent panel
  not foreground, command resolved against an empty Composer input rather
  than the chat textarea, etc. The plugin trusted that signal and the
  daemon was told ``submitted: true`` while the prompt was still sitting
  in the chat input. The reported symptom: "Koru typed the prompt but
  did not press Send."
  - After every winning submit candidate (registered command OR host-key
    fallback) on Cursor we now sentinel-probe the chat input via
    select-all + ``editor.action.clipboardCopyAction`` and check whether
    the trailing portion of the original prompt is still present.
  - When the residue matches, the plugin discards the cached "winner"
    (``probeCache.v3.submit``), keeps walking the candidate ladder, and
    finally falls through to the host-level Ctrl+Return ladder
    (wtype → ydotool → xdotool, Wayland-aware ordering).
  - When verification fails on the host-key path too, the plugin emits
    a ``submit_failed`` ack with ``verification: "strict"`` so the
    autonomous loop will not log ``message.sent`` for a phantom send.
  - Controlled by new setting ``koruAutopilot.verifySubmitOnCursor``
    (default ``true``). The probe is only run when a non-trivial prompt
    (≥4 trimmed chars) is in flight; short prompts can collide with
    arbitrary input residue, so we trust the command's own signal there.

## [0.1.52] — 2026-05-23

### Added
- **Multi-IDE chat-history watcher.** The watcher introduced in 0.1.51 is
  now adapter-driven and ships coverage for every IDE the plugin can
  detect. The cursor (resume position) is persisted per-IDE under
  ``chatHistory.cursor.<ide>``.
  - ``cursor`` — full support via ``cursorDiskKV.bubbleId:*`` (SQLite,
    ``type=2``, ``text``).
  - ``vscode`` / ``vscodium`` — best-effort support via VS Code's
    Built-in Chat API store (``ItemTable.chat.ChatSessionStore.index``
    JSON; oldest-first by ``createdAt``). Returns nothing when the chat
    surface is provided by a third-party extension that owns its
    storage (Copilot Chat, Continue, …).
  - ``windsurf`` — Cascade conversations live in
    ``~/.codeium/windsurf/cascade/*.pb`` and are encrypted at rest, so
    the watcher logs ``CHAT_HISTORY_UNSUPPORTED`` once and emits no
    events. Input-busy precheck and escalation cooldown still protect
    Windsurf.
  - ``antigravity`` — analogous: ``~/.gemini/antigravity/conversations/*.pb``
    is encrypted; same fallback as Windsurf.

## [0.1.51] — 2026-05-23

### Added
- **Cursor chat-history watcher → real ``message.received`` events.** The
  plugin now polls Cursor's per-user chat-history SQLite DB
  (``~/.config/Cursor/User/globalStorage/state.vscdb``, table
  ``cursorDiskKV``, ``bubbleId:*`` keys) and forwards every newly observed
  assistant bubble (``type=2``, non-empty ``.text``) as a
  ``message.received`` event over the autopilot socket. This is the
  long-missing other half of the ``chat.events`` capability — without it
  the koru daemon could see only what *koru* pasted, never what the
  IDE-side LLM actually answered, leaving ``koru.llm_reflect`` (the
  OpenRouter-backed reflection layer) without input. With this watcher
  active, koru can now decide on each cycle whether the LLM is still
  working, has finished, or is asking the user a clarifying question.
- ``koruAutopilot.chatHistoryWatch`` (default true).
- ``koruAutopilot.chatHistoryPollIntervalMs`` (default 4000 ms).

## [0.1.50] — 2026-05-23

### Added
- **Pre-paste check: chat input must be empty.** Before driving a prompt, the
  plugin now sentinel-probes the chat input via select-all + clipboardCopy.
  If the chat input already holds un-submitted text — typically because the
  user is in the middle of typing a reply, or the IDE-side LLM left a
  pending question — the drive aborts with ``ack.verification="input_busy"``
  and ``reason="chat_input_not_empty"`` instead of pasting on top. Without
  this guard koru would either concatenate its prompt onto the user's reply
  (creating a Frankenstein prompt) or overwrite work the user had not yet
  sent.
- ``koruAutopilot.skipWhenInputBusy`` (default true). Set to false to
  restore the legacy 'always paste on top' behavior.

## [0.1.49] — 2026-05-23

### Fixed
- **Cursor on Wayland-native compositors (e.g. GNOME): submit silently
  delivered keystrokes to the wrong OS window.** ``xdotool`` cannot see
  Wayland-native surfaces; it succeeds with exit 0 but routes the synthetic
  ``Return`` / ``Ctrl+Return`` to whatever XWayland window happens to be
  active (often a terminal where ``koru auto`` is running, or a sibling
  VS Code window). Cursor never received the key, so the message stayed in
  the chat input. The probe ladder happily latched onto ``xdotool`` because
  ``rc=0`` looks like success.
- The host-key ladder is now **session-aware**: when ``XDG_SESSION_TYPE`` is
  ``wayland`` or ``WAYLAND_DISPLAY`` is set, ``ydotool`` (which uses
  ``/dev/uinput`` and is accepted by Wayland compositors as legitimate
  hardware input) is tried BEFORE ``xdotool`` for every modifier row. On
  X11 sessions the previous order is preserved.
- Combined with 0.1.48's Cursor-prefers-Ctrl+Return change, the resulting
  Cursor/Wayland order is: ``wtype -M ctrl -k Return`` (only succeeds on
  Sway/wlroots), then ``ydotool key ctrl+Return``, then ``xdotool key
  ctrl+Return`` as a last resort.

### Notes
- For ``ydotool`` to reach Cursor, the Cursor window must be the focused
  Wayland surface. Running ``koru auto`` from a foreground terminal in front
  of Cursor works; switching focus to another window during a drive cycle
  will route the key elsewhere.
- If ``ydotool`` reports ``ydotoold backend unavailable``, install and
  enable the system service (``systemctl --user enable --now ydotool``)
  for lower-latency injection. Without the daemon ``ydotool`` still works
  via ``/dev/uinput`` (the user must be in the ``input`` group).

## [0.1.48] — 2026-05-23

### Fixed
- **Cursor on Wayland: submit silently inserted a newline instead of sending.**
  The chat textarea on recent Cursor builds (Linux, GNOME/Wayland with XWayland)
  treats plain `Enter` as "newline" and reserves `Ctrl+Enter` for "submit". The
  host-key ladder previously tried `Return` first; on Wayland `wtype -k Return`
  fails (compositor lacks the virtual-keyboard protocol) and `xdotool key
  Return` succeeds with exit 0 but only adds a newline to the input. The next
  autonomous cycle re-pasted the same prompt with another newline above it.
- For `ide === "cursor"` we now try `Ctrl+Return` BEFORE plain `Return` on every
  injector (`wtype` / `xdotool` / `ydotool`). Other IDEs keep the old order.

### Added
- `koruAutopilot.submitHostKey` (`auto` | `Return` | `ctrl+Return`, default
  `auto`) — explicit override for users whose chat input expects a different
  submit shortcut.

## [0.1.47] — 2026-05-22

### Fixed
- **Cursor: submit step silently failed** (text was pasted into chat but never
  sent). The submit ladder fell through to `vscode.commands.executeCommand("type",
  { text: "\n" })`, which in Cursor's multi-line chat textarea only inserts a
  newline. The daemon then logged `winning_submit=type:` with
  `verification=strict` and the next autonomous cycle drove the same prompt
  again, accumulating pasted-but-not-sent messages in the chat.
- For `ide === "cursor"`, after the registered-command ladder is exhausted we
  now try `_tryHostKeySubmit()` (real **Enter** via `wtype` / `xdotool` /
  `ydotool`) before any `type:` fallback. Cursor accepts the host-level Enter
  as "submit chat".
- Poisoned cache: any previously cached `submit = "type:…"` value for Cursor
  is now invalidated on load, so existing installations recover without a
  manual reset.

## [0.1.12] — 2026-05-18

### Added
- **Probe ladder** (`koruAutopilot.probeLadder`, default on): tries focus/paste/submit
  commands in order, verifies focus left the file editor and paste did not contaminate
  the active editor, caches winning command IDs in extension global state.
- **`koru: Calibrate chat probe ladder`**: runs a harmless probe token through the
  ladder and shows which commands won.
- **`ack` metadata**: `winning_focus_open`, `winning_paste`, `winning_submit`,
  `probe_ladder` for daemon diagnostics.

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
