import * as vscode from "vscode";
import { SharedAutopilotBridgeAck } from "./bridge-ack";
import { safeLog, debugLog } from "./bridge-config";
import {
  ANTIGRAVITY_SEND_PROMPT_COMMAND,
  canUseAntigravitySendPrompt,
  selectAntigravityOpenCommand,
} from "../antigravity-fastpath";
import {
  buildSubmitCommands,
  filterRegistered,
} from "../probe-ladder";
import {
  decideBusyInputAction,
  interpretPostSubmitProbe,
  shouldVerifyPrePasteBusy,
  type BusyInputAction,
  type KoruAutopilotStepConfig,
} from "../step-decisions";
import { CommandOutcome, Envelope } from "./types";
import {
  CURSOR_COMPOSER_PROMPT_PASTE_COMMANDS,
  CURSOR_COMPOSER_SAFE_PASTE_COMMANDS,
  isGlassTypedPasteCommand,
  resolveCursorComposerPasteCandidates,
} from "./cursor-composer-paste";

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

  protected resolveCursorComposerPasteCandidates(existing: Set<string>) {
    return resolveCursorComposerPasteCandidates(existing);
  }

  protected async tryGlassComposerPromptPaste(text: string): Promise<CommandOutcome | undefined> {
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const { glassUi, promptPastes } = this.resolveCursorComposerPasteCandidates(existing);
    if (!glassUi || promptPastes.length === 0) {
      return undefined;
    }
    for (const pasteCmd of promptPastes) {
      this.traceOperation({
        op: "paste",
        route: `glass-composer-prompt:${pasteCmd}`,
        ok: true,
        command: pasteCmd,
        detail: { textLength: text.length },
      });
      try {
        const result = await Promise.resolve(vscode.commands.executeCommand(pasteCmd, text));
        if (result === false) {
          this.traceOperation({
            op: "paste",
            route: `glass-composer-prompt:${pasteCmd}`,
            ok: false,
            reason: "command returned false",
          });
          continue;
        }
      } catch (err) {
        this.traceOperation({
          op: "paste",
          route: `glass-composer-prompt:${pasteCmd}`,
          ok: false,
          reason: String(err),
        });
        continue;
      }
      await this.sleep(this.probePasteDelayMs());
      return { ok: true, command: pasteCmd };
    }
    return undefined;
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
    const { glassUi, promptPastes, safePastes } = this.resolveCursorComposerPasteCandidates(existing);
    if (
      glassUi &&
      !CURSOR_COMPOSER_PROMPT_PASTE_COMMANDS.some((cmd) => existing.has(cmd)) &&
      promptPastes.length > 0
    ) {
      safeLog("CURSOR_COMPOSER_FASTPATH_GLASS_OPTIMISTIC_PROMPT", {
        reason: "composer.startComposerPrompt* not listed in getCommands(false); trying anyway",
      });
    }
    const modernChatRoute =
      !glassUi &&
      existing.has("workbench.action.chat.stopListeningAndSubmit") &&
      existing.has("workbench.action.chat.typeText");
    // Prefer probe ladder only when registered typeText+stopListening exist on
    // classic chat UI. Glass builds register typeText but it no-ops; keep the
    // startComposerPrompt* fast-path (glass.focusInput alone is unreliable).
    const skipFastPath = modernChatRoute || (promptPastes.length === 0 && safePastes.length === 0);
    if (skipFastPath) {
      const reason = modernChatRoute
        ? glassUi
          ? "Glass Agent UI with registered typeText/stopListening; using probe ladder"
          : "modern chat typeText/stopListeningAndSubmit registered; using probe ladder instead"
        : "no registered composer paste commands";
      safeLog("CURSOR_COMPOSER_FASTPATH_SKIP", { reason });
      this.traceOperation({
        op: "paste",
        route: "cursor-composer-fastpath",
        ok: false,
        reason,
      });
      return false;
    }
    // Glass: prefer native composer prompt API even when typeText is registered
    // (registered but no-op on Glass). Classic chat keeps typeText first.
    const pasteQueue = glassUi
      ? [
          ...promptPastes,
          ...safePastes.filter(
            (cmd) => !promptPastes.includes(cmd as (typeof promptPastes)[number]),
          ),
        ]
      : [
          ...safePastes,
          ...promptPastes.filter((cmd) => !safePastes.includes(cmd as typeof safePastes[number])),
        ];
    if (pasteQueue.length === 0) {
      safeLog("CURSOR_COMPOSER_FASTPATH_ABORT_NO_PASTE_COMMANDS");
      this.traceOperation({
        op: "paste",
        route: "cursor-composer-fastpath",
        ok: false,
        reason: "no registered composer paste commands",
      });
      return false;
    }
    const submitCandidates = filterRegistered(buildSubmitCommands("cursor"), existing);
    if (submit && submitCandidates.length === 0) {
      safeLog("CURSOR_COMPOSER_FASTPATH_ABORT_NO_SUBMIT_COMMANDS");
      this.traceOperation({
        op: "submit",
        route: "cursor-composer-fastpath",
        ok: false,
        reason: "no registered submit commands",
      });
      return false;
    }
    for (const pasteCmd of pasteQueue) {
      safeLog("CURSOR_COMPOSER_FASTPATH_START", {
        submit,
        textLength: text.length,
        pasteCmd,
        submitCandidates,
      });
      const succeeded = await this._runCursorComposerFastPathPaste(
        env,
        text,
        submit,
        pasteCmd,
        submitCandidates
      );
      if (succeeded) {
        return true;
      }
      const riskyPaste = /startcomposerprompt/i.test(pasteCmd);
      if (riskyPaste) {
        safeLog("CURSOR_COMPOSER_FASTPATH_RETRY_AFTER_PROMPT_PASTE", { failedPasteCmd: pasteCmd });
        this.traceOperation({
          op: "paste",
          route: "cursor-composer-fastpath",
          ok: false,
          reason: `startComposerPrompt paste failed verification; retrying with typeText fallback`,
          detail: { failedPasteCmd: pasteCmd },
        });
      }
      await this.clearComposerDraft();
    }
    safeLog("CURSOR_COMPOSER_FASTPATH_EXHAUSTED", { pasteQueue });
    this.traceOperation({
      op: "paste",
      route: "cursor-composer-fastpath",
      ok: false,
      reason: "all composer fast-path paste candidates failed",
      detail: { pasteQueue },
    });
    return false;
  }

  private async _runCursorComposerFastPathPaste(
    env: Envelope,
    text: string,
    submit: boolean,
    pasteCmd: string,
    submitCandidates: string[]
  ): Promise<boolean> {
    await this.captureCursorBubbleAnchor();
    this.traceOperation({
      op: "paste",
      route: `cursor-composer-fastpath:${pasteCmd}`,
      ok: true,
      command: pasteCmd,
      detail: { textLength: text.length },
    });
    try {
      const result = await Promise.resolve(vscode.commands.executeCommand(pasteCmd, text));
      if (result === false) {
        this.traceOperation({
          op: "paste",
          route: `cursor-composer-fastpath:${pasteCmd}`,
          ok: false,
          reason: "command returned false",
        });
        return false;
      }
    } catch (err) {
      safeLog("CURSOR_COMPOSER_FASTPATH_PASTE_FAILED", { pasteCmd, error: String(err) });
      this.traceOperation({
        op: "paste",
        route: `cursor-composer-fastpath:${pasteCmd}`,
        ok: false,
        reason: String(err),
      });
      return false;
    }
    await this.sleep(this.probePasteDelayMs());
    const focus: CommandOutcome = { ok: true, command: pasteCmd };
    const pasted: CommandOutcome = { ok: true, command: pasteCmd };
    if (!submit) {
      this.sendSuccessAck(env, focus, pasted, undefined);
      return true;
    }
    for (const submitCmd of submitCandidates) {
      await this.captureCursorBubbleAnchor();
      this.traceOperation({
        op: "submit",
        route: `cursor-composer-fastpath:${submitCmd}`,
        ok: true,
        command: submitCmd,
      });
      const inputFocus = await this.confirmCursorChatInputBeforeSubmit(
        text,
        `cursor-composer-fastpath:${submitCmd}:focus`,
        pasteCmd
      );
      if (!inputFocus.ok) {
        this.traceOperation({
          op: "submit",
          route: `cursor-composer-fastpath:${submitCmd}`,
          ok: false,
          command: submitCmd,
          reason: inputFocus.reason,
        });
        return false;
      }
      if (!(await this.runCommand(submitCmd))) {
        this.traceOperation({
          op: "submit",
          route: `cursor-composer-fastpath:${submitCmd}`,
          ok: false,
          reason: "command unavailable or returned false",
        });
        continue;
      }
      const verifyResult = await this._verifySubmitViaCursorBubble(text);
      if (verifyResult === null) {
        const observed = await this.probeChatInputContents();
        const fallbackVerify = interpretPostSubmitProbe(observed, text, { requireEmpty: true });
        this.traceOperation({
          op: "submit_verify",
          route: "sentinel-clipboard",
          ok: fallbackVerify.action === "accept",
          reason: fallbackVerify.action === "accept"
            ? "bubble db unavailable; chat input probe confirms prompt was cleared"
            : "bubble db unavailable and chat input probe did not confirm submit",
          detail: {
            observedLength: fallbackVerify.observedLength,
            requireEmptyAfterSubmit: true,
          },
        });
        if (fallbackVerify.action === "accept") {
          this.traceOperation({ op: "submit", route: "success", ok: true, command: submitCmd });
          this.sendSuccessAck(env, focus, pasted, submitCmd);
          this.sendMessageSent(text);
          return true;
        }
        continue;
      }
      if (verifyResult.matched) {
        this.traceOperation({
          op: "submit_verify",
          route: "cursor-bubble-db",
          ok: true,
          detail: { newUserBubbles: verifyResult.newUserBubbles },
        });
        this.traceOperation({ op: "submit", route: "success", ok: true, command: submitCmd });
        this.sendSuccessAck(env, focus, pasted, submitCmd);
        this.sendMessageSent(text);
        return true;
      }
      this.traceOperation({
        op: "submit_verify",
        route: "cursor-bubble-db",
        ok: false,
        reason: "no new user bubble in cursorDiskKV after composer fastpath",
        detail: { pasteCmd, submitCmd, newUserBubbles: verifyResult.newUserBubbles },
      });
    }
    return false;
  }

  private async clearComposerDraft(): Promise<void> {
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const focusCmd = [
      "workbench.action.chat.focusInput",
      "composer.focusComposer",
    ].find((cmd) => existing.has(cmd));
    if (!focusCmd) {
      return;
    }
    try {
      await vscode.commands.executeCommand(focusCmd);
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
