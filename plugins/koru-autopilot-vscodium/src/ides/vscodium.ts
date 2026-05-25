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

const ID = "vscodium";

function detect(appName: string): string | undefined {
  const lowered = appName.toLowerCase();
  return lowered.includes("vscodium") || lowered.includes("code - oss") || lowered.includes("code-oss")
    ? ID
    : undefined;
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
  return true;
}

function sanitizeProbeCache(
  entry: ProbeCacheEntry,
  _opts: { isWayland: boolean }
): void {
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

function focusOpenCommandsDefaults(): string[] {
  return [];
}

function trustFocusOpenWithoutEditorSnapshot(): boolean {
  return true;
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
