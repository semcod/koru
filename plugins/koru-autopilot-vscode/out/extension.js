"use strict";
// koru autopilot — VS Code entrypoint wrapper
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const autopilot_bridge_1 = require("./_shared/autopilot-bridge");
const VSCODE_BRIDGE_OPTIONS = {
    extensionPackageId: "semcod.koru-autopilot-vscode",
    openChatOnConnect: true,
    openChatOnConnectDelayMs: 500,
    preflightFocusOnlyPolicy: "any-toggle",
    enableCursorComposerFastPath: false,
    enableDiscardToxicFocusOpenCache: false,
    reloadCommandStrategies: ["workbench.action.reloadWindow"],
};
let activeBridge = null;
function siblingIdeForAppName(appName) {
    const lowered = appName.toLowerCase();
    if (lowered.includes("cursor"))
        return "cursor";
    if (lowered.includes("vscodium") || lowered.includes("code - oss") || lowered.includes("code-oss")) {
        return "vscodium";
    }
    if (lowered.includes("windsurf"))
        return "windsurf";
    if (lowered.includes("antigravity"))
        return "antigravity";
    return null;
}
function maybeAutoConnect(bridge) {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (cfg.get("autoConnect", true))
        bridge.connect();
}
function registerBridgeCommands(context, bridge) {
    context.subscriptions.push(vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()), vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
        const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
        if (text)
            await bridge.sendManualChat(text);
    }), vscode.commands.registerCommand("koruAutopilot.calibrateProbe", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrate", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrateCompact", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.captureSubmitClick", () => bridge.captureSubmitClickPosition()), vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("koruAutopilot.socketPath") ||
            event.affectsConfiguration("koruAutopilot.autoConnect")) {
            maybeAutoConnect(bridge);
        }
    }));
}
function activateBridge(context) {
    const bridge = (0, autopilot_bridge_1.createBridgeController)(context, VSCODE_BRIDGE_OPTIONS);
    activeBridge = bridge;
    registerBridgeCommands(context, bridge);
    maybeAutoConnect(bridge);
}
function activate(context) {
    const appName = vscode.env.appName || "";
    (0, autopilot_bridge_1.debugLog)("ACTIVATE", {
        appName,
        extensionMode: context.extensionMode,
        extensionPath: context.extensionPath,
    });
    // Each sibling IDE has its own dedicated VSIX. This umbrella plugin
    // serves Microsoft VS Code only — silently no-op on other hosts so we
    // never race the per-IDE plugin for the same Unix socket.
    const siblingIde = siblingIdeForAppName(appName);
    if (siblingIde) {
        console.warn(`koru-autopilot-vscode: not activating on ${siblingIde} (appName="${appName}"); ` +
            `install koru-autopilot-${siblingIde} instead.`);
        return;
    }
    activateBridge(context);
}
function deactivate() {
    if (activeBridge) {
        activeBridge.disconnect();
        activeBridge = null;
    }
}
//# sourceMappingURL=extension.js.map