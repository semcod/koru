/**
 * Microsoft VS Code IDE strategy (extension side).
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "vscode";

function detect(appName: string): string | undefined {
  const lowered = appName.toLowerCase();
  // Qoder masquerades as "Visual Studio Code" in appName; its install
  // paths in the detect probe carry the real product name.
  if (lowered.includes("qoder")) return undefined;
  if (
    lowered.includes("visual studio code") ||
    (lowered.includes("code") &&
      !lowered.includes("cursor") &&
      !lowered.includes("codium") &&
      !lowered.includes("windsurf") &&
      !lowered.includes("antigravity"))
  ) {
    return ID;
  }
  return undefined;
}

function pasteDirectCommandsPrefix(): string[] {
  return [];
}

function submitCommandsOverride(): string[] | null {
  return null;
}

function focusInputCommandsPrefix(): string[] {
  return [];
}

function preferCtrlSubmit(): boolean {
  return false;
}

function sanitizeProbeCache(_entry: ProbeCacheEntry, _opts: { isWayland: boolean }): void {
  // These commands can behave like panel toggles in VS Code and hide chat.
  const unsafeFocusOpen = new Set<string>([
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
    "workbench.panel.aichat.view.copilot.focus",
    "workbench.action.chat.openagent",
    "workbench.action.chat.openask",
    "aichat.newchataction",
  ]);
  const focusOpen = String(_entry.focusOpen || "").trim().toLowerCase();
  if (
    focusOpen &&
    (unsafeFocusOpen.has(focusOpen) ||
      focusOpen.includes("newchat") ||
      focusOpen.includes("newwindow") ||
      focusOpen.includes("totheside"))
  ) {
    _entry.focusOpen = undefined;
  }
}

function focusOpenCommandsDefaults(): string[] {
  return ["workbench.action.chat.open"];
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return false;
}

export const vscodeStrategy: IdeStrategy = {
  id: ID,
  label: "VS Code",
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

registerStrategy(vscodeStrategy);
