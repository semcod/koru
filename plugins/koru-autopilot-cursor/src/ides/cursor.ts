/**
 * Cursor IDE strategy.
 *
 * The **single source of truth** for everything Cursor-specific on the
 * extension side: detection, chat paste/submit command order, host-key
 * preference, probe-cache sanitization, and submit fallback policy.
 *
 * Other IDEs (VS Code, VSCodium, Windsurf, Antigravity) must not be
 * affected by changes in this file.
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "cursor";

function detect(appName: string): string | undefined {
  return appName.toLowerCase().includes("cursor") ? ID : undefined;
}

function pasteDirectCommandsPrefix(): string[] {
  // Cursor 1.x removed ``composer.*`` / ``cursor.action.*`` on many builds;
  // ``workbench.action.chat.typeText`` is the registered paste on Agent/Glass.
  return [
    "workbench.action.chat.typeText",
    "workbench.action.chat.insertText",
    "cursor.action.chat.typeText",
    "composer.typeText",
    "aichat.typeText",
  ];
}

/**
 * Cursor's submit command in recent builds is `composer.sendToAgent` —
 * it sends whatever is currently in the Composer/Agent chat input. The
 * legacy `composer.submit` / `aichat.submit` candidates are NOT
 * registered any more, so we kept falling through to the host-key
 * ladder where `xdotool key Return` and `xdotool key ctrl+Return`
 * both exit 0 but only insert a newline. Try the registered command
 * FIRST so we never need to forge keystrokes.
 */
function submitCommandsOverride(): string[] {
  // Cursor 1.x removed ``composer.*`` entirely; the only registered
  // submit on modern builds is ``workbench.action.chat.submit``.
  // ``composer.sendToAgent`` is kept at the tail for compatibility
  // with older builds where ``getCommands`` still lists it.
  return [
    "workbench.action.chat.stopListeningAndSubmit",
    "workbench.action.chat.submit",
    "workbench.action.chat.acceptInput",
    "workbench.action.chat.send",
    "workbench.action.chat.sendMessage",
    "workbench.action.interactive.accept",
    // Legacy Cursor 0.x candidates — kept last as fallback.
    "composer.sendToAgent",
    "composer.acceptComposerStep",
    "composer.submit",
    "aichat.submit",
  ];
}

function focusInputCommandsPrefix(): string[] {
  // Glass / Cursor 1.x: ``glass.focusInput`` is the registered textarea focus
  // on Agent builds; ``workbench.action.chat.focusInput`` when present.
  // ``composer.focusComposer`` / ``panel.chat.view.*`` only focus panel chrome.
  return [
    "glass.focusInput",
    "workbench.action.chat.focusInput",
    "chat.action.focus",
    "workbench.chat.action.focusLastFocused",
    "cursor.composer.focus",
  ];
}

/** Generic VS Code focus commands that are NOT chat input on Cursor. */
function focusInputCommandsBlocklist(): string[] {
  return [
    "workbench.action.focusAuxiliaryBar",
    "workbench.action.focusPanel",
    "workbench.action.focusSideBar",
    "composer.focusComposer",
    "workbench.panel.chat.view.copilot.focus",
    "workbench.panel.aichat.view.copilot.focus",
  ];
}

function acceptFocusInputCommand(command: string): boolean {
  const normalized = command.toLowerCase();
  if (
    normalized.includes("panel.chat.view")
    || normalized.includes("panel.aichat.view")
    || normalized === "composer.focuscomposer"
    || normalized.startsWith("notebook.cell.")
  ) {
    return false;
  }
  return (
    normalized === "workbench.action.chat.open"
    || normalized.includes("glass.focusinput")
    || normalized.includes("focusinput")
    || normalized.includes("chat.action.focus")
    || normalized.includes("focuslastfocused")
  );
}

function acceptFocusOpenCommand(command: string): boolean {
  return trustFocusOpenCommand(command);
}

function isToxicCursorPasteCache(paste: string): boolean {
  if (
    paste === "editor.action.clipboardPasteAction" ||
    paste === "editor.action.selectionClipboardPaste" ||
    paste === "editor.action.pasteAs" ||
    paste === "execPaste" ||
    paste === "paste" ||
    paste === "workbench.action.terminal.paste"
  ) {
    return true;
  }
  const lower = paste.toLowerCase();
  return (
    /clipboard.*paste|paste.*clipboard/.test(lower)
    || lower.includes("terminal.paste")
  );
}

