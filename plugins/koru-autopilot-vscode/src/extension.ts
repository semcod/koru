// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.

import * as fs from "fs";
import * as net from "net";
import { spawn } from "child_process";
import * as vscode from "vscode";
import { planDispatch } from "./dispatch-plan";
import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildPasteDirectCommands,
  buildSubmitCommands,
  captureEditorSnapshot,
  filterRegistered,
  loadProbeCache,
  mergeProbeCache,
  orderWithCache,
  pasteLandedInEditor,
  type ProbeCacheEntry,
  verifyFocusAfterOpen,
} from "./probe-ladder";
import { defaultSocketPathFromEnv, socketCandidatesFromEnv } from "./socketPath";

interface Envelope {
  type: string;
  id?: string;
  [k: string]: unknown;
}

type CommandOutcome = { ok: boolean; command?: string };
type FocusOutcome = CommandOutcome & { diagnostics?: Record<string, unknown> };
type PasteAttempt = { handled: boolean; result: CommandOutcome };
type SubmitOutcome = CommandOutcome & { unverified?: boolean };
type HostCommandResult = { ok: boolean; stdout: string };

let activeBridge: AutopilotBridge | null = null;

function debugLog(message: string, data?: unknown): void {
  try {
    const suffix = data === undefined ? "" : " " + JSON.stringify(data);
    fs.appendFileSync("/tmp/koru-plugin-debug.log", `${new Date().toISOString()} ${message}${suffix}\n`);
  } catch {
    /* ignore */
  }
}

class AutopilotBridge {
  private socket: net.Socket | null = null;
  private buf = "";
  private status: vscode.StatusBarItem;
  private retryTimer: NodeJS.Timeout | null = null;
  private connectCandidates: string[] = [];
  private connectIndex = 0;
  private reconnectBlockedReason: string | null = null;

