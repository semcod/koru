// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.

import * as vscode from "vscode";
import { SharedAutopilotBridgeFocus } from "./bridge-focus";
import {
  BridgeOptions,
  ResolvedBridgeOptions,
  resolveBridgeOptions,
  debugLog,
  safeLog,
  setBridgeInstance,
} from "./bridge-config";
import {
  ANTIGRAVITY_SEND_PROMPT_COMMAND,
  canUseAntigravitySendPrompt,
  selectAntigravityOpenCommand,
} from "../antigravity-fastpath";
import {
  bottomRightSubmitPoint,
  parseXdotoolGeometryShell,
  type ScreenPoint,
} from "./host-click-submit";
import {
  buildPasteDirectCommands,
  buildSubmitCommands,
  prioritizePlainHostKeySubmitCandidates,
  ProbeCacheEntry,
  captureEditorSnapshot,
  pasteLandedInEditor,
  filterRegistered,
  buildHostKeySubmitCandidates,
} from "../probe-ladder";
import {
  decideBusyInputAction,
  shouldRequireVerifiedHostSubmit,
  shouldVerifyPostSubmit,
  shouldVerifyPrePasteBusy,
  interpretPostSubmitProbe,
  type BusyInputAction,
  type KoruAutopilotStepConfig,
} from "../step-decisions";
import { getStrategy } from "../ides/registry";
import {
  Envelope,
  OperationTraceStep,
  CommandOutcome,
  FocusOutcome,
  PasteAttempt,
  SubmitOutcome,
  CommandCapability,
} from "./types";
import {
  filterVSCodiumSubmitCandidates,
  isHostClipboardPasteCommand,
} from "./bridge-helpers";

export { debugLog, BridgeOptions } from "./bridge-config";

type VerifiedHostKeySubmitOptions = {
  preserveFocus?: boolean;
  preferPlain?: boolean;
  ctrlOnly?: boolean;
};

export interface BridgeHandle {
  connect(): void;
  disconnect(): void;
  sendManualChat(text: string): Promise<void>;
  openChatFromCommand(): Promise<void>;
  calibrateProbe(): Promise<void>;
  captureSubmitClickPosition(): Promise<void>;
}

export class SharedAutopilotBridge extends SharedAutopilotBridgeFocus implements BridgeHandle {
  protected pendingCommandOrder: Partial<Record<CommandCapability, string[]>> | undefined;

  constructor(context: vscode.ExtensionContext, options: BridgeOptions) {
    super(context, options);
  }

