// koru autopilot — Antigravity entrypoint wrapper

import {
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import {
  createIdeBridgeExtension,
  type IdeBridgeExtensionConfig,
} from "./_shared/extension-wrapper";

const ANTIGRAVITY_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-antigravity",
  openChatOnConnect: true,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "any-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: false,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

const ANTIGRAVITY_EXTENSION_CONFIG: IdeBridgeExtensionConfig = {
  bridgeOptions: ANTIGRAVITY_BRIDGE_OPTIONS,
  isHost: (appName: string): boolean => appName.toLowerCase().includes("antigravity"),
  // ``koru-autopilot-antigravity`` is an Antigravity-only VSIX.
  notHostWarning: (appName: string): string => (
    `koru-autopilot-antigravity: not activating (appName="${appName}"; ` +
    "install the matching koru-autopilot-<ide> VSIX for this IDE)."
  ),
};

const runtime = createIdeBridgeExtension(ANTIGRAVITY_EXTENSION_CONFIG);

export const activate = runtime.activate;
export const deactivate = runtime.deactivate;
