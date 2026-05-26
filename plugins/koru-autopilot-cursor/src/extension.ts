// koru autopilot — Cursor entrypoint wrapper

import { type BridgeOptions } from "./_shared/autopilot-bridge";
import {
  createIdeBridgeExtension,
  type IdeBridgeExtensionConfig,
} from "./_shared/extension-wrapper";

const CURSOR_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-cursor",
  openChatOnConnect: false,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "all-toggle",
  enableCursorComposerFastPath: true,
  enableDiscardToxicFocusOpenCache: true,
  reloadCommandStrategies: [
    "workbench.action.restartExtensionHost",
    "workbench.action.reloadWindow",
    "workbench.action.reloadExtensions",
  ],
};

const CURSOR_EXTENSION_CONFIG: IdeBridgeExtensionConfig = {
  bridgeOptions: CURSOR_BRIDGE_OPTIONS,
  isHost: (appName: string): boolean => appName.toLowerCase().includes("cursor"),
  // ``koru-autopilot-cursor`` is a Cursor-only VSIX. The matching
  // VS Code Marketplace metadata cannot constrain installation to a
  // single IDE, so we enforce it at runtime: silently no-op when the
  // host is not Cursor. Sibling plugins
  // (``koru-autopilot-vscode``/``-vscodium``/``-windsurf``/``-antigravity``)
  // handle the other IDEs and a regression here cannot bleed into them.
  notHostWarning: (appName: string): string => (
    `koru-autopilot-cursor: not activating (appName="${appName}"; ` +
    "this VSIX is the Cursor-only build — install the matching " +
    "koru-autopilot-<ide> VSIX for this IDE)."
  ),
};

const runtime = createIdeBridgeExtension(CURSOR_EXTENSION_CONFIG);

export const activate = runtime.activate;
export const deactivate = runtime.deactivate;
