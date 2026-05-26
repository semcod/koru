import * as vscode from "vscode";
import { spawn } from "child_process";
import { SharedAutopilotBridgeWatcher } from "./bridge-watcher";
import { debugLog } from "./bridge-config";
import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  captureEditorSnapshot,
  chatFocusHeuristic,
  filterRegistered,
  loadProbeCache,
  mergeProbeCache,
  orderWithCache,
  sanitizeProbeCacheForIde,
  verifyFocusAfterOpen,
  type ProbeCacheEntry,
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
  CommandCapability,
  CommandOutcome,
  FocusChatContext,
  FocusOutcome,
  HostCommandResult,
  OperationTraceStep,
} from "./types";

const OPEN_CHAT_PANEL_DEBOUNCE_MS = 2000;

export abstract class SharedAutopilotBridgeFocus extends SharedAutopilotBridgeWatcher {
  protected openChatPanelInFlight: Promise<FocusOutcome> | null = null;
  protected lastOpenChatPanelAt = 0;
  protected lastOpenChatPanelOutcome: FocusOutcome | null = null;

  protected sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  protected async runCommand(command: string): Promise<boolean> {
    try {
      const result = await Promise.resolve(vscode.commands.executeCommand(command));
      if (result === false) {
        return false;
      }
      return true;
    } catch (err) {
      console.error(`koru autopilot: command ${command} failed`, err);
      return false;
    }
  }

  protected probeLadderEnabled(): boolean {
    return vscode.workspace.getConfiguration("koruAutopilot").get<boolean>("probeLadder", true);
  }

  protected probeFocusDelayMs(): number {
    return vscode.workspace.getConfiguration("koruAutopilot").get<number>("probeFocusDelayMs", 220);
  }

  protected probePasteDelayMs(): number {
    return vscode.workspace.getConfiguration("koruAutopilot").get<number>("probePasteDelayMs", 120);
  }

