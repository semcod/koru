// koru autopilot — VSCodium entrypoint wrapper

import * as vscode from "vscode";
import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import { wireBridgeCommands } from "./_shared/bridge-base";
import { detectIdeViaStrategies } from "./ides/registry";

const VSCODIUM_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-vscodium",
  openChatOnConnect: false,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "all-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: true,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

let activeBridge: BridgeHandle | null = null;

function isVscodiumHost(appName: string): boolean {
  const lowered = appName.toLowerCase();
  return lowered.includes("vscodium") || lowered.includes("code - oss") || lowered.includes("code-oss") || lowered === "";
}

function activateBridge(context: vscode.ExtensionContext): void {
  const bridge = createBridgeController(context, VSCODIUM_BRIDGE_OPTIONS);
  activeBridge = bridge;
  wireBridgeCommands(context, bridge, {
    includeOpenChatCommand: true,
    safeRegisterCommands: true,
    onRegisterCommandError: (command, message) => {
      debugLog("COMMAND_REGISTER_SKIPPED", { command, message });
      console.warn(`koru-autopilot-vscodium: command ${command} unavailable (${message})`);
    },
  });
}

export function activate(context: vscode.ExtensionContext): void {
  const appName = vscode.env.appName || "";
  const detectedIde = detectIdeViaStrategies(appName) ?? "vscodium";
  debugLog("ACTIVATE", {
    appName,
    detectedIde,
    extensionMode: context.extensionMode,
    extensionPath: context.extensionPath,
  });
  // ``koru-autopilot-vscodium`` is a VSCodium / Code - OSS-only VSIX.
  if (!isVscodiumHost(appName)) {
    console.warn(
      `koru-autopilot-vscodium: not activating (appName="${appName}"; ` +
      "install the matching koru-autopilot-<ide> VSIX for this IDE)."
    );
    return;
  }
  activateBridge(context);
}

export function deactivate(): void {
  if (activeBridge) {
    activeBridge.disconnect();
    activeBridge = null;
  }
}