function preferCtrlSubmit(): boolean {
  // Cursor's chat textarea treats plain `Return` as a newline; only
  // `Ctrl+Return` actually submits.
  return true;
}

function sanitizeProbeCache(
  entry: ProbeCacheEntry,
  opts: { isWayland: boolean }
): void {
  // ``editor.action.clipboardPasteAction`` ignores the ``text`` argument and
  // reads the OS clipboard. Cached as paste winner it caused ticket prompts to
  // be replaced by whatever the user had copied earlier. Prefer re-probing
  // ``cursor.action.chat.typeText`` / ``composer.typeText`` which take text
  // directly (or clipboard paste after verified seed in extension.ts).
  if (typeof entry.paste === "string" && isToxicCursorPasteCache(entry.paste)) {
    entry.paste = undefined;
  }
  // ``composer.startComposerPrompt*`` is handled only by the dedicated
  // Cursor fast path. Cached as the probe-ladder paste winner it opens a
  // fresh Composer tab while the user watches another chat — paste looks
  // successful in traces but the visible chat stays empty.
  if (
    typeof entry.paste === "string" &&
    /startcomposerprompt/i.test(entry.paste)
  ) {
    entry.paste = undefined;
  }
  // ``aichat.newchataction`` opens a *new* chat tab in Cursor. Cached as the
  // focus_open winner it makes every subsequent drive paste+submit into a
  // fresh tab while the user is still looking at the original chat — so
  // they only see "pasted but not submitted" in the chat they were
  // watching. Force re-probing so we land on
  // ``composer.showComposer`` / ``workbench.panel.chat`` instead.
  //
  // ``composer.openAsPane`` is a *toggle*: when the user has the chat
  // panel already open, running this command hides it. The plugin then
  // pastes into a now-invisible target and the registered submit
  // commands no-op (no new bubble in ``cursorDiskKV``). Cached as the
  // focus_open winner it produces the exact "schowal panel + wkleil ale
  // nie wysłał" symptom we just hit on Cursor builds where the user
  // already had Composer visible. Never cache it — re-probe each drive
  // so the ladder picks the non-toggling ``composer.openComposer`` when
  // Composer is closed and the focus-only short-circuit when it is open.
  if (typeof entry.focusOpen === "string") {
    const focusOpen = entry.focusOpen.split("+")[0]?.trim() ?? entry.focusOpen;
    if (
      focusOpen === "aichat.newchataction" ||
      focusOpen === "composer.openAsPane" ||
      focusOpen === "composer.openChatAsEditor" ||
      focusOpen === "composer.openBrowserTab" ||
      focusOpen === "composer.openAddContextMenu" ||
      focusOpen === "workbench.panel.chat" ||
      focusOpen.includes("panel.chat.view") ||
      focusOpen.includes("panel.aichat.view")
    ) {
      entry.focusOpen = undefined;
    }
  }
  // ``workbench.action.focusAuxiliaryBar`` exits 0 but only focuses the
  // auxiliary bar chrome — not the Composer textarea. Cached as focusInput
  // it blocked every focus_open attempt because snapshot verify never saw
  // chat focus.
  if (typeof entry.focusInput === "string") {
    const blocked = new Set(focusInputCommandsBlocklist().map((c) => c.toLowerCase()));
    const cmd = entry.focusInput.toLowerCase();
    if (
      blocked.has(cmd)
      || cmd === "composer.focuscomposer"
      || cmd.includes("panel.chat.view")
      || cmd.includes("panel.aichat.view")
      || (!cmd.includes("chat") && !cmd.includes("glass") && !cmd.includes("composer") && !cmd.includes("cascade"))
    ) {
      entry.focusInput = undefined;
    }
  }
  // Discard "type:" wins (legacy plugin ≤0.1.46 cached typing `\n` as the
  // submit; in Cursor that just inserts a newline).
  if (
    typeof entry.submit === "string" &&
    (entry.submit.startsWith("type:") || entry.submit === "type")
  ) {
    entry.submit = undefined;
    return;
  }
  if (typeof entry.submit !== "string") return;
  const cmd = entry.submit;
  // Legacy ``composer.*`` submit commands report ``ok`` on many Cursor 1.x /
  // Glass builds but do not create a user bubble. Cached winners skip
  // ``workbench.action.chat.stopListeningAndSubmit`` and trap drives on
  // host-key false positives (especially on Wayland).
  if (/^composer\.(sendToAgent|acceptComposerStep|submit)$/i.test(cmd) || cmd === "aichat.submit") {
    entry.submit = undefined;
    return;
  }
  // On Wayland, xdotool cannot reach native Cursor windows at all — every
  // xdotool host-key probe is a false positive (exit 0, no effect).
  // Discard the cached winner so the ladder re-probes
  // composer.sendToAgent / ydotool.
  if (opts.isWayland && cmd.startsWith("xdotool ")) {
    entry.submit = undefined;
    return;
  }
  // Plugin 0.1.47 cached host-level plain `Return` for Cursor. On Linux
  // (Wayland with XWayland) `xdotool key Return` exits 0 even though
  // Cursor's chat textarea treats it as a newline rather than a submit.
  const hasCtrl = /\bctrl\b/i.test(cmd) || /-M\s+ctrl\b/.test(cmd);
  const isHostKey =
    /^(xdotool|ydotool)\s+key\s+Return$/.test(cmd) ||
    /^wtype(\s+-[Mm]\s+\S+)*\s+-k\s+Return$/.test(cmd);
  if (!hasCtrl && isHostKey) {
    entry.submit = undefined;
  }
}