  protected async waitForCommand(command: string, timeoutMs: number, intervalMs = 100): Promise<boolean> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() <= deadline) {
      const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
      if (existing.has(command)) {
        return true;
      }
      await this.sleep(intervalMs);
    }
    return false;
  }

  protected editorSnapshot(): ReturnType<typeof captureEditorSnapshot> {
    return captureEditorSnapshot(vscode.window.activeTextEditor);
  }

  protected getProbeCache(): ProbeCacheEntry | undefined {
    const ide = this.detectIde();
    const raw = this.context.globalState.get<unknown>("probeCache.v3");
    const cache = loadProbeCache(raw, ide, vscode.env.appName || "");
    return sanitizeProbeCacheForIde(cache, ide);
  }

  protected async saveProbeCache(
    wins: Partial<Pick<ProbeCacheEntry, "focusOpen" | "focusInput" | "paste" | "submit">>
  ): Promise<void> {
    const next = mergeProbeCache(
      this.getProbeCache(),
      this.detectIde(),
      vscode.env.appName || "",
      wins
    );
    await this.context.globalState.update("probeCache.v3", next);
    debugLog("PROBE_CACHE", next);
  }

  protected async runHostCommand(command: string, args: string[], input?: string): Promise<HostCommandResult> {
    if (process.platform !== "linux") {
      return { ok: false, stdout: "" };
    }
    return new Promise<HostCommandResult>((resolve) => {
      const child = spawn(command, args, { stdio: ["pipe", "pipe", "ignore"] });
      const chunks: Buffer[] = [];
      child.stdout.on("data", (chunk: Buffer) => chunks.push(chunk));
      child.on("error", () => resolve({ ok: false, stdout: "" }));
      child.on("close", (code) => {
        resolve({ ok: code === 0, stdout: Buffer.concat(chunks).toString("utf8") });
      });
      if (input !== undefined) {
        child.stdin.end(input);
      } else {
        child.stdin.end();
      }
    });
  }

  protected async runHostKeyCandidates(
    label: string,
    candidates: Array<[string, string[]]>
  ): Promise<CommandOutcome> {
    const attempts: string[] = [];
    this.traceOperation({
      op: label.toLowerCase(),
      route: "host-key-candidates",
      ok: true,
      detail: { candidates: candidates.map(([command, args]) => `${command} ${args.join(" ")}`) },
    });
    for (const [command, args] of candidates) {
      const res = await this.runHostCommand(command, args);
      const rendered = `${command} ${args.join(" ")}`;
      attempts.push(`${rendered} => ${res.ok ? "ok" : "failed"}`);
      debugLog(label, { command: rendered, ok: res.ok });
      this.traceOperation({
        op: label.toLowerCase(),
        route: command,
        ok: res.ok,
        command: rendered,
      });
      if (res.ok) {
        return { ok: true, command: rendered, attempts };
      }
      await this.sleep(80);
    }
    return { ok: false, reason: "host key command failed", attempts };
  }

  protected async clearChatInput(): Promise<void> {
    if (this.detectIde() !== "vscodium" || process.platform !== "linux") {
      return;
    }
    await this.runHostKeyCandidates("CLEAR_INPUT_SELECT_ALL", [
      ["wtype", ["-M", "ctrl", "-k", "a", "-m", "ctrl"]],
      ["xdotool", ["key", "ctrl+a"]],
      ["ydotool", ["key", "ctrl+a"]],
    ]);
    await this.runHostKeyCandidates("CLEAR_INPUT_BACKSPACE", [
      ["wtype", ["-k", "BackSpace"]],
      ["xdotool", ["key", "BackSpace"]],
      ["ydotool", ["key", "Backspace"]],
    ]);
  }

  async openChatFromCommand(): Promise<void> {
    await this.openChatPanel("command");
  }

  protected async openChatPanel(reason: string): Promise<FocusOutcome> {
    if (this.openChatPanelInFlight) {
      return this.openChatPanelInFlight;
    }
    const now = Date.now();
    if (
      this.lastOpenChatPanelOutcome &&
      now - this.lastOpenChatPanelAt < OPEN_CHAT_PANEL_DEBOUNCE_MS
    ) {
      return this.lastOpenChatPanelOutcome;
    }

    this.openChatPanelInFlight = this.performOpenChatPanel(reason);
    try {
      const outcome = await this.openChatPanelInFlight;
      this.lastOpenChatPanelAt = Date.now();
      this.lastOpenChatPanelOutcome = outcome;
      return outcome;
    } finally {
      this.openChatPanelInFlight = null;
    }
  }

  private async performOpenChatPanel(reason: string): Promise<FocusOutcome> {
    this.resetOperationTrace();
    this.traceOperation({
      op: "focus_open",
      route: "plugin",
      ok: true,
      detail: { ide: this.detectIde(), reason },
    });
    const focus = await this.focusChat();
    this.traceOperation({
      op: focus.command ? `command:${focus.command}` : "command",
      route: focus.command ? `command:${focus.command}` : "command",
      ok: focus.ok,
      reason: focus.reason,
      attempts: focus.attempts,
      detail: focus.diagnostics,
    });
    this.send({
      type: "chat.opened",
      chat: "default",
      ok: focus.ok,
      reason,
      command: focus.command,
      message: focus.reason,
      operation_trace: this.currentOperationTrace(),
    });
    return focus;
  }

  protected abstract currentOperationTrace(): OperationTraceStep[];

  private async focusChat(): Promise<FocusOutcome> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const primary = (cfg.get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const context = await this._buildFocusChatContext(primary);
    const alreadyFocused = this._focusChatAlreadyFocused(context);
    if (alreadyFocused) {
      return alreadyFocused;
    }
    const rejected: Array<Record<string, unknown>> = [];
    if (this._shouldPreflightFocusOnly(context)) {
      const inputOnly = await this._focusChatWithoutOpenCommands(rejected);
      if (inputOnly) {
        return inputOnly;
      }
    } else if (context.commands.length === 0) {
      const inputOnly = await this._focusChatWithoutOpenCommands(rejected);
      if (inputOnly) {
        return inputOnly;
      }
    }
    for (const command of context.commands) {
      const result = await this._tryFocusChatCommand(command, context, rejected);
      if (result) {
        return result;
      }
    }
    return this._focusChatFailure(primary, context, rejected);
  }

  private _shouldPreflightFocusOnly(context: FocusChatContext): boolean {
    if (context.commands.length === 0) {
      return false;
    }
    const hasToggleOpen = context.commands.some((cmd) => isTogglingFocusOpenCommand(cmd));
    if (!hasToggleOpen) {
      return false;
    }
    if (this.options.preflightFocusOnlyPolicy === "all-toggle") {
      const hasNonToggleOpen = context.commands.some(
        (cmd) => !isTogglingFocusOpenCommand(cmd),
      );
      return !hasNonToggleOpen;
    }
    return true;
  }

  private async _buildFocusChatContext(primary: string[]): Promise<FocusChatContext> {
    const ide = this.detectIde();
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
    if (
      context.useProbe
      && context.ide === "vscode"
      && context.commands.length === 0
      && chatFocusHeuristic(context.before)
    ) {
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
    if (!(await this.runCommand(command))) {
      console.warn(`koru autopilot: focusChat command not available: ${command}`);
      rejected.push({ cmd: command, reason: "executeCommand returned false" });
      debugLog("FOCUS_OPEN_COMMAND_FAILED", { cmd: command, reason: "executeCommand returned false" });
      return null;
    }
    await this.sleep(this.probeFocusDelayMs());
    const inputFocus = await this.focusChatInput();
    if (isSpecificChatInputFocusCommand(inputFocus.command)) {
      const combined = `${command}+${inputFocus.command}`;
      debugLog("FOCUS_OPEN_SUCCESS_INPUT", { cmd: command, inputFocus: inputFocus.command });
      if (context.useProbe) {
        await this.saveProbeCache({ focusOpen: command });
      }
      this.traceOperation({ op: "focus_open", route: "command+input", ok: true, command: combined });
      return { ok: true, command: combined };
    }
    const strategy = getStrategy(context.ide);
    if (strategy?.trustFocusOpenCommand?.(command)) {
      debugLog("FOCUS_OPEN_SUCCESS_TRUSTED", { cmd: command, ide: context.ide });
      if (context.useProbe) {
        await this.saveProbeCache({ focusOpen: command });
      }
      this.traceOperation({ op: "focus_open", route: "trusted-command", ok: true, command });
      return { ok: true, command };
    }
    const after = this.editorSnapshot();
    debugLog("FOCUS_OPEN_AFTER_SNAPSHOT", { cmd: command, after });
    if (!context.useProbe || verifyFocusAfterOpen(context.before, after, context.ide)) {
      debugLog("FOCUS_OPEN_SUCCESS", { cmd: command });
      if (context.useProbe) {
        await this.saveProbeCache({ focusOpen: command });
      }
      this.traceOperation({ op: "focus_open", route: "command", ok: true, command });
      return { ok: true, command };
    }
    debugLog("PROBE_FOCUS_REJECT", { cmd: command, before: context.before, after });
    rejected.push({ cmd: command, reason: "probe rejected focus snapshot", before: context.before, after });
    return null;
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

  protected async focusChatInput(): Promise<{ ok: boolean; command?: string }> {
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      this.orderWithServerOverride("focus_input", buildFocusInputCommands(ide), cache?.focusInput),
      existing
    );
    debugLog("FOCUS_INPUT_START", { ide, candidatesCount: candidates.length, cacheFocusInput: cache?.focusInput });
    debugLog("FOCUS_INPUT_CANDIDATES", { ide, candidates });
    for (const cmd of candidates) {
      debugLog("FOCUS_INPUT_ATTEMPT", { cmd });
      if (!(await this.runCommand(cmd))) {
        debugLog("FOCUS_INPUT_COMMAND_FAILED", { cmd });
        continue;
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
        continue;
      }
      debugLog("FOCUS_INPUT_SUCCESS", { cmd });
      if (this.probeLadderEnabled()) {
        await this.saveProbeCache({ focusInput: cmd });
      }
      this.traceOperation({ op: "focus_input", route: "command", ok: true, command: cmd });
      return { ok: true, command: cmd };
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

  protected orderWithServerOverride(
    capability: CommandCapability,
    localCommands: string[],
    cacheWinner?: string,
  ): string[] {
    const server = this.pendingCommandOrder?.[capability];
    if (server?.length) {
      return mergeUnique(server, localCommands);
    }
    return orderWithCache(localCommands, cacheWinner);
  }

  protected abstract get pendingCommandOrder(): Partial<Record<CommandCapability, string[]>> | undefined;
}

function mergeUnique(arr1: readonly string[], arr2: readonly string[]): string[] {
  const seen = new Set<string>();
  const res: string[] = [];
  for (const x of arr1) {
    if (!seen.has(x)) {
      seen.add(x);
      res.push(x);
    }
  }
  for (const x of arr2) {
    if (!seen.has(x)) {
      seen.add(x);
      res.push(x);
    }
  }
  return res;
}
