// koru autopilot — Windsurf entrypoint wrapper

import {
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import {
  createIdeBridgeExtension,
  type IdeBridgeExtensionConfig,
} from "./_shared/extension-wrapper";

const WINDSURF_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-windsurf",
  openChatOnConnect: false,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "all-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: true,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

const WINDSURF_EXTENSION_CONFIG: IdeBridgeExtensionConfig = {
  bridgeOptions: WINDSURF_BRIDGE_OPTIONS,
  isHost: (appName: string): boolean => appName.toLowerCase().includes("windsurf"),
  // ``koru-autopilot-windsurf`` is a Windsurf-only VSIX.
  notHostWarning: (appName: string): string => (
    `koru-autopilot-windsurf: not activating (appName="${appName}"; ` +
    "install the matching koru-autopilot-<ide> VSIX for this IDE)."
  ),
};

const runtime = createIdeBridgeExtension(WINDSURF_EXTENSION_CONFIG);

export const activate = runtime.activate;
export const deactivate = runtime.deactivate;
