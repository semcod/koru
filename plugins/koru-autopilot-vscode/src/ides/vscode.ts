/**
 * Microsoft VS Code IDE strategy (extension side).
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "vscode";

function detect(appName: string): string | undefined {
  const lowered = appName.toLowerCase();
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
  // no-op
}

function focusOpenCommandsDefaults(): string[] {
  return [];
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
