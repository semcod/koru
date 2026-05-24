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
  return [
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
  return [
    "composer.sendToAgent",
    "composer.acceptComposerStep",
    "composer.startComposerPrompt",
    "composer.startComposerPrompt2",
    "composer.submit",
    "aichat.submit",
    // Generic VS Code candidates as last-resort fallback.
    "workbench.action.chat.submit",
    "workbench.action.chat.acceptInput",
    "workbench.action.chat.send",
    "workbench.action.chat.sendMessage",
    "workbench.action.interactive.accept",
  ];
}

function focusInputCommandsPrefix(): string[] {
  return [];
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

function focusOpenCommandsDefaults(): string[] {
  return [];
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