  constructor(private context: vscode.ExtensionContext) {
    this.status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 50);
    this.status.text = "$(plug) koru: off";
    this.status.tooltip = "Click to connect to koru autopilot daemon";
    this.status.command = "koruAutopilot.connect";
    this.status.show();
    context.subscriptions.push(this.status);
  }

  socketPath(): string {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const override = (cfg.get<string>("socketPath") || "").trim();
    return override || defaultSocketPathFromEnv();
  }

  connect(): void {
    this.disconnect();
    this.reconnectBlockedReason = null;
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const override = (cfg.get<string>("socketPath") || "").trim();
    this.connectCandidates = socketCandidatesFromEnv(this.detectIde(), override);
    this.connectIndex = 0;
    debugLog("CONNECT_CANDIDATES", {
      ide: this.detectIde(),
      override,
      candidates: this.connectCandidates,
    });
    this.tryConnectNext();
  }

  private tryConnectNext(): void {
    if (this.connectIndex >= this.connectCandidates.length) {
      this.status.text = "$(warning) koru: off";
      this.status.tooltip = "koru autopilot: no reachable socket candidate";
      this.scheduleRetry();
      return;
    }
    const p = this.connectCandidates[this.connectIndex++];
    debugLog("CONNECT_TRY", { path: p });
    const sock = net.createConnection(p);
    sock.setEncoding("utf-8");
    let connected = false;
    sock.on("connect", () => {
      connected = true;
      this.socket = sock;
      this.status.text = "$(plug) koru: on";
      this.status.tooltip = `koru autopilot: connected ${p}`;
      debugLog("CONNECT_OK", { path: p, ide: this.detectIde() });
      Promise.resolve(vscode.commands.getCommands(false)).then((cmds) => {
        const matching = cmds.filter(c =>
          c.includes("windsurf") || c.includes("cascade") || c.includes("codeium") || c.includes("chat") || c.includes("composer")
        );
        try {
          fs.writeFileSync("/tmp/windsurf-commands.json", JSON.stringify(cmds, null, 2), "utf-8");
        } catch (err) {
          console.error("koru autopilot: failed to write commands to /tmp", err);
        }
        this.send({
          type: "hello",
          id: "vscode-hello",
          ide: this.detectIde(),
          version: vscode.extensions.getExtension("semcod.koru-autopilot-vscode")?.packageJSON.version || "unknown",
          protocolVersion: 1,
          capabilities: [
            "ide.commands",
            "chat.focus",
            "chat.paste",
            "chat.submit",
            "chat.events",
            "probe.ladder",
          ],
          pid: process.pid,
          matchingCommands: matching,
        });
      });
    });
    sock.on("data", (chunk: string) => this.onData(chunk));
    sock.on("error", (err: Error) => {
      debugLog("CONNECT_ERROR", { path: p, connected, message: err.message });
      if (!connected) {
        // Try next candidate immediately on initial connect failure.
        try { sock.destroy(); } catch { /* ignore */ }
        this.tryConnectNext();
        return;
      }
      this.status.text = "$(warning) koru: err";
      this.status.tooltip = `koru autopilot: ${err.message}`;
      this.scheduleRetry();
    });
    sock.on("close", () => {
      debugLog("CONNECT_CLOSE", { path: p, connected });
      if (!connected) return;
      this.status.text = "$(plug) koru: off";
      this.socket = null;
      if (this.reconnectBlockedReason) {
        this.status.text = "$(warning) koru: reload";
        this.status.tooltip = `koru autopilot: ${this.reconnectBlockedReason}`;
        return;
      }
      this.scheduleRetry();
    });
  }

  disconnect(): void {
    debugLog("DISCONNECT");
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.socket) {
      try { this.socket.end(); } catch { /* ignore */ }
      this.socket = null;
    }
  }

  private scheduleRetry(): void {
    if (this.reconnectBlockedReason) return;
    if (this.retryTimer) return;
    // Add ~±500 ms of jitter so 30 IDE windows don't all reconnect in
    // the same 3 s window after the daemon restarts (R10).
    const delay = 3000 + Math.floor((Math.random() - 0.5) * 1000);
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      const cfg = vscode.workspace.getConfiguration("koruAutopilot");
      if (cfg.get<boolean>("autoConnect", true)) this.connect();
    }, delay);
  }

  private async runCommand(command: string): Promise<boolean> {
    // Wrap a Thenable in a real Promise so we can ``.catch`` it.
    // VS Code's ``Thenable<T>`` lacks ``catch``; ``Promise.resolve``
    // upgrades it without losing the resolved value.
    // Some commands resolve ``false`` when they did not run (no-op) — treat
    // that as failure so Windsurf/Cascade fallbacks still run (R15).
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

  private probeLadderEnabled(): boolean {
    return vscode.workspace.getConfiguration("koruAutopilot").get<boolean>("probeLadder", true);
  }

  private probeFocusDelayMs(): number {
    return vscode.workspace.getConfiguration("koruAutopilot").get<number>("probeFocusDelayMs", 220);
  }

  private probePasteDelayMs(): number {
    return vscode.workspace.getConfiguration("koruAutopilot").get<number>("probePasteDelayMs", 120);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private editorSnapshot(): ReturnType<typeof captureEditorSnapshot> {
    return captureEditorSnapshot(vscode.window.activeTextEditor);
  }

  private getProbeCache(): ProbeCacheEntry | undefined {
    const raw = this.context.globalState.get<unknown>("probeCache");
    const cache = loadProbeCache(raw, this.detectIde(), vscode.env.appName || "");
    if (cache && this.detectIde() === "windsurf") {
      const unsafePaste = ["editor.action.clipboardPasteAction", "type"];
      if (cache.paste && unsafePaste.includes(cache.paste)) {
        cache.paste = undefined;
      }
      if (cache.submit && (cache.submit.startsWith("type:") || cache.submit === "type")) {
        cache.submit = undefined;
      }
    }
    if (cache && this.detectIde() === "vscodium" && cache.submit === "workbench.action.chat.submit") {
      cache.submit = undefined;
    }
    return cache;
  }

  private async saveProbeCache(
    wins: Partial<Pick<ProbeCacheEntry, "focusOpen" | "focusInput" | "paste" | "submit">>
  ): Promise<void> {
    const next = mergeProbeCache(
      this.getProbeCache(),
      this.detectIde(),
      vscode.env.appName || "",
      wins
    );
    await this.context.globalState.update("probeCache", next);
    debugLog("PROBE_CACHE", next);
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

  private async _tryHostKeySubmit(): Promise<{ ok: boolean; command?: string }> {
    if (process.platform !== "linux") {
      return { ok: false };
    }
    const attempts: string[][] = [
      ["-k", "Return"],
      ["-M", "ctrl", "-k", "Return", "-m", "ctrl"],
    ];
    for (const args of attempts) {
      const ok = await new Promise<boolean>((resolve) => {
        const child = spawn("wtype", args, { stdio: "ignore" });
        child.on("error", () => resolve(false));
        child.on("close", (code) => resolve(code === 0));
      });
      debugLog("SUBMIT_HOST_KEY", { command: `wtype ${args.join(" ")}`, ok });
      if (ok) {
        return { ok: true, command: `wtype ${args.join(" ")}` };
      }
      await this.sleep(100);
    }
    return { ok: false };
  }

  private async runHostCommand(command: string, args: string[], input?: string): Promise<HostCommandResult> {
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

  private async clearChatInput(): Promise<void> {
    if (this.detectIde() !== "vscodium" || process.platform !== "linux") {
      return;
    }
    const sequences: string[][] = [
      ["-M", "ctrl", "-k", "a", "-m", "ctrl"],
      ["-k", "BackSpace"],
    ];
    for (const args of sequences) {
      await new Promise<void>((resolve) => {
        const child = spawn("wtype", args, { stdio: "ignore" });
        child.on("error", () => resolve());
        child.on("close", () => resolve());
      });
      debugLog("CLEAR_INPUT_HOST_KEY", { command: `wtype ${args.join(" ")}` });
      await this.sleep(80);
    }
  }

  private async submitChat(): Promise<SubmitOutcome> {
    const ide = this.detectIde();
    if (ide === "vscodium") {
      const hostKey = await this._tryHostKeySubmit();
      if (hostKey.ok) {
        return { ...hostKey, unverified: true };
      }
      return {
        ok: false,
        command: "vscodium-submit-unavailable",
        unverified: true,
      };
    }
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      orderWithCache(buildSubmitCommands(ide), cache?.submit),
      existing
    );
    debugLog("SUBMIT_CANDIDATES", { ide, candidates });
    for (const cmd of candidates) {
      if (await this.runCommand(cmd)) {
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ submit: cmd });
        }
        return { ok: true, command: cmd };
      }
      console.warn(`koru autopilot: submitChat command not available: ${cmd}`);
    }
    const fallbacks: Array<() => Promise<{ ok: boolean; command?: string }>> = [
      () => this._tryTypeSubmit("\n"),
      () => this._tryTypeSubmit("\r"),
    ];
    for (const attempt of fallbacks) {
      const result = await attempt();
      if (result.ok) {
        return result;
      }
    }
    return { ok: false };
  }

  private async focusChat(): Promise<FocusOutcome> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const primary = (cfg.get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const useProbe = this.probeLadderEnabled();
    const commands = filterRegistered(
      orderWithCache(buildFocusOpenCommands(ide, primary), cache?.focusOpen),
      existing
    );
    debugLog("FOCUS_OPEN_CANDIDATES", { ide, commands });
    const before = this.editorSnapshot();
    const rejected: Array<Record<string, unknown>> = [];
    for (const cmd of commands) {
      if (!(await this.runCommand(cmd))) {
        console.warn(`koru autopilot: focusChat command not available: ${cmd}`);
        rejected.push({ cmd, reason: "executeCommand returned false" });
        continue;
      }
      await this.sleep(this.probeFocusDelayMs());
      const after = this.editorSnapshot();
      if (!useProbe || verifyFocusAfterOpen(before, after, ide)) {
        if (useProbe) {
          await this.saveProbeCache({ focusOpen: cmd });
        }
        return { ok: true, command: cmd };
      }
      debugLog("PROBE_FOCUS_REJECT", { cmd, before, after });
      rejected.push({ cmd, reason: "probe rejected focus snapshot", before, after });
    }
    return {
      ok: false,
      diagnostics: {
        ide,
        appName: vscode.env.appName,
        logPath: "/tmp/koru-plugin-debug.log",
        probeLadder: useProbe,
        configuredChatOpenCommands: primary,
        focusOpenCandidates: commands,
        cacheFocusOpen: cache?.focusOpen,
        before,
        rejected,
      },
    };
  }

  private async pasteText(text: string): Promise<CommandOutcome> {
    const ide = this.detectIde();
    const useProbe = this.probeLadderEnabled();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const before = this.editorSnapshot();

    if (ide === "vscodium") {
      const hostPaste = await this.tryHostClipboardPaste(text, before, useProbe);
      if (hostPaste.handled) {
        return hostPaste.result;
      }
    }

    const direct = await this.tryDirectPasteCommands(text, ide, existing, cache, before, useProbe);
    if (direct) {
      return direct;
    }

    if (ide === "windsurf") {
      // Direct paste must succeed on Windsurf to prevent fallback editor contamination.
      return { ok: false };
    }

    const clipboard = await this.tryClipboardPaste(text, before, useProbe);
    if (clipboard.handled) {
      return clipboard.result;
    }

    return this.tryTypePaste(text, before, useProbe);
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
      orderWithCache(buildPasteDirectCommands(ide), cache?.paste),
      existing
    );
    for (const cmd of directCommands) {
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
        /* command doesn't exist — try next */
      }
    }

    return undefined;
  }

  private async tryHostClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("HOST_PASTE_NO_INPUT_FOCUS");
    }
    await this.clearChatInput();
    const clip = await this.writeHostClipboard(text);
    if (!clip) {
      debugLog("HOST_PASTE_NO_CLIPBOARD_TOOL");
      return { handled: false, result: { ok: false } };
    }
    const paste = await this.runHostCommand("wtype", ["-M", "ctrl", "-k", "v", "-m", "ctrl"]);
    debugLog("HOST_PASTE_KEY", { ok: paste.ok, clipboard: clip });
    if (!paste.ok) {
      return { handled: true, result: { ok: false } };
    }
    await this.sleep(Math.max(this.probePasteDelayMs(), 350));
    const after = this.editorSnapshot();
    if (useProbe && pasteLandedInEditor(before, after, text)) {
      return { handled: true, result: { ok: false } };
    }
    if (useProbe) {
      await this.saveProbeCache({ paste: `host-clipboard:${clip}+wtype-ctrl-v` });
    }
    return { handled: true, result: { ok: true, command: `host-clipboard:${clip}+wtype-ctrl-v` } };
  }

  private async tryClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("PROBE_PASTE_NO_INPUT_FOCUS");
    }
    try {
      await this.clearChatInput();
      await vscode.env.clipboard.writeText(text);
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
      /* clipboard paste failed — fallback to type */
    }

    return { handled: false, result: { ok: false } };
  }

  private async tryTypePaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<CommandOutcome> {
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

  private async focusChatInput(): Promise<{ ok: boolean; command?: string }> {
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      orderWithCache(buildFocusInputCommands(ide), cache?.focusInput),
      existing
    );
    debugLog("FOCUS_INPUT_CANDIDATES", { ide, candidates });
    for (const cmd of candidates) {
      if (await this.runCommand(cmd)) {
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ focusInput: cmd });
        }
        return { ok: true, command: cmd };
      }
    }
    return { ok: false };
  }

  private detectIde(): string {
    const app = (vscode.env.appName || "").toLowerCase();
    if (app.includes("windsurf")) return "windsurf";
    if (app.includes("cursor")) return "cursor";
    if (app.includes("codium") || app.includes("code - oss") || app.includes("code-oss")) return "vscodium";
    return "vscode";
  }

  private send(env: Envelope): void {
    if (!this.socket) return;
    const line = JSON.stringify(env) + "\n";
    debugLog("OUT", env);
    this.socket.write(line);
  }

  private onData(chunk: string): void {
    this.buf += chunk;
    while (true) {
      const idx = this.buf.indexOf("\n");
      if (idx < 0) break;
      const line = this.buf.slice(0, idx);
      this.buf = this.buf.slice(idx + 1);
      if (!line.trim()) continue;
      try {
        const env = JSON.parse(line) as Envelope;
        if (!env || typeof env !== "object" || typeof env.type !== "string") {
          console.error("koru autopilot: malformed envelope", env);
          continue;
        }
        void this.dispatch(env).catch((err) => {
          const message = err instanceof Error ? err.message : String(err);
          console.error("koru autopilot: dispatch failed", env, err);
          this.send({ type: "error", id: env.id, ok: false, message });
        });
      } catch (err) {
        console.error("koru autopilot: bad envelope", line, err);
      }
    }
  }

  private async dispatch(env: Envelope): Promise<void> {
    if (env.type === "error") {
      const message = typeof env.message === "string" ? env.message : "daemon rejected plugin";
      if (message.includes("plugin version mismatch")) {
        this.reconnectBlockedReason = message;
        this.status.text = "$(warning) koru: reload";
        this.status.tooltip = message;
        void vscode.window.showWarningMessage(`koru autopilot: ${message}`);
      }
      return;
    }
    const plan = planDispatch(env);
    switch (plan.kind) {
      case "injectChat":
        await this.injectChat(env);
        return;
      case "ack":
        this.send({ type: "ack", id: env.id, ok: true, ...plan.info });
        return;
      case "ignore":
        return;
      case "ackAndDisconnect":
        this.send({ type: "ack", id: env.id, ok: true, ...plan.info });
        this.disconnect();
        return;
      case "error":
        this.send({ type: "error", id: env.id, ok: false, message: plan.message });
        return;
    }
  }

  private async saveClipboard(): Promise<string | null> {
    try {
      return await vscode.env.clipboard.readText();
    } catch {
      return null;
    }
  }

  private async restoreClipboard(previous: string | null): Promise<void> {
    if (previous !== null) {
      try {
        await vscode.env.clipboard.writeText(previous);
      } catch {
        /* ignore */
      }
    }
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
      message:
        "chat input is not focused/open; "
        + `ide=${details.ide || this.detectIde()} app=${details.appName || vscode.env.appName}; `
        + `focus_open_candidates=${candidates || "(none)"}; `
        + "log=/tmp/koru-plugin-debug.log. Open chat input manually, then retry.",
    });
  }

  private sendPasteFailureAck(env: Envelope, focus: { ok: boolean; command?: string }): void {
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      opened: true,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      message: "chat opened but paste command failed (probe rejected editor contamination)",
    });
  }

  private sendSubmitFailureAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string },
    attemptedSubmit?: string
  ): void {
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
      verification: "submit_unverified",
      message:
        "chat opened and text injected, but submit could not be verified; "
        + "manual Send may be required. Input was cleared before paste to avoid prompt concatenation.",
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
    });
  }

  private sendMessageSent(text: string): void {
    console.log("koru autopilot: sending message.sent");
    this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
  }

  private async injectChat(env: Envelope): Promise<void> {
    const text = typeof env.text === "string" ? env.text : "";
    const submit = env.submit !== false;
    if (!text) {
      this.send({ type: "ack", id: env.id, ok: false, message: "empty text" });
      return;
    }
    // Snapshot the user's clipboard BEFORE we do anything else so we
    // can always restore it — even if focus/paste/submit throws (R8).
    const previous = await this.saveClipboard();
    const previousHost = await this.saveHostClipboard();
    try {
      await this._performInject(env, text, submit);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.send({ type: "ack", id: env.id, ok: false, message });
    } finally {
      // Restore clipboard regardless of outcome.
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
    let existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
    if (!existing.has("windsurf.sendTextToChat")) {
      try {
        let openCmd = "windsurf.openCascade";
        if (existing.has("workbench.view.windsurfAgentSidebarContainer")) {
          openCmd = "workbench.view.windsurfAgentSidebarContainer";
        } else if (existing.has("windsurf.cascadePanel.open")) {
          openCmd = "windsurf.cascadePanel.open";
        }
        await Promise.resolve(vscode.commands.executeCommand(openCmd));
        await this.sleep(200);
        existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
      } catch (err) {
        console.warn("koru autopilot: failed to open Cascade early", err);
      }
    }
    if (!existing.has("windsurf.sendTextToChat")) {
      return false;
    }
    try {
      await Promise.resolve(vscode.commands.executeCommand("windsurf.sendTextToChat", text));
      this.sendSuccessAck(env, { ok: true, command: "none" }, { ok: true, command: "windsurf.sendTextToChat" }, "windsurf.sendTextToChat");
      if (submit) {
        this.sendMessageSent(text);
      }
      return true;
    } catch (err) {
      console.warn("koru autopilot: windsurf.sendTextToChat fast path failed, trying fallback", err);
      return false;
    }
  }

  private async submitAfterPaste(
    env: Envelope,
    focus: CommandOutcome,
    pasted: CommandOutcome,
    submit: boolean
  ): Promise<string | undefined | null> {
    if (pasted.command === "windsurf.sendTextToChat") {
      return "windsurf.sendTextToChat";
    }
    if (!submit) {
      return undefined;
    }
    await this.sleep(150);
    await this.focusChatInput();
    const submitResult = await this.submitChat();
    if (submitResult.unverified) {
      this.sendSubmitFailureAck(env, focus, pasted, submitResult.command);
      return null;
    }
    if (submitResult.ok) {
      return submitResult.command;
    }
    this.sendSubmitFailureAck(env, focus, pasted);
    return null;
  }

  private async _performInject(env: Envelope, text: string, submit: boolean): Promise<void> {
    if (await this.tryWindsurfSendTextFastPath(env, text, submit)) {
      return;
    }

    const focus = await this.focusChat();
    if (focus.ok) {
      // Extra settle time after verified open (R13).
      await this.sleep(80);
    }
    if (!focus.ok) {
      this.sendFocusFailureAck(env, focus);
      return;
    }
    const pasted = await this.pasteText(text);
    if (!pasted.ok) {
      this.sendPasteFailureAck(env, focus);
      return;
    }
    const submitCmd = await this.submitAfterPaste(env, focus, pasted, submit);
    if (submitCmd === null) {
      return;
    }
    this.sendSuccessAck(env, focus, pasted, submitCmd);
    if (submit) {
      this.sendMessageSent(text);
    }
  }

  async calibrateProbe(): Promise<void> {
    const token = `__koru_probe_${Math.random().toString(36).slice(2, 10)}__`;
    const lines: string[] = [`IDE: ${this.detectIde()} (${vscode.env.appName})`];
    const focus = await this.focusChat();
    lines.push(focus.ok ? `focus open: ${focus.command}` : "focus open: FAILED");
    if (!focus.ok) {
      void vscode.window.showWarningMessage(`koru probe: could not open chat.\n${lines.join("\n")}`);
      return;
    }
    await this.sleep(this.probeFocusDelayMs());
    const pasted = await this.pasteText(token);
    lines.push(pasted.ok ? `paste: ${pasted.command}` : "paste: FAILED");
    if (!pasted.ok) {
      void vscode.window.showWarningMessage(`koru probe: paste failed.\n${lines.join("\n")}`);
      return;
    }
    const cache = this.getProbeCache();
    if (cache) {
      lines.push(`cache: ${JSON.stringify(cache)}`);
    }
    void vscode.window.showInformationMessage(`koru probe OK\n${lines.join("\n")}`);
  }

  async sendManualChat(text: string): Promise<void> {
    await this.injectChat({ type: "chat.send", text, submit: true });
  }
}

