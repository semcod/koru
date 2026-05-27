// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.

import * as vscode from "vscode";
import { SharedAutopilotBridgeSubmit } from "./bridge-submit";
import type { BridgeHandle } from "./bridge-handle";
import {
  BridgeOptions,
  debugLog,
} from "./bridge-config";
import {
  Envelope,
  CommandCapability,
} from "./types";

export { debugLog, BridgeOptions } from "./bridge-config";

export type { BridgeHandle } from "./bridge-handle";

export class SharedAutopilotBridge extends SharedAutopilotBridgeSubmit implements BridgeHandle {
  protected pendingCommandOrder: Partial<Record<CommandCapability, string[]>> | undefined;

  constructor(context: vscode.ExtensionContext, options: BridgeOptions) {
    super(context, options);
  }

  private parseCommandOrder(
    raw: unknown,
  ): Partial<Record<CommandCapability, string[]>> | undefined {
    if (!raw || typeof raw !== "object") {
      return undefined;
    }
    const allowed: CommandCapability[] = ["focus_open", "focus_input", "paste", "submit"];
    const order: Partial<Record<CommandCapability, string[]>> = {};
    for (const capability of allowed) {
      const value = (raw as Record<string, unknown>)[capability];
      if (!Array.isArray(value)) {
        continue;
      }
      const commands = value.filter((item): item is string => typeof item === "string");
      if (commands.length > 0) {
        order[capability] = commands;
      }
    }
    return Object.keys(order).length > 0 ? order : undefined;
  }

  protected async injectChat(env: Envelope): Promise<void> {
    const text = typeof env.text === "string" ? env.text : "";
    const submit = env.submit !== false;
    this.pendingCommandOrder = this.parseCommandOrder(env.command_order);
    this.resetOperationTrace();
    this.traceOperation({
      op: "drive",
      route: "plugin",
      ok: true,
      detail: { ide: this.detectIde(), submit, textLength: text.length, id: env.id },
    });
    if (!text) {
      this.traceOperation({ op: "drive", route: "validate", ok: false, reason: "empty text" });
      this.send({ type: "ack", id: env.id, ok: false, message: "empty text", operation_trace: this.currentOperationTrace() });
      return;
    }
    const previous = await this.saveClipboard();
    const previousHost = await this.saveHostClipboard();
    try {
      await this._performInject(env, text, submit);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.traceOperation({ op: "drive", route: "exception", ok: false, reason: message });
      this.send({ type: "ack", id: env.id, ok: false, message, operation_trace: this.currentOperationTrace() });
    } finally {
      this.pendingCommandOrder = undefined;
      if (this.detectIde() === "vscodium") {
        await this.sleep(400);
      }
      await this.restoreHostClipboard(previousHost);
      await this.restoreClipboard(previous);
    }
  }

  private async _performInject(env: Envelope, text: string, submit: boolean): Promise<void> {
    const ide = this.detectIde();
    this.traceOperation({
      op: "drive",
      route: "perform",
      ok: true,
      detail: { ide, submit, textLength: text.length },
    });
    if (await this.tryIdeFastPath(env, text, submit)) {
      return;
    }
    if (this.sendNativeFastPathRequiredFailure(env, ide)) {
      return;
    }

    const focus = await this.focusChatForInject(env);
    if (focus === null) {
      return;
    }
    const busyInput = await this.decideBusyInput(text);
    if (await this.handleBusyInputBeforePaste(env, focus, busyInput, text, submit)) {
      return;
    }
    const pasted = await this.pasteText(text, busyInput.action === "replace_known_koru_draft");
    if (!pasted.ok) {
      this.sendPasteFailureAck(env, focus, pasted);
      return;
    }
    const submitCmd = await this.submitAfterPaste(env, focus, pasted, submit, text);
    if (submitCmd === null) {
      return;
    }
    this.sendSuccessAck(env, focus, pasted, submitCmd);
    if (submit) {
      this.sendMessageSent(text);
    }
  }

  private async tryIdeFastPath(env: Envelope, text: string, submit: boolean): Promise<boolean> {
    if (await this.tryAntigravitySendPromptFastPath(env, text, submit)) {
      this.traceOperation({ op: "drive", route: "antigravity-fastpath", ok: true });
      return true;
    }
    if (await this.tryWindsurfSendTextFastPath(env, text, submit)) {
      this.traceOperation({ op: "drive", route: "windsurf-fastpath", ok: true });
      return true;
    }
    if (
      this.options.enableCursorComposerFastPath &&
      await this.tryCursorComposerPromptFastPath(env, text, submit)
    ) {
      this.traceOperation({ op: "drive", route: "cursor-composer-fastpath", ok: true });
      return true;
    }
    return false;
  }

  private sendNativeFastPathRequiredFailure(env: Envelope, ide: string): boolean {
    if (ide === "windsurf") {
      this.traceOperation({ op: "paste", route: "windsurf-fastpath-required", ok: false, reason: "fast path failed" });
      this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "fast path failed" });
      return true;
    }
    if (ide === "antigravity") {
      this.traceOperation({ op: "paste", route: "antigravity-native-required", ok: false, reason: "native send command unavailable" });
      this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "native send command unavailable" });
      return true;
    }
    return false;
  }

  private async focusChatForInject(env: Envelope): Promise<any | null> {
    const focus = await this.openChatPanel("inject");
    if (focus.ok) {
      await this.sleep(80);
    }
    if (!focus.ok) {
      this.sendFocusFailureAck(env, focus);
      return null;
    }
    return focus;
  }

  private async handleBusyInputBeforePaste(
    env: Envelope,
    focus: any,
    busyInput: { action: string; observedLength: number },
    text: string,
    submit: boolean,
  ): Promise<boolean> {
    if (busyInput.action === "submit_existing") {
      debugLog("CHAT_INPUT_BUSY_SUBMIT_EXISTING", { length: busyInput.observedLength });
      await this.submitExistingChatInput(env, focus, text, submit);
      return true;
    }
    if (busyInput.action === "block") {
      this.sendInputBusyAck(env, focus, busyInput.observedLength);
      return true;
    }
    if (busyInput.action === "replace_known_koru_draft") {
      debugLog("CHAT_INPUT_BUSY_REPLACE_KORU_DRAFT", { length: busyInput.observedLength });
    }
    return false;
  }

}

export function createBridgeController(
  context: vscode.ExtensionContext,
  options: BridgeOptions,
): BridgeHandle {
  return new SharedAutopilotBridge(context, options);
}
