// koru autopilot — VSCodium entrypoint wrapper

import {
  debugLog,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import {
  createIdeBridgeExtension,
  type IdeBridgeExtensionConfig,
} from "./_shared/extension-wrapper";
import { isVscodiumHost } from "./ides/vscodium-host";

const VSCODIUM_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-vscodium",
  openChatOnConnect: false,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "all-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: true,
  reloadCommandStrategies: [
    "workbench.action.restartExtensionHost",
    "workbench.action.reloadWindow",
    "workbench.action.reloadExtensions",
  ],
};

const VSCODIUM_EXTENSION_CONFIG: IdeBridgeExtensionConfig = {
  bridgeOptions: VSCODIUM_BRIDGE_OPTIONS,
  isHost: (appName: string): boolean => isVscodiumHost(appName),
  notHostWarning: (appName: string): string => (
    `koru-autopilot-vscodium: not activating (appName="${appName}"; ` +
    "install the matching koru-autopilot-<ide> VSIX for this IDE)."
  ),
  wireOptions: {
    includeOpenChatCommand: true,
    safeRegisterCommands: true,
    onRegisterCommandError: (command, message) => {
      debugLog("COMMAND_REGISTER_SKIPPED", { command, message });
      console.warn(`koru-autopilot-vscodium: command ${command} unavailable (${message})`);
    },
  },
};

const runtime = createIdeBridgeExtension(VSCODIUM_EXTENSION_CONFIG);

export const activate = runtime.activate;
export const deactivate = runtime.deactivate;
