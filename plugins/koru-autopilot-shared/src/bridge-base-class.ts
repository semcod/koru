import * as vscode from "vscode";
import * as net from "net";
import {
  BridgeOptions,
  ResolvedBridgeOptions,
  resolveBridgeOptions,
  setBridgeInstance,
  safeLog,
} from "./bridge-config";
import { OperationTraceStep } from "./types";

export abstract class SharedAutopilotBridgeBase {
  protected socket: net.Socket | null = null;
  protected buf = "";
  protected status: vscode.StatusBarItem;
  protected retryTimer: NodeJS.Timeout | null = null;
  protected connectCandidates: string[] = [];
  protected connectIndex = 0;
  protected reconnectBlockedReason: string | null = null;
  protected operationTrace: OperationTraceStep[] = [];
  protected readonly options: ResolvedBridgeOptions;

  constructor(protected context: vscode.ExtensionContext, options: BridgeOptions) {
    this.options = resolveBridgeOptions(options);
    this.status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 50);
    this.status.text = "$(plug) koru: off";
    this.status.tooltip = "Click to connect to koru autopilot daemon";
    this.status.command = "koruAutopilot.connect";
    this.status.show();
    context.subscriptions.push(this.status);
    setBridgeInstance(this);
  }

  isConnected(): boolean {
    return this.socket !== null;
  }

  protected resetOperationTrace(): void {
    this.operationTrace = [];
  }

  protected updateStatus(text: string, tooltip: string): void {
    this.status.text = text;
    this.status.tooltip = tooltip;
  }

  protected workspaceFolders(): string[] {
    return (vscode.workspace.workspaceFolders || [])
      .map((folder) => folder.uri.fsPath)
      .filter((path): path is string => typeof path === "string" && path.length > 0);
  }

  protected abstract emitLiveDsl(step: OperationTraceStep): void;
  public abstract sendConsoleLog(message: string, data?: unknown): void;

  protected traceOperation(step: OperationTraceStep): void {
    const clipped: OperationTraceStep = {
      ...step,
      attempts: step.attempts?.slice(0, 12),
    };
    this.operationTrace.push(clipped);
    safeLog("OP_ROUTE", clipped);
    this.emitLiveDsl(clipped);
  }
}
