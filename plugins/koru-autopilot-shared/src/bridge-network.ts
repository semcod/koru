import * as fs from "fs";
import * as net from "net";
import * as vscode from "vscode";
import { SharedAutopilotBridgeBase } from "./bridge-base-class";
import {
  debugLog,
  safeLog,
} from "./bridge-config";
import {
  defaultSocketPathFromEnv,
  socketCandidatesFromEnv,
} from "./socketPath";
import {
  classifyCommands,
  matchingCommandsFlat,
} from "../command-catalog";
import { sanitizeOutboundEnvelope } from "./ack-payload";
import { planDispatch } from "./dispatch-plan";
import { ChatHistoryWatcher, SupportedIde } from "../chat-history-watcher";
import { detectIdeViaStrategies } from "../ides/registry";
import { Envelope, OperationTraceStep, FocusOutcome } from "./types";

const OPEN_CHAT_PANEL_DEBOUNCE_MS = 2000;

export abstract class SharedAutopilotBridgeNetwork extends SharedAutopilotBridgeBase {
  protected chatHistoryWatcher: ChatHistoryWatcher | null = null;

  protected abstract openChatPanel(reason: string): Promise<FocusOutcome>;
  protected abstract injectChat(env: Envelope): Promise<void>;

  protected detectIde(): string {
    const app = vscode.env.appName || "";
    return detectIdeViaStrategies(app) ?? "vscode";
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
      this.maybeOpenChatOnConnect();
      Promise.resolve(vscode.commands.getCommands(false)).then((cmds) => {
        const commandCatalog = classifyCommands(cmds);
        const matching = matchingCommandsFlat(commandCatalog);
        try {
          fs.writeFileSync("/tmp/windsurf-commands.json", JSON.stringify(cmds, null, 2), "utf-8");
        } catch (err) {
          console.error("koru autopilot: failed to write commands to /tmp", err);
        }
        this.send({
          type: "hello",
          id: "vscode-hello",
          ide: this.detectIde(),
          version: vscode.extensions.getExtension(this.options.extensionPackageId)?.packageJSON.version || "unknown",
          buildSha: this.extensionBuildSha(),
          protocolVersion: 2,
          capabilities: [
            "ide.commands",
            "chat.focus",
            "chat.paste",
            "chat.submit",
            "chat.events",
            "chat.history",
            "probe.ladder",
            "command.catalog",
          ],
          pid: process.pid,
          workspaceName: vscode.workspace.name || "",
          workspaceFolders: this.workspaceFolders(),
          matchingCommands: matching,
          commandCatalog,
        });
        this.startChatHistoryWatcherIfEligible();
      });
    });
    sock.on("data", (chunk: string) => this.onData(chunk));
    sock.on("error", (err: Error) => {
      debugLog("CONNECT_ERROR", { path: p, connected, message: err.message });
      if (!connected) {
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

  private extensionBuildSha(): string {
    const raw = vscode.extensions.getExtension(this.options.extensionPackageId)?.packageJSON
      ?.koruAutopilotBuild?.sha;
    return typeof raw === "string" ? raw : "";
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
    if (this.chatHistoryWatcher) {
      this.chatHistoryWatcher.stop();
      this.chatHistoryWatcher = null;
    }
  }

  private startChatHistoryWatcherIfEligible(): void {
    if (this.chatHistoryWatcher) return;
    const ide = this.detectIde();
    const supported: SupportedIde[] = ["cursor", "vscode", "vscodium", "windsurf", "antigravity"];
    if (!supported.includes(ide as SupportedIde)) return;
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (!cfg.get<boolean>("chatHistoryWatch", true)) return;
    const persistKey = `chatHistory.cursor.${ide}`;
    const initialCursor = String(this.context.globalState.get<string>(persistKey, "") || "");
    this.chatHistoryWatcher = new ChatHistoryWatcher({
      ide: ide as SupportedIde,
      pollIntervalMs: cfg.get<number>("chatHistoryPollIntervalMs", 4000) || 4000,
      initialCursor,
      log: (msg, data) => debugLog(msg, data),
      onMessage: async (row) => {
        if (!this.socket) return false;
        this.send({
          type: "message.received",
          chat: row.conversationId || "default",
          text: row.text.substring(0, 4000),
          length: row.text.length,
          summary: row.text.split(/\r?\n/, 1)[0].substring(0, 200),
          createdAt: row.createdAt,
        });
        return true;
      },
      onCursorAdvance: async (cursor) => {
        await this.context.globalState.update(persistKey, cursor);
      },
    });
    this.chatHistoryWatcher.start();
    debugLog("CHAT_HISTORY_WATCH_START", {
      ide,
      adapter: this.chatHistoryWatcher.adapterDescription,
      initialCursor,
    });
  }

  private scheduleRetry(): void {
    if (this.reconnectBlockedReason) return;
    if (this.retryTimer) return;
    const delay = 3000 + Math.floor((Math.random() - 0.5) * 1000);
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      const cfg = vscode.workspace.getConfiguration("koruAutopilot");
      if (cfg.get<boolean>("autoConnect", true)) this.connect();
    }, delay);
  }

  private maybeOpenChatOnConnect(): void {
    if (!this.options.openChatOnConnect) {
      return;
    }
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (cfg.get<boolean>("openChatOnConnect", true) === false) {
      return;
    }
    setTimeout(() => {
      void this.openChatPanel("connect").catch((err) => {
        const detail = err instanceof Error ? err.message : String(err);
        safeLog("OPEN_CHAT_ON_CONNECT_FAILED", { detail });
      });
    }, this.options.openChatOnConnectDelayMs);
  }

  protected emitLiveDsl(step: OperationTraceStep): void {
    if (!this.socket) return;
    try {
      const seq = String(this.operationTrace.length).padStart(3, "0");
      const okToken = step.ok === true ? "true" : step.ok === false ? "false" : "ambiguous";
      const routeToken = step.command ? `${step.route}:${step.command}` : step.route;
      const parts = [
        `#${seq}`,
        `act=${step.op}`,
        `route=${routeToken}`,
        `ok=${okToken}`,
      ];
      if (step.reason) {
        const reason = String(step.reason).replace(/"/g, "'").replace(/\s+/g, " ").slice(0, 160);
        parts.push(`reason="${reason}"`);
      }
      this.sendConsoleLog(`[DSL-LIVE] ${parts.join(" ")}`);
    } catch (err) {
      debugLog("DSL_LIVE_EMIT_FAILED", { err: String(err) });
    }
  }

  public sendConsoleLog(message: string, data?: unknown): void {
    if (!this.socket) return;
    this.send({
      type: "console_log",
      id: "console-log",
      message,
      data,
      timestamp: new Date().toISOString(),
    });
  }

  protected send(env: Envelope): void {
    if (!this.socket) return;
    const wire = sanitizeOutboundEnvelope(env as Record<string, unknown>);
    const line = JSON.stringify(wire) + "\n";
    debugLog("OUT", env);
    const bytes = Buffer.byteLength(line, "utf8");
    if (bytes > 32 * 1024) {
      const fieldSizes: Record<string, number> = {};
      for (const [k, v] of Object.entries(env as Record<string, unknown>)) {
        try {
          fieldSizes[k] = Buffer.byteLength(JSON.stringify(v), "utf8");
        } catch {
          fieldSizes[k] = -1;
        }
      }
      safeLog("OUT_OVERSIZED", {
        type: env.type,
        id: (env as { id?: unknown }).id,
        bytes,
        fields: fieldSizes,
      });
    }
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
      if (this.isReloadablePluginMismatch(message)) {
        this.reconnectBlockedReason = message;
        this.status.text = "$(warning) koru: reload";
        this.status.tooltip = message;
        await this._handleVersionMismatchRejection(message);
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

  private async _handleVersionMismatchRejection(message: string): Promise<void> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const enabled = cfg.get<boolean>("reloadOnVersionMismatch");
    if (enabled === false) {
      void vscode.window.showWarningMessage(`koru autopilot: ${message}`);
      return;
    }
    const ctx = this.context;
    const lastReloadAt = ctx.globalState.get<number>(
      "koruAutopilot.lastVersionMismatchReloadAt",
      0,
    );
    const COOLDOWN_MS = 60_000;
    if (Date.now() - lastReloadAt < COOLDOWN_MS) {
      void vscode.window.showWarningMessage(
        `koru autopilot: ${message} (reload skipped — already attempted within last 60s; ` +
          "run `Developer: Reload Window` manually if the IDE has not loaded the fresh VSIX)",
      );
      return;
    }
    await ctx.globalState.update("koruAutopilot.lastVersionMismatchReloadAt", Date.now());
    const strategies = this.options.reloadCommandStrategies;
    const failures: Array<{ id: string; detail: string }> = [];
    for (const strategy of strategies) {
      try {
        debugLog("PLUGIN_VERSION_MISMATCH_RELOAD_TRY", { strategy });
        const ok = await this.runCommand(strategy);
        if (ok) {
          return;
        }
        failures.push({ id: strategy, detail: "executeCommand returned false" });
      } catch (err) {
        failures.push({ id: strategy, detail: err instanceof Error ? err.message : String(err) });
      }
    }
    safeLog("PLUGIN_VERSION_MISMATCH_RELOAD_FAILED", {
      detail: failures.map((f) => `${f.id}=${f.detail}`).join("; "),
    });
    void vscode.window.showWarningMessage(
      `koru autopilot: automatic reload failed (all strategies failed: ${failures
        .map((f) => `${f.id}=${f.detail}`)
        .join(", ")}). Run \`Developer: Reload Window\` manually.`,
    );
  }

  private isReloadablePluginMismatch(message: string): boolean {
    const lowered = message.toLowerCase();
    return lowered.includes("plugin version mismatch") || lowered.includes("plugin build mismatch");
  }

  protected abstract runCommand(command: string): Promise<boolean>;
}
