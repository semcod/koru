"use strict";
// koru autopilot — VS Code entrypoint wrapper
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const extension_wrapper_1 = require("./_shared/extension-wrapper");
const VSCODE_BRIDGE_OPTIONS = {
    extensionPackageId: "semcod.koru-autopilot-vscode",
    openChatOnConnect: true,
    openChatOnConnectDelayMs: 500,
    preflightFocusOnlyPolicy: "any-toggle",
    enableCursorComposerFastPath: false,
    enableDiscardToxicFocusOpenCache: false,
    reloadCommandStrategies: ["workbench.action.reloadWindow"],
};
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
const VSCODE_EXTENSION_CONFIG = {
    bridgeOptions: VSCODE_BRIDGE_OPTIONS,
    isHost: (appName) => !siblingIdeForAppName(appName),
    notHostWarning: (appName) => {
        const siblingIde = siblingIdeForAppName(appName);
        if (siblingIde) {
            return (`koru-autopilot-vscode: not activating on ${siblingIde} (appName="${appName}"); ` +
                `install koru-autopilot-${siblingIde} instead.`);
        }
        return (`koru-autopilot-vscode: not activating (appName="${appName}"; ` +
            "install the matching koru-autopilot-<ide> VSIX for this IDE).");
    },
};
const runtime = (0, extension_wrapper_1.createIdeBridgeExtension)(VSCODE_EXTENSION_CONFIG);
exports.activate = runtime.activate;
exports.deactivate = runtime.deactivate;
//# sourceMappingURL=extension.js.map