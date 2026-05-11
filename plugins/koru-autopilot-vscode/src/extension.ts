// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.

import * as net from "net";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

interface Envelope {
  type: string;
  id?: string;
  [k: string]: unknown;
}

function defaultSocketPath(): string {
  const xdg = process.env.XDG_RUNTIME_DIR;
  if (xdg) return path.join(xdg, "koru-autopilot.sock");
  const uid = (process.getuid?.() ?? 0).toString();
  return `/tmp/koru-autopilot-${uid}.sock`;
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
    return override || defaultSocketPath();
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
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      const cfg = vscode.workspace.getConfiguration("koruAutopilot");
      if (cfg.get<boolean>("autoConnect", true)) this.connect();
    }, 3000);
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
    try {
      // Best-effort path: focus the active chat view (works in
      // VS Code GitHub Copilot Chat, Windsurf Cascade and most forks).
      await vscode.commands.executeCommand("workbench.action.chat.open").catch(() => undefined);
      // Place the text on the clipboard, paste, then optionally submit.
      const previous = await vscode.env.clipboard.readText();
      await vscode.env.clipboard.writeText(text);
      await vscode.commands.executeCommand("editor.action.clipboardPasteAction");
      if (submit) {
        await vscode.commands
          .executeCommand("workbench.action.chat.submit")
          .catch(() => vscode.commands.executeCommand("workbench.action.chat.acceptInput"));
      }
      // Restore clipboard.
      try { await vscode.env.clipboard.writeText(previous); } catch { /* ignore */ }
      this.send({ type: "ack", id: env.id, ok: true, delivered: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.send({ type: "ack", id: env.id, ok: false, message });
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
