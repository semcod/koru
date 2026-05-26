// koru autopilot — Antigravity entrypoint wrapper

import * as vscode from "vscode";
import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import { wireBridgeCommands } from "./_shared/bridge-base";

const ANTIGRAVITY_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-antigravity",
  openChatOnConnect: true,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "any-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: false,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

let activeBridge: BridgeHandle | null = null;

function isAntigravityHost(appName: string): boolean {
  return appName.toLowerCase().includes("antigravity");
}

function activateBridge(context: vscode.ExtensionContext): void {
  const bridge = createBridgeController(context, ANTIGRAVITY_BRIDGE_OPTIONS);
  activeBridge = bridge;
  wireBridgeCommands(context, bridge);
}

export function activate(context: vscode.ExtensionContext): void {
  const appName = vscode.env.appName || "";
  debugLog("ACTIVATE", {
    appName,
    extensionMode: context.extensionMode,
    extensionPath: context.extensionPath,
  });
  // ``koru-autopilot-antigravity`` is an Antigravity-only VSIX.
  if (!isAntigravityHost(appName)) {
    console.warn(
      `koru-autopilot-antigravity: not activating (appName="${appName}"; ` +
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
