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
const fs = __importStar(require("fs"));
const net = __importStar(require("net"));
const child_process_1 = require("child_process");
const vscode = __importStar(require("vscode"));
const ack_payload_1 = require("./ack-payload");
const dispatch_plan_1 = require("./dispatch-plan");
const antigravity_fastpath_1 = require("./antigravity-fastpath");
const host_click_submit_1 = require("./host-click-submit");
const probe_ladder_1 = require("./probe-ladder");
const socketPath_1 = require("./socketPath");
const chat_history_watcher_1 = require("./chat-history-watcher");
const cursor_bubble_adapter_1 = require("./cursor-bubble-adapter");
const step_decisions_1 = require("./step-decisions");
const registry_1 = require("./ides/registry");
const DISALLOWED_FOCUS_OPEN_COMMANDS = new Set([
    "workbench.action.chat.openagent",
    "workbench.action.chat.openask",
]);
const UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS = new Set([
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
    "workbench.panel.aichat.view.copilot.focus",
]);
function isAllowedFocusOpenCommand(command) {
    return (typeof command === "string" &&
        command.trim().length > 0 &&
        !DISALLOWED_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()));
}
function sanitizeFocusOpenCommand(command) {
    if (!isAllowedFocusOpenCommand(command)) {
        return undefined;
    }
    return command.trim();
}
function sanitizeFocusOpenCandidates(commands) {
    return commands.filter(isAllowedFocusOpenCommand);
}
function filterUnsafeFocusOpenForIde(commands, ide) {
    if (ide !== "vscode") {
        return [...commands];
    }
    return commands.filter((command) => !UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()));
}
function isSpecificChatInputFocusCommand(command) {
    if (!command) {
        return false;
    }
    const normalized = command.toLowerCase();
    return normalized.includes("chat") || normalized.includes("composer") || normalized.includes("cascade");
}
/**
 * Commands whose effect *toggles* a chat/composer panel (open → hidden,
 * hidden → open) rather than idempotently opening it. Running these on
 * an already-visible panel hides it, which silently breaks the
 * subsequent paste+submit pipeline because the target surface is no
 * longer rendered. The focus ladder uses this to gate a focus-only
 * preflight (try ``composer.focusComposer`` first; only fall through
 * to toggle commands when the chat input cannot be focused, which
 * implies the panel really is closed).
 */
