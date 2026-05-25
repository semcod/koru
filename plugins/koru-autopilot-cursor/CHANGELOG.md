# Changelog — koru autopilot (Cursor edition)

All notable changes to this extension will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.76] — 2026-05-25

### Changed (architecture — Cursor split)

- **Cursor moved to a dedicated VSIX**: `koru-autopilot-cursor` is now
  a standalone package with extension ID `semcod.koru-autopilot-cursor`.
  Sibling IDEs (VS Code / VSCodium / Windsurf / Antigravity) stay in
  `koru-autopilot-vscode` until each is extracted in a follow-up
  iteration. A regression in Cursor focus/paste/submit logic can no
  longer leak into another IDE's runtime — and vice versa.
- Runtime guard: the new VSIX silently no-ops on any host whose
  `vscode.env.appName` does not contain "cursor". The legacy
  `koru-autopilot-vscode` plugin now refuses to activate on Cursor
  so the two builds never race for the same Unix socket.
- Migration: `koru up` / `cursor --install-extension` automatically
  picks the matching VSIX. Existing Cursor installs that still carry
  the legacy `semcod.koru-autopilot-vscode` extension should run:
  `cursor --uninstall-extension semcod.koru-autopilot-vscode`.
- Daemon: per-IDE expected version table
  (`koruide.plugin_version.EXPECTED_PLUGIN_VERSIONS`); strict version
  check resolves the expected version from the connected plugin's IDE.

## [0.1.75] — 2026-05-25

### Fixed
- **Cursor: drive hid the chat panel and pasted-but-did-not-submit.**
  Symptom: user had Composer visible on the right column; after a
  drive started the panel disappeared and the prompt landed in
  something else (no submit, no bubble in `cursorDiskKV`). Plugin
  honestly reported `submit_unverified` (thanks to 0.1.74's bubble-DB
  cross-check) but the underlying focus path was wrong.

  Root cause: `composer.openAsPane` is a **toggle** in current Cursor
  builds — running it on a *visible* Composer panel hides it. The
  plugin had cached `composer.openAsPane` as the focus_open winner
  from a previous drive (when chat was closed and the command did
  open it). Every subsequent drive then ran the cached toggle and
  closed the panel the user was watching.

  Fix:
  - `cursor.ts.sanitizeProbeCache` now discards `composer.openAsPane`
    just like it discards `aichat.newchataction`. Toggles are
    state-dependent and unsafe as cached winners.
  - `focusChat()` now runs a **focus-only preflight** whenever the
    open-command ladder contains any toggle (e.g. `composer.openAsPane`,
    `workbench.action.toggle*`). The preflight tries
    `composer.focusComposer` first; if the editor snapshot heuristic
    confirms chat is the foreground surface, we skip the open commands
    entirely. This means: when Composer is already visible we never
    touch the toggle; when Composer is closed the preflight fails
    (file editor still active) and the ladder falls through to
    `composer.openComposer` (the non-toggling opener).
  - The focus-only path additionally cross-checks
    `chatFocusHeuristic(editorSnapshot)` after `focusChatInput` to
    catch the case where `composer.focusComposer` returns `true`
    while the file `TextEditor` is still active — that means chat is
    "logically" focused but not visible, which would otherwise hand
    the next paste to an invisible target.

## [0.1.74] — 2026-05-25

### Fixed
- **Cursor: paste landed but submit silently failed.** Plugin reported
  `winning_submit=composer.sendToAgent` + `input_probe/select-copy=ok`
  + `ok=true`, but the user saw the prompt sitting in the chat input
  with no message sent.

  Root cause: the post-submit probe (`select-all` + `clipboardCopy`)
  is unreliable on Cursor's chat webview. When `composer.focusComposer`
  only focused the surrounding chrome (not the input contenteditable),
  `editor.action.selectAll` fell back to the underlying file
  `TextEditor` and the probe returned unrelated file content. That
  content did not contain the prompt tail, so `decideSubmitCleared`
  returned `cleared=true` and we cached `composer.sendToAgent` as the
  winner — even though no `type=1` user bubble was ever written to
  `cursorDiskKV`.

  The bubble-DB cross-check existed but was gated on
  `probe === null` and never triggered for non-null garbage probes.

  Fix:
  - `verifySubmitStep` now consults `_verifySubmitViaCursorBubble` for
    **every** Cursor submit (when `probe`-cleared and prompt length
    ≥ 4), not only when the probe returned `null`. The bubble DB is
    ground truth: if `cursorDiskKV` has no fresh `type=1` row with the
    prompt tail after submit, the candidate is rejected and the ladder
    tries the next one (`composer.acceptComposerStep`,
    `composer.startComposerPrompt`, …).
  - Bubble-poll deadline bumped from 1.2 s to 2.5 s so the debounced
    writer has time to materialize the new row before we give up.

