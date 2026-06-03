import * as vscode from "vscode";
import { SharedAutopilotBridgeCommands } from "./bridge-commands";
import { debugLog } from "./bridge-config";
import {
  type ScreenPoint,
  bottomRightSubmitPoint,
  parseXdotoolGeometryShell,
} from "./host-click-submit";
import {
  buildSubmitCommands,
  prioritizePlainHostKeySubmitCandidates,
  filterRegistered,
  buildHostKeySubmitCandidates,
} from "../probe-ladder";
import {
  shouldRequireVerifiedHostSubmit,
  shouldVerifyPostSubmit,
  interpretPostSubmitProbe,
  postSubmitProbeMaxAttempts,
  type KoruAutopilotStepConfig,
} from "../step-decisions";
import { getStrategy } from "../ides/registry";
import {
  Envelope,
  CommandOutcome,
  SubmitOutcome,
} from "./types";
import {
  filterVSCodiumSubmitCandidates,
  isHostClipboardPasteCommand,
} from "./bridge-helpers";

type VerifiedHostKeySubmitOptions = {
  preserveFocus?: boolean;
  preferPlain?: boolean;
  ctrlOnly?: boolean;
};

type HostClickSubmitOptions = {
  allowActiveWindowFallback?: boolean;
};

export abstract class SharedAutopilotBridgeSubmit extends SharedAutopilotBridgeCommands {
  protected async submitAfterPaste(
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

  protected async submitExistingChatInput(
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

  protected koruStepConfig(): KoruAutopilotStepConfig {
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
    let observed = await this.probeChatInputContents();
    const maxAttempts = postSubmitProbeMaxAttempts(ide, { requireEmpty: requireEmptyAfterSubmit });
    for (let attempt = 2; observed === null && attempt <= maxAttempts; attempt += 1) {
      await this.sleep(80 * attempt);
      await this.focusChatInput();
      observed = await this.probeChatInputContents();
      const retryObservedLength = observed === null ? -1 : observed.trim().length;
      this.traceOperation({
        op: "submit_verify",
        route: "sentinel-clipboard-retry",
        ok: observed !== null,
        detail: {
          attempt,
          observedLength: retryObservedLength,
          verifyTextLength: originalText.length,
          requireEmptyAfterSubmit,
        },
      });
    }
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
      // VSCodium can report command success while the prompt remains in the
      // chat input. Treat inconclusive post-submit probes as unverified so the
      // bridge can fall through to repair/fallback instead of emitting
      // message.sent for a paste-only drive.
      true
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
      this.traceOperation({
        op: "submit",
        route: "vscodium-preserve-focus-host-key-rejected",
        ok: false,
        command: preservedFocusHostKey.command,
        reason: preservedFocusHostKey.reason,
      });
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
      const hostClick = await this._tryHostClickSubmit({ allowActiveWindowFallback: true });
      if (hostClick.ok && hostClick.command) {
        const accepted = await this.finalizeSubmitCandidate(
          hostClick.command,
          verifyText,
          hostVerifyEnabled,
          true
        );
        if (accepted) return accepted;
        return {
          ok: false,
          command: hostClick.command,
          reason: "host-click submit ran but chat input still contains pasted text",
          attempts: hostClick.attempts,
          unverified: true,
        };
      }
      if (hostVerifyEnabled && verifyText) {
        const hostKey = await this._tryVerifiedHostKeySubmit("cursor", verifyText, {
          preserveFocus: true,
          ctrlOnly: true,
        });
        if (hostKey.ok && hostKey.command) return hostKey;
        this.traceOperation({
          op: "submit",
          route: "cursor-verified-host-key-rejected",
          ok: false,
          command: hostKey.command,
          reason: hostKey.reason,
          attempts: hostKey.attempts,
        });
      }
      this.traceOperation({
        op: "submit",
        route: "cursor-host-fallback-refused",
        ok: false,
        reason: "registered submit commands exhausted; verified host-click/host-key "
          + "fallbacks were unavailable or did not create a Cursor user bubble",
      });
      return {
        ok: false,
        command: "cursor-submit-unavailable",
        reason: "registered Cursor submit commands no-oped and verified "
          + "host-click/host-key submit fallbacks were unavailable or did not "
          + "create a Cursor user bubble",
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
      if (this.detectIde() === "cursor") {
        await this.captureCursorBubbleAnchor();
      }
      if (!(await this.runSubmitCommand(cmd, verifyText))) {
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

  private async runSubmitCommand(command: string, _verifyText: string | undefined): Promise<boolean> {
    // Do NOT forward verifyText as { inputValue } — VSCodium's workbench.action.chat.submit
    // does not consume that parameter reliably; the text is already in the input via paste.
    return this.runCommand(command);
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
      const ctrlOnly = candidates.filter(([, args]: [string, string[]]) => SharedAutopilotBridgeSubmit.isCtrlHostKeyCandidateArgs(args));
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
      if (ide === "vscodium" && verify.observedLength < 0 && this.trustUnverifiedHostSubmit()) {
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ submit: rendered });
        }
        this.traceOperation({
          op: "submit",
          route: "accepted-unverified-host-key",
          ok: true,
          command: rendered,
          reason: "post-submit probe unavailable; trusting successful VSCodium host key",
          detail: { verifyEnabled: true, requireEmptyAfterSubmit: true, observedLength: verify.observedLength },
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
      await this.runHostKeyCandidates("SUBMIT_DESELECT", this.submitDeselectKeyCandidates());
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

  private async activeWindowSubmitClickPoint(): Promise<{ point: ScreenPoint; source: string } | null> {
    if (process.platform !== "linux") {
      return null;
    }
    if (this.isWaylandSession()) {
      this.traceOperation({
        op: "submit",
        route: "host-click:active-window-geometry",
        ok: false,
        command: "xdotool getactivewindow getwindowgeometry --shell",
        reason: "xdotool active-window geometry skipped on Wayland; calibrate submitClickX/submitClickY",
      });
      return null;
    }
    const geometry = await this.runHostCommand("xdotool", ["getactivewindow", "getwindowgeometry", "--shell"]);
    const parsed = geometry.ok ? parseXdotoolGeometryShell(geometry.stdout) : null;
    this.traceOperation({
      op: "submit",
      route: "host-click:active-window-geometry",
      ok: parsed !== null,
      command: "xdotool getactivewindow getwindowgeometry --shell",
      reason: parsed === null ? "could not resolve active window geometry" : undefined,
    });
    if (!parsed) {
      return null;
    }
    return {
      point: bottomRightSubmitPoint(parsed),
      source: "active-window-bottom-right",
    };
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

  private async _tryHostClickSubmit(options: HostClickSubmitOptions = {}): Promise<SubmitOutcome> {
    if (process.platform !== "linux") {
      this.traceOperation({ op: "submit", route: "host-click", ok: false, reason: "non-linux" });
      return { ok: false };
    }
    const configuredPoint = this.submitClickPoint();
    const resolvedPoint = configuredPoint
      ? { point: configuredPoint, source: "configured" }
      : options.allowActiveWindowFallback
        ? await this.activeWindowSubmitClickPoint()
        : null;
    if (!resolvedPoint) {
      debugLog("SUBMIT_CLICK_SKIP", { reason: "missing submitClickX/submitClickY" });
      this.traceOperation({
        op: "submit",
        route: "host-click",
        ok: false,
        reason: options.allowActiveWindowFallback
          ? "missing calibrated submitClickX/submitClickY and active-window fallback unavailable"
          : "missing calibrated submitClickX/submitClickY",
      });
      return {
        ok: false,
        reason: options.allowActiveWindowFallback
          ? "missing calibrated submit click coordinates and active-window fallback unavailable"
          : "missing calibrated submit click coordinates",
        attempts: ["submit click skipped: no calibrated submitClickX/submitClickY"],
      };
    }
    const { point, source } = resolvedPoint;
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

  private submitDeselectKeyCandidates(): Array<[string, string[]]> {
    const endKeys: Array<[string, string[]]> = [
      ["wtype", ["-k", "End"]],
      ["ydotool", ["key", "End"]],
      ["xdotool", ["key", "End"]],
    ];
    if (this.isWaylandSession()) {
      return endKeys.filter(([command]) => command !== "xdotool");
    }
    return endKeys;
  }

  private trustUnverifiedHostSubmit(): boolean {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    return cfg.get<boolean>("trustUnverifiedHostSubmit", true);
  }
}
