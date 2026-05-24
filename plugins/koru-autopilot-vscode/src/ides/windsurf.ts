/**
 * Windsurf IDE strategy (extension side).
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "windsurf";

function detect(appName: string): string | undefined {
  return appName.toLowerCase().includes("windsurf") ? ID : undefined;
}

function pasteDirectCommandsPrefix(): string[] {
  return [
    "windsurf.sendTextToChat",
    "windsurf.action.chat.typeText",
    "windsurf.action.cascade.typeText",
    "windsurf.chat.typeText",
    "windsurf.cascade.typeText",
    "cascade.typeText",
  ];
}

function submitCommandsOverride(): string[] {
  const generic = [
    "workbench.action.chat.submit",
    "workbench.action.chat.acceptInput",
    "workbench.action.chat.send",
    "workbench.action.chat.sendMessage",
    "workbench.action.interactive.accept",
    "composer.submit",
    "aichat.submit",
  ];
  return [
    "windsurf.action.cascade.submit",
    "windsurf.action.submitCascade",
    "windsurf.action.submitChat",
    "windsurf.action.chat.submit",
    "windsurf.chat.submit",
    "windsurf.cascade.submit",
    "cascade.submit",
    ...generic,
  ];
}

function focusInputCommandsPrefix(): string[] {
  return [
    "windsurf.cascadePanel.focus",
    "windsurf.action.focusChatInput",
    "windsurf.chat.focusInput",
    "windsurf.cascade.focusInput",
    "cascade.focusInput",
    "windsurf.action.focusCascadeInput",
  ];
}

function preferCtrlSubmit(): boolean {
  return false;
}

function sanitizeProbeCache(entry: ProbeCacheEntry, _opts: { isWayland: boolean }): void {
  const unsafePaste = ["editor.action.clipboardPasteAction", "type"];
  if (entry.paste && unsafePaste.includes(entry.paste)) {
    entry.paste = undefined;
  }
  if (entry.submit && (entry.submit.startsWith("type:") || entry.submit === "type")) {
    entry.submit = undefined;
  }
}

function focusOpenCommandsDefaults(): string[] {
  return [
    "windsurf.cascadePanel.open",
    "windsurf.cascadePanel.focus",
    "windsurf.action.openChat",
    "windsurf.chat.open",
    "windsurf.cascade.open",
    "windsurf.panel.chat",
    "cascade.focus",
    "windsurf.action.showCascade",
    "composer.showComposer",
    "aichat.newchataction",
  ];
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return true;
}

export const windsurfStrategy: IdeStrategy = {
  id: ID,
  label: "Windsurf",
  detectIde: detect,
  pasteDirectCommandsPrefix,
  submitCommandsOverride,
  focusInputCommandsPrefix,
  preferCtrlSubmit,
  sanitizeProbeCache,
  focusOpenCommandsDefaults,
  trustFocusOpenWithoutEditorSnapshot,
  submitFallback: {
    refuseTypeNewlineFallback: true,
  },
};

registerStrategy(windsurfStrategy);
