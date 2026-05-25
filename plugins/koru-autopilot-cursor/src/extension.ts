// koru autopilot — Cursor entrypoint wrapper

import * as vscode from "vscode";
import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./_shared/autopilot-bridge";

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

let activeBridge: BridgeHandle | null = null;

function isCursorHost(appName: string): boolean {
  return appName.toLowerCase().includes("cursor");
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
  const bridge = createBridgeController(context, CURSOR_BRIDGE_OPTIONS);
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
  // ``koru-autopilot-cursor`` is a Cursor-only VSIX. The matching
  // VS Code Marketplace metadata cannot constrain installation to a
  // single IDE, so we enforce it at runtime: silently no-op when the
  // host is not Cursor. Sibling plugins
  // (``koru-autopilot-vscode``/``-vscodium``/``-windsurf``/``-antigravity``)
  // handle the other IDEs and a regression here cannot bleed into them.
  if (!isCursorHost(appName)) {
    console.warn(
      `koru-autopilot-cursor: not activating (appName="${appName}"; ` +
      "this VSIX is the Cursor-only build — install the matching " +
      "koru-autopilot-<ide> VSIX for this IDE)."
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