## [0.1.73] — 2026-05-25

### Fixed
- **Plugin now reloads its own window when the daemon rejects it for a
  version mismatch.** Previously the daemon told the user to run
  `Developer: Reload Window` and Koru's Python side tried to do it for
  them via `wtype Ctrl+Shift+P`, which silently fails on most
  GNOME/mutter sessions (the compositor doesn't expose
  `virtual-keyboard-v1` to arbitrary clients). The user then sat in a
  permanent `plugin_not_connected` state.

  Fix: when the daemon replies with an `error` envelope whose message
  contains `plugin version mismatch`, the extension now calls
  `vscode.commands.executeCommand('workbench.action.reloadWindow')`
  itself. This bypasses every xdotool/wtype/ydotool quirk because the
  IDE reloads itself natively. A 60-second cooldown stored in
  `globalState` ensures we never enter a reload loop, and the new
  `koruAutopilot.reloadOnVersionMismatch` setting (default `true`) lets
  power users keep the manual recovery if they prefer it.

## [0.1.72] — 2026-05-25

### Fixed
- **VSCodium submit now tries verified in-process chat commands before OS
  click/key fallbacks.** This avoids paste-only failures on Wayland where the
  prompt remains in the chat input after ``ydotool ctrl+Return`` or a
  bottom-right click reports success.

## [0.1.71] — 2026-05-25

### Fixed
- **Cursor: drive failed with `focus_open/all-candidates=fail` and
  `focus_input/command=ok:workbench.action.focusAuxiliaryBar`.** Two bugs:
  1. ``focusAuxiliaryBar`` was cached as the focus-input winner even though
     it only focuses the auxiliary bar chrome, not the Composer textarea.
     Every ``focus_open`` attempt then failed snapshot verification because
     the file editor stayed active.
  2. ``composer.showComposer`` is not registered in recent Cursor builds;
     ``composer.openComposer`` is. Valid open commands were rejected because
     Cursor keeps the file ``TextEditor`` active while Composer lives in the
     auxiliary bar — ``verifyFocusAfterOpen`` never saw a snapshot change.

  Fix:
  - ``focusChatInput`` only accepts/caches commands that pass
    ``isSpecificChatInputFocusCommand`` (chat/composer/cascade).
  - Cursor strategy blocklists ``focusAuxiliaryBar`` / ``focusPanel`` /
    ``focusSideBar`` from the focus-input ladder and clears poisoned cache
    entries on load.
  - Cursor ``focusOpenCommandsDefaults`` now lead with ``composer.openComposer``.
  - New ``trustFocusOpenCommand`` strategy hook: composer/chat surface
    commands are accepted after ``executeCommand`` succeeds without
    requiring editor-snapshot proof.

## [0.1.70] — 2026-05-25

### Fixed
- **VSCodium no longer reports paste-only as a sent chat message when the
  post-submit probe is inconclusive.** In strict host-submit mode,
  ``sentinel unchanged`` / ``null`` probes are now treated as retry/failure
  instead of success. This prevents ``ydotool key ctrl+Return`` from producing
  a false ``message.sent`` event when the chat input still contains the prompt.

## [0.1.69] — 2026-05-25

### Fixed
- **Cursor: drive pasted to the terminal instead of the chat (regression
  introduced in 0.1.68).** `koru auto` runs from a terminal, so when 0.1.68
  disabled the VS Code internal `editor.action.clipboardPasteAction` path
  for Cursor, the ladder fell through to host clipboard + `xdotool ctrl+v`
  / `ydotool ctrl+v`. Those synthetic keystrokes target whichever OS window
  currently has keyboard focus — the terminal, not Cursor — so the paste
  reported `ok` (xdotool exit 0) but the chat input stayed empty and
  every registered submit command (`composer.sendToAgent`,
  `workbench.action.chat.submit`) no-oped, failing the `cursorDiskKV`
  bubble check.

  Fix:
  - **Re-enable `editor.action.clipboardPasteAction` for Cursor.** It is a
    VS Code internal command, not a host keystroke, so it pastes into the
    focused VS Code element (the chat input) without needing the Cursor
    window to have OS keyboard focus. The 0.1.61 verified-clipboard-seed
    logic still applies, so the OS clipboard never leaks a stale value.
  - **Refuse host-clipboard paste for Cursor.** Only VSCodium uses
    `tryHostClipboardPaste`. For Cursor we go through direct-command
    paste (`composer.typeText` / `cursor.action.chat.typeText` if
    registered), then internal `editor.action.clipboardPasteAction`,
    then the `type` command — all of which run inside VS Code and do
    not depend on OS keyboard focus.
  - **Refuse host-key / host-click submit for Cursor.** When registered
    submit commands fail their `cursorDiskKV` verification (chat input
    was empty / Composer not foreground / wrong tab), `koru auto` now
    surfaces a clean `cursor-submit-unavailable` failure instead of
    pseudo-succeeding via a synthetic Ctrl+Return aimed at the terminal.
