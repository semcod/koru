// koru autopilot — VS Code entrypoint wrapper

import * as vscode from "vscode";
import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";

const VSCODE_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-vscode",
  openChatOnConnect: true,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "any-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: false,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

let activeBridge: BridgeHandle | null = null;

function siblingIdeForAppName(appName: string): string | null {
  const lowered = appName.toLowerCase();
  if (lowered.includes("cursor")) return "cursor";
  if (lowered.includes("vscodium") || lowered.includes("code - oss") || lowered.includes("code-oss")) {
    return "vscodium";
  }
  if (lowered.includes("windsurf")) return "windsurf";
  if (lowered.includes("antigravity")) return "antigravity";
  return null;
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
  const bridge = createBridgeController(context, VSCODE_BRIDGE_OPTIONS);
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
  // Each sibling IDE has its own dedicated VSIX. This umbrella plugin
  // serves Microsoft VS Code only — silently no-op on other hosts so we
  // never race the per-IDE plugin for the same Unix socket.
  const siblingIde = siblingIdeForAppName(appName);
  if (siblingIde) {
    console.warn(
      `koru-autopilot-vscode: not activating on ${siblingIde} (appName="${appName}"); ` +
      `install koru-autopilot-${siblingIde} instead.`
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
