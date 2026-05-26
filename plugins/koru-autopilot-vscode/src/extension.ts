// koru autopilot — VS Code entrypoint wrapper

import {
  type BridgeOptions,
} from "./_shared/autopilot-bridge";
import {
  createIdeBridgeExtension,
  type IdeBridgeExtensionConfig,
} from "./_shared/extension-wrapper";

const VSCODE_BRIDGE_OPTIONS: BridgeOptions = {
  extensionPackageId: "semcod.koru-autopilot-vscode",
  openChatOnConnect: true,
  openChatOnConnectDelayMs: 500,
  preflightFocusOnlyPolicy: "any-toggle",
  enableCursorComposerFastPath: false,
  enableDiscardToxicFocusOpenCache: false,
  reloadCommandStrategies: ["workbench.action.reloadWindow"],
};

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

const VSCODE_EXTENSION_CONFIG: IdeBridgeExtensionConfig = {
  bridgeOptions: VSCODE_BRIDGE_OPTIONS,
  isHost: (appName: string): boolean => !siblingIdeForAppName(appName),
  notHostWarning: (appName: string): string => {
    const siblingIde = siblingIdeForAppName(appName);
    if (siblingIde) {
      return (
        `koru-autopilot-vscode: not activating on ${siblingIde} (appName="${appName}"); ` +
        `install koru-autopilot-${siblingIde} instead.`
      );
    }
    return (
      `koru-autopilot-vscode: not activating (appName="${appName}"; ` +
      "install the matching koru-autopilot-<ide> VSIX for this IDE)."
    );
  },
};

const runtime = createIdeBridgeExtension(VSCODE_EXTENSION_CONFIG);

export const activate = runtime.activate;
export const deactivate = runtime.deactivate;