- **VSCodium submit verification no longer accepts arbitrary non-empty
  clipboard probe text as success.** Host-click/host-key submit now requires
  the post-submit input probe to be empty. If the probe copies unrelated text
  from the editor or UI, the candidate is discarded and Koru reports
  `submit_unverified` instead of emitting a false `message.sent`.

## [0.1.68] — 2026-05-25

### Fixed
- **Cursor (Wayland): drive no longer stops at paste-without-submit when
  ``ydotool key ctrl+Return`` exits 0 but the chat webview ignores it.**
  After registered submit commands fail ``cursorDiskKV`` verification, the
  fallback ladder now tries a bottom-right Send-button click (``ydotool`` first
  on Wayland, ``xdotool`` on X11) before host-key chords — the same path that
  fixed VSCodium in 0.1.67.
- **Cursor paste: skip ``editor.action.clipboardPasteAction`` fallback** so
  the probe cache cannot latch onto a clipboard-reading command that misses
  the chat webview. Cursor now prefers ``composer.typeText`` / host
  ``wl-copy``+``Ctrl+V`` before ``type`` fallback.
- **Cursor focus-input ladder** now tries ``composer.focusComposer`` and
  related composer/chat focus commands before generic VS Code candidates.

## [0.1.67] — 2026-05-25

### Fixed
- VSCodium submit now tries an automatic bottom-right Send-button click
  based on the active window geometry before falling back to host key
  chords. This prevents the drive path from only pasting text when
  ``Ctrl+Return`` is accepted by the OS injector but not by the chat
  webview.

## [0.1.66] — 2026-05-25

### Fixed (STARTER-242)
- **Wire ack payloads are now capped before they hit the daemon socket.**
  Root cause of the ~170 KB truncated NDJSON crash: failure-path
  ``diagnostics.rejected`` entries included full editor snapshots
  (``before`` / ``after`` document text) and long ``operation_trace``
  steps. The CLI client read a partial JSON line and ``koru auto`` exited
  with ``ProtocolError: Unterminated string``.

  Fix:
  - New ``ack-payload.ts`` sanitizes every outbound ``ack`` / ``error``
    envelope in ``send()``: strips editor snapshots from
    ``diagnostics.rejected``, caps ``operation_trace`` (20 steps, short
    reason/command strings), caps ``focusOpenCandidates``, and drops
    heavy fields if the line still exceeds 48 KiB.
  - Daemon ``_cap_ack_info_for_cli`` mirrors the same budget before
    relaying plugin acks to the CLI (defense in depth).
  - ``koruide.client`` already maps parse failures to a structured
    ``error`` reply so the autonomous loop survives a bad frame.

## [0.1.65] — 2026-05-25

### Added (diagnostics for STARTER-242)
- **Oversized envelope telemetry.** ``send(env)`` now measures
  ``Buffer.byteLength(JSON.stringify(env) + "\n", "utf8")`` before
  writing to the socket. Envelopes >32 KB emit a ``OUT_OVERSIZED``
  ``safeLog`` entry that lists per-field byte counts, so the next
  reproduction of the cycle #632 crash (~170 KB ack truncated mid-string
  on the CLI side) pinpoints which field is exploding (operation_trace
  vs winning_* vs verification message). No behavioural change.
- Companion daemon-side telemetry: ``AutopilotDaemon._send`` logs
  ``send to <addr> oversized: bytes=… head=…`` when the relay frame
  exceeds 32 KB.

## [0.1.64] — 2026-05-25

