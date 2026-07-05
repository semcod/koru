/**
 * Qoder IDE strategy (extension side).
 *
 * Qoder is a VS Code fork without a standalone VSIX — the umbrella
 * vscode plugin serves it. This strategy makes `detectIde()` report
 * "qoder" so the bridge dials `koru-autopilot-qoder.sock` and the ack
 * registers under the qoder lane instead of masquerading as vscode.
 */

import type { ProbeCacheEntry } from "../probe-ladder";
import type { IdeStrategy } from "./ide-strategy";
import { registerStrategy } from "./registry";

const ID = "qoder";

function detect(appName: string): string | undefined {
  return appName.toLowerCase().includes("qoder") ? ID : undefined;
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
  // Same panel-toggle hazard as VS Code: cached focus-open winners that
  // spawn new chats or side windows must not be replayed.
  const focusOpen = String(_entry.focusOpen || "").trim().toLowerCase();
  if (
    focusOpen &&
    (focusOpen.includes("newchat") ||
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

export const qoderStrategy: IdeStrategy = {
  id: ID,
  label: "Qoder",
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

registerStrategy(qoderStrategy);
