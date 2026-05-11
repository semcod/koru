"use strict";
// koru autopilot — VS Code bridge
//
// Connects to the local koru autopilot daemon over a unix socket, sends a
// `hello`, and forwards chat-session lifecycle events. When the daemon
// asks us to inject text (`chat.send`), we open the chat view, type the
// message, and submit it.
//
// Wire protocol: see ../docs/autopilot-design.md.
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const net = __importStar(require("net"));
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
function defaultSocketPath() {
    const xdg = process.env.XDG_RUNTIME_DIR;
    if (xdg)
        return path.join(xdg, "koru-autopilot.sock");
    const uid = (process.getuid?.() ?? 0).toString();
    return `/tmp/koru-autopilot-${uid}.sock`;
}
class AutopilotBridge {
    context;
    socket = null;
    buf = "";
    status;
    retryTimer = null;
    constructor(context) {
        this.context = context;
        this.status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 50);
        this.status.text = "$(plug) koru: off";
        this.status.tooltip = "Click to connect to koru autopilot daemon";
        this.status.command = "koruAutopilot.connect";
        this.status.show();
        context.subscriptions.push(this.status);
    }
    socketPath() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const override = (cfg.get("socketPath") || "").trim();
        return override || defaultSocketPath();
    }
    connect() {
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
        sock.on("data", (chunk) => this.onData(chunk));
        sock.on("error", (err) => {
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
    disconnect() {
        if (this.retryTimer) {
            clearTimeout(this.retryTimer);
            this.retryTimer = null;
        }
        if (this.socket) {
            try {
                this.socket.end();
            }
            catch { /* ignore */ }
            this.socket = null;
        }
    }
    scheduleRetry() {
        if (this.retryTimer)
            return;
        // Add ~±500 ms of jitter so 30 IDE windows don't all reconnect in
        // the same 3 s window after the daemon restarts (R10).
        const delay = 3000 + Math.floor((Math.random() - 0.5) * 1000);
        this.retryTimer = setTimeout(() => {
            this.retryTimer = null;
            const cfg = vscode.workspace.getConfiguration("koruAutopilot");
            if (cfg.get("autoConnect", true))
                this.connect();
        }, delay);
    }
    async runCommand(command) {
        // Wrap a Thenable in a real Promise so we can ``.catch`` it.
        // VS Code's ``Thenable<T>`` lacks ``catch``; ``Promise.resolve``
        // upgrades it without losing the resolved value.
        try {
            await Promise.resolve(vscode.commands.executeCommand(command));
            return true;
        }
        catch (err) {
            console.error(`koru autopilot: command ${command} failed`, err);
            return false;
        }
    }
    detectIde() {
        const app = (vscode.env.appName || "").toLowerCase();
        if (app.includes("windsurf"))
            return "windsurf";
        if (app.includes("cursor"))
            return "cursor";
        return "vscode";
    }
    send(env) {
        if (!this.socket)
            return;
        this.socket.write(JSON.stringify(env) + "\n");
    }
    onData(chunk) {
        this.buf += chunk;
        while (true) {
            const idx = this.buf.indexOf("\n");
            if (idx < 0)
                break;
            const line = this.buf.slice(0, idx);
            this.buf = this.buf.slice(idx + 1);
            if (!line.trim())
                continue;
            try {
                const env = JSON.parse(line);
                this.dispatch(env);
            }
            catch (err) {
                console.error("koru autopilot: bad envelope", line, err);
            }
        }
    }
    async dispatch(env) {
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
    async injectChat(env) {
        const text = typeof env.text === "string" ? env.text : "";
        const submit = env.submit !== false;
        if (!text) {
            this.send({ type: "ack", id: env.id, ok: false, message: "empty text" });
            return;
        }
        // Snapshot the user's clipboard BEFORE we do anything else so we
        // can always restore it — even if focus/paste/submit throws (R8).
        let previous = null;
        try {
            previous = await vscode.env.clipboard.readText();
        }
        catch {
            previous = null;
        }
        try {
            // Best-effort path: focus the active chat view (works in
            // VS Code GitHub Copilot Chat, Windsurf Cascade and most forks).
            await this.runCommand("workbench.action.chat.open");
            await vscode.env.clipboard.writeText(text);
            await this.runCommand("editor.action.clipboardPasteAction");
            if (submit) {
                const ok = await this.runCommand("workbench.action.chat.submit");
                if (!ok)
                    await this.runCommand("workbench.action.chat.acceptInput");
            }
            this.send({ type: "ack", id: env.id, ok: true, delivered: true });
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.send({ type: "ack", id: env.id, ok: false, message });
        }
        finally {
            // Restore clipboard regardless of outcome.
            if (previous !== null) {
                try {
                    await vscode.env.clipboard.writeText(previous);
                }
                catch { /* ignore */ }
            }
        }
    }
}
function activate(context) {
    const bridge = new AutopilotBridge(context);
    context.subscriptions.push(vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()), vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
        const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
        if (text)
            bridge.injectChat({ type: "chat.send", text, submit: true });
    }));
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (cfg.get("autoConnect", true))
        bridge.connect();
}
function deactivate() {
    /* no-op — sockets are released by the runtime */
}
//# sourceMappingURL=extension.js.map