### Fixed
- **Cursor: drive pasted the prompt and reported `verification=strict
  ok=true` but the user's chat input remained populated; the submit
  silently happened in a brand-new chat tab.** Root cause: the generic
  `focus_open` ladder defaults included `aichat.newchataction`, which in
  Cursor opens a **new** Composer/Agent tab. Once that command won the
  probe, every subsequent drive pasted + submitted into the fresh tab
  while the user was still looking at the original chat — so the
  `cursorDiskKV` watcher correctly emitted `message.sent` (the message
  *was* sent, just in a different tab) and the v0.1.63 bubble-tail
  verification confirmed it, hiding the regression.

  Fix:
  1. `cursor.ts` now ships an explicit `focusOpenCommandsDefaults()` list
     that points at the *existing* chat surface
     (`composer.showComposer`, `composer.openAsPane`,
     `cursor.composer.open`, `workbench.panel.chat.view.copilot.focus`,
     `workbench.panel.chat`, …) and deliberately excludes
     `aichat.newchataction`.
  2. `sanitizeProbeCache` now invalidates `entry.focusOpen` when it
     equals `aichat.newchataction`, so any cached winner from a
     pre-0.1.64 plugin is discarded on the next drive and the ladder
     re-probes against the correct commands.

  New unit tests (`cursor.test.ts → testFocusOpenDefaultsExcludeNewChatTab`,
  extended `testProbeCacheSanitizationForCursor`) lock the invariant.

## [0.1.63] — 2026-05-25

### Fixed
- **Cursor: drive reported `verification=strict ok=true` but the prompt
  stayed in the chat input.** Root cause: Cursor's chat surface is a
  webview, so the post-submit `editor.action.selectAll` +
  clipboard-copy probe has no effect and returns `null`. The legacy
  `decideSubmitCleared` falls closed to `cleared=true` on `null`, so a
  silently-failing `composer.sendToAgent` was cached as the winning
  submit command and the ladder never re-probed. Cursor submits are now
  cross-checked against `cursorDiskKV`: the plugin captures the highest
  `bubbleId:*` rowid right before invoking the submit command, then
  looks for a fresh `type = 1` (user) bubble whose text contains the
  tail of the pasted prompt. When the DB confirms the bubble → verified
  (`route=cursor-bubble-db ok=true`). When the DB query worked but no
  matching bubble appeared → submit is treated as failed, the cached
  winner is discarded, and the ladder advances to the next candidate.
  Daemon logs now show `submit_verify:route=cursor-bubble-db ok=...`
  so the user can see whether Cursor actually accepted the message.

## [0.1.61] — 2026-05-24

### Fixed
- **Cursor: ticket prompts no longer paste the user's clipboard instead of
  the drive text.** The probe ladder had cached
  `editor.action.clipboardPasteAction` as the paste winner. That VS Code
  command ignores the `text` argument and reads the OS clipboard, so Koru
  reported `verification=strict` while the chat received unrelated copied
  content. Direct paste now seeds the clipboard with a verified write before
  invoking clipboard-reading commands, restores the user's clipboard
  afterward, and the Cursor strategy discards stale clipboard-paste cache
  entries so `cursor.action.chat.typeText` / `composer.typeText` are tried
  first.

## [0.1.60] — 2026-05-24

### Fixed
- **Transparent per-operation routing diagnostics.** Chat drive ACKs now carry
  an `operation_trace` showing the independent focus, input-busy probe, paste,
  submit, submit verification, and message-sent routes. The daemon logs the
  same trace so regressions such as "pasted but not sent" identify the exact
  failing operation and host tool (`wtype`, `xdotool`, `ydotool`, click, or
  registered IDE command) instead of only reporting the final winner.

## [0.1.59] — 2026-05-24

### Fixed
- **Cursor/Wayland: paste no longer leaks the user's previous clipboard
  contents into chat.** The input-busy probe saves and restores the clipboard
  before paste, so on Wayland (where `vscode.env.clipboard.writeText` is
  asynchronous against the underlying `wl-copy` / selection-manager pipeline)
  the immediate `editor.action.clipboardPasteAction` could land the *restored*
  pre-probe clipboard into the Cursor chat webview instead of the prompt text.
  The plugin now writes the prompt with a verified read-back retry loop and
  aborts the paste if the clipboard does not match, returning a clean
  `ok: false` instead of clobbering the chat with stale user text. The host
  clipboard path (`wl-copy` + Ctrl+V) also mirrors the prompt into
  `vscode.env.clipboard` so any webview-internal paste route reads the same
  text.

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
