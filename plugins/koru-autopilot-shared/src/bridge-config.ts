import * as fs from "fs";
import * as vscode from "vscode";

export type PreflightFocusOnlyPolicy = "any-toggle" | "all-toggle";

export interface BridgeOptions {
  extensionPackageId: string;
  openChatOnConnect?: boolean;
  openChatOnConnectDelayMs?: number;
  preflightFocusOnlyPolicy?: PreflightFocusOnlyPolicy;
  enableCursorComposerFastPath?: boolean;
  enableDiscardToxicFocusOpenCache?: boolean;
  reloadCommandStrategies?: readonly string[];
}

export type ResolvedBridgeOptions = {
  extensionPackageId: string;
  openChatOnConnect: boolean;
  openChatOnConnectDelayMs: number;
  preflightFocusOnlyPolicy: PreflightFocusOnlyPolicy;
  enableCursorComposerFastPath: boolean;
  enableDiscardToxicFocusOpenCache: boolean;
  reloadCommandStrategies: readonly string[];
};

export function resolveBridgeOptions(options: BridgeOptions): ResolvedBridgeOptions {
  return {
    extensionPackageId: options.extensionPackageId,
    openChatOnConnect: options.openChatOnConnect ?? false,
    openChatOnConnectDelayMs: options.openChatOnConnectDelayMs ?? 500,
    preflightFocusOnlyPolicy: options.preflightFocusOnlyPolicy ?? "all-toggle",
    enableCursorComposerFastPath: options.enableCursorComposerFastPath ?? true,
    enableDiscardToxicFocusOpenCache: options.enableDiscardToxicFocusOpenCache ?? true,
    reloadCommandStrategies:
      options.reloadCommandStrategies ?? [
        "workbench.action.restartExtensionHost",
        "workbench.action.reloadWindow",
        "workbench.action.reloadExtensions",
      ],
  };
}

export function debugLog(message: string, data?: unknown): void {
  try {
    const suffix = data === undefined ? "" : " " + JSON.stringify(data);
    fs.appendFileSync("/tmp/koru-plugin-debug.log", `${new Date().toISOString()} ${message}${suffix}\n`);
  } catch (err) {
    console.error("koru autopilot: debugLog failed", message, err);
  }
}

function safeLogPayload(data: unknown): string {
  return JSON.stringify(data, (key, value) => {
    if (typeof value === "object" && value !== null) {
      if (key === "before" || key === "after" || key === "beforeSnapshot" || key === "afterSnapshot") {
        const snapshot = value as { hasEditor?: unknown; isFileLike?: unknown };
        return { hasEditor: snapshot.hasEditor, isFileLike: snapshot.isFileLike };
      }
    }
    return value;
  });
}

export let bridgeInstance: any = null;

export function setBridgeInstance(instance: any): void {
  bridgeInstance = instance;
}

export function safeLog(message: string, data?: unknown): void {
  try {
    const suffix = data === undefined ? "" : " " + safeLogPayload(data);
    console.log(`[koru] ${message}${suffix}`);
    debugLog(message, data);
    bridgeInstance?.sendConsoleLog?.(message, data);
  } catch (err) {
    console.log(`[koru] ${message}`);
    debugLog(message, { log_error: String(err) });
  }
}
