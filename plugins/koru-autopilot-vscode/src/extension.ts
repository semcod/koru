// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.

import * as net from "net";
import * as vscode from "vscode";
import { defaultSocketPathFromEnv } from "./socketPath";

interface Envelope {
  type: string;
  id?: string;
  [k: string]: unknown;
}

class AutopilotBridge {
  private socket: net.Socket | null = null;
  private buf = "";
  private status: vscode.StatusBarItem;
  private retryTimer: NodeJS.Timeout | null = null;

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
    const p = this.socketPath();
    const sock = net.createConnection(p);
    sock.setEncoding("utf-8");
    sock.on("connect", () => {
      this.socket = sock;
      this.status.text = "$(plug) koru: on";
      this.send({
        type: "hello",
        id: "vscode-hello",
        ide: this.detectIde(),
        version: "0.1.0",
        pid: process.pid,
      });
    });
    sock.on("data", (chunk: string) => this.onData(chunk));
    sock.on("error", (err: Error) => {
      this.status.text = "$(warning) koru: err";
      this.status.tooltip = `koru autopilot: ${err.message}`;
      this.scheduleRetry();
    });
    sock.on("close", () => {
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
    try {
      await Promise.resolve(vscode.commands.executeCommand(command));
      return true;
    } catch (err) {
      console.error(`koru autopilot: command ${command} failed`, err);
      return false;
    }
  }

  private async submitChat(): Promise<boolean> {
    // Try every known chat-submit command across VS Code / Windsurf /
    // Cursor / Code OSS. Order: most common → niche fallbacks.
    const ide = this.detectIde();
    const candidates = [
      "workbench.action.chat.submit",
      "workbench.action.chat.acceptInput",
      "workbench.action.chat.send",
      "workbench.action.chat.sendMessage",
      "workbench.action.interactive.accept",
      "composer.submit",
      "aichat.submit",
      ...(ide === "windsurf" ? [
        "windsurf.action.submitChat",
        "windsurf.action.cascade.submit",
      ] : []),
    ];
    for (const cmd of candidates) {
      if (await this.runCommand(cmd)) return true;
    }
    return false;
  }

  private async focusChat(): Promise<boolean> {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const primary = (cfg.get<string[]>("chatOpenCommands") || []).filter(Boolean);
    const ide = this.detectIde();
    const defaults = [
      "workbench.action.chat.open",
      "composer.showComposer",
      "aichat.newchataction",
      ...(ide === "windsurf" ? [
        "windsurf.action.openChat",
        "windsurf.action.openCascade",
        "cascade.focus",
      ] : []),
    ];
    const commands = primary.length > 0 ? primary : defaults;
    for (const cmd of commands) {
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

    // Fallback: clipboard + paste.  Before pasting, try to move focus
    // away from the terminal and into the chat / editor area.
    await this.focusChatInput();
    await vscode.env.clipboard.writeText(text);
    return await this.runCommand("editor.action.clipboardPasteAction");
  }

  private async focusChatInput(): Promise<boolean> {
    const ide = this.detectIde();
    const candidates = [
      ...(ide === "windsurf"
        ? [
            "windsurf.action.focusChatInput",
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
    this.socket.write(JSON.stringify(env) + "\n");
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
        this.dispatch(env);
      } catch (err) {
        console.error("koru autopilot: bad envelope", line, err);
      }
    }
  }

  private async dispatch(env: Envelope): Promise<void> {
    switch (env.type) {
      case "chat.send":
        await this.injectChat(env);
        break;
      case "ping":
        this.send({ type: "ack", id: env.id, ok: true, pong: true });
        break;
      case "ack":
      case "error":
        // Server-initiated ack/error — informational only.
        break;
      default:
        this.send({ type: "error", id: env.id, ok: false, message: `unhandled ${env.type}` });
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
        // Even if focusChat failed, try the direct text-insertion path
        // (some IDEs accept text without explicitly opening the panel).
        const directPasted = await this.pasteText(text);
        if (!directPasted) {
          this.send({
            type: "ack",
            id: env.id,
            ok: false,
            message:
              "no chat open command succeeded and paste fallback failed — check koruAutopilot.chatOpenCommands",
          });
          return;
        }
        this.send({ type: "ack", id: env.id, ok: true, delivered: true, opened: false, submitted: false });
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
}

export function activate(context: vscode.ExtensionContext): void {
  const bridge = new AutopilotBridge(context);
  context.subscriptions.push(
    vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()),
    vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
      const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
      if (text) (bridge as any).injectChat({ type: "chat.send", text, submit: true });
    }),
  );
  const cfg = vscode.workspace.getConfiguration("koruAutopilot");
  if (cfg.get<boolean>("autoConnect", true)) bridge.connect();
}

export function deactivate(): void {
  /* no-op — sockets are released by the runtime */
}
