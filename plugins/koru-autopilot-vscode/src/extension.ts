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
import { defaultSocketPathFromEnv, socketCandidatesFromEnv } from "./socketPath";

interface Envelope {
  type: string;
  id?: string;
  [k: string]: unknown;
}

let activeBridge: AutopilotBridge | null = null;

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
    const sock = net.createConnection(p);
    sock.setEncoding("utf-8");
    let connected = false;
    sock.on("connect", () => {
      connected = true;
      this.socket = sock;
      this.status.text = "$(plug) koru: on";
      this.status.tooltip = `koru autopilot: connected ${p}`;
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
      if (!connected) return;
      this.status.text = "$(plug) koru: off";
      this.socket = null;
      this.scheduleRetry();
    });
  }

  disconnect(): void {
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

  private async submitChat(): Promise<boolean> {
    // Windsurf Cascade often ignores generic workbench chat.submit — try
    // Cascade-specific command IDs first.
    const ide = this.detectIde();
    const generic = [
      "workbench.action.chat.submit",
      "workbench.action.chat.acceptInput",
      "workbench.action.chat.send",
      "workbench.action.chat.sendMessage",
      "workbench.action.interactive.accept",
      "composer.submit",
      "aichat.submit",
    ];
    const windsurfFirst = [
      "windsurf.action.cascade.submit",
      "windsurf.action.submitCascade",
      "windsurf.action.submitChat",
      "windsurf.action.chat.submit",
      "windsurf.chat.submit",
      "windsurf.cascade.submit",
      "cascade.submit",
      ...generic,
    ];
    const candidates = ide === "windsurf" ? windsurfFirst : generic;
    for (const cmd of candidates) {
      if (await this.runCommand(cmd)) return true;
      console.warn(`koru autopilot: submitChat command not available: ${cmd}`);
    }
    // Extra fallback for IDEs where chat input is focused but command IDs are hidden.
    try {
      await Promise.resolve(vscode.commands.executeCommand("workbench.action.acceptSelectedQuickOpenItem"));
      return true;
    } catch {
      // ignore
    }
    // Last resort: synthetic Enter in currently focused chat input.
    try {
      await Promise.resolve(vscode.commands.executeCommand("type", { text: "\n" }));
      return true;
    } catch {
      // Some hosts react to CR (\r) but not LF (\n) for submit.
      try {
        await Promise.resolve(vscode.commands.executeCommand("type", { text: "\r" }));
        return true;
      } catch {
        return false;
      }
    }
  }

  private async focusChat(): Promise<boolean> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const primary = (cfg.get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const ide = this.detectIde();
    const defaults =
      ide === "windsurf"
        ? [
            "windsurf.action.openCascade",
            "windsurf.action.openChat",
            "windsurf.chat.open",
            "windsurf.cascade.open",
            "windsurf.panel.chat",
            "cascade.focus",
            "windsurf.action.showCascade",
            "composer.showComposer",
            "workbench.action.chat.open",
            "aichat.newchataction",
          ]
        : [
            "workbench.action.chat.open",
            "composer.showComposer",
            "aichat.newchataction",
          ];
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const runList = async (commands: string[]): Promise<boolean> => {
      for (const cmd of commands) {
        if (!existing.has(cmd)) {
          console.warn(`koru autopilot: focusChat command not registered: ${cmd}`);
          continue;
        }
        if (await this.runCommand(cmd)) return true;
        console.warn(`koru autopilot: focusChat command not available: ${cmd}`);
      }
      return false;
    };
    // If user configured custom commands, try them first, then always fallback
    // to built-ins to avoid hard lock-in on stale command IDs.
    if (primary.length > 0 && (await runList(primary))) {
      return true;
    }
    for (const cmd of defaults) {
      if (primary.includes(cmd)) continue;
      if (!existing.has(cmd)) {
        continue;
      }
      if (await this.runCommand(cmd)) return true;
    }
    return false;
  }

  private async pasteText(text: string): Promise<boolean> {
    const ide = this.detectIde();

    // Try IDE-specific direct text-insertion commands first (avoids
    // clipboard-paste landing in the terminal / wrong editor).
    const directCommands: string[] = [];
    if (ide === "windsurf") {
      directCommands.push(
        "windsurf.action.chat.typeText",
        "windsurf.action.cascade.typeText",
        "windsurf.chat.typeText",
        "windsurf.cascade.typeText",
        "cascade.typeText",
      );
    } else if (ide === "cursor") {
      directCommands.push(
        "cursor.action.chat.typeText",
        "composer.typeText",
      );
    } else {
      directCommands.push(
        "workbench.action.chat.insertText",
        "workbench.action.chat.typeText",
      );
    }
    for (const cmd of directCommands) {
      try {
        await Promise.resolve(vscode.commands.executeCommand(cmd, text));
        // If the command didn't throw we optimistically assume it worked.
        return true;
      } catch {
        /* command doesn't exist — try next */
      }
    }

    // Fallback: synthetic typing via the ``type`` command.
    // ``editor.action.clipboardPasteAction`` only works in text editors,
    // not in webview-based chat panels.  The ``type`` command sends
    // keystrokes to whatever DOM element currently has focus, so we
    // must ensure the chat input is focused first.
    await this.focusChatInput();
    try {
      await Promise.resolve(
        vscode.commands.executeCommand("type", { text })
      );
      return true;
    } catch {
      return false;
    }
  }

  private async focusChatInput(): Promise<boolean> {
    const ide = this.detectIde();
    const existing = new Set(await Promise.resolve(vscode.commands.getCommands(true)));
    const candidates = [
      ...(ide === "windsurf"
        ? [
            "windsurf.action.focusChatInput",
            "windsurf.chat.focusInput",
            "windsurf.cascade.focusInput",
            "cascade.focusInput",
            "windsurf.action.focusCascadeInput",
          ]
        : []),
      // Focus the sidebar / panel areas where the chat lives.
      // Do NOT use focusActiveEditorGroup — that moves focus back
      // to the editor and the paste lands there instead of the chat.
      "workbench.action.focusAuxiliaryBar",   // secondary sidebar (right)
      "workbench.action.focusPanel",          // bottom panel
      "workbench.action.focusSideBar",      // primary sidebar (left)
    ];
    for (const cmd of candidates) {
      if (!existing.has(cmd)) {
        continue;
      }
      if (await this.runCommand(cmd)) return true;
    }
    return false;
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
    try {
      fs.appendFileSync("/tmp/koru-plugin-debug.log", new Date().toISOString() + " OUT " + line);
    } catch { /* ignore */ }
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
      const opened = await this.focusChat();
      if (opened) {
        // Give the chat panel time to render and grab focus before we
        // try to paste (otherwise the editor may still be focused).
        await new Promise(r => setTimeout(r, 300));
      }
      if (!opened) {
        this.send({
          type: "ack",
          id: env.id,
          ok: false,
          opened: false,
          submitted: false,
          message:
            "chat input is not focused/open (no supported focus command in this IDE build). Open chat input manually, then retry.",
        });
        return;
      }
      const pasted = await this.pasteText(text);
      if (!pasted) {
        this.send({
          type: "ack",
          id: env.id,
          ok: false,
          message: "chat opened but paste command failed",
        });
        return;
      }
      let submitted = false;
      if (submit) {
        // Small delay so the chat input has time to process the paste
        // before we try to submit (R13).
        await new Promise(r => setTimeout(r, 150));
        submitted = await this.submitChat();
      }
      if (submit) {
        console.log("koru autopilot: sending message.sent");
        this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
      }
      this.send({ type: "ack", id: env.id, ok: true, delivered: true, opened, submitted });
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

  async sendManualChat(text: string): Promise<void> {
    await this.injectChat({ type: "chat.send", text, submit: true });
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const bridge = new AutopilotBridge(context);
  activeBridge = bridge;
  context.subscriptions.push(
    vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()),
    vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
      const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
      if (text) await bridge.sendManualChat(text);
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