const TOGGLING_FOCUS_OPEN_COMMANDS = new Set([
    "composer.openaspane",
    "workbench.action.toggleauxiliarybar",
    "workbench.action.togglepanel",
    "workbench.action.togglesidebar",
    "workbench.view.chat.toggle",
]);
function isTogglingFocusOpenCommand(command) {
    if (!command) {
        return false;
    }
    return TOGGLING_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase());
}
let activeBridge = null;
function debugLog(message, data) {
    try {
        const suffix = data === undefined ? "" : " " + JSON.stringify(data);
        fs.appendFileSync("/tmp/koru-plugin-debug.log", `${new Date().toISOString()} ${message}${suffix}\n`);
    }
    catch (err) {
        console.error("koru autopilot: debugLog failed", message, err);
    }
}
function safeLogPayload(data) {
    return JSON.stringify(data, (key, value) => {
        // Avoid circular references and large objects.
        if (typeof value === "object" && value !== null) {
            if (key === "before" || key === "after" || key === "beforeSnapshot" || key === "afterSnapshot") {
                const snapshot = value;
                return { hasEditor: snapshot.hasEditor, isFileLike: snapshot.isFileLike };
            }
        }
        return value;
    });
}
let bridgeInstance = null;
function safeLog(message, data) {
    try {
        const suffix = data === undefined ? "" : " " + safeLogPayload(data);
        console.log(`[koru] ${message}${suffix}`);
        debugLog(message, data);
        // Send to daemon for koru doctor
        bridgeInstance?.sendConsoleLog(message, data);
    }
    catch (err) {
        console.log(`[koru] ${message}`);
        debugLog(message, { log_error: String(err) });
    }
}
class AutopilotBridge {
    context;
    socket = null;
    buf = "";
    status;
    retryTimer = null;
    connectCandidates = [];
    connectIndex = 0;
    reconnectBlockedReason = null;
    chatHistoryWatcher = null;
    operationTrace = [];
    /**
     * Anchor ``rowid`` captured from Cursor's ``cursorDiskKV`` *just before*
     * the current drive's submit step. Used by ``verifySubmitStep`` to look
     * for a fresh ``type = 1`` (user) bubble proving Cursor actually
     * accepted the message — the only ground truth available because the
     * clipboard sentinel probe cannot reach Cursor's chat webview.
     */
    cursorBubbleAnchorRowid = null;
    /**
     * Adapter used to query Cursor's bubble database for post-submit
     * verification. Reused across calls so we don't repeatedly resolve the
     * db path.
     */
    cursorBubbleVerifierAdapter = null;
    constructor(context) {
        this.context = context;
        this.status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 50);
        this.status.text = "$(plug) koru: off";
        this.status.tooltip = "Click to connect to koru autopilot daemon";
        this.status.command = "koruAutopilot.connect";
        this.status.show();
        context.subscriptions.push(this.status);
        bridgeInstance = this;
    }
    isConnected() {
        return this.socket !== null;
    }
    sendConsoleLog(message, data) {
        if (!this.socket)
            return;
        this.send({
            type: "console_log",
            id: "console-log",
            message,
            data,
            timestamp: new Date().toISOString(),
        });
    }
    resetOperationTrace() {
        this.operationTrace = [];
    }
    traceOperation(step) {
        const clipped = {
            ...step,
            attempts: step.attempts?.slice(0, 12),
        };
        this.operationTrace.push(clipped);
        safeLog("OP_ROUTE", clipped);
    }
    currentOperationTrace() {
        return this.operationTrace.slice(-40);
    }
    socketPath() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const override = (cfg.get("socketPath") || "").trim();
        return override || (0, socketPath_1.defaultSocketPathFromEnv)();
    }
    connect() {
        this.disconnect();
        this.reconnectBlockedReason = null;
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const override = (cfg.get("socketPath") || "").trim();
        this.connectCandidates = (0, socketPath_1.socketCandidatesFromEnv)(this.detectIde(), override);
        this.connectIndex = 0;
        debugLog("CONNECT_CANDIDATES", {
            ide: this.detectIde(),
            override,
            candidates: this.connectCandidates,
        });
        this.tryConnectNext();
    }
    tryConnectNext() {
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
                const matching = cmds.filter(c => c.includes("windsurf") || c.includes("cascade") || c.includes("codeium") || c.includes("chat") || c.includes("composer"));
                try {
                    fs.writeFileSync("/tmp/windsurf-commands.json", JSON.stringify(cmds, null, 2), "utf-8");
                }
                catch (err) {
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
                        "chat.history",
                        "probe.ladder",
                    ],
                    pid: process.pid,
                    matchingCommands: matching,
                });
                this.startChatHistoryWatcherIfEligible();
            });
        });
        sock.on("data", (chunk) => this.onData(chunk));
        sock.on("error", (err) => {
            debugLog("CONNECT_ERROR", { path: p, connected, message: err.message });
            if (!connected) {
                // Try next candidate immediately on initial connect failure.
                try {
                    sock.destroy();
                }
                catch { /* ignore */ }
                this.tryConnectNext();
                return;
            }
            this.status.text = "$(warning) koru: err";
            this.status.tooltip = `koru autopilot: ${err.message}`;
            this.scheduleRetry();
        });
        sock.on("close", () => {
            debugLog("CONNECT_CLOSE", { path: p, connected });
            if (!connected)
                return;
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
    disconnect() {
        debugLog("DISCONNECT");
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
        if (this.chatHistoryWatcher) {
            this.chatHistoryWatcher.stop();
            this.chatHistoryWatcher = null;
        }
    }
    /**
     * Start the per-IDE chat-history watcher when (a) the IDE is one we
     * have an adapter for, (b) the user has not explicitly disabled it,
     * and (c) the watcher is not already running. The watcher reads the
     * assistant's latest replies from each IDE's local conversation store
     * and forwards them as ``message.received`` events — exactly the half
     * of ``chat.events`` that the VS Code Extension API itself does NOT
     * expose. Encrypted stores (Windsurf Cascade, Antigravity) are still
     * recognized but no rows are emitted; the input-busy precheck and
     * escalation cooldown still protect those IDEs.
     */
    startChatHistoryWatcherIfEligible() {
        if (this.chatHistoryWatcher)
            return;
        const ide = this.detectIde();
        const supported = ["cursor", "vscode", "vscodium", "windsurf", "antigravity"];
        if (!supported.includes(ide))
            return;
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        if (!cfg.get("chatHistoryWatch", true))
            return;
        const persistKey = `chatHistory.cursor.${ide}`;
        const initialCursor = String(this.context.globalState.get(persistKey, "") || "");
        this.chatHistoryWatcher = new chat_history_watcher_1.ChatHistoryWatcher({
            ide: ide,
            pollIntervalMs: cfg.get("chatHistoryPollIntervalMs", 4000) || 4000,
            initialCursor,
            log: (msg, data) => debugLog(msg, data),
            onMessage: async (row) => {
                if (!this.socket)
                    return false;
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
    scheduleRetry() {
        if (this.reconnectBlockedReason)
            return;
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
        // Some commands resolve ``false`` when they did not run (no-op) — treat
        // that as failure so Windsurf/Cascade fallbacks still run (R15).
        try {
            const result = await Promise.resolve(vscode.commands.executeCommand(command));
            if (result === false) {
                return false;
            }
            return true;
        }
        catch (err) {
            console.error(`koru autopilot: command ${command} failed`, err);
            return false;
        }
    }
    probeLadderEnabled() {
        return vscode.workspace.getConfiguration("koruAutopilot").get("probeLadder", true);
    }
    probeFocusDelayMs() {
        return vscode.workspace.getConfiguration("koruAutopilot").get("probeFocusDelayMs", 220);
    }
    probePasteDelayMs() {
        return vscode.workspace.getConfiguration("koruAutopilot").get("probePasteDelayMs", 120);
    }
    sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }
    async waitForCommand(command, timeoutMs, intervalMs = 100) {
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
    editorSnapshot() {
        return (0, probe_ladder_1.captureEditorSnapshot)(vscode.window.activeTextEditor);
    }
    getProbeCache() {
        const ide = this.detectIde();
        const raw = this.context.globalState.get("probeCache.v3");
        const cache = (0, probe_ladder_1.loadProbeCache)(raw, ide, vscode.env.appName || "");
        return (0, probe_ladder_1.sanitizeProbeCacheForIde)(cache, ide);
    }
    async saveProbeCache(wins) {
        const next = (0, probe_ladder_1.mergeProbeCache)(this.getProbeCache(), this.detectIde(), vscode.env.appName || "", wins);
        await this.context.globalState.update("probeCache.v3", next);
        debugLog("PROBE_CACHE", next);
    }
    async _tryTypeSubmit(char) {
        try {
            await Promise.resolve(vscode.commands.executeCommand("type", { text: char }));
            const cmd = `type:${char}`;
            if (this.probeLadderEnabled()) {
                await this.saveProbeCache({ submit: cmd });
            }
            return { ok: true, command: cmd };
        }
        catch {
            return { ok: false };
        }
    }
    async _tryHostKeySubmit(ide) {
        if (process.platform !== "linux") {
            return { ok: false };
        }
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const override = cfg.get("submitHostKey", "auto") || "auto";
        const candidates = (0, probe_ladder_1.buildHostKeySubmitCandidates)(ide, override);
        return this.runHostKeyCandidates("SUBMIT_HOST_KEY", candidates);
    }
    async _tryVerifiedHostKeySubmit(ide, verifyText) {
        if (process.platform !== "linux" || !verifyText) {
            return { ok: false };
        }
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const override = cfg.get("submitHostKey", "auto") || "auto";
        const candidates = (0, probe_ladder_1.buildHostKeySubmitCandidates)(ide, override);
        const attempts = [];
        this.traceOperation({
            op: "submit_host_key_verified",
            route: "host-key-candidates",
            ok: true,
            detail: { candidates: candidates.map(([command, args]) => `${command} ${args.join(" ")}`) },
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
            await this.discardCachedSubmitWinner(rendered);
            this.traceOperation({
                op: "submit",
                route: "host-key-verified",
                ok: false,
                command: rendered,
                reason: "input still contains pasted text",
                detail: { observedLength: verify.observedLength },
            });
            await this.focusChatInput();
            await this.runHostKeyCandidates("SUBMIT_DESELECT", [
                ["wtype", ["-k", "End"]],
                ["xdotool", ["key", "End"]],
                ["ydotool", ["key", "End"]],
            ]);
        }
        return {
            ok: false,
            command: `${ide}-host-key-noop`,
            reason: "host-key submit candidates ran but chat input still contains pasted text",
            attempts,
            unverified: true,
        };
    }
    async runHostCommand(command, args, input) {
        if (process.platform !== "linux") {
            return { ok: false, stdout: "" };
        }
        return new Promise((resolve) => {
            const child = (0, child_process_1.spawn)(command, args, { stdio: ["pipe", "pipe", "ignore"] });
            const chunks = [];
            child.stdout.on("data", (chunk) => chunks.push(chunk));
            child.on("error", () => resolve({ ok: false, stdout: "" }));
            child.on("close", (code) => {
                resolve({ ok: code === 0, stdout: Buffer.concat(chunks).toString("utf8") });
            });
            if (input !== undefined) {
                child.stdin.end(input);
            }
            else {
                child.stdin.end();
            }
        });
    }
    async runHostKeyCandidates(label, candidates) {
        const attempts = [];
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
    submitClickPoint() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const x = Math.trunc(cfg.get("submitClickX", 0));
        const y = Math.trunc(cfg.get("submitClickY", 0));
        if (x <= 0 || y <= 0) {
            return null;
        }
        return { x, y };
    }
    async autoSubmitClickPoint() {
        const geometry = await this.runHostCommand("xdotool", [
            "getactivewindow",
            "getwindowgeometry",
            "--shell",
        ]);
        if (!geometry.ok) {
            this.traceOperation({
                op: "submit",
                route: "host-click:auto-point",
                ok: false,
                reason: "xdotool window geometry unavailable",
            });
            return null;
        }
        const parsed = (0, host_click_submit_1.parseXdotoolGeometryShell)(geometry.stdout);
        if (!parsed) {
            this.traceOperation({
                op: "submit",
                route: "host-click:auto-point",
                ok: false,
                reason: "invalid xdotool window geometry",
            });
            return null;
        }
        const point = (0, host_click_submit_1.bottomRightSubmitPoint)(parsed);
        this.traceOperation({
            op: "submit",
            route: "host-click:auto-point",
            ok: true,
            detail: { x: point.x, y: point.y },
        });
        return point;
    }
    isWaylandSession() {
        return ((process.env.XDG_SESSION_TYPE || "").toLowerCase() === "wayland"
            || Boolean(process.env.WAYLAND_DISPLAY));
    }
    async _tryHostClickSubmitYdotool(point, source, details) {
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
    async _tryHostClickSubmitXdotool(point, source, details) {
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
    async _tryHostClickSubmit() {
        if (process.platform !== "linux") {
            this.traceOperation({ op: "submit", route: "host-click", ok: false, reason: "non-linux" });
            return { ok: false };
        }
        const configuredPoint = this.submitClickPoint();
        const point = configuredPoint ?? await this.autoSubmitClickPoint();
        if (!point) {
            debugLog("SUBMIT_CLICK_SKIP", { reason: "missing submitClickX/submitClickY" });
            this.traceOperation({
                op: "submit",
                route: "host-click",
                ok: false,
                reason: "missing submitClickX/submitClickY and auto point unavailable",
            });
            return {
                ok: false,
                reason: "missing submit click coordinates and auto point unavailable",
                attempts: ["submit click skipped: no calibrated or auto bottom-right point"],
            };
        }
        const source = configuredPoint ? "configured" : "auto-bottom-right";
        const details = [];
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
    trustUnverifiedHostSubmit() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        return cfg.get("trustUnverifiedHostSubmit", true);
    }
    async saveHostClipboard() {
        if (this.detectIde() !== "vscodium") {
            return null;
        }
        for (const [cmd, args] of [
            ["wl-paste", ["--no-newline"]],
            ["xclip", ["-selection", "clipboard", "-out"]],
            ["xsel", ["--clipboard", "--output"]],
        ]) {
            const res = await this.runHostCommand(cmd, args);
            if (res.ok) {
                debugLog("HOST_CLIPBOARD_READ", { cmd });
                return res.stdout;
            }
        }
        return null;
    }
    async writeHostClipboard(text) {
        for (const [cmd, args] of [
            ["wl-copy", []],
            ["xclip", ["-selection", "clipboard"]],
            ["xsel", ["--clipboard", "--input"]],
        ]) {
            const res = await this.runHostCommand(cmd, args, text);
            if (res.ok) {
                debugLog("HOST_CLIPBOARD_WRITE", { cmd, length: text.length });
                return cmd;
            }
        }
        return null;
    }
    async restoreHostClipboard(previous) {
        if (previous === null || this.detectIde() !== "vscodium") {
            return;
        }
        await this.writeHostClipboard(previous);
        debugLog("HOST_CLIPBOARD_RESTORE", { length: previous.length });
    }
    async clearChatInput() {
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
    koruStepConfig() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const legacyVerify = cfg.get("verifySubmitOnCursor");
        const verifySubmit = cfg.get("verifySubmit");
        return {
            probeLadder: this.probeLadderEnabled(),
            verifySubmit: typeof verifySubmit === "boolean" ? verifySubmit : (legacyVerify ?? true),
            verifySubmitOnCursor: legacyVerify,
            skipWhenInputBusy: cfg.get("skipWhenInputBusy", true),
        };
    }
    postSubmitVerifyEnabled(verifyText) {
        return (0, step_decisions_1.shouldVerifyPostSubmit)(this.detectIde(), verifyText, this.koruStepConfig());
    }
    async discardCachedSubmitWinner(cmd) {
        if (!this.probeLadderEnabled()) {
            return;
        }
        const current = this.getProbeCache();
        if (current?.submit === cmd) {
            await this.saveProbeCache({ submit: undefined });
        }
    }
    /**
     * Post-submit step: probe chat input and decide accept vs retry next candidate.
     */
    async verifySubmitStep(originalText, requireEmpty = false) {
        await this.sleep(180);
        const probe = await this._probeChatInputContents();
        const result = (0, step_decisions_1.interpretPostSubmitProbe)(probe, originalText, { requireEmpty });
        if (result.action === "retry") {
            debugLog("SUBMIT_VERIFY_FAILED", {
                observedLength: result.observedLength,
                tailMatched: result.tailMatched,
            });
        }
        this.traceOperation({
            op: "submit_verify",
            route: "chat-input-probe",
            ok: result.cleared,
            reason: result.cleared ? undefined : "input still contains pasted text",
            detail: { observedLength: result.observedLength, tailMatched: result.tailMatched },
        });
        // The clipboard probe is unreliable on Cursor's chat webview:
        // ``editor.action.selectAll`` may either no-op (probe → ``null``)
        // or, when the focus chrome falls back to the underlying file
        // ``TextEditor``, copy unrelated editor content. In *either* case
        // the legacy heuristic returns ``cleared=true`` because the tail
        // of our prompt is not present, and we cache the bogus winner.
        //
        // The only ground truth on Cursor is the conversation database
        // (``cursorDiskKV``): a successful submit creates a new
        // ``type = 1`` user bubble containing the prompt tail. Consult it
        // unconditionally for Cursor whenever the probe said the input
        // was cleared.
        if (result.cleared
            && this.detectIde() === "cursor"
            && originalText.trim().length >= 4) {
            const dbResult = await this._verifySubmitViaCursorBubble(originalText);
            if (dbResult !== null) {
                const detail = {
                    observedLength: result.observedLength,
                    tailMatched: result.tailMatched,
                    dbVerified: dbResult.matched,
                    newUserBubbles: dbResult.newUserBubbles,
                    probeWasNull: probe === null,
                };
                this.traceOperation({
                    op: "submit_verify",
                    route: "cursor-bubble-db",
                    ok: dbResult.matched,
                    reason: dbResult.matched
                        ? undefined
                        : "no new user bubble in cursorDiskKV after submit "
                            + "(probe-cleared was a false positive on the webview chat input)",
                    detail,
                });
                return { cleared: dbResult.matched, observedLength: result.observedLength };
            }
        }
        return { cleared: result.cleared, observedLength: result.observedLength };
    }
    /**
     * Cursor-specific post-submit verification using ``cursorDiskKV``.
     *
     * Returns ``null`` when the verification could not run (sqlite missing,
     * database unavailable, no anchor recorded), in which case the caller
     * keeps the previous probe result. Returns ``{ matched: true }`` when a
     * fresh ``type = 1`` bubble containing the tail of our prompt was
     * observed (real submit). Returns ``{ matched: false }`` when the
     * sqlite query worked but no matching user bubble appeared (the
     * submit-command call no-oped on the webview).
     */
    async _verifySubmitViaCursorBubble(originalText) {
        const anchor = this.cursorBubbleAnchorRowid;
        if (anchor === null) {
            debugLog("CURSOR_BUBBLE_VERIFY_NO_ANCHOR");
            return null;
        }
        const adapter = this.cursorBubbleVerifierAdapter ?? new cursor_bubble_adapter_1.CursorBubbleAdapter({ ide: "cursor" });
        this.cursorBubbleVerifierAdapter = adapter;
        if (!adapter.storeAvailable()) {
            debugLog("CURSOR_BUBBLE_VERIFY_DB_UNAVAILABLE");
            return null;
        }
        const tail = originalText.trim().slice(-40);
        // Cursor's bubble writer is debounced; on slower machines the new
        // ``type=1`` row sometimes lands 1.5–2.0 s after ``executeCommand``
        // returns. 1.2 s was too short and produced ``matched=false`` for
        // submits that actually went through.
        const deadline = Date.now() + 2500;
        let attempts = 0;
        let lastRows = 0;
        while (Date.now() <= deadline) {
            attempts += 1;
            let rows;
            try {
                rows = await adapter.fetchLatestUserBubbles(anchor, null);
            }
            catch (err) {
                debugLog("CURSOR_BUBBLE_VERIFY_QUERY_ERROR", { err: String(err) });
                return null;
            }
            lastRows = rows.length;
            for (const row of rows) {
                if (row.type === 1 && typeof row.text === "string" && row.text.includes(tail)) {
                    debugLog("CURSOR_BUBBLE_VERIFY_MATCH", {
                        attempts,
                        rowid: row.cursor,
                        bubbleId: row.bubbleId,
                        textLength: row.text.length,
                    });
                    return { matched: true, newUserBubbles: rows.length };
                }
            }
            await this.sleep(150);
        }
        debugLog("CURSOR_BUBBLE_VERIFY_NO_MATCH", {
            attempts,
            anchor,
            tailLength: tail.length,
            newUserBubbles: lastRows,
        });
        return { matched: false, newUserBubbles: lastRows };
    }
    /**
     * Capture the current ``MAX(rowid)`` from Cursor's ``cursorDiskKV``
     * so the post-submit verifier can tell "new" rows from "stale" ones.
     * Called right before ``submitChat`` for Cursor. No-op on other IDEs.
     */
    async captureCursorBubbleAnchor() {
        if (this.detectIde() !== "cursor") {
            this.cursorBubbleAnchorRowid = null;
            return;
        }
        const adapter = this.cursorBubbleVerifierAdapter ?? new cursor_bubble_adapter_1.CursorBubbleAdapter({ ide: "cursor" });
        this.cursorBubbleVerifierAdapter = adapter;
        if (!adapter.storeAvailable()) {
            this.cursorBubbleAnchorRowid = null;
            debugLog("CURSOR_BUBBLE_ANCHOR_DB_UNAVAILABLE");
            return;
        }
        try {
            this.cursorBubbleAnchorRowid = await adapter.latestBubbleRowid(null);
            debugLog("CURSOR_BUBBLE_ANCHOR_CAPTURED", {
                rowid: this.cursorBubbleAnchorRowid,
            });
        }
        catch (err) {
            this.cursorBubbleAnchorRowid = null;
            debugLog("CURSOR_BUBBLE_ANCHOR_ERROR", { err: String(err) });
        }
    }
    /**
     * Run submit candidate + optional post-submit verify + cache winner.
     * Returns ``null`` when verification failed and the ladder should continue.
     */
    async finalizeSubmitCandidate(cmd, verifyText, verifyEnabled, requireEmptyAfterSubmit = false, extra) {
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
    async _submitChatVSCodium(verifyText, verifyEnabled) {
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const candidates = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildSubmitCommands)("vscodium"), cache?.submit), existing);
        const hostVerifyEnabled = verifyEnabled ||
            (0, step_decisions_1.shouldRequireVerifiedHostSubmit)("vscodium", verifyText, this.koruStepConfig());
        this.traceOperation({
            op: "submit",
            route: "vscodium",
            ok: true,
            detail: {
                verifyEnabled,
                hostVerifyEnabled,
                trustUnverifiedHostSubmit: this.trustUnverifiedHostSubmit(),
                registeredCandidates: candidates,
            },
        });
        const registered = await this._tryRegisteredCommands(candidates, verifyText, hostVerifyEnabled);
        if (registered)
            return registered;
        const hostClick = await this._tryHostClickSubmit();
        if (hostClick.ok && hostClick.command) {
            const accepted = await this.finalizeSubmitCandidate(hostClick.command, verifyText, hostVerifyEnabled, true);
            if (accepted)
                return accepted;
        }
        if (hostVerifyEnabled && verifyText) {
            const hostKey = await this._tryVerifiedHostKeySubmit("vscodium", verifyText);
            if (hostKey.ok && hostKey.command)
                return hostKey;
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
    async _submitChatCursorVSCodeFallback(ide, verifyText, verifyEnabled) {
        const strategy = (0, registry_1.getStrategy)(ide);
        const hostVerifyEnabled = verifyEnabled ||
            (0, step_decisions_1.shouldRequireVerifiedHostSubmit)(ide, verifyText, this.koruStepConfig());
        // Cursor: host-key / host-click submit requires the OS keyboard focus to
        // be on the Cursor window. When `koru auto` runs from a terminal the
        // synthetic keystroke goes to the terminal and the chat never receives
        // it. Registered commands (composer.sendToAgent, workbench.action.chat.*)
        // operate inside VS Code without OS focus, so if they failed there is
        // nothing meaningful to fall back to — return a verified failure with
        // operator guidance instead of pseudo-succeeding via the wrong window.
        if (ide === "cursor") {
            this.traceOperation({
                op: "submit",
                route: "cursor-host-fallback-refused",
                ok: false,
                reason: "registered submit commands exhausted; host-key/host-click "
                    + "would target whatever OS window has keyboard focus (typically "
                    + "the terminal running `koru auto`), not the Cursor chat input",
            });
            return {
                ok: false,
                command: "cursor-submit-unavailable",
                reason: "registered Cursor submit commands no-oped (chat input was "
                    + "likely empty because paste did not land in the chat); host-key "
                    + "fallback refused because Cursor does not have OS keyboard focus",
                unverified: true,
            };
        }
        const hostKey = await this._tryHostKeySubmit(strategy?.preferCtrlSubmit() ? ide : undefined);
        if (hostKey.ok && hostKey.command) {
            const accepted = await this.finalizeSubmitCandidate(hostKey.command, verifyText, hostVerifyEnabled, true, { unverified: hostVerifyEnabled ? false : !this.trustUnverifiedHostSubmit() });
            if (accepted)
                return accepted;
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
    async _tryRegisteredCommands(candidates, verifyText, verifyEnabled) {
        for (const cmd of candidates) {
            if (!(await this.runCommand(cmd))) {
                console.warn(`koru autopilot: submitChat command not available: ${cmd}`);
                continue;
            }
            const accepted = await this.finalizeSubmitCandidate(cmd, verifyText, verifyEnabled);
            if (accepted)
                return accepted;
        }
        return null;
    }
    async _tryTypeSubmitFallbacks(verifyText, verifyEnabled) {
        for (const attempt of [() => this._tryTypeSubmit("\n"), () => this._tryTypeSubmit("\r")]) {
            const result = await attempt();
            if (result.ok && result.command) {
                const accepted = await this.finalizeSubmitCandidate(result.command, verifyText, verifyEnabled);
                if (accepted)
                    return accepted;
            }
        }
        return null;
    }
    async submitChat(verifyText) {
        const ide = this.detectIde();
        const verifyEnabled = this.postSubmitVerifyEnabled(verifyText);
        this.traceOperation({
            op: "submit",
            route: "start",
            ok: true,
            detail: { ide, verifyEnabled, verifyTextLength: verifyText?.length || 0 },
        });
        if (ide === "vscodium") {
            return this._submitChatVSCodium(verifyText, verifyEnabled);
        }
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const candidates = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildSubmitCommands)(ide), cache?.submit), existing);
        debugLog("SUBMIT_CANDIDATES", { ide, candidates, verifyEnabled });
        const registered = await this._tryRegisteredCommands(candidates, verifyText, verifyEnabled);
        if (registered)
            return registered;
        if (ide === "windsurf") {
            // On Windsurf, typing a newline is extremely dangerous because if Cascade is not focused, it toggles/closes the panel!
            return { ok: false };
        }
        if (ide === "cursor" || ide === "vscode") {
            const fallback = await this._submitChatCursorVSCodeFallback(ide, verifyText, verifyEnabled);
            if (fallback)
                return fallback;
        }
        const typeFallback = await this._tryTypeSubmitFallbacks(verifyText, verifyEnabled);
        if (typeFallback)
            return typeFallback;
        return { ok: false };
    }
    async _buildFocusChatContext(primary) {
        const ide = this.detectIde();
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const useProbe = this.probeLadderEnabled();
        let commands = filterUnsafeFocusOpenForIde((0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildFocusOpenCommands)(ide, primary), cache?.focusOpen), existing), ide);
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
    _focusChatAlreadyFocused(context) {
        if (context.useProbe
            && context.ide === "vscode"
            && context.commands.length === 0
            && (0, probe_ladder_1.chatFocusHeuristic)(context.before)) {
            debugLog("FOCUS_OPEN_ALREADY_FOCUSED");
            this.traceOperation({ op: "focus_open", route: "already-focused", ok: true });
            return { ok: true, command: "already-focused" };
        }
        return null;
    }
    async _focusChatWithoutOpenCommands(rejected) {
        const before = this.editorSnapshot();
        const inputOnly = await this.focusChatInput();
        if (!isSpecificChatInputFocusCommand(inputOnly.command)) {
            rejected.push({
                cmd: "(input-only)",
                reason: "no specific chat input focus command succeeded",
            });
            return null;
        }
        // ``composer.focusComposer`` (and friends) can return ``true`` even
        // when the chat panel is *hidden* — Cursor focuses the logical
        // composer state without making it visible. Paste then lands in the
        // invisible composer and the submit pipeline silently no-ops. Guard
        // against this with the editor-snapshot heuristic: if the active
        // text editor is still a file-like editor after the focus command,
        // chat is NOT actually the foreground surface and we must fall
        // through to the open commands instead of returning a false win.
        const after = this.editorSnapshot();
        if (!(0, probe_ladder_1.chatFocusHeuristic)(after)) {
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
    async _tryFocusChatCommand(command, context, rejected) {
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
        const strategy = (0, registry_1.getStrategy)(context.ide);
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
        if (!context.useProbe || (0, probe_ladder_1.verifyFocusAfterOpen)(context.before, after, context.ide)) {
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
    _focusChatFailure(primary, context, rejected) {
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
    async focusChat() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const primary = (cfg.get("chatOpenCommands") || []).filter(Boolean);
        const context = await this._buildFocusChatContext(primary);
        const alreadyFocused = this._focusChatAlreadyFocused(context);
        if (alreadyFocused) {
            return alreadyFocused;
        }
        const rejected = [];
        // Preflight: try focus-only commands BEFORE any open-command in the
        // ladder. On Cursor (and any IDE whose open commands include
        // toggles like ``composer.openAsPane``) running an open command
        // when the chat panel is *already visible* hides it. The plugin
        // then pastes into an invisible/file-editor target and the
        // bubble-DB verifier correctly reports "no new user bubble", but
        // the user sees "schowal panel, wkleil, nie wysłał". When a
        // focus-only command can land focus on a specific chat input,
        // chat is already open and we must not call any toggle commands.
        if (this._shouldPreflightFocusOnly(context)) {
            const inputOnly = await this._focusChatWithoutOpenCommands(rejected);
            if (inputOnly) {
                return inputOnly;
            }
        }
        else if (context.commands.length === 0) {
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
    /**
     * Should we try focus-only commands *before* any open command?
     *
     * Returns ``true`` when the open-command ladder contains at least
     * one toggle (currently: ``composer.openAsPane`` for Cursor).
     * Running a toggle on an already-visible panel hides it, and the
     * subsequent paste+submit pipeline silently no-ops. The preflight
     * short-circuits that by checking whether a focus-only command can
     * land focus on the chat input without touching the panel chrome.
     */
    _shouldPreflightFocusOnly(context) {
        if (context.commands.length === 0) {
            return false;
        }
        return context.commands.some((cmd) => isTogglingFocusOpenCommand(cmd));
    }
    async pasteText(text, replaceCurrentInput = false) {
        const ide = this.detectIde();
        const useProbe = this.probeLadderEnabled();
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const before = this.editorSnapshot();
        this.traceOperation({
            op: "paste",
            route: "start",
            ok: true,
            detail: { ide, replaceCurrentInput, useProbe, textLength: text.length },
        });
        if (replaceCurrentInput) {
            await this.focusChatInput();
            await this.runCommand("editor.action.selectAll");
            await this.sleep(50);
            const clipboard = await this.tryClipboardPaste(text, before, useProbe);
            if (clipboard.handled && clipboard.result.ok) {
                this.traceOperation({ op: "paste", route: "replace:clipboard", ok: true, command: clipboard.result.command });
                return clipboard.result;
            }
            const typed = await this.tryTypePaste(text, before, useProbe);
            if (typed.ok) {
                this.traceOperation({ op: "paste", route: "replace:type", ok: true, command: typed.command });
                return typed;
            }
        }
        if (ide === "vscodium") {
            const hostPaste = await this.tryHostClipboardPaste(text, before, useProbe);
            if (hostPaste.handled) {
                this.traceOperation({
                    op: "paste",
                    route: "vscodium:host-clipboard",
                    ok: hostPaste.result.ok,
                    command: hostPaste.result.command,
                    reason: hostPaste.result.reason,
                    attempts: hostPaste.result.attempts,
                });
                return hostPaste.result;
            }
        }
        const direct = await this.tryDirectPasteCommands(text, ide, existing, cache, before, useProbe);
        if (direct) {
            this.traceOperation({ op: "paste", route: "direct-command", ok: direct.ok, command: direct.command, reason: direct.reason });
            return direct;
        }
        if (ide === "windsurf") {
            // Direct paste must succeed on Windsurf to prevent fallback editor contamination.
            return { ok: false };
        }
        const clipboard = await this.tryClipboardPaste(text, before, useProbe);
        if (clipboard.handled) {
            this.traceOperation({
                op: "paste",
                route: "vscode-clipboard",
                ok: clipboard.result.ok,
                command: clipboard.result.command,
                reason: clipboard.result.reason,
            });
            return clipboard.result;
        }
        const typed = await this.tryTypePaste(text, before, useProbe);
        this.traceOperation({ op: "paste", route: "type", ok: typed.ok, command: typed.command, reason: typed.reason });
        return typed;
    }
    /**
     * Whether ``cmd`` reads the system clipboard rather than its ``text``
     * argument. ``editor.action.clipboardPasteAction`` (and friends) ignore
     * the argument we pass and paste whatever is currently in the OS
     * clipboard — so we MUST seed the clipboard with ``text`` first or the
     * IDE will paste whatever the user had on their clipboard (a copy from
     * earlier, completely unrelated content, etc.).
     */
    static directPasteReadsClipboard(cmd) {
        return (cmd === "editor.action.clipboardPasteAction"
            || cmd === "editor.action.pasteAs"
            || cmd === "execPaste"
            || cmd === "paste");
    }
    async tryDirectPasteCommands(text, ide, existing, cache, before, useProbe) {
        const directCommands = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildPasteDirectCommands)(ide), cache?.paste), existing);
        const previousClip = await this.saveClipboard();
        let clipboardSeeded = false;
        try {
            for (const cmd of directCommands) {
                const readsClipboard = AutopilotBridge.directPasteReadsClipboard(cmd);
                if (readsClipboard) {
                    const seeded = await this.writeClipboardVerified(text);
                    if (!seeded) {
                        debugLog("DIRECT_PASTE_CLIPBOARD_SEED_FAILED", { cmd });
                        this.traceOperation({
                            op: "paste",
                            route: `direct-command:${cmd}`,
                            ok: false,
                            reason: "clipboard seed unverified; refusing to invoke clipboard-reading paste with stale clipboard",
                        });
                        continue;
                    }
                    clipboardSeeded = true;
                }
                try {
                    const result = await Promise.resolve(vscode.commands.executeCommand(cmd, text));
                    if (result === false) {
                        continue;
                    }
                    await this.sleep(this.probePasteDelayMs());
                    const after = this.editorSnapshot();
                    if (useProbe && (0, probe_ladder_1.pasteLandedInEditor)(before, after, text)) {
                        debugLog("PROBE_PASTE_REJECT", { cmd, reason: "landed_in_editor" });
                        continue;
                    }
                    if (useProbe) {
                        await this.saveProbeCache({ paste: cmd });
                    }
                    return { ok: true, command: cmd };
                }
                catch {
                    /* command doesn't exist — try next */
                }
            }
            return undefined;
        }
        finally {
            if (clipboardSeeded) {
                await this.sleep(120);
                await this.restoreClipboard(previousClip);
            }
        }
    }
    async tryHostClipboardPaste(text, before, useProbe) {
        const inputFocused = await this.focusChatInput();
        if (!inputFocused.ok) {
            debugLog("HOST_PASTE_NO_INPUT_FOCUS");
            this.traceOperation({ op: "paste", route: "host-clipboard:focus-input", ok: false, reason: "input focus unavailable" });
        }
        await this.clearChatInput();
        const clip = await this.writeHostClipboard(text);
        if (!clip) {
            debugLog("HOST_PASTE_NO_CLIPBOARD_TOOL");
            this.traceOperation({ op: "paste", route: "host-clipboard:write", ok: false, reason: "no host clipboard tool" });
            return { handled: false, result: { ok: false, reason: "no host clipboard tool" } };
        }
        this.traceOperation({ op: "paste", route: `host-clipboard:${clip}`, ok: true, detail: { textLength: text.length } });
        await this.writeClipboardVerified(text);
        const paste = await this.runHostKeyCandidates("HOST_PASTE_KEY", [
            ["wtype", ["-M", "ctrl", "-k", "v", "-m", "ctrl"]],
            ["xdotool", ["key", "ctrl+v"]],
            ["ydotool", ["key", "ctrl+v"]],
        ]);
        if (!paste.ok) {
            return { handled: true, result: { ...paste, reason: "host clipboard paste key failed" } };
        }
        await this.sleep(Math.max(this.probePasteDelayMs(), 350));
        const after = this.editorSnapshot();
        if (useProbe && (0, probe_ladder_1.pasteLandedInEditor)(before, after, text)) {
            this.traceOperation({ op: "paste", route: "host-clipboard:probe", ok: false, reason: "paste landed in editor" });
            return { handled: true, result: { ok: false, command: paste.command, reason: "paste landed in editor" } };
        }
        if (useProbe) {
            await this.saveProbeCache({ paste: `host-clipboard:${clip}+${paste.command}` });
        }
        return { handled: true, result: { ok: true, command: `host-clipboard:${clip}+${paste.command}` } };
    }
    async tryClipboardPaste(text, before, useProbe) {
        const inputFocused = await this.focusChatInput();
        if (!inputFocused.ok) {
            debugLog("PROBE_PASTE_NO_INPUT_FOCUS");
            if (useProbe && before.hasEditor && before.isFileLike) {
                return { handled: true, result: { ok: false, reason: "chat input focus unavailable; refusing editor clipboard paste fallback" } };
            }
        }
        try {
            await this.clearChatInput();
            const ok = await this.writeClipboardVerified(text);
            if (!ok) {
                debugLog("CLIPBOARD_PASTE_ABORT_UNVERIFIED");
                return {
                    handled: true,
                    result: {
                        ok: false,
                        reason: "clipboard writeText did not propagate (readback mismatch); "
                            + "refusing paste to avoid clobbering chat input with stale clipboard content",
                    },
                };
            }
            await vscode.commands.executeCommand("editor.action.clipboardPasteAction");
            await this.sleep(this.probePasteDelayMs());
            const after = this.editorSnapshot();
            if (useProbe && (0, probe_ladder_1.pasteLandedInEditor)(before, after, text)) {
                return { handled: true, result: { ok: false } };
            }
            if (useProbe) {
                await this.saveProbeCache({ paste: "editor.action.clipboardPasteAction" });
            }
            return { handled: true, result: { ok: true, command: "editor.action.clipboardPasteAction" } };
        }
        catch {
            /* clipboard paste failed — fallback to type */
        }
        return { handled: false, result: { ok: false } };
    }
    async tryTypePaste(text, before, useProbe) {
        const inputFocused = await this.focusChatInput();
        if (!inputFocused.ok && useProbe && before.hasEditor && before.isFileLike) {
            debugLog("TYPE_PASTE_NO_INPUT_FOCUS_REFUSED");
            return { ok: false, reason: "chat input focus unavailable; refusing editor type fallback" };
        }
        try {
            await this.clearChatInput();
            await Promise.resolve(vscode.commands.executeCommand("type", { text }));
            await this.sleep(this.probePasteDelayMs());
            const after = this.editorSnapshot();
            if (useProbe && (0, probe_ladder_1.pasteLandedInEditor)(before, after, text)) {
                return { ok: false };
            }
            if (useProbe) {
                await this.saveProbeCache({ paste: "type" });
            }
            return { ok: true, command: "type" };
        }
        catch {
            return { ok: false };
        }
    }
    async focusChatInput() {
        const ide = this.detectIde();
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const candidates = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildFocusInputCommands)(ide), cache?.focusInput), existing);
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
    detectIde() {
        const app = vscode.env.appName || "";
        return (0, registry_1.detectIdeViaStrategies)(app) ?? "vscode";
    }
    send(env) {
        if (!this.socket)
            return;
        const wire = (0, ack_payload_1.sanitizeOutboundEnvelope)(env);
        const line = JSON.stringify(wire) + "\n";
        debugLog("OUT", env);
        // STARTER-242 telemetry: log oversized envelopes BEFORE they hit the
        // daemon socket. The truncated-NDJSON crash reported on cycle #632
        // (~170 KB ack with no trailing newline reaching the CLI) needs a
        // concrete size budget per envelope type before we cap fields. Treat
        // >32 KB as "investigate" and >128 KB as "almost certainly the cause".
        const bytes = Buffer.byteLength(line, "utf8");
        if (bytes > 32 * 1024) {
            const fieldSizes = {};
            for (const [k, v] of Object.entries(env)) {
                try {
                    fieldSizes[k] = Buffer.byteLength(JSON.stringify(v), "utf8");
                }
                catch {
                    fieldSizes[k] = -1;
                }
            }
            safeLog("OUT_OVERSIZED", {
                type: env.type,
                id: env.id,
                bytes,
                fields: fieldSizes,
            });
        }
        this.socket.write(line);
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
                if (!env || typeof env !== "object" || typeof env.type !== "string") {
                    console.error("koru autopilot: malformed envelope", env);
                    continue;
                }
                void this.dispatch(env).catch((err) => {
                    const message = err instanceof Error ? err.message : String(err);
                    console.error("koru autopilot: dispatch failed", env, err);
                    this.send({ type: "error", id: env.id, ok: false, message });
                });
            }
            catch (err) {
                console.error("koru autopilot: bad envelope", line, err);
            }
        }
    }
    async dispatch(env) {
        if (env.type === "error") {
            const message = typeof env.message === "string" ? env.message : "daemon rejected plugin";
            if (message.includes("plugin version mismatch")) {
                this.reconnectBlockedReason = message;
                this.status.text = "$(warning) koru: reload";
                this.status.tooltip = message;
                await this._handleVersionMismatchRejection(message);
            }
            return;
        }
        const plan = (0, dispatch_plan_1.planDispatch)(env);
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
    /**
     * Daemon rejected this plugin because the installed VSIX version no
     * longer matches the expected version. The classic recovery is for the
     * user to run `Developer: Reload Window`, but Koru's host-side reload
     * automation (`wtype Ctrl+Shift+P`) fails on many Wayland compositors.
     * Since we already have a privileged VS Code extension context, just
     * call `workbench.action.reloadWindow` ourselves — that bypasses every
     * xdotool/wtype quirk because the IDE reloads itself natively.
     *
     * Honours `koruAutopilot.reloadOnVersionMismatch` (default: `true`)
     * and a per-session cooldown so we never loop into a reload storm.
     */
    async _handleVersionMismatchRejection(message) {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const enabled = cfg.get("reloadOnVersionMismatch");
        if (enabled === false) {
            void vscode.window.showWarningMessage(`koru autopilot: ${message}`);
            return;
        }
        const ctx = this.context;
        const lastReloadAt = ctx.globalState.get("koruAutopilot.lastVersionMismatchReloadAt", 0);
        const COOLDOWN_MS = 60_000;
        if (Date.now() - lastReloadAt < COOLDOWN_MS) {
            void vscode.window.showWarningMessage(`koru autopilot: ${message} (reload skipped — already attempted within last 60s; ` +
                "use Developer: Reload Window manually if the mismatch persists)");
            return;
        }
        await ctx.globalState.update("koruAutopilot.lastVersionMismatchReloadAt", Date.now());
        safeLog("PLUGIN_VERSION_MISMATCH_AUTO_RELOAD", { message });
        void vscode.window.showInformationMessage(`koru autopilot: ${message}. Reloading the window to load the new VSIX…`);
        try {
            await vscode.commands.executeCommand("workbench.action.reloadWindow");
        }
        catch (err) {
            const detail = err instanceof Error ? err.message : String(err);
            safeLog("PLUGIN_VERSION_MISMATCH_RELOAD_FAILED", { detail });
            void vscode.window.showWarningMessage(`koru autopilot: automatic reload failed (${detail}). ` +
                "Run `Developer: Reload Window` manually.");
        }
    }
    async saveClipboard() {
        try {
            return await vscode.env.clipboard.readText();
        }
        catch {
            return null;
        }
    }
    async restoreClipboard(previous) {
        if (previous !== null) {
            try {
                await vscode.env.clipboard.writeText(previous);
            }
            catch {
                /* ignore */
            }
        }
    }
    /**
     * Write `text` to the OS clipboard and verify the write took effect.
     *
     * On Linux/Wayland (and some Cursor builds where the chat input is a
     * webview-rooted contenteditable that reads the OS clipboard natively
     * via the browser APIs), `vscode.env.clipboard.writeText` returns
     * before the underlying `wl-copy` / selection-manager pipeline has
     * propagated. If we fire `editor.action.clipboardPasteAction`
     * immediately, the webview can paste the *previous* clipboard content
     * (e.g. the user's last manual copy, freshly restored by the
     * input-busy probe). Read back the clipboard with a short retry loop
     * to guarantee the prompt text is actually visible before paste.
     */
    async writeClipboardVerified(text) {
        const maxTries = 6;
        for (let i = 0; i < maxTries; i++) {
            try {
                await vscode.env.clipboard.writeText(text);
            }
            catch (err) {
                debugLog("CLIPBOARD_WRITE_ERROR", { err: String(err) });
            }
            await this.sleep(i === 0 ? 20 : 40);
            try {
                const observed = await vscode.env.clipboard.readText();
                if (observed === text) {
                    if (i > 0) {
                        debugLog("CLIPBOARD_WRITE_VERIFIED_RETRY", { attempts: i + 1 });
                    }
                    return true;
                }
            }
            catch (err) {
                debugLog("CLIPBOARD_READBACK_ERROR", { err: String(err) });
            }
        }
        debugLog("CLIPBOARD_WRITE_UNVERIFIED", { length: text.length });
        return false;
    }
    /**
     * Best-effort detection: is the chat input already holding un-submitted text?
     *
     * Cursor's chat input is a webview-rooted contenteditable, not a normal
     * TextEditor, so it is invisible to ``vscode.window.activeTextEditor``. We
     * therefore probe via the only thing the editor reliably exposes when chat
     * has focus: select-all + clipboardCopy will copy the chat input's current
     * contents into VS Code's clipboard. We snapshot, sentinel-write, copy,
     * and compare; if the clipboard ends up holding non-trivial text that is
     * NOT our sentinel, we treat the chat input as busy and abort drive.
     *
     * Falls closed on errors (missing commands, clipboard failures): when in
     * doubt, do NOT skip — let the legacy paste path run.
     */
    async decideBusyInput(text) {
        if (!(0, step_decisions_1.shouldVerifyPrePasteBusy)(this.koruStepConfig())) {
            this.traceOperation({ op: "input_busy_probe", route: "disabled", ok: true });
            return { action: "empty", observedLength: 0 };
        }
        const observed = await this._probeChatInputContents();
        const observedLength = observed === null ? -1 : observed.trim().length;
        const action = (0, step_decisions_1.decideBusyInputAction)(observed, text);
        debugLog("CHAT_INPUT_BUSY_PROBE", { busy: action !== "empty", action, length: observedLength });
        this.traceOperation({
            op: "input_busy_probe",
            route: "select-copy",
            ok: action !== "block",
            reason: action === "block" ? "input contains unrelated draft" : undefined,
            detail: { action, observedLength },
        });
        return { action, observedLength };
    }
    /**
     * Sentinel-probe the chat input via select-all + clipboardCopy.
     *
     * Returns the chat input's current text (empty string if cleared by a
     * successful submit), or ``null`` when the probe could not run (clipboard
     * unreadable, sentinel still present meaning select+copy did not pick up
     * any chat content). The sentinel guards against false positives when the
     * select+copy pipeline has no effect — without it an empty clipboard read
     * would look identical to "input is empty".
     */
    async _probeChatInputContents() {
        const sentinel = `__koru_input_probe_${Date.now().toString(36)}__`;
        const previous = await this.saveClipboard();
        try {
            await vscode.env.clipboard.writeText(sentinel);
            await this.runCommand("editor.action.selectAll");
            await this.runCommand("editor.action.clipboardCopyAction");
            await this.sleep(60);
            const observed = await this.saveClipboard();
            if (observed === null || observed === sentinel) {
                this.traceOperation({
                    op: "input_probe",
                    route: "select-copy",
                    ok: false,
                    reason: observed === sentinel ? "sentinel unchanged" : "clipboard unreadable",
                });
                return null;
            }
            this.traceOperation({
                op: "input_probe",
                route: "select-copy",
                ok: true,
                detail: { observedLength: observed.length },
            });
            return observed;
        }
        catch (err) {
            debugLog("CHAT_INPUT_PROBE_ERROR", { err: String(err) });
            return null;
        }
        finally {
            await this.restoreClipboard(previous);
        }
    }
    sendInputBusyAck(env, focus, observedLength) {
        this.send({
            type: "ack",
            id: env.id,
            ok: false,
            delivered: false,
            opened: focus.ok,
            submitted: false,
            probe_ladder: this.probeLadderEnabled(),
            winning_focus_open: focus.command,
            verification: "input_busy",
            operation_trace: this.currentOperationTrace(),
            reason: "chat_input_not_empty",
            observed_length: observedLength,
            message: "chat input already contains un-submitted text — skipping drive to "
                + "avoid clobbering the user's reply or concatenating prompts.",
        });
    }
    async submitExistingChatInput(env, focus, text, submit) {
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
            this.sendSubmitFailureAck(env, focus, { ok: true, command: "existing-input" }, submitResult.command, submitResult);
            return;
        }
        this.sendSuccessAck(env, focus, { ok: true, command: "existing-input" }, submitResult.command);
        this.sendMessageSent(text);
    }
    sendFocusFailureAck(env, focus) {
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
            operation_trace: this.currentOperationTrace(),
            message: "chat input is not focused/open; "
                + `ide=${details.ide || this.detectIde()} app=${details.appName || vscode.env.appName}; `
                + `focus_open_candidates=${candidates || "(none)"}; `
                + "log=/tmp/koru-plugin-debug.log. Open chat input manually, then retry.",
        });
    }
    sendPasteFailureAck(env, focus, pasted) {
        const reason = pasted.reason || "unknown paste failure";
        this.send({
            type: "ack",
            id: env.id,
            ok: false,
            opened: true,
            probe_ladder: this.probeLadderEnabled(),
            winning_focus_open: focus.command,
            attempted_paste: pasted.command,
            paste_failure_reason: reason,
            operation_trace: this.currentOperationTrace(),
            message: `chat opened but paste command failed (${reason})`,
        });
    }
    sendSubmitFailureAck(env, focus, pasted, attemptedSubmit, submitDetails) {
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
            submit_failure_reason: submitDetails?.reason,
            submit_attempts: submitDetails?.attempts,
            verification: "submit_unverified",
            operation_trace: this.currentOperationTrace(),
            message: "chat opened and text injected, but submit could not be verified; "
                + "manual Send may be required. Input was cleared before paste to avoid prompt concatenation.",
        });
    }
    sendSuccessAck(env, focus, pasted, submitCmd) {
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
            operation_trace: this.currentOperationTrace(),
        });
    }
    sendMessageSent(text) {
        console.log("koru autopilot: sending message.sent");
        this.traceOperation({
            op: "message_sent",
            route: "plugin-event",
            ok: true,
            detail: { length: text.length },
        });
        this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
    }
    async injectChat(env) {
        const text = typeof env.text === "string" ? env.text : "";
        const submit = env.submit !== false;
        this.resetOperationTrace();
        this.traceOperation({
            op: "drive",
            route: "plugin",
            ok: true,
            detail: { ide: this.detectIde(), submit, textLength: text.length, id: env.id },
        });
        if (!text) {
            this.traceOperation({ op: "drive", route: "validate", ok: false, reason: "empty text" });
            this.send({ type: "ack", id: env.id, ok: false, message: "empty text", operation_trace: this.currentOperationTrace() });
            return;
        }
        // Snapshot the user's clipboard BEFORE we do anything else so we
        // can always restore it — even if focus/paste/submit throws (R8).
        const previous = await this.saveClipboard();
        const previousHost = await this.saveHostClipboard();
        try {
            await this._performInject(env, text, submit);
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.traceOperation({ op: "drive", route: "exception", ok: false, reason: message });
            this.send({ type: "ack", id: env.id, ok: false, message, operation_trace: this.currentOperationTrace() });
        }
        finally {
            // Restore clipboard regardless of outcome.
            if (this.detectIde() === "vscodium") {
                await this.sleep(400);
            }
            await this.restoreHostClipboard(previousHost);
            await this.restoreClipboard(previous);
        }
    }
    async tryWindsurfSendTextFastPath(env, text, submit) {
        if (this.detectIde() !== "windsurf") {
            return false;
        }
        safeLog("WINDSURF_FASTPATH_START", { submit, textLength: text.length });
        const hasCommand = await this.waitForCommand("windsurf.sendTextToChat", 1200, 150);
        safeLog("WINDSURF_FASTPATH_CHECK_COMMAND", { hasSendCmd: hasCommand });
        if (!hasCommand) {
            safeLog("WINDSURF_FASTPATH_ABORT_MISSING_COMMAND");
            return false;
        }
        let lastError = "";
        for (let attempt = 1; attempt <= 4; attempt += 1) {
            try {
                safeLog("WINDSURF_FASTPATH_EXECUTE_SEND", { attempt, textLength: text.length });
                await Promise.resolve(vscode.commands.executeCommand("windsurf.sendTextToChat", text));
                await this.maybeKeepWindsurfChatPanelVisible("after-sendTextToChat");
                safeLog("WINDSURF_FASTPATH_EXECUTE_SEND_OK", { attempt });
                this.sendSuccessAck(env, { ok: true, command: "none" }, { ok: true, command: "windsurf.sendTextToChat" }, "windsurf.sendTextToChat");
                if (submit) {
                    this.sendMessageSent(text);
                }
                return true;
            }
            catch (err) {
                lastError = String(err);
                safeLog("WINDSURF_FASTPATH_EXECUTE_SEND_ERROR", { attempt, error: lastError });
                if (attempt < 4) {
                    await this.sleep(450);
                }
            }
        }
        console.warn("koru autopilot: windsurf.sendTextToChat fast path failed", lastError);
        return false;
    }
    async maybeKeepWindsurfChatPanelVisible(reason) {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const enabled = cfg.get("windsurfKeepOpenAfterSend", false);
        if (!enabled) {
            safeLog("WINDSURF_KEEP_OPEN_DISABLED", {
                reason,
                detail: "post-send cascade open commands can toggle the Windsurf right chat column closed",
            });
            return;
        }
        await this.ensureWindsurfChatPanelVisible(reason);
    }
    async ensureWindsurfChatPanelVisible(reason) {
        if (this.detectIde() !== "windsurf") {
            return;
        }
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const registered = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.buildFocusOpenCommands)("windsurf", []), existing);
        const preferred = [
            "windsurf.cascadePanel.open",
            "windsurf.action.showCascade",
            "windsurf.action.openChat",
            "windsurf.chat.open",
            "windsurf.cascade.open",
            "windsurf.panel.chat",
        ];
        const commands = (0, probe_ladder_1.mergeUnique)(preferred.filter((cmd) => registered.includes(cmd)), registered.filter((cmd) => !cmd.includes(".focus")));
        safeLog("WINDSURF_KEEP_OPEN_START", { reason, candidates: commands, registered });
        for (let attempt = 1; attempt <= 3; attempt += 1) {
            await this.sleep(attempt === 1 ? 900 : 700);
            for (const cmd of commands) {
                if (cmd.includes("toggle") || cmd === "workbench.view.windsurfAgentSidebarContainer") {
                    safeLog("WINDSURF_KEEP_OPEN_SKIP_TOGGLE", { attempt, cmd });
                    continue;
                }
                if (await this.runCommand(cmd)) {
                    safeLog("WINDSURF_KEEP_OPEN_OK", { attempt, cmd, reason });
                    return;
                }
                safeLog("WINDSURF_KEEP_OPEN_COMMAND_FAILED", { attempt, cmd, reason });
            }
        }
        safeLog("WINDSURF_KEEP_OPEN_ALL_FAILED", { reason, candidatesCount: commands.length });
    }
    async tryAntigravitySendPromptFastPath(env, text, submit) {
        if (this.detectIde() !== "antigravity" || !submit) {
            return false;
        }
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        try {
            if (!(0, antigravity_fastpath_1.canUseAntigravitySendPrompt)(existing)) {
                debugLog("ANTIGRAVITY_FAST_PATH_MISSING", {
                    reason: `${antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND} command is not registered`,
                    openCommand: (0, antigravity_fastpath_1.selectAntigravityOpenCommand)(existing),
                });
                return false;
            }
            await Promise.resolve(vscode.commands.executeCommand(antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND, text));
            this.sendSuccessAck(env, { ok: true, command: "none" }, { ok: true, command: antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND }, antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND);
            this.sendMessageSent(text);
            return true;
        }
        catch (err) {
            console.warn("koru autopilot: antigravity.sendPromptToAgentPanel fast path failed, trying fallback", err);
            return false;
        }
    }
    async submitAfterPaste(env, focus, pasted, submit, pastedText) {
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
        const submitResult = await this.submitChat(pastedText);
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
    async _performInject(env, text, submit) {
        const ide = this.detectIde();
        this.traceOperation({
            op: "drive",
            route: "perform",
            ok: true,
            detail: { ide, submit, textLength: text.length },
        });
        if (await this.tryAntigravitySendPromptFastPath(env, text, submit)) {
            this.traceOperation({ op: "drive", route: "antigravity-fastpath", ok: true });
            return;
        }
        if (await this.tryWindsurfSendTextFastPath(env, text, submit)) {
            this.traceOperation({ op: "drive", route: "windsurf-fastpath", ok: true });
            return;
        }
        if (ide === "windsurf") {
            // On Windsurf, if the fast path failed, we should NOT fall back to the traditional focus and paste path,
            // because traditional paste is disabled on Windsurf to prevent active file editor contamination.
            // Doing so would only cause unsafe toggles and failures.
            this.traceOperation({ op: "paste", route: "windsurf-fastpath-required", ok: false, reason: "fast path failed" });
            this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "fast path failed" });
            return;
        }
        if (ide === "antigravity") {
            // Antigravity exposes a native send command when its agent surface is ready.
            // Avoid generic focus/open fallbacks here: several Antigravity commands behave like panel toggles.
            this.traceOperation({ op: "paste", route: "antigravity-native-required", ok: false, reason: "native send command unavailable" });
            this.sendPasteFailureAck(env, { ok: false }, { ok: false, reason: "native send command unavailable" });
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
        const busyInput = await this.decideBusyInput(text);
        if (busyInput.action === "submit_existing") {
            debugLog("CHAT_INPUT_BUSY_SUBMIT_EXISTING", { length: busyInput.observedLength });
            await this.submitExistingChatInput(env, focus, text, submit);
            return;
        }
        if (busyInput.action === "block") {
            // The chat input already has un-submitted content (the user is typing,
            // or the IDE-side LLM left the user with a prompt and nothing has been
            // sent yet). Pasting our prompt on top would either concatenate with
            // their text (creating a Frankenstein prompt) or overwrite an answer
            // they were preparing. Skip the drive cleanly so the autonomous loop
            // can either back off or retry later — it is the operator's job to
            // resolve the pending input.
            this.sendInputBusyAck(env, focus, busyInput.observedLength);
            return;
        }
        if (busyInput.action === "replace_known_koru_draft") {
            debugLog("CHAT_INPUT_BUSY_REPLACE_KORU_DRAFT", { length: busyInput.observedLength });
        }
        const pasted = await this.pasteText(text, busyInput.action === "replace_known_koru_draft");
        if (!pasted.ok) {
            this.sendPasteFailureAck(env, focus, pasted);
            return;
        }
        const submitCmd = await this.submitAfterPaste(env, focus, pasted, submit, text);
        if (submitCmd === null) {
            return;
        }
        this.sendSuccessAck(env, focus, pasted, submitCmd);
        if (submit) {
            this.sendMessageSent(text);
        }
    }
    async calibrateProbe() {
        const token = `__koru_probe_${Math.random().toString(36).slice(2, 10)}__`;
        const lines = [`IDE: ${this.detectIde()} (${vscode.env.appName})`];
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
    async captureSubmitClickPosition() {
        const res = await this.runHostCommand("xdotool", ["getmouselocation"]);
        const match = res.stdout.match(/\bx:(\d+)\s+y:(\d+)\b/);
        if (!res.ok || !match) {
            void vscode.window.showWarningMessage("koru autopilot: could not capture mouse position with xdotool.");
            debugLog("SUBMIT_CLICK_CAPTURE_FAILED", { ok: res.ok, stdout: res.stdout });
            return;
        }
        const x = Number(match[1]);
        const y = Number(match[2]);
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        await cfg.update("submitClickX", x, vscode.ConfigurationTarget.Global);
        await cfg.update("submitClickY", y, vscode.ConfigurationTarget.Global);
        debugLog("SUBMIT_CLICK_CAPTURED", { x, y });
        void vscode.window.showInformationMessage(`koru submit click captured: ${x}, ${y}`);
    }
    async sendManualChat(text) {
        await this.injectChat({ type: "chat.send", text, submit: true });
    }
}
function siblingIdeForAppName(appName) {
    const lowered = appName.toLowerCase();
    if (lowered.includes("cursor"))
        return "cursor";
    if (lowered.includes("vscodium") || lowered.includes("code - oss") || lowered.includes("code-oss")) {
        return "vscodium";
    }
    if (lowered.includes("windsurf"))
        return "windsurf";
    if (lowered.includes("antigravity"))
        return "antigravity";
    return null;
}
function maybeAutoConnect(bridge) {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (cfg.get("autoConnect", true))
        bridge.connect();
}
function registerBridgeCommands(context, bridge) {
    context.subscriptions.push(vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()), vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
        const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
        if (text)
            await bridge.sendManualChat(text);
    }), vscode.commands.registerCommand("koruAutopilot.calibrateProbe", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrate", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrateCompact", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.captureSubmitClick", () => bridge.captureSubmitClickPosition()), vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("koruAutopilot.socketPath") ||
            event.affectsConfiguration("koruAutopilot.autoConnect")) {
            maybeAutoConnect(bridge);
        }
    }));
}
function activateBridge(context) {
    const bridge = new AutopilotBridge(context);
    activeBridge = bridge;
    registerBridgeCommands(context, bridge);
    maybeAutoConnect(bridge);
}
function activate(context) {
    const appName = vscode.env.appName || "";
    debugLog("ACTIVATE", {
        appName,
        extensionMode: context.extensionMode,
        extensionPath: context.extensionPath,
    });
    // Each sibling IDE has its own dedicated VSIX. This umbrella plugin
    // serves Microsoft VS Code only — silently no-op on other hosts so we
    // never race the per-IDE plugin for the same Unix socket.
    const siblingIde = siblingIdeForAppName(appName);
    if (siblingIde) {
        console.warn(`koru-autopilot-vscode: not activating on ${siblingIde} (appName="${appName}"); ` +
            `install koru-autopilot-${siblingIde} instead.`);
        return;
    }
    activateBridge(context);
}
function deactivate() {
    if (activeBridge) {
        activeBridge.disconnect();
        activeBridge = null;
    }
}
//# sourceMappingURL=extension.js.map