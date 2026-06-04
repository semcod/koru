import * as vscode from "vscode";
import { SharedAutopilotBridgeFocusCore } from "./bridge-focus-core";
import { debugLog } from "./bridge-config";
import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  chatFocusHeuristic,
  filterRegistered,
  verifyFocusAfterOpen,
} from "../probe-ladder";
import {
  isSpecificChatInputFocusCommand,
  isTogglingFocusOpenCommand,
  sanitizeFocusOpenCandidates,
  sanitizeFocusOpenCommand,
  filterUnsafeFocusOpenForIde,
} from "./bridge-helpers";
import { getStrategy } from "../ides/registry";
import {
  FocusChatContext,
  FocusOutcome,
} from "./types";

export abstract class SharedAutopilotBridgeFocusStrategy extends SharedAutopilotBridgeFocusCore {
  protected async focusChat(): Promise<FocusOutcome> {
    const primary = (vscode.workspace.getConfiguration("koruAutopilot")
      .get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const context = await this._buildFocusChatContext(primary);
    const alreadyFocused = this._focusChatAlreadyFocused(context);
    if (alreadyFocused) {
      return alreadyFocused;
    }

    const rejected: Array<Record<string, unknown>> = [];
    const inputOnly = await this._preflightFocusInputOnly(context, rejected);
    if (inputOnly) {
      return inputOnly;
    }

    for (const command of context.commands) {
      const result = await this._tryFocusChatCommand(command, context, rejected);
      if (result) {
        return result;
      }
    }
    return this._focusChatFailure(primary, context, rejected);
  }

  private async _preflightFocusInputOnly(
    context: FocusChatContext,
    rejected: Array<Record<string, unknown>>,
  ): Promise<FocusOutcome | null> {
    if (!shouldTryInputOnlyPreflight(context, this.options.preflightFocusOnlyPolicy)) {
      return null;
    }
    return this._focusChatWithoutOpenCommands(rejected);
  }

  private async _buildFocusChatContext(primary: string[]): Promise<FocusChatContext> {
    const ide = this.detectIde();
    await this.quietIDELayoutForChatFocus();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const useProbe = this.probeLadderEnabled();
    let commands = filterUnsafeFocusOpenForIde(filterRegistered(
      this.orderWithServerOverride(
        "focus_open",
        buildFocusOpenCommands(ide, primary),
        cache?.focusOpen,
      ),
      existing
    ), ide);
    if (ide === "vscode" && commands.length === 0 && existing.has("workbench.action.chat.open")) {
      commands = ["workbench.action.chat.open"];
      debugLog("FOCUS_OPEN_HARD_FALLBACK", { ide, command: "workbench.action.chat.open" });
    }
    const before = this.editorSnapshot();
    debugLog("FOCUS_OPEN_START", { ide, commandsCount: commands.length, useProbe, cacheFocusOpen: cache?.focusOpen });
    debugLog("FOCUS_OPEN_CANDIDATES", { ide, commands });
    debugLog("FOCUS_OPEN_BEFORE_SNAPSHOT", { before });
    return { ide, cache, useProbe, commands, before };
  }

  private _focusChatAlreadyFocused(context: FocusChatContext): FocusOutcome | null {
    if (isAlreadyFocusedWithoutOpenCommand(context)) {
      debugLog("FOCUS_OPEN_ALREADY_FOCUSED");
      this.traceOperation({ op: "focus_open", route: "already-focused", ok: true });
      return { ok: true, command: "already-focused" };
    }
    return null;
  }

  private async _focusChatWithoutOpenCommands(
    rejected: Array<Record<string, unknown>>
  ): Promise<FocusOutcome | null> {
    const before = this.editorSnapshot();
    const inputOnly = await this.focusChatInput();
    if (!isSpecificChatInputFocusCommand(inputOnly.command)) {
      rejected.push({
        cmd: "(input-only)",
        reason: "no specific chat input focus command succeeded",
      });
      return null;
    }
    const after = this.editorSnapshot();
    if (!chatFocusHeuristic(after)) {
      debugLog("FOCUS_OPEN_INPUT_ONLY_HIDDEN_PANEL", {
        command: inputOnly.command,
        before,
        after,
      });
      this.traceOperation({
        op: "focus_open",
        route: "input-only",
        ok: false,
        command: inputOnly.command,
        reason: "focus command succeeded but file editor is still active "
          + "(chat panel likely hidden) — fall through to open commands",
      });
      rejected.push({
        cmd: inputOnly.command || "(input-only)",
        reason: "focus succeeded but snapshot shows file editor active",
      });
      return null;
    }
    debugLog("FOCUS_OPEN_INPUT_ONLY_SUCCESS", { command: inputOnly.command });
    this.traceOperation({
      op: "focus_open",
      route: "input-only",
      ok: true,
      command: inputOnly.command,
    });
    return { ok: true, command: inputOnly.command };
  }

  private async _tryFocusChatCommand(
    command: string,
    context: FocusChatContext,
    rejected: Array<Record<string, unknown>>,
  ): Promise<FocusOutcome | null> {
    debugLog("FOCUS_OPEN_ATTEMPT", { cmd: command, isToggle: command.includes("toggle") });
    if (isTogglingFocusOpenCommand(command)) {
      rejected.push({
        cmd: command,
        reason: "toggle command skipped (would hide an already-open chat panel)",
      });
      debugLog("FOCUS_OPEN_TOGGLE_SKIPPED", { cmd: command, ide: context.ide });
      return null;
    }
    const openStrategy = getStrategy(context.ide);
    if (openStrategy?.acceptFocusOpenCommand && !openStrategy.acceptFocusOpenCommand(command)) {
      rejected.push({
        cmd: command,
        reason: "IDE strategy rejected focus-open command (panel chrome / false positive)",
      });
      debugLog("FOCUS_OPEN_STRATEGY_REJECTED", { cmd: command, ide: context.ide });
      return null;
    }
    if (!(await this.runCommand(command))) {
      console.warn(`koru autopilot: focusChat command not available: ${command}`);
      rejected.push({ cmd: command, reason: "executeCommand returned false" });
      debugLog("FOCUS_OPEN_COMMAND_FAILED", { cmd: command, reason: "executeCommand returned false" });
      return null;
    }
    await this.sleep(this.probeFocusDelayMs());
    const inputFocus = await this.focusChatInput();
    if (isSpecificChatInputFocusCommand(inputFocus.command)) {
      return this._verifiedFocusOpenCommand(command, inputFocus.command, context.useProbe);
    }
    if (getStrategy(context.ide)?.trustFocusOpenCommand?.(command)) {
      return this._trustedFocusOpenCommand(command, context);
    }
    const after = this.editorSnapshot();
    debugLog("FOCUS_OPEN_AFTER_SNAPSHOT", { cmd: command, after });
    if (!context.useProbe || verifyFocusAfterOpen(context.before, after, context.ide)) {
      if (openStrategy?.acceptFocusOpenCommand && !openStrategy.acceptFocusOpenCommand(command)) {
        rejected.push({
          cmd: command,
          reason: "IDE strategy rejected focus-open command after snapshot verify",
        });
        return null;
      }
      return this._snapshotVerifiedFocusOpenCommand(command, context.useProbe);
    }
    debugLog("PROBE_FOCUS_REJECT", { cmd: command, before: context.before, after });
    rejected.push({ cmd: command, reason: "probe rejected focus snapshot", before: context.before, after });
    return null;
  }

  private async _verifiedFocusOpenCommand(
    command: string,
    inputFocusCommand: string | undefined,
    useProbe: boolean,
  ): Promise<FocusOutcome> {
    const combined = `${command}+${inputFocusCommand}`;
    debugLog("FOCUS_OPEN_SUCCESS_INPUT", { cmd: command, inputFocus: inputFocusCommand });
    if (useProbe && !isTogglingFocusOpenCommand(command)) {
      await this.saveProbeCache({ focusOpen: command });
    }
    this.traceOperation({ op: "focus_open", route: "command+input", ok: true, command: combined });
    return { ok: true, command: combined };
  }

  private async _trustedFocusOpenCommand(command: string, context: FocusChatContext): Promise<FocusOutcome> {
    debugLog("FOCUS_OPEN_SUCCESS_TRUSTED", { cmd: command, ide: context.ide });
    if (context.useProbe && !isTogglingFocusOpenCommand(command)) {
      await this.saveProbeCache({ focusOpen: command });
    }
    this.traceOperation({ op: "focus_open", route: "trusted-command", ok: true, command });
    return { ok: true, command };
  }

  private async _snapshotVerifiedFocusOpenCommand(command: string, useProbe: boolean): Promise<FocusOutcome> {
    debugLog("FOCUS_OPEN_SUCCESS", { cmd: command });
    if (useProbe && !isTogglingFocusOpenCommand(command)) {
      await this.saveProbeCache({ focusOpen: command });
    }
    this.traceOperation({ op: "focus_open", route: "command", ok: true, command });
    return { ok: true, command };
  }

  private _focusChatFailure(
    primary: string[],
    context: FocusChatContext,
    rejected: Array<Record<string, unknown>>,
  ): FocusOutcome {
    debugLog("FOCUS_OPEN_ALL_FAILED", { rejectedCount: rejected.length });
    this.traceOperation({
      op: "focus_open",
      route: "all-candidates",
      ok: false,
      reason: "no focus-open candidate verified",
      detail: { rejectedCount: rejected.length, candidates: sanitizeFocusOpenCandidates(context.commands) },
    });
    return {
      ok: false,
      diagnostics: {
        ide: context.ide,
        appName: vscode.env.appName,
        logPath: "/tmp/koru-plugin-debug.log",
        probeLadder: context.useProbe,
        configuredChatOpenCommands: primary,
        focusOpenCandidates: sanitizeFocusOpenCandidates(context.commands),
        cacheFocusOpen: sanitizeFocusOpenCommand(context.cache?.focusOpen),
        before: context.before,
        rejected,
      },
    };
  }

  protected cursorEssentialFocusInputCommands(): string[] {
    return [
      "glass.focusInput",
      "workbench.action.chat.focusInput",
      "chat.action.focus",
      "workbench.chat.action.focusLastFocused",
    ];
  }

  protected async cursorRecoverGlassChatFocus(route: string): Promise<{ ok: boolean; command?: string; reason?: string }> {
    for (const opener of ["workbench.action.chat.open", "workbench.action.chat.openagent"]) {
      if (await this.runCommand(opener)) {
        await this.sleep(this.probeFocusDelayMs());
        this.traceOperation({
          op: "focus_open",
          route: `${route}:glass-recover`,
          ok: true,
          command: opener,
        });
        break;
      }
    }
    for (const cmd of this.cursorEssentialFocusInputCommands()) {
      const result = await this._tryFocusInputCommand(cmd);
      if (result.ok) {
        this.traceOperation({
          op: "focus_input",
          route: `${route}:glass-recover`,
          ok: true,
          command: result.command,
        });
        return result;
      }
    }
    return { ok: false, reason: "glass/chat focus recovery exhausted" };
  }

  protected sanitizeFocusInputCacheWinner(
    ide: string,
    cacheWinner: string | undefined
  ): string | undefined {
    if (!cacheWinner) {
      return undefined;
    }
    const strategy = getStrategy(ide);
    if (strategy?.acceptFocusInputCommand && !strategy.acceptFocusInputCommand(cacheWinner)) {
      return undefined;
    }
    return cacheWinner;
  }

  protected async focusChatInput(): Promise<{ ok: boolean; command?: string }> {
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    if (ide === "cursor") {
      for (const cmd of this.cursorEssentialFocusInputCommands()) {
        const result = await this._tryFocusInputCommand(cmd);
        if (result.ok) {
          return result;
        }
      }
    }
    const candidates = filterRegistered(
      this.orderWithServerOverride(
        "focus_input",
        buildFocusInputCommands(ide),
        this.sanitizeFocusInputCacheWinner(ide, cache?.focusInput),
      ),
      existing
    );
    debugLog("FOCUS_INPUT_START", { ide, candidatesCount: candidates.length, cacheFocusInput: cache?.focusInput });
    debugLog("FOCUS_INPUT_CANDIDATES", { ide, candidates });
    for (const cmd of candidates) {
      const result = await this._tryFocusInputCommand(cmd);
      if (result.ok) {
        return result;
      }
    }
    debugLog("FOCUS_INPUT_ALL_FAILED");
    this.traceOperation({
      op: "focus_input",
      route: "all-candidates",
      ok: false,
      reason: "no focus-input command succeeded",
      detail: { candidates },
    });
    return { ok: false };
  }

  private async _tryFocusInputCommand(cmd: string): Promise<{ ok: boolean; command?: string }> {
    debugLog("FOCUS_INPUT_ATTEMPT", { cmd });
    if (!(await this.runCommand(cmd))) {
      debugLog("FOCUS_INPUT_COMMAND_FAILED", { cmd });
      this.traceOperation({
        op: "focus_input",
        route: "command-failed",
        ok: false,
        command: cmd,
        reason: "executeCommand returned false or threw",
      });
      return { ok: false };
    }
    if (!isSpecificChatInputFocusCommand(cmd)) {
      debugLog("FOCUS_INPUT_NOT_CHAT", { cmd });
      this.traceOperation({
        op: "focus_input",
        route: "non-chat-command",
        ok: false,
        command: cmd,
        reason: "command succeeded but is not a chat/composer focus command",
      });
      return { ok: false };
    }
    const strategy = getStrategy(this.detectIde());
    if (strategy?.acceptFocusInputCommand && !strategy.acceptFocusInputCommand(cmd)) {
      debugLog("FOCUS_INPUT_REJECTED_BY_STRATEGY", { cmd });
      this.traceOperation({
        op: "focus_input",
        route: "strategy-rejected",
        ok: false,
        command: cmd,
        reason: "command exited ok but IDE strategy does not trust it for chat textarea focus",
      });
      return { ok: false };
    }
    debugLog("FOCUS_INPUT_SUCCESS", { cmd });
    if (this.probeLadderEnabled()) {
      await this.saveProbeCache({ focusInput: cmd });
    }
    this.traceOperation({ op: "focus_input", route: "command", ok: true, command: cmd });
    return { ok: true, command: cmd };
  }
}

function shouldTryInputOnlyPreflight(
  context: FocusChatContext,
  policy: string,
): boolean {
  if (context.commands.length === 0) {
    return true;
  }
  const hasToggleOpen = context.commands.some((cmd) => isTogglingFocusOpenCommand(cmd));
  if (!hasToggleOpen) {
    return false;
  }
  if (policy === "all-toggle") {
    return context.commands.every((cmd) => isTogglingFocusOpenCommand(cmd));
  }
  return true;
}

function isAlreadyFocusedWithoutOpenCommand(context: FocusChatContext): boolean {
  return (
    context.useProbe
    && context.ide === "vscode"
    && context.commands.length === 0
    && chatFocusHeuristic(context.before)
  );
}