export function activate(context: vscode.ExtensionContext): void {
  debugLog("ACTIVATE", {
    appName: vscode.env.appName,
    extensionMode: context.extensionMode,
    extensionPath: context.extensionPath,
  });
  const bridge = new AutopilotBridge(context);
  activeBridge = bridge;
  context.subscriptions.push(
    vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()),
    vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
      const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
      if (text) await bridge.sendManualChat(text);
    }),
    vscode.commands.registerCommand("koruAutopilot.calibrateProbe", () => bridge.calibrateProbe()),
    vscode.commands.registerCommand("koruAutopilot.calibrate", () => bridge.calibrateProbe()),
    vscode.commands.registerCommand("koruAutopilot.calibrateCompact", () => bridge.calibrateProbe()),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (
        event.affectsConfiguration("koruAutopilot.socketPath") ||
        event.affectsConfiguration("koruAutopilot.autoConnect")
      ) {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        if (cfg.get<boolean>("autoConnect", true)) bridge.connect();
      }
    }),
  );
  const cfg = vscode.workspace.getConfiguration("koruAutopilot");
  if (cfg.get<boolean>("autoConnect", true)) bridge.connect();
}

export function deactivate(): void {
  if (activeBridge) {
    activeBridge.disconnect();
    activeBridge = null;
  }
}
