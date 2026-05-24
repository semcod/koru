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
