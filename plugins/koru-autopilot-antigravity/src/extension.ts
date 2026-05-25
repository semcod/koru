// koru autopilot — Antigravity entrypoint wrapper

import * as vscode from "vscode";
import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";

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

function maybeAutoConnect(bridge: BridgeHandle): void {
  const cfg = vscode.workspace.getConfiguration("koruAutopilot");
  if (cfg.get<boolean>("autoConnect", true)) bridge.connect();
}

function registerBridgeCommands(context: vscode.ExtensionContext, bridge: BridgeHandle): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()),
    vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
      const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
      if (text) await bridge.sendManualChat(text);
    }),
    vscode.commands.registerCommand("koruAutopilot.calibrateProbe", () => bridge.calibrateProbe()),
    vscode.commands.registerCommand("koruAutopilot.calibrate", () => bridge.calibrateProbe()),
    vscode.commands.registerCommand("koruAutopilot.calibrateCompact", () => bridge.calibrateProbe()),
    vscode.commands.registerCommand("koruAutopilot.captureSubmitClick", () => bridge.captureSubmitClickPosition()),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (
        event.affectsConfiguration("koruAutopilot.socketPath") ||
        event.affectsConfiguration("koruAutopilot.autoConnect")
      ) {
        maybeAutoConnect(bridge);
      }
    }),
  );
}

function activateBridge(context: vscode.ExtensionContext): void {
  const bridge = createBridgeController(context, ANTIGRAVITY_BRIDGE_OPTIONS);
  activeBridge = bridge;
  registerBridgeCommands(context, bridge);
  maybeAutoConnect(bridge);
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