/**
 * Cursor-specific ``focus_open`` order. The generic default list includes
 * ``aichat.newchataction`` which in Cursor opens a **new** chat tab — the
 * subsequent ``paste`` + ``composer.sendToAgent`` then write to the new
 * tab and the user sees nothing happen in their existing chat. We list
 * every command that targets the *existing* Composer/Agent surface
 * explicitly so the probe ladder never falls through to
 * ``aichat.newchataction``.
 */
function focusOpenCommandsDefaults(): string[] {
  // Cursor 1.x removed the ``composer.*`` namespace entirely
  // (``getCommands(false)`` returns 0 matches). The modern surface is
  // ``workbench.action.chat.*``. ``composer.openAsPane`` was a *toggle*
  // that hid the panel when it was already visible — never include it
  // in defaults (kept in ``sanitizeProbeCache`` for legacy caches).
  // Legacy ``composer.openComposer`` / ``cursor.composer.open`` are
  // kept at the tail for older Cursor builds that still expose them.
  return [
    "workbench.action.chat.open",
    "workbench.action.chat.openagent",
    "workbench.action.openChat",
    "composer.openComposer",
    "cursor.composer.open",
    "cursor.composer.focus",
  ];
}

/**
 * Cursor keeps the file ``TextEditor`` active while Composer lives in the
 * auxiliary bar webview, so ``verifyFocusAfterOpen`` (editor snapshot) always
 * rejects valid open commands. Trust composer/chat surface commands when
 * ``executeCommand`` returned true.
 */
function trustFocusOpenCommand(command: string): boolean {
  const n = command.toLowerCase();
  if (
    n === "aichat.newchataction"
    || n === "workbench.panel.chat"
    || n.includes("panel.chat.view")
    || n.includes("panel.aichat.view")
    || n === "composer.focuscomposer"
    || n === "composer.openaddcontextmenu"
    || n === "composer.openchataseditor"
    || n === "composer.openbrowsertab"
  ) {
    return false;
  }
  return (
    n.startsWith("composer.open")
    || n.includes("cursor.composer.open")
    || n.startsWith("workbench.action.chat.open")
    || n === "workbench.action.openchat"
  );
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return false;
}

export const cursorStrategy: IdeStrategy = {
  id: ID,
  label: "Cursor",
  detectIde: detect,
  pasteDirectCommandsPrefix,
  submitCommandsOverride,
  focusInputCommandsPrefix,
  preferCtrlSubmit,
  sanitizeProbeCache,
  focusOpenCommandsDefaults,
  trustFocusOpenWithoutEditorSnapshot,
  trustFocusOpenCommand,
  focusInputCommandsBlocklist,
  acceptFocusInputCommand,
  acceptFocusOpenCommand,
  submitFallback: {
    // When the host-key submit produced no effect we must NOT fall back to
    // typing newlines into the chat textarea — those just accumulate
    // unsent text and the user sees no message in the chat. Return
    // `cursor-submit-unavailable` instead so the daemon retries via a
    // different backend.
    refuseTypeNewlineFallback: true,
  },
};

registerStrategy(cursorStrategy);
