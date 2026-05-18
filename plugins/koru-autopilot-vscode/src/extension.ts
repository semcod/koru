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
      this.send({
        type: "hello",
        id: "vscode-hello",
        ide: this.detectIde(),
        version: vscode.extensions.getExtension("semcod.koru-autopilot-vscode")?.packageJSON.version || "unknown",
        pid: process.pid,
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
    return loadProbeCache(raw, this.detectIde(), vscode.env.appName || "");
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

  private async submitChat(): Promise<{ ok: boolean; command?: string }> {
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      orderWithCache(buildSubmitCommands(ide), cache?.submit),
      existing
    );
    for (const cmd of candidates) {
      if (await this.runCommand(cmd)) {
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ submit: cmd });
        }
        return { ok: true, command: cmd };
      }
      console.warn(`koru autopilot: submitChat command not available: ${cmd}`);
    }
    const fallbacks = [
      "workbench.action.acceptSelectedQuickOpenItem",
      "type:\\n",
      "type:\\r",
    ];
    for (const fb of fallbacks) {
      if (fb === "type:\\n") {
        try {
          await Promise.resolve(vscode.commands.executeCommand("type", { text: "\n" }));
          if (this.probeLadderEnabled()) {
            await this.saveProbeCache({ submit: "type:\\n" });
          }
          return { ok: true, command: "type:\\n" };
        } catch {
          continue;
        }
      }
      if (fb === "type:\\r") {
        try {
          await Promise.resolve(vscode.commands.executeCommand("type", { text: "\r" }));
          if (this.probeLadderEnabled()) {
            await this.saveProbeCache({ submit: "type:\\r" });
          }
          return { ok: true, command: "type:\\r" };
        } catch {
          continue;
        }
      }
      try {
        await Promise.resolve(vscode.commands.executeCommand(fb));
        if (this.probeLadderEnabled()) {
          await this.saveProbeCache({ submit: fb });
        }
        return { ok: true, command: fb };
      } catch {
        /* try next */
      }
    }
    return { ok: false };
  }

  private async focusChat(): Promise<{ ok: boolean; command?: string }> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const primary = (cfg.get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const cache = this.getProbeCache();
    const useProbe = this.probeLadderEnabled();
    const commands = filterRegistered(
      orderWithCache(buildFocusOpenCommands(ide, primary), cache?.focusOpen),
      existing
    );
    const before = this.editorSnapshot();
    for (const cmd of commands) {
      if (!(await this.runCommand(cmd))) {
        console.warn(`koru autopilot: focusChat command not available: ${cmd}`);
        continue;
      }
      await this.sleep(this.probeFocusDelayMs());
      const after = this.editorSnapshot();
      if (!useProbe || verifyFocusAfterOpen(before, after)) {
        if (useProbe) {
          await this.saveProbeCache({ focusOpen: cmd });
        }
        return { ok: true, command: cmd };
      }
      debugLog("PROBE_FOCUS_REJECT", { cmd, before, after });
    }
    return { ok: false };
  }

  private async pasteText(text: string): Promise<{ ok: boolean; command?: string }> {
    const ide = this.detectIde();
    const useProbe = this.probeLadderEnabled();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const cache = this.getProbeCache();
    const before = this.editorSnapshot();

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

    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("PROBE_PASTE_NO_INPUT_FOCUS");
    }
    try {
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
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const cache = this.getProbeCache();
    const candidates = filterRegistered(
      orderWithCache(buildFocusInputCommands(ide), cache?.focusInput),
      existing
    );
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

  private async injectChat(env: Envelope): Promise<void> {
    const text = typeof env.text === "string" ? env.text : "";
    const submit = env.submit !== false;
    if (!text) {
      this.send({ type: "ack", id: env.id, ok: false, message: "empty text" });
      return;
    }
    // Snapshot the user's clipboard BEFORE we do anything else so we
    // can always restore it — even if focus/paste/submit throws (R8).
    let previous: string | null = null;
    try {
      previous = await vscode.env.clipboard.readText();
    } catch {
      previous = null;
    }
    try {
      const focus = await this.focusChat();
      if (focus.ok) {
        // Extra settle time after verified open (R13).
        await this.sleep(80);
      }
      if (!focus.ok) {
        this.send({
          type: "ack",
          id: env.id,
          ok: false,
          opened: false,
          submitted: false,
          probe_ladder: this.probeLadderEnabled(),
          message:
            "chat input is not focused/open (no supported focus command in this IDE build). Open chat input manually, then retry.",
        });
        return;
      }
      const pasted = await this.pasteText(text);
      if (!pasted.ok) {
        this.send({
          type: "ack",
          id: env.id,
          ok: false,
          opened: true,
          probe_ladder: this.probeLadderEnabled(),
          winning_focus_open: focus.command,
          message: "chat opened but paste command failed (probe rejected editor contamination)",
        });
        return;
      }
      let submitted = false;
      let submitCmd: string | undefined;
      if (submit) {
        await this.sleep(150);
        const submitResult = await this.submitChat();
        submitted = submitResult.ok;
        submitCmd = submitResult.command;
      }
      if (submit && submitted) {
        console.log("koru autopilot: sending message.sent");
        this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
      }
      if (submit && !submitted) {
        this.send({
          type: "ack",
          id: env.id,
          ok: false,
          delivered: false,
          opened: true,
          submitted,
          probe_ladder: this.probeLadderEnabled(),
          winning_focus_open: focus.command,
          winning_paste: pasted.command,
          message: "chat opened and text injected, but submit command failed",
        });
        return;
      }
      this.send({
        type: "ack",
        id: env.id,
        ok: true,
        delivered: true,
        opened: true,
        submitted,
        probe_ladder: this.probeLadderEnabled(),
        winning_focus_open: focus.command,
        winning_paste: pasted.command,
        winning_submit: submitCmd,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.send({ type: "ack", id: env.id, ok: false, message });
    } finally {
      // Restore clipboard regardless of outcome.
      if (previous !== null) {
        try { await vscode.env.clipboard.writeText(previous); } catch { /* ignore */ }
      }
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
