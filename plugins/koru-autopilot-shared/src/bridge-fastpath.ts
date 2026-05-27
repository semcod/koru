import * as vscode from "vscode";
import { SharedAutopilotBridgeAck } from "./bridge-ack";
import { safeLog, debugLog } from "./bridge-config";
import {
  ANTIGRAVITY_SEND_PROMPT_COMMAND,
  canUseAntigravitySendPrompt,
  selectAntigravityOpenCommand,
} from "../antigravity-fastpath";
import {
  decideBusyInputAction,
  shouldVerifyPrePasteBusy,
  type BusyInputAction,
  type KoruAutopilotStepConfig,
} from "../step-decisions";
import { Envelope } from "./types";

export abstract class SharedAutopilotBridgeFastPath extends SharedAutopilotBridgeAck {
  protected abstract koruStepConfig(): KoruAutopilotStepConfig;

  protected async tryWindsurfSendTextFastPath(
    env: Envelope,
    text: string,
    submit: boolean,
  ): Promise<boolean> {
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

  protected async tryAntigravitySendPromptFastPath(
    env: Envelope,
    text: string,
    submit: boolean,
  ): Promise<boolean> {
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

  protected async tryCursorComposerPromptFastPath(
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
    await this.clearComposerDraft();
    return false;
  }

  private async clearComposerDraft(): Promise<void> {
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

  protected async decideBusyInput(
    text: string,
  ): Promise<{ action: BusyInputAction; observedLength: number }> {
    if (!shouldVerifyPrePasteBusy(this.koruStepConfig())) {
      this.traceOperation({ op: "input_busy_probe", route: "disabled", ok: true });
      return { action: "empty", observedLength: 0 };
    }
    const observed = await this.probeChatInputContents();
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
}