  protected currentOperationTrace(): OperationTraceStep[] {
    return this.operationTrace.slice(-40);
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

  private async tryWindsurfSendTextFastPath(env: Envelope, text: string, submit: boolean): Promise<boolean> {
    if (this.detectIde() !== "windsurf") {
      return false;
    }
    safeLog("WINDSURF_FASTPATH_START", { submit, textLength: text.length });
    const hasCommand = await this.waitForCommand("windsurf.sendTextToChat", 1200, 150);
    safeLog("WINDSURF_FASTPATH_CHECK_COMMAND", { hasSendCmd: hasCommand });
    if (!hasCommand) {
      safeLog("WINDSURF_FASTPATH_ABORT_MISSING_COMMAND");
      return false;
    }
    let lastError = "";
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        safeLog("WINDSURF_FASTPATH_EXECUTE_SEND", { attempt, textLength: text.length });
        await Promise.resolve(vscode.commands.executeCommand("windsurf.sendTextToChat", text));
        await this.maybeKeepWindsurfChatPanelVisible("after-sendTextToChat");
        safeLog("WINDSURF_FASTPATH_EXECUTE_SEND_OK", { attempt });
        this.sendSuccessAck(
          env,
          { ok: true, command: "none" },
          { ok: true, command: "windsurf.sendTextToChat" },
          "windsurf.sendTextToChat"
        );
        if (submit) {
          this.sendMessageSent(text);
        }
        return true;
      } catch (err) {
        lastError = String(err);
        safeLog("WINDSURF_FASTPATH_EXECUTE_SEND_ERROR", { attempt, error: lastError });
        if (attempt < 4) {
          await this.sleep(450);
        }
      }
    }
    this.traceOperation({
      op: "submit",
      route: "windsurf-fastpath-exhausted",
      ok: false,
      reason: `windsurf.sendTextToChat failed after 4 retries; lastError=${lastError}`,
    });
    this.sendSubmitFailureAck(
      env,
      { ok: true, command: "none" },
      { ok: true, command: "windsurf.sendTextToChat" },
      "windsurf.sendTextToChat",
      {
        ok: false,
        command: "windsurf.sendTextToChat",
        reason: `windsurf.sendTextToChat command failed 4 times; lastError=${lastError}`,
      }
    );
    return true;
  }

  private async maybeKeepWindsurfChatPanelVisible(reason: string): Promise<void> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const keepOpen = cfg.get<boolean>("windsurfKeepOpenAfterSend", false);
    if (!keepOpen) {
      return;
    }
    const strategies = [
      "windsurf.focusCascadeChat",
      "windsurf.focusCascade",
      "windsurf.openCascadeChat",
      "windsurf.openCascade",
    ];
    for (const strategy of strategies) {
      try {
        safeLog("WINDSURF_KEEP_OPEN_TRY", { strategy, reason });
        await Promise.resolve(vscode.commands.executeCommand(strategy));
        await this.sleep(120);
        return;
      } catch (err) {
        safeLog("WINDSURF_KEEP_OPEN_FAILED", { strategy, reason, error: String(err) });
      }
    }
  }

  private async tryAntigravitySendPromptFastPath(env: Envelope, text: string, submit: boolean): Promise<boolean> {
    if (this.detectIde() !== "antigravity") {
      return false;
    }
    safeLog("ANTIGRAVITY_FASTPATH_START", { submit, textLength: text.length });
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const hasCommand = await canUseAntigravitySendPrompt(existing);
    safeLog("ANTIGRAVITY_FASTPATH_CHECK_COMMAND", { hasSendCmd: hasCommand });
    if (!hasCommand) {
      safeLog("ANTIGRAVITY_FASTPATH_ABORT_MISSING_COMMAND");
      return false;
    }
    try {
      safeLog("ANTIGRAVITY_FASTPATH_EXECUTE_SEND", { textLength: text.length });
      await Promise.resolve(vscode.commands.executeCommand(ANTIGRAVITY_SEND_PROMPT_COMMAND, text));
      safeLog("ANTIGRAVITY_FASTPATH_EXECUTE_SEND_OK");
      const openCmd = selectAntigravityOpenCommand(existing);
      try {
        await Promise.resolve(vscode.commands.executeCommand(openCmd));
      } catch (err) {
        safeLog("ANTIGRAVITY_FASTPATH_OPEN_FAILED", { openCmd, error: String(err) });
      }
      this.sendSuccessAck(
        env,
        { ok: true, command: openCmd },
        { ok: true, command: ANTIGRAVITY_SEND_PROMPT_COMMAND },
        ANTIGRAVITY_SEND_PROMPT_COMMAND
      );
      if (submit) {
        this.sendMessageSent(text);
      }
      return true;
    } catch (err) {
      const lastError = String(err);
      safeLog("ANTIGRAVITY_FASTPATH_EXECUTE_SEND_ERROR", { error: lastError });
      this.traceOperation({
        op: "submit",
        route: "antigravity-fastpath-failed",
        ok: false,
        reason: `antigravity native send failed; error=${lastError}`,
      });
      this.sendSubmitFailureAck(
        env,
        { ok: true, command: "none" },
        { ok: true, command: ANTIGRAVITY_SEND_PROMPT_COMMAND },
        ANTIGRAVITY_SEND_PROMPT_COMMAND,
        {
          ok: false,
          command: ANTIGRAVITY_SEND_PROMPT_COMMAND,
          reason: `antigravity native send failed; error=${lastError}`,
        }
      );
      return true;
    }
  }

  private async tryCursorComposerPromptFastPath(
    env: Envelope,
    text: string,
    submit: boolean
  ): Promise<boolean> {
    if (this.detectIde() !== "cursor") {
      return false;
    }
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const pasteCmd = "composer.focusComposer";
    const submitCmd = "composer.sendToAgent";
    if (!existing.has(pasteCmd) || !existing.has(submitCmd)) {
      return false;
    }
    safeLog("CURSOR_COMPOSER_FASTPATH_START", { submit, textLength: text.length });
    this.traceOperation({
      op: "focus_open",
      route: "composer-fastpath",
      ok: true,
      command: pasteCmd,
    });
    try {
      await vscode.commands.executeCommand(pasteCmd);
    } catch (err) {
      safeLog("CURSOR_COMPOSER_FASTPATH_FOCUS_FAILED", { error: String(err) });
      return false;
    }
    await this.sleep(this.probeFocusDelayMs());
    const busyInput = await this.decideBusyInput(text);
    if (busyInput.action === "block") {
      this.sendInputBusyAck(env, { ok: true, command: pasteCmd }, busyInput.observedLength);
      return true;
    }
    const replace = busyInput.action === "replace_known_koru_draft";
    const pasted = await this.pasteText(text, replace);
    if (!pasted.ok) {
      return false;
    }
    if (!submit) {
      this.sendSuccessAck(env, { ok: true, command: pasteCmd }, pasted, undefined);
      return true;
    }
    await this.captureCursorBubbleAnchor();
    this.traceOperation({
      op: "submit",
      route: "composer-fastpath",
      ok: true,
      command: submitCmd,
    });
    try {
      await vscode.commands.executeCommand(submitCmd);
    } catch (err) {
      safeLog("CURSOR_COMPOSER_FASTPATH_SUBMIT_FAILED", { error: String(err) });
      return false;
    }
    const verifyResult = await this._verifySubmitViaCursorBubble(text);
    if (verifyResult && verifyResult.matched) {
      this.traceOperation({ op: "submit", route: "success", ok: true, command: submitCmd });
      this.sendSuccessAck(env, { ok: true, command: pasteCmd }, pasted, submitCmd);
      this.sendMessageSent(text);
      return true;
    }
    this.traceOperation({
      op: "submit_verify",
      route: "cursor-bubble-db",
      ok: false,
      reason: "no new user bubble in cursorDiskKV after composer fastpath (paste+sendToAgent)",
      detail: { pasteCmd, submitCmd, newUserBubbles: verifyResult?.newUserBubbles },
    });
    await this._clearComposerDraft();
    return false;
  }

  private async _clearComposerDraft(): Promise<void> {
    try {
      await vscode.commands.executeCommand("composer.focusComposer");
      await this.sleep(60);
      await vscode.commands.executeCommand("editor.action.selectAll");
      await this.sleep(40);
      await vscode.commands.executeCommand("deleteLeft");
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      safeLog("CURSOR_COMPOSER_FASTPATH_CLEAR_DRAFT_FAILED", { detail });
    }
  }

  private async submitAfterPaste(
    env: Envelope,
    focus: CommandOutcome,
    pasted: CommandOutcome,
    submit: boolean,
    pastedText?: string
  ): Promise<string | undefined | null> {
    if (pasted.command === "windsurf.sendTextToChat") {
      this.traceOperation({ op: "submit", route: "windsurf-native", ok: true, command: "windsurf.sendTextToChat" });
      return "windsurf.sendTextToChat";
    }
    if (!submit) {
      this.traceOperation({ op: "submit", route: "disabled-by-request", ok: true });
      return undefined;
    }
    await this.sleep(150);
    await this.focusChatInput();
    await this.captureCursorBubbleAnchor();
    const submitResult = await this.submitChat(pastedText, pasted.command);
    if (submitResult.unverified) {
      this.traceOperation({
        op: "submit",
        route: "unverified",
        ok: false,
        command: submitResult.command,
        reason: submitResult.reason,
        attempts: submitResult.attempts,
      });
      this.sendSubmitFailureAck(env, focus, pasted, submitResult.command, submitResult);
      return null;
    }
    if (submitResult.ok) {
      this.traceOperation({ op: "submit", route: "success", ok: true, command: submitResult.command });
      return submitResult.command;
    }
    this.traceOperation({
      op: "submit",
      route: "failed",
      ok: false,
      command: submitResult.command,
      reason: submitResult.reason,
      attempts: submitResult.attempts,
    });
    this.sendSubmitFailureAck(env, focus, pasted, submitResult.command, submitResult);
    return null;
  }

  private async _performInject(env: Envelope, text: string, submit: boolean): Promise<void> {
    const ide = this.detectIde();
    this.traceOperation({
      op: "drive",
      route: "perform",
      ok: true,
      detail: { ide, submit, textLength: text.length },
    });
    if (await this.tryAntigravitySendPromptFastPath(env, text, submit)) {
      this.traceOperation({ op: "drive", route: "antigravity-fastpath", ok: true });
      return;
    }
    if (await this.tryWindsurfSendTextFastPath(env, text, submit)) {
      this.traceOperation({ op: "drive", route: "windsurf-fastpath", ok: true });
      return;
    }
    if (
      this.options.enableCursorComposerFastPath &&
      await this.tryCursorComposerPromptFastPath(env, text, submit)
    ) {
      this.traceOperation({ op: "drive", route: "cursor-composer-fastpath", ok: true });
      return;
    }
    if (ide === "windsurf") {
      this.traceOperation({ op: "paste", route: "windsurf-fastpath-required", ok: false, reason: "fast path failed" });
      this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "fast path failed" });
      return;
    }
    if (ide === "antigravity") {
      this.traceOperation({ op: "paste", route: "antigravity-native-required", ok: false, reason: "native send command unavailable" });
      this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "native send command unavailable" });
      return;
    }

    const focus = await this.openChatPanel("inject");
    if (focus.ok) {
      await this.sleep(80);
    }
    if (!focus.ok) {
      this.sendFocusFailureAck(env, focus);
      return;
    }
    const busyInput = await this.decideBusyInput(text);
    if (busyInput.action === "submit_existing") {
      debugLog("CHAT_INPUT_BUSY_SUBMIT_EXISTING", { length: busyInput.observedLength });
      await this.submitExistingChatInput(env, focus, text, submit);
      return;
    }
    if (busyInput.action === "block") {
      this.sendInputBusyAck(env, focus, busyInput.observedLength);
      return;
    }
    if (busyInput.action === "replace_known_koru_draft") {
      debugLog("CHAT_INPUT_BUSY_REPLACE_KORU_DRAFT", { length: busyInput.observedLength });
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

  private async pasteText(text: string, replaceCurrentInput = false): Promise<CommandOutcome> {
    const ide = this.detectIde();
    const useProbe = this.probeLadderEnabled();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const before = this.editorSnapshot();
    this.traceOperation({
      op: "paste",
      route: "start",
      ok: true,
      detail: { ide, replaceCurrentInput, useProbe, textLength: text.length },
    });

    if (replaceCurrentInput) {
      await this.focusChatInput();
      await this.runCommand("editor.action.selectAll");
      await this.sleep(50);
      const clipboard = await this.tryClipboardPaste(text, before, useProbe);
      if (clipboard.handled && clipboard.result.ok) {
        this.traceOperation({ op: "paste", route: "replace:clipboard", ok: true, command: clipboard.result.command });
        return clipboard.result;
      }
      const typed = await this.tryTypePaste(text, before, useProbe);
      if (typed.ok) {
        this.traceOperation({ op: "paste", route: "replace:type", ok: true, command: typed.command });
        return typed;
      }
    }

    const direct = await this.tryDirectPasteCommands(text, ide, existing, cache, before, useProbe);
    if (direct) {
      this.traceOperation({ op: "paste", route: "direct-command", ok: direct.ok, command: direct.command, reason: direct.reason });
      return direct;
    }

    if (ide === "windsurf") {
      return { ok: false };
    }

    const clipboard = await this.tryClipboardPaste(text, before, useProbe);
    if (clipboard.handled) {
      this.traceOperation({
        op: "paste",
        route: "vscode-clipboard",
        ok: clipboard.result.ok,
        command: clipboard.result.command,
        reason: clipboard.result.reason,
      });
      return clipboard.result;
    }

    if (ide === "vscodium" && this.allowVSCodiumHostInputFallback()) {
      const hostPaste = await this.tryHostClipboardPaste(text, before, useProbe);
      if (hostPaste.handled) {
        this.traceOperation({
          op: "paste",
          route: "vscodium:host-clipboard",
          ok: hostPaste.result.ok,
          command: hostPaste.result.command,
          reason: hostPaste.result.reason,
          attempts: hostPaste.result.attempts,
        });
        return hostPaste.result;
      }
    }

    const typed = await this.tryTypePaste(text, before, useProbe);
    this.traceOperation({ op: "paste", route: "type", ok: typed.ok, command: typed.command, reason: typed.reason });
    return typed;
  }

  private static directPasteReadsClipboard(cmd: string): boolean {
    return (
      cmd === "editor.action.clipboardPasteAction"
      || cmd === "editor.action.pasteAs"
      || cmd === "execPaste"
      || cmd === "paste"
    );
  }

  private async tryDirectPasteCommands(
    text: string,
    ide: string,
    existing: Set<string>,
    cache: ProbeCacheEntry | undefined,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<CommandOutcome | undefined> {
    const directCommands = filterRegistered(
      this.orderWithServerOverride("paste", buildPasteDirectCommands(ide), cache?.paste),
      existing
    );
    const previousClip = await this.saveClipboard();
    let clipboardSeeded = false;
    try {
      for (const cmd of directCommands) {
        const readsClipboard = SharedAutopilotBridge.directPasteReadsClipboard(cmd);
        if (readsClipboard) {
          const seeded = await this.writeClipboardVerified(text);
          if (!seeded) {
            debugLog("DIRECT_PASTE_CLIPBOARD_SEED_FAILED", { cmd });
            this.traceOperation({
              op: "paste",
              route: `direct-command:${cmd}`,
              ok: false,
              reason: "clipboard seed unverified; refusing to invoke clipboard-reading paste with stale clipboard",
            });
            continue;
          }
          clipboardSeeded = true;
        }
        try {
          const result = await Promise.resolve(vscode.commands.executeCommand(cmd, text));
          if (result === false) {
            continue;
          }
          await this.sleep(this.probePasteDelayMs());
          const after = this.editorSnapshot();
          if (useProbe && pasteLandedInEditor(before, after, text)) {
            debugLog("PROBE_PASTE_REJECT", { cmd, reason: "landed_in_editor" });
            continue;
          }
          if (useProbe) {
            await this.saveProbeCache({ paste: cmd });
          }
          return { ok: true, command: cmd };
        } catch {
          /* ignore */
        }
      }
      return undefined;
    } finally {
      if (clipboardSeeded) {
        await this.sleep(120);
        await this.restoreClipboard(previousClip);
      }
    }
  }

  private async tryHostClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("HOST_PASTE_NO_INPUT_FOCUS");
      this.traceOperation({ op: "paste", route: "host-clipboard:focus-input", ok: false, reason: "input focus unavailable" });
    }
    const guard = await this.guardVSCodiumTerminalRiskPaste("host-clipboard");
    if (guard) {
      return guard;
    }
    await this.clearChatInput();
    const clip = await this.writeHostClipboard(text);
    if (!clip) {
      debugLog("HOST_PASTE_NO_CLIPBOARD_TOOL");
      this.traceOperation({ op: "paste", route: "host-clipboard:write", ok: false, reason: "no host clipboard tool" });
      return { handled: false, result: { ok: false, reason: "no host clipboard tool" } };
    }
    this.traceOperation({ op: "paste", route: `host-clipboard:${clip}`, ok: true, detail: { textLength: text.length } });
    await this.writeClipboardVerified(text);
    const paste = await this.runHostKeyCandidates("HOST_PASTE_KEY", [
      ["wtype", ["-M", "ctrl", "-k", "v", "-m", "ctrl"]],
      ["xdotool", ["key", "ctrl+v"]],
      ["ydotool", ["key", "ctrl+v"]],
    ]);
    if (!paste.ok) {
      return { handled: true, result: { ...paste, reason: "host clipboard paste key failed" } };
    }
    await this.sleep(Math.max(this.probePasteDelayMs(), 350));
    const after = this.editorSnapshot();
    if (useProbe && pasteLandedInEditor(before, after, text)) {
      this.traceOperation({ op: "paste", route: "host-clipboard:probe", ok: false, reason: "paste landed in editor" });
      return { handled: true, result: { ok: false, command: paste.command, reason: "paste landed in editor" } };
    }
    if (useProbe) {
      await this.saveProbeCache({ paste: `host-clipboard:${clip}+${paste.command}` });
    }
    return { handled: true, result: { ok: true, command: `host-clipboard:${clip}+${paste.command}` } };
  }

  private async tryClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("PROBE_PASTE_NO_INPUT_FOCUS");
      if (useProbe && before.hasEditor && before.isFileLike) {
        return { handled: true, result: { ok: false, reason: "chat input focus unavailable; refusing editor clipboard paste fallback" } };
      }
    }
    try {
      const guard = await this.guardVSCodiumTerminalRiskPaste("vscode-clipboard");
      if (guard) {
        return guard;
      }
      await this.clearChatInput();
      const ok = await this.writeClipboardVerified(text);
      if (!ok) {
        debugLog("CLIPBOARD_PASTE_ABORT_UNVERIFIED");
        return {
          handled: true,
          result: {
            ok: false,
            reason:
              "clipboard writeText did not propagate (readback mismatch); "
              + "refusing paste to avoid clobbering chat input with stale clipboard content",
          },
        };
      }
      await vscode.commands.executeCommand("editor.action.clipboardPasteAction");
      await this.sleep(this.probePasteDelayMs());
      const after = this.editorSnapshot();
      if (useProbe && pasteLandedInEditor(before, after, text)) {
        return { handled: true, result: { ok: false } };
      }
      if (useProbe) {
        await this.saveProbeCache({ paste: "editor.action.clipboardPasteAction" });
      }
      return { handled: true, result: { ok: true, command: "editor.action.clipboardPasteAction" } };
    } catch {
      /* ignore */
    }
    return { handled: false, result: { ok: false } };
  }

  private async guardVSCodiumTerminalRiskPaste(route: string): Promise<PasteAttempt | null> {
    if (this.detectIde() !== "vscodium" || !this.probeLadderEnabled()) {
      return null;
    }
    const observed = await this._probeChatInputContents();
    if (observed !== null) {
      return null;
    }
    const reason =
      "chat input probe inconclusive; refusing terminal-risk paste fallback";
    this.traceOperation({
      op: "paste",
      route: `${route}:terminal-risk-guard`,
      ok: false,
      reason,
    });
    return { handled: true, result: { ok: false, reason } };
  }

  private async tryTypePaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<CommandOutcome> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok && useProbe && before.hasEditor && before.isFileLike) {
      debugLog("TYPE_PASTE_NO_INPUT_FOCUS_REFUSED");
      return { ok: false, reason: "chat input focus unavailable; refusing editor type fallback" };
    }
    try {
      await this.clearChatInput();
      await Promise.resolve(vscode.commands.executeCommand("type", { text }));
      await this.sleep(this.probePasteDelayMs());
      const after = this.editorSnapshot();
      if (useProbe && pasteLandedInEditor(before, after, text)) {
        return { ok: false };
      }
      if (useProbe) {
        await this.saveProbeCache({ paste: "type" });
      }
      return { ok: true, command: "type" };
    } catch {
      return { ok: false };
    }
  }

  protected async saveClipboard(): Promise<string | null> {
    try {
      return await vscode.env.clipboard.readText();
    } catch {
      return null;
    }
  }

  protected async restoreClipboard(previous: string | null): Promise<void> {
    if (previous !== null) {
      try {
        await vscode.env.clipboard.writeText(previous);
      } catch {
        /* ignore */
      }
    }
  }

  protected async writeClipboardVerified(text: string): Promise<boolean> {
    const maxTries = 6;
    for (let i = 0; i < maxTries; i++) {
      try {
        await vscode.env.clipboard.writeText(text);
      } catch (err) {
        debugLog("CLIPBOARD_WRITE_ERROR", { err: String(err) });
      }
      await this.sleep(i === 0 ? 20 : 40);
      try {
        const observed = await vscode.env.clipboard.readText();
        if (observed === text) {
          if (i > 0) {
            debugLog("CLIPBOARD_WRITE_VERIFIED_RETRY", { attempts: i + 1 });
          }
          return true;
        }
      } catch (err) {
        debugLog("CLIPBOARD_READBACK_ERROR", { err: String(err) });
      }
    }
    debugLog("CLIPBOARD_WRITE_UNVERIFIED", { length: text.length });
    return false;
  }

  private async decideBusyInput(text: string): Promise<{ action: BusyInputAction; observedLength: number }> {
    if (!shouldVerifyPrePasteBusy(this.koruStepConfig())) {
      this.traceOperation({ op: "input_busy_probe", route: "disabled", ok: true });
      return { action: "empty", observedLength: 0 };
    }
    const observed = await this._probeChatInputContents();
    const observedLength = observed === null ? -1 : observed.trim().length;
    const action = decideBusyInputAction(observed, text);
    debugLog("CHAT_INPUT_BUSY_PROBE", { busy: action !== "empty", action, length: observedLength });
    this.traceOperation({
      op: "input_busy_probe",
      route: "select-copy",
      ok: action !== "block",
      reason: action === "block" ? "input contains unrelated draft" : undefined,
      detail: { action, observedLength },
    });
    return { action, observedLength };
  }

  private async _probeChatInputContents(): Promise<string | null> {
    const sentinel = `__koru_input_probe_${Date.now().toString(36)}__`;
    const previous = await this.saveClipboard();
    try {
      await vscode.env.clipboard.writeText(sentinel);
      await this.runCommand("editor.action.selectAll");
      await this.runCommand("editor.action.clipboardCopyAction");
      await this.sleep(60);
      const observed = await this.saveClipboard();
      if (observed === null || observed === sentinel) {
        this.traceOperation({
          op: "input_probe",
          route: "select-copy",
          ok: false,
          reason: observed === sentinel ? "sentinel unchanged" : "clipboard unreadable",
        });
        return null;
      }
      this.traceOperation({
        op: "input_probe",
        route: "select-copy",
        ok: true,
        detail: { observedLength: observed.length },
      });
      return observed;
    } catch (err) {
      debugLog("CHAT_INPUT_PROBE_ERROR", { err: String(err) });
      return null;
    } finally {
      await this.restoreClipboard(previous);
      await this.collapseProbeSelection();
    }
  }

  private async collapseProbeSelection(): Promise<void> {
    try {
      await Promise.resolve(vscode.commands.executeCommand("cursorMove", {
        to: "wrappedLineEnd",
        select: false,
      }));
      this.traceOperation({ op: "input_probe", route: "collapse-selection", ok: true });
    } catch (err) {
      const fallbackOk = await this.runCommand("cursorLineEnd");
      this.traceOperation({
        op: "input_probe",
        route: "collapse-selection",
        ok: fallbackOk,
        reason: fallbackOk ? undefined : String(err),
      });
    }
  }

  private sendInputBusyAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    observedLength?: number
  ): void {
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      delivered: false,
      opened: focus.ok,
      submitted: false,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      verification: "input_busy",
      operation_trace: this.currentOperationTrace(),
      reason: "chat_input_not_empty",
      observed_length: observedLength,
      message:
        "chat input already contains un-submitted text — skipping drive to "
        + "avoid clobbering the user's reply or concatenating prompts.",
    });
  }

  private async submitExistingChatInput(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    text: string,
    submit: boolean
  ): Promise<void> {
    if (!submit) {
      this.send({
        type: "ack",
        id: env.id,
        ok: true,
        delivered: true,
        opened: true,
        submitted: false,
        probe_ladder: this.probeLadderEnabled(),
        winning_focus_open: focus.command,
        verification: "input_matches_prompt",
        operation_trace: this.currentOperationTrace(),
      });
      return;
    }
    await this.captureCursorBubbleAnchor();
    const submitResult = await this.submitChat(text);
    if (submitResult.unverified || !submitResult.ok) {
      this.sendSubmitFailureAck(
        env,
        focus,
        { ok: true, command: "existing-input" },
        submitResult.command,
        submitResult
      );
      return;
    }
    this.sendSuccessAck(env, focus, { ok: true, command: "existing-input" }, submitResult.command);
    this.sendMessageSent(text);
  }

  private sendFocusFailureAck(env: Envelope, focus: FocusOutcome): void {
    const details = focus.diagnostics || {};
    const candidates = Array.isArray(details.focusOpenCandidates)
      ? details.focusOpenCandidates.join(", ")
      : "";
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      opened: false,
      submitted: false,
      probe_ladder: this.probeLadderEnabled(),
      diagnostics: details,
      operation_trace: this.currentOperationTrace(),
      message:
        "chat input is not focused/open; "
        + `ide=${details.ide || this.detectIde()} app=${details.appName || vscode.env.appName}; `
        + `focus_open_candidates=${candidates || "(none)"}; `
        + "log=/tmp/koru-plugin-debug.log. Open chat input manually, then retry.",
    });
  }

  private sendPasteFailureAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string; reason?: string }
  ): void {
    const reason = pasted.reason || "unknown paste failure";
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      opened: true,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      attempted_paste: pasted.command,
      paste_failure_reason: reason,
      operation_trace: this.currentOperationTrace(),
      message: `chat opened but paste command failed (${reason})`,
    });
  }

  private sendSubmitFailureAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string },
    attemptedSubmit?: string,
    submitDetails?: SubmitOutcome
  ): void {
    if (this.options.enableDiscardToxicFocusOpenCache) {
      this.discardToxicFocusOpenCache(focus.command).catch((err) => {
        debugLog("FOCUS_OPEN_CACHE_DISCARD_FAILED", { err: String(err) });
      });
    }
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      delivered: true,
      opened: true,
      submitted: false,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      winning_paste: pasted.command,
      attempted_submit: attemptedSubmit,
      submit_failure_reason: submitDetails?.reason,
      submit_attempts: submitDetails?.attempts,
      verification: "submit_unverified",
      operation_trace: this.currentOperationTrace(),
      message:
        "chat opened and text injected, but submit could not be verified; "
        + "manual Send may be required. Input was cleared before paste to avoid prompt concatenation.",
    });
  }

  private async discardToxicFocusOpenCache(focusCommand: string | undefined): Promise<void> {
    if (!this.probeLadderEnabled()) return;
    const cache = this.getProbeCache();
    const cached = cache?.focusOpen;
    if (!cached) return;
    const focusToken = (focusCommand || "").toLowerCase();
    const isInputOnlyFocus =
      focusToken.includes("focuscomposer") ||
      focusToken.includes("focuscascade") ||
      (this.detectIde() === "vscodium" && focusToken.includes("openquickchat")) ||
      (this.detectIde() === "vscodium" && focusToken.includes("quickchat.openinchatview")) ||
      focusToken.startsWith("input-only");
    if (!isInputOnlyFocus) return;
    const cleared: any = { ...cache, focusOpen: undefined };
    await this.context.globalState.update("probeCache.v3", cleared);
    debugLog("PROBE_CACHE_FOCUS_OPEN_DISCARDED", { previous: cached });
    this.traceOperation({
      op: "focus_open",
      route: "cache-discard",
      ok: false,
      command: cached,
      reason:
        "cached focus_open winner was an input-only/focus-only command "
        + "but submit could not be verified — discarding so the next "
        + "drive re-probes via the non-toggling open command",
    });
  }

  private sendSuccessAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string },
    submitCmd: string | undefined
  ): void {
    this.send({
      type: "ack",
      id: env.id,
      ok: true,
      delivered: true,
      opened: true,
      submitted: true,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      winning_paste: pasted.command,
      winning_submit: submitCmd,
      operation_trace: this.currentOperationTrace(),
    });
  }

  private sendMessageSent(text: string): void {
    console.log("koru autopilot: sending message.sent");
    this.traceOperation({
      op: "message_sent",
      route: "plugin-event",
      ok: true,
      detail: { length: text.length },
    });
    this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
  }

  private koruStepConfig(): KoruAutopilotStepConfig {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const legacyVerify = cfg.get<boolean>("verifySubmitOnCursor");
    const verifySubmit = cfg.get<boolean>("verifySubmit");
    return {
      probeLadder: this.probeLadderEnabled(),
      verifySubmit: typeof verifySubmit === "boolean" ? verifySubmit : (legacyVerify ?? true),
      verifySubmitOnCursor: legacyVerify,
      skipWhenInputBusy: cfg.get<boolean>("skipWhenInputBusy", true),
    };
  }

  private postSubmitVerifyEnabled(verifyText?: string): boolean {
    return shouldVerifyPostSubmit(this.detectIde(), verifyText, this.koruStepConfig());
  }

  private async discardCachedSubmitWinner(cmd: string): Promise<void> {
    if (!this.probeLadderEnabled()) {
      return;
    }
    const current = this.getProbeCache();
    if (current?.submit === cmd) {
      await this.saveProbeCache({ submit: undefined });
    }
  }

  private async verifySubmitStep(
    originalText: string,
    requireEmptyAfterSubmit = false
  ): Promise<{ cleared: boolean; observedLength: number }> {
    const ide = this.detectIde();
    const config = this.koruStepConfig();
    this.traceOperation({
      op: "submit_verify",
      route: "start",
      ok: true,
      detail: { ide, verifySubmitEnabled: config.verifySubmit, requireEmptyAfterSubmit },
    });
    if (ide === "cursor") {
      const bubble = await this._verifySubmitViaCursorBubble(originalText);
      if (bubble) {
        this.traceOperation({
          op: "submit_verify",
          route: "cursor-bubble-db",
          ok: bubble.matched,
          detail: { newUserBubbles: bubble.newUserBubbles },
        });
        return { cleared: bubble.matched, observedLength: bubble.matched ? 0 : originalText.length };
      }
    }
    if (!config.verifySubmit) {
      this.traceOperation({ op: "submit_verify", route: "skipped-by-configuration", ok: true });
      return { cleared: true, observedLength: 0 };
    }
    const observed = await this._probeChatInputContents();
    const verifyResult = interpretPostSubmitProbe(observed, originalText, { requireEmpty: requireEmptyAfterSubmit });
    const verified = verifyResult.cleared;
    const observedLength = observed === null ? -1 : observed.trim().length;
    this.traceOperation({
      op: "submit_verify",
      route: "sentinel-clipboard",
      ok: verified,
      detail: { observedLength, verifyTextLength: originalText.length, requireEmptyAfterSubmit },
    });
    return { cleared: verified, observedLength };
  }

  private async finalizeSubmitCandidate(
    cmd: string,
    verifyText: string | undefined,
    verifyEnabled: boolean,
    requireEmptyAfterSubmit = false,
    extra?: Partial<SubmitOutcome>
  ): Promise<SubmitOutcome | null> {
    if (verifyEnabled && verifyText) {
      const verify = await this.verifySubmitStep(verifyText, requireEmptyAfterSubmit);
      if (!verify.cleared) {
        debugLog("SUBMIT_VERIFY_DISCARD", { cmd, observedLength: verify.observedLength });
        await this.discardCachedSubmitWinner(cmd);
        return null;
      }
    }
    if (this.probeLadderEnabled()) {
      await this.saveProbeCache({ submit: cmd });
    }
    this.traceOperation({
      op: "submit",
      route: "accepted",
      ok: true,
      command: cmd,
      detail: { verifyEnabled, requireEmptyAfterSubmit },
    });
    return { ok: true, command: cmd, ...extra };
  }

  private async submitChat(verifyText?: string, pasteCommand?: string): Promise<SubmitOutcome> {
    const ide = this.detectIde();
    const verifyEnabled = this.postSubmitVerifyEnabled(verifyText);
    this.traceOperation({
      op: "submit",
      route: "start",
      ok: true,
      detail: { ide, verifyEnabled, verifyTextLength: verifyText?.length || 0 },
    });
    if (ide === "vscodium") {
      return this._submitChatVSCodium(verifyText, verifyEnabled, pasteCommand);
    }
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      this.orderWithServerOverride("submit", buildSubmitCommands(ide), cache?.submit),
      existing
    );
    debugLog("SUBMIT_CANDIDATES", { ide, candidates, verifyEnabled });
    const registered = await this._tryRegisteredCommands(candidates, verifyText, verifyEnabled);
    if (registered) return registered;
    if (ide === "windsurf") {
      return { ok: false };
    }
    if (ide === "cursor" || ide === "vscode") {
      const fallback = await this._submitChatCursorVSCodeFallback(ide, verifyText, verifyEnabled);
      if (fallback) return fallback;
    }
    const typeFallback = await this._tryTypeSubmitFallbacks(verifyText, verifyEnabled);
    if (typeFallback) return typeFallback;
    return { ok: false };
  }

  private async _submitChatVSCodium(
    verifyText: string | undefined,
    verifyEnabled: boolean,
    pasteCommand?: string
  ): Promise<SubmitOutcome> {
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const orderedCandidates = this.orderWithServerOverride(
      "submit",
      buildSubmitCommands("vscodium"),
      cache?.submit
    );
    const safeOrderedCandidates = filterVSCodiumSubmitCandidates(orderedCandidates);
    const registeredCandidates = filterRegistered(safeOrderedCandidates, existing);
    const candidates = registeredCandidates.length > 0 ? registeredCandidates : safeOrderedCandidates;
    const hostVerifyEnabled =
      verifyEnabled ||
      shouldRequireVerifiedHostSubmit("vscodium", verifyText, this.koruStepConfig());
    const preserveWebviewFocus = isHostClipboardPasteCommand(pasteCommand);
    this.traceOperation({
      op: "submit",
      route: "vscodium",
      ok: true,
      detail: {
        verifyEnabled,
        hostVerifyEnabled,
        trustUnverifiedHostSubmit: this.trustUnverifiedHostSubmit(),
        pasteCommand,
        preserveWebviewFocus,
        usedUnregisteredFallback: registeredCandidates.length === 0,
        unsafeRegisteredCandidatesFiltered: orderedCandidates.length - safeOrderedCandidates.length,
        registeredCandidates: candidates,
      },
    });
    const registered = await this._tryRegisteredCommands(
      candidates,
      verifyText,
      hostVerifyEnabled,
      false
    );
    if (registered) return registered;

    const typeFallback = await this._tryTypeSubmitFallbacks(verifyText, hostVerifyEnabled);
    if (typeFallback?.ok) return typeFallback;

    let preservedFocusHostKey: SubmitOutcome | undefined;
    if (
      hostVerifyEnabled
      && verifyText
      && preserveWebviewFocus
      && this.allowVSCodiumHostInputFallback()
    ) {
      preservedFocusHostKey = await this._tryVerifiedHostKeySubmit("vscodium", verifyText, {
        preserveFocus: true,
        ctrlOnly: true,
      });
      if (preservedFocusHostKey.ok && preservedFocusHostKey.command) return preservedFocusHostKey;
      return preservedFocusHostKey;
    }

    if (!this.allowVSCodiumHostInputFallback()) {
      this.traceOperation({
        op: "submit",
        route: "vscodium-host-fallback-refused",
        ok: false,
        reason: "registered submit commands exhausted; host-key/host-click fallback disabled "
          + "because it targets the active OS window, which may be another VSCodium workspace",
      });
      return {
        ok: false,
        command: "vscodium-submit-unavailable",
        reason: "registered VSCodium submit commands no-oped and host-key fallback is disabled "
          + "to avoid submitting in the wrong workspace/window",
        unverified: true,
      };
    }

    const hostClick = await this._tryHostClickSubmit();
    if (hostClick.ok && hostClick.command) {
      const accepted = await this.finalizeSubmitCandidate(
        hostClick.command,
        verifyText,
        hostVerifyEnabled,
        true
      );
      if (accepted) return accepted;
    }
    if (hostVerifyEnabled && verifyText) {
      if (preservedFocusHostKey) return preservedFocusHostKey;
      const hostKey = await this._tryVerifiedHostKeySubmit("vscodium", verifyText);
      if (hostKey.ok && hostKey.command) return hostKey;
      return hostKey;
    }
    const hostKey = await this._tryHostKeySubmit("vscodium");
    if (hostKey.ok && hostKey.command) {
      return {
        ok: true,
        command: hostKey.command,
        attempts: hostKey.attempts,
        unverified: !this.trustUnverifiedHostSubmit(),
      };
    }
    return {
      ok: false,
      command: "vscodium-submit-unavailable",
      reason: hostClick.reason || hostKey.reason,
      attempts: [...(hostClick.attempts || []), ...(hostKey.attempts || [])],
      unverified: true,
    };
  }

  private async _submitChatCursorVSCodeFallback(
    ide: string,
    verifyText: string | undefined,
    verifyEnabled: boolean
  ): Promise<SubmitOutcome | null> {
    const strategy = getStrategy(ide);
    const hostVerifyEnabled =
      verifyEnabled ||
      shouldRequireVerifiedHostSubmit(ide, verifyText, this.koruStepConfig());

    if (ide === "cursor") {
      this.traceOperation({
        op: "submit",
        route: "cursor-host-fallback-refused",
        ok: false,
        reason: "registered submit commands exhausted; host-key/host-click "
          + "would target whatever OS window has keyboard focus (typically "
          + "the terminal running `koru auto`), not the Cursor chat input",
      });
      return {
        ok: false,
        command: "cursor-submit-unavailable",
        reason: "registered Cursor submit commands no-oped (chat input was "
          + "likely empty because paste did not land in the chat); host-key "
          + "fallback refused because Cursor does not have OS keyboard focus",
        unverified: true,
      };
    }

    const hostKey = await this._tryHostKeySubmit(strategy?.preferCtrlSubmit() ? ide : undefined);
    if (hostKey.ok && hostKey.command) {
      const accepted = await this.finalizeSubmitCandidate(
        hostKey.command,
        verifyText,
        hostVerifyEnabled,
        true,
        { unverified: hostVerifyEnabled ? false : !this.trustUnverifiedHostSubmit() }
      );
      if (accepted) return accepted;
      if (hostVerifyEnabled && verifyText) {
        return {
          ok: false,
          command: hostKey.command || `${ide}-host-key-noop`,
          reason: "host-key submit ran but chat input still contains pasted text",
          attempts: hostKey.attempts,
          unverified: true,
        };
      }
    }
    if (strategy?.submitFallback.refuseTypeNewlineFallback) {
      return {
        ok: false,
        command: `${ide}-submit-unavailable`,
        reason: hostKey.reason,
        attempts: hostKey.attempts,
        unverified: true,
      };
    }
    return null;
  }

  private async _tryRegisteredCommands(
    candidates: string[],
    verifyText: string | undefined,
    verifyEnabled: boolean,
    requireEmptyAfterSubmit = false
  ): Promise<SubmitOutcome | null> {
    for (const cmd of candidates) {
      if (!(await this.runCommand(cmd))) {
        console.warn(`koru autopilot: submitChat command not available: ${cmd}`);
        this.traceOperation({
          op: "submit",
          route: "registered-command",
          ok: false,
          command: cmd,
          reason: "command unavailable or returned false",
        });
        continue;
      }
      this.traceOperation({
        op: "submit",
        route: "registered-command",
        ok: true,
        command: cmd,
        detail: { verifyEnabled, requireEmptyAfterSubmit },
      });
      const accepted = await this.finalizeSubmitCandidate(
        cmd,
        verifyText,
        verifyEnabled,
        requireEmptyAfterSubmit
      );
      if (accepted) return accepted;
      this.traceOperation({
        op: "submit",
        route: "registered-command-rejected",
        ok: false,
        command: cmd,
        reason: "post-submit verification failed; input still contains pasted text",
      });
    }
    return null;
  }

  private async _tryTypeSubmitFallbacks(
    verifyText: string | undefined,
    verifyEnabled: boolean
  ): Promise<SubmitOutcome | null> {
    for (const attempt of [() => this._tryTypeSubmit("\n")]) {
      const result = await attempt();
      if (result.ok && result.command) {
        if (this.detectIde() === "vscodium") {
          this.traceOperation({
            op: "submit",
            route: "type-newline-untrusted",
            ok: false,
            command: result.command,
            reason:
              "VSCodium accepted VS Code type-newline command, but this is not "
              + "a trusted chat send proof; treating as submit_unverified",
          });
          return {
            ok: false,
            command: result.command,
            reason:
              "VSCodium type-newline fallback did not produce a trusted chat "
              + "send proof",
            unverified: true,
          };
        }
        const accepted = await this.finalizeSubmitCandidate(result.command, verifyText, verifyEnabled);
        if (accepted) return accepted;
      }
    }
    return null;
  }

  private async _tryTypeSubmit(char: string): Promise<{ ok: boolean; command?: string }> {
    try {
      await Promise.resolve(vscode.commands.executeCommand("type", { text: char }));
      const cmd = `type:${char}`;
      if (this.probeLadderEnabled()) {
        await this.saveProbeCache({ submit: cmd });
      }
      return { ok: true, command: cmd };
    } catch {
      return { ok: false };
    }
  }

  private async _tryHostKeySubmit(ide?: string): Promise<CommandOutcome> {
    if (process.platform !== "linux") {
      return { ok: false };
    }
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const override = cfg.get<string>("submitHostKey", "auto") || "auto";
    const effectiveOverride = this.resolveSubmitHostKeyOverride(ide, override);
    const candidates = buildHostKeySubmitCandidates(ide, effectiveOverride);
    return this.runHostKeyCandidates("SUBMIT_HOST_KEY", candidates);
  }

  private resolveSubmitHostKeyOverride(ide: string | undefined, override: string): string {
    const normalized = (override || "auto").toLowerCase();
    if (ide === "vscodium" && normalized === "auto") {
      return "ctrl+Return";
    }
    return override;
  }

  private static isCtrlHostKeyCandidateArgs(args: string[]): boolean {
    return args.some((arg) => /\bctrl\b/i.test(arg));
  }

  private async _tryVerifiedHostKeySubmit(
    ide: string,
    verifyText: string | undefined,
    options: VerifiedHostKeySubmitOptions = {}
  ): Promise<SubmitOutcome> {
    if (process.platform !== "linux" || !verifyText) {
      return { ok: false };
    }
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const override = cfg.get<string>("submitHostKey", "auto") || "auto";
    const effectiveOverride = this.resolveSubmitHostKeyOverride(ide, override);
    const builtCandidates = buildHostKeySubmitCandidates(ide, effectiveOverride);
    let candidates =
      options.preferPlain && override.toLowerCase() === "auto"
        ? prioritizePlainHostKeySubmitCandidates(builtCandidates)
        : builtCandidates;
    if (options.ctrlOnly) {
      const ctrlOnly = candidates.filter(([, args]: [string, string[]]) => SharedAutopilotBridge.isCtrlHostKeyCandidateArgs(args));
      if (ctrlOnly.length > 0) {
        candidates = ctrlOnly;
      }
    }
    const attempts: string[] = [];
    this.traceOperation({
      op: "submit_host_key_verified",
      route: "host-key-candidates",
      ok: true,
      detail: {
        candidates: candidates.map(([command, args]: [string, string[]]) => `${command} ${args.join(" ")}`),
        preserveFocus: Boolean(options.preserveFocus),
        preferPlain: Boolean(options.preferPlain),
        ctrlOnly: Boolean(options.ctrlOnly),
      },
    });
    for (const [command, args] of candidates) {
      const rendered = `${command} ${args.join(" ")}`;
      const res = await this.runHostCommand(command, args);
      attempts.push(`${rendered} => ${res.ok ? "ok" : "failed"}`);
      this.traceOperation({
        op: "submit",
        route: "host-key-verified",
        ok: res.ok,
        command: rendered,
      });
      if (!res.ok) {
        await this.sleep(80);
        continue;
      }
      const verify = await this.verifySubmitStep(verifyText, true);
      if (verify.cleared) {
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ submit: rendered });
        }
        this.traceOperation({
          op: "submit",
          route: "accepted",
          ok: true,
          command: rendered,
          detail: { verifyEnabled: true, requireEmptyAfterSubmit: true },
        });
        return { ok: true, command: rendered, attempts };
      }
      await this.discardCachedSubmitWinner(rendered);
      this.traceOperation({
        op: "submit",
        route: "host-key-verified",
        ok: false,
        command: rendered,
        reason: "input still contains pasted text",
        detail: { observedLength: verify.observedLength },
      });
      if (!options.preserveFocus) {
        await this.focusChatInput();
      }
      await this.runHostKeyCandidates("SUBMIT_DESELECT", [
        ["wtype", ["-k", "End"]],
        ["xdotool", ["key", "End"]],
        ["ydotool", ["key", "End"]],
      ]);
      if (options.preserveFocus) {
        this.traceOperation({
          op: "submit_deselect",
          route: "preserve-focused-webview",
          ok: true,
          reason: "kept host focus on webview input and collapsed select-all selection before retry",
        });
      }
    }
    return {
      ok: false,
      command: `${ide}-host-key-noop`,
      reason: "host-key submit candidates ran but chat input still contains pasted text",
      attempts,
      unverified: true,
    };
  }

  private submitClickPoint(): { x: number; y: number } | null {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const x = Math.trunc(cfg.get<number>("submitClickX", 0));
    const y = Math.trunc(cfg.get<number>("submitClickY", 0));
    if (x <= 0 || y <= 0) {
      return null;
    }
    return { x, y };
  }

  private async autoSubmitClickPoint(): Promise<ScreenPoint | null> {
    const geometry = await this.runHostCommand("xdotool", [
      "getactivewindow",
      "getwindowgeometry",
      "--shell",
    ]);
    if (!geometry.ok) {
      this.traceOperation({
        op: "submit",
        route: "host-click:auto-point",
        ok: false,
        reason: "xdotool window geometry unavailable",
      });
      return null;
    }
    const parsed = parseXdotoolGeometryShell(geometry.stdout);
    if (!parsed) {
      this.traceOperation({
        op: "submit",
        route: "host-click:auto-point",
        ok: false,
        reason: "invalid xdotool window geometry",
      });
      return null;
    }
    const point = bottomRightSubmitPoint(parsed);
    this.traceOperation({
      op: "submit",
      route: "host-click:auto-point",
      ok: point !== null,
      detail: point !== null ? { x: point.x, y: point.y } : {},
    });
    return point;
  }

  private isWaylandSession(): boolean {
    return (
      (process.env.XDG_SESSION_TYPE || "").toLowerCase() === "wayland"
      || Boolean(process.env.WAYLAND_DISPLAY)
    );
  }

  private async _tryHostClickSubmitYdotool(
    point: ScreenPoint,
    source: string,
    details: string[]
  ): Promise<SubmitOutcome | null> {
    const move = await this.runHostCommand("ydotool", ["mousemove", String(point.x), String(point.y)]);
    details.push(`ydotool mousemove ${point.x} ${point.y} => ${move.ok ? "ok" : "failed"}`);
    debugLog("SUBMIT_CLICK", { command: `ydotool mousemove ${point.x} ${point.y}`, ok: move.ok, x: point.x, y: point.y });
    this.traceOperation({
      op: "submit",
      route: "host-click:ydotool-move",
      ok: move.ok,
      command: `ydotool mousemove ${point.x} ${point.y}`,
    });
    if (!move.ok) {
      return null;
    }
    const click = await this.runHostCommand("ydotool", ["click", "1"]);
    details.push(`ydotool click 1 => ${click.ok ? "ok" : "failed"}`);
    debugLog("SUBMIT_CLICK", { command: "ydotool click 1", ok: click.ok, x: point.x, y: point.y });
    this.traceOperation({
      op: "submit",
      route: "host-click:ydotool-click",
      ok: click.ok,
      command: `ydotool click@${point.x},${point.y}`,
      detail: { source },
    });
    if (!click.ok) {
      return null;
    }
    return {
      ok: true,
      command: `ydotool click@${point.x},${point.y} (${source})`,
      attempts: details,
    };
  }

  private async _tryHostClickSubmitXdotool(
    point: ScreenPoint,
    source: string,
    details: string[]
  ): Promise<SubmitOutcome | null> {
    const x = String(point.x);
    const y = String(point.y);
    const xdotoolResult = await this.runHostCommand("xdotool", ["mousemove", "--sync", x, y, "click", "1"]);
    details.push(`xdotool mousemove --sync ${x} ${y} click 1 => ${xdotoolResult.ok ? "ok" : "failed"}`);
    debugLog("SUBMIT_CLICK", {
      command: `xdotool mousemove --sync ${x} ${y} click 1`,
      ok: xdotoolResult.ok,
      x: point.x,
      y: point.y,
      source,
    });
    this.traceOperation({
      op: "submit",
      route: "host-click:xdotool",
      ok: xdotoolResult.ok,
      command: `xdotool click@${point.x},${point.y}`,
      detail: { source },
    });
    if (!xdotoolResult.ok) {
      return null;
    }
    return {
      ok: true,
      command: `xdotool click@${point.x},${point.y} (${source})`,
      attempts: details,
    };
  }

  private async _tryHostClickSubmit(): Promise<SubmitOutcome> {
    if (process.platform !== "linux") {
      this.traceOperation({ op: "submit", route: "host-click", ok: false, reason: "non-linux" });
      return { ok: false };
    }
    const configuredPoint = this.submitClickPoint();
    const point = configuredPoint ?? await this.autoSubmitClickPoint();
    if (!point) {
      debugLog("SUBMIT_CLICK_SKIP", { reason: "missing submitClickX/submitClickY" });
      this.traceOperation({
        op: "submit",
        route: "host-click",
        ok: false,
        reason: "missing submitClickX/submitClickY and auto point unavailable",
      });
      return {
        ok: false,
        reason: "missing submit click coordinates and auto point unavailable",
        attempts: ["submit click skipped: no calibrated or auto bottom-right point"],
      };
    }
    const source = configuredPoint ? "configured" : "auto-bottom-right";
    const details: string[] = [];
    const tryYdotoolFirst = this.isWaylandSession();
    const first = tryYdotoolFirst
      ? await this._tryHostClickSubmitYdotool(point, source, details)
      : await this._tryHostClickSubmitXdotool(point, source, details);
    if (first?.ok) {
      return first;
    }
    const second = tryYdotoolFirst
      ? await this._tryHostClickSubmitXdotool(point, source, details)
      : await this._tryHostClickSubmitYdotool(point, source, details);
    if (second?.ok) {
      return second;
    }
    this.traceOperation({ op: "submit", route: "host-click", ok: false, reason: "submit click failed", attempts: details });
    return { ok: false, reason: "submit click failed", attempts: details };
  }

  private trustUnverifiedHostSubmit(): boolean {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    return cfg.get<boolean>("trustUnverifiedHostSubmit", true);
  }

  private allowVSCodiumHostInputFallback(): boolean {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    return cfg.get<boolean>("allowVSCodiumHostInputFallback", false)
      || process.env.KORU_VSCODIUM_ALLOW_HOST_INPUT_FALLBACK === "1";
  }

  private async saveHostClipboard(): Promise<string | null> {
    if (this.detectIde() !== "vscodium") {
      return null;
    }
    for (const [cmd, args] of [
      ["wl-paste", ["--no-newline"]],
      ["xclip", ["-selection", "clipboard", "-out"]],
      ["xsel", ["--clipboard", "--output"]],
    ] as Array<[string, string[]]>) {
      const res = await this.runHostCommand(cmd, args);
      if (res.ok) {
        debugLog("HOST_CLIPBOARD_READ", { cmd });
        return res.stdout;
      }
    }
    return null;
  }

  private async writeHostClipboard(text: string): Promise<string | null> {
    for (const [cmd, args] of [
      ["wl-copy", []],
      ["xclip", ["-selection", "clipboard"]],
      ["xsel", ["--clipboard", "--input"]],
    ] as Array<[string, string[]]>) {
      const res = await this.runHostCommand(cmd, args, text);
      if (res.ok) {
        debugLog("HOST_CLIPBOARD_WRITE", { cmd, length: text.length });
        return cmd;
      }
    }
    return null;
  }

  private async restoreHostClipboard(previous: string | null): Promise<void> {
    if (previous === null || this.detectIde() !== "vscodium") {
      return;
    }
    await this.writeHostClipboard(previous);
    debugLog("HOST_CLIPBOARD_RESTORE", { length: previous.length });
  }

  async calibrateProbe(): Promise<void> {
    const token = `__koru_probe_${Math.random().toString(36).slice(2, 10)}__`;
    const lines: string[] = [`IDE: ${this.detectIde()} (${vscode.env.appName})`];
    const focus = await this.openChatPanel("probe");
    lines.push(focus.ok ? `focus open: ${focus.command}` : "focus open: FAILED");
    if (!focus.ok) {
      void vscode.window.showWarningMessage(`koru autopilot: could not open chat.\n${lines.join("\n")}`);
      return;
    }
    await this.sleep(this.probeFocusDelayMs());
    const pasted = await this.pasteText(token);
    lines.push(pasted.ok ? `paste: ${pasted.command}` : "paste: FAILED");
    if (!pasted.ok) {
      void vscode.window.showWarningMessage(`koru autopilot: paste failed.\n${lines.join("\n")}`);
      return;
    }
    const cache = this.getProbeCache();
    if (cache) {
      lines.push(`cache: ${JSON.stringify(cache)}`);
    }
    void vscode.window.showInformationMessage(`koru autopilot: probe OK\n${lines.join("\n")}`);
  }

  async captureSubmitClickPosition(): Promise<void> {
    const res = await this.runHostCommand("xdotool", ["getmouselocation"]);
    const match = res.stdout.match(/\bx:(\d+)\s+y:(\d+)\b/);
    if (!res.ok || !match) {
      void vscode.window.showWarningMessage(
        "koru autopilot: could not capture mouse position with xdotool.",
      );
      debugLog("SUBMIT_CLICK_CAPTURE_FAILED", { ok: res.ok, stdout: res.stdout });
      return;
    }
    const x = Number(match[1]);
    const y = Number(match[2]);
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    await cfg.update("submitClickX", x, vscode.ConfigurationTarget.Global);
    await cfg.update("submitClickY", y, vscode.ConfigurationTarget.Global);
    debugLog("SUBMIT_CLICK_CAPTURED", { x, y });
    void vscode.window.showInformationMessage(`koru autopilot: submit click captured: ${x}, ${y}`);
  }

  async sendManualChat(text: string): Promise<void> {
    await this.injectChat({ type: "chat.send", text, submit: true });
  }

  async openChatFromCommand(): Promise<void> {
    await this.openChatPanel("command");
  }
}

export function createBridgeController(
  context: vscode.ExtensionContext,
  options: BridgeOptions,
): BridgeHandle {
  return new SharedAutopilotBridge(context, options);
}
