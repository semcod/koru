import * as vscode from "vscode";

import {
  createBridgeController,
  debugLog,
  type BridgeHandle,
  type BridgeOptions,
} from "./autopilot-bridge";
import {
  wireBridgeCommands,
  type WireBridgeCommandsOptions,
} from "./bridge-base";

export interface IdeBridgeExtensionConfig {
  bridgeOptions: BridgeOptions;
  isHost: (appName: string) => boolean;
  notHostWarning: (appName: string) => string;
  wireOptions?: WireBridgeCommandsOptions;
}

export interface IdeBridgeExtensionRuntime {
  activate: (context: vscode.ExtensionContext) => void;
  deactivate: () => void;
}

export function createIdeBridgeExtension(
  config: IdeBridgeExtensionConfig,
): IdeBridgeExtensionRuntime {
  let activeBridge: BridgeHandle | null = null;

  return {
    activate(context: vscode.ExtensionContext): void {
      const appName = vscode.env.appName || "";
      debugLog("ACTIVATE", {
        appName,
        extensionMode: context.extensionMode,
        extensionPath: context.extensionPath,
      });

      if (!config.isHost(appName)) {
        console.warn(config.notHostWarning(appName));
        return;
      }

      const bridge = createBridgeController(context, config.bridgeOptions);
      activeBridge = bridge;
      wireBridgeCommands(context, bridge, config.wireOptions);
    },

    deactivate(): void {
      if (activeBridge) {
        activeBridge.disconnect();
        activeBridge = null;
      }
    },
  };
}
