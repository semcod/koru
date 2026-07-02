/**
 * VSCodium IDE strategy.
 *
 * Keep Codium-specific host-key behavior out of the generic VS Code path.
 * In Codium on Wayland, plain Return can report success while leaving the
 * pasted chat text in the input. Prefer Ctrl+Return first so the submit probe
 * does not cache a no-op Return as the winner.
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";
import { isVscodiumHost } from "./vscodium-host";

const ID = "vscodium";

function detect(appName: string): string | undefined {
  return isVscodiumHost(appName) ? ID : undefined;
}

function pasteDirectCommandsPrefix(): string[] {
  return [];
}

function submitCommandsOverride(): string[] | null {
  return null;
}

function focusInputCommandsPrefix(): string[] {
  return [
    "chatgpt.sidebarView.focus",
    "chatgpt.sidebarSecondaryView.focus",
    "chat.action.focus",
    "workbench.action.chat.focusInput",
  ];
}

function preferCtrlSubmit(): boolean {
  return true;
}

function sanitizeProbeCache(
  entry: ProbeCacheEntry,
  _opts: { isWayland: boolean }
): void {
  if (typeof entry.focusOpen === "string" && isUnsafeVSCodiumFocusOpen(entry.focusOpen)) {
    entry.focusOpen = undefined;
  }
  if (typeof entry.submit !== "string") return;
  const cmd = entry.submit;
  const hasCtrl = /\bctrl\b/i.test(cmd) || /-M\s+ctrl\b/.test(cmd);
  const isHostPlainReturn =
    /^(xdotool|ydotool)\s+key\s+Return$/.test(cmd) ||
    /^wtype(\s+-[Mm]\s+\S+)*\s+-k\s+Return$/.test(cmd);
  if (!hasCtrl && isHostPlainReturn) {
    entry.submit = undefined;
  }
}

function isUnsafeVSCodiumFocusOpen(command: string): boolean {
  const normalized = command.trim().toLowerCase();
  return (
    normalized.includes("settings") ||
    normalized.includes("preferences") ||
    normalized.includes("focusinput") ||
    normalized.includes("newchataction") ||
    normalized.includes("opennewchat") ||
    normalized.includes("newchat") ||
    normalized.includes("openinnewwindow") ||
    normalized.includes("newwindow") ||
    normalized.includes("totheside")
  );
}

function focusOpenCommandsDefaults(): string[] {
  return [
    "chatgpt.sidebarView.open",
    "chatgpt.openSidebar",
    "chatgpt.sidebarSecondaryView.open",
    "workbench.action.chat.openInSidebar",
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
  ];
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return false;
}

export const vscodiumStrategy: IdeStrategy = {
  id: ID,
  label: "VSCodium",
  detectIde: detect,
  pasteDirectCommandsPrefix,
  submitCommandsOverride,
  focusInputCommandsPrefix,
  preferCtrlSubmit,
  sanitizeProbeCache,
  focusOpenCommandsDefaults,
  trustFocusOpenWithoutEditorSnapshot,
  submitFallback: {
    refuseTypeNewlineFallback: false,
  },
};

registerStrategy(vscodiumStrategy);
