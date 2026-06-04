/**
 * Antigravity IDE strategy (extension side).
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "antigravity";

function detect(appName: string): string | undefined {
  return appName.toLowerCase().includes("antigravity") ? ID : undefined;
}

function pasteDirectCommandsPrefix(): string[] {
  return ["antigravity.sendPromptToAgentPanel"];
}

function submitCommandsOverride(): string[] | null {
  return null;
}

function focusInputCommandsPrefix(): string[] {
  return [
    "antigravity.agentSidePanel.focus",
  ];
}

function preferCtrlSubmit(): boolean {
  return false;
}

function sanitizeProbeCache(entry: ProbeCacheEntry, _opts: { isWayland: boolean }): void {
  if (entry.focusOpen && entry.focusOpen.toLowerCase().includes("openagent")) {
    entry.focusOpen = undefined;
  }
  if (entry.focusInput && entry.focusInput.toLowerCase().includes("openagent")) {
    entry.focusInput = undefined;
  }
}

function focusOpenCommandsDefaults(): string[] {
  return [
    "antigravity.agentSidePanel.focus",
  ];
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return false;
}

export const antigravityStrategy: IdeStrategy = {
  id: ID,
  label: "Antigravity",
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

registerStrategy(antigravityStrategy);
