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
const dispatch_plan_1 = require("./dispatch-plan");
const antigravity_fastpath_1 = require("./antigravity-fastpath");
const probe_ladder_1 = require("./probe-ladder");
const socketPath_1 = require("./socketPath");
const DISALLOWED_FOCUS_OPEN_COMMANDS = new Set([
    "workbench.action.chat.open",
    "workbench.action.chat.openagent",
    "workbench.action.chat.openask",
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
let activeBridge = null;
function debugLog(message, data) {
    try {
        const suffix = data === undefined ? "" : " " + JSON.stringify(data);
        fs.appendFileSync("/tmp/koru-plugin-debug.log", `${new Date().toISOString()} ${message}${suffix}\n`);
    }
    catch {
        /* ignore */
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
                        "probe.ladder",
                    ],
                    pid: process.pid,
                    matchingCommands: matching,
                });
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
        const raw = this.context.globalState.get("probeCache.v3");
        const cache = (0, probe_ladder_1.loadProbeCache)(raw, this.detectIde(), vscode.env.appName || "");
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
    async _tryHostKeySubmit() {
        if (process.platform !== "linux") {
            return { ok: false };
        }
        return this.runHostKeyCandidates("SUBMIT_HOST_KEY", [
            ["wtype", ["-k", "Return"]],
            ["xdotool", ["key", "Return"]],
            ["ydotool", ["key", "Return"]],
            ["wtype", ["-M", "ctrl", "-k", "Return", "-m", "ctrl"]],
            ["xdotool", ["key", "ctrl+Return"]],
            ["ydotool", ["key", "ctrl+Return"]],
        ]);
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
        for (const [command, args] of candidates) {
            const res = await this.runHostCommand(command, args);
            const rendered = `${command} ${args.join(" ")}`;
            attempts.push(`${rendered} => ${res.ok ? "ok" : "failed"}`);
            debugLog(label, { command: rendered, ok: res.ok });
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
    async _tryHostClickSubmit() {
        if (process.platform !== "linux") {
            return { ok: false };
        }
        const point = this.submitClickPoint();
        if (!point) {
            debugLog("SUBMIT_CLICK_SKIP", { reason: "missing submitClickX/submitClickY" });
            return {
                ok: false,
                reason: "missing submit click coordinates",
                attempts: ["submit click skipped: missing submitClickX/submitClickY"],
            };
        }
        const x = String(point.x);
        const y = String(point.y);
        const attempts = [
            ["xdotool", ["mousemove", "--sync", x, y, "click", "1"]],
            ["ydotool", ["mousemove", x, y]],
            ["ydotool", ["click", "1"]],
        ];
        const xdotoolResult = await this.runHostCommand(attempts[0][0], attempts[0][1]);
        const details = [];
        details.push(`${attempts[0][0]} ${attempts[0][1].join(" ")} => ${xdotoolResult.ok ? "ok" : "failed"}`);
        debugLog("SUBMIT_CLICK", { command: `${attempts[0][0]} ${attempts[0][1].join(" ")}`, ok: xdotoolResult.ok, x: point.x, y: point.y });
        if (xdotoolResult.ok) {
            return { ok: true, command: `xdotool click@${point.x},${point.y}`, attempts: details };
        }
        const move = await this.runHostCommand(attempts[1][0], attempts[1][1]);
        details.push(`${attempts[1][0]} ${attempts[1][1].join(" ")} => ${move.ok ? "ok" : "failed"}`);
        debugLog("SUBMIT_CLICK", { command: `${attempts[1][0]} ${attempts[1][1].join(" ")}`, ok: move.ok, x: point.x, y: point.y });
        if (move.ok) {
            const click = await this.runHostCommand(attempts[2][0], attempts[2][1]);
            details.push(`${attempts[2][0]} ${attempts[2][1].join(" ")} => ${click.ok ? "ok" : "failed"}`);
            debugLog("SUBMIT_CLICK", { command: `${attempts[2][0]} ${attempts[2][1].join(" ")}`, ok: click.ok, x: point.x, y: point.y });
            if (click.ok) {
                return { ok: true, command: `ydotool click@${point.x},${point.y}`, attempts: details };
            }
        }
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
    async submitChat() {
        const ide = this.detectIde();
        if (ide === "vscodium") {
            const hostClick = await this._tryHostClickSubmit();
            if (hostClick.ok) {
                return hostClick;
            }
            const hostKey = await this._tryHostKeySubmit();
            if (hostKey.ok) {
                return { ...hostKey, unverified: !this.trustUnverifiedHostSubmit() };
            }
            return {
                ok: false,
                command: "vscodium-submit-unavailable",
                reason: hostClick.reason || hostKey.reason,
                attempts: [...(hostClick.attempts || []), ...(hostKey.attempts || [])],
                unverified: true,
            };
        }
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const candidates = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildSubmitCommands)(ide), cache?.submit), existing);
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
        if (ide === "windsurf") {
            // On Windsurf, typing a newline is extremely dangerous because if Cascade is not focused, it toggles/closes the panel!
            return { ok: false };
        }
        const fallbacks = [
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
    async focusChat() {
        const cfg = vscode.workspace.getConfiguration("koruAutopilot");
        const primary = (cfg.get("chatOpenCommands") || []).filter(Boolean);
        const ide = this.detectIde();
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        const cache = this.getProbeCache();
        const useProbe = this.probeLadderEnabled();
        const commands = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildFocusOpenCommands)(ide, primary), cache?.focusOpen), existing);
        debugLog("FOCUS_OPEN_CANDIDATES", { ide, commands });
        const before = this.editorSnapshot();
        if (useProbe && ide === "vscode" && commands.length === 0 && (0, probe_ladder_1.chatFocusHeuristic)(before)) {
            return { ok: true, command: "already-focused" };
        }
        const rejected = [];
        for (const cmd of commands) {
            if (!(await this.runCommand(cmd))) {
                console.warn(`koru autopilot: focusChat command not available: ${cmd}`);
                rejected.push({ cmd, reason: "executeCommand returned false" });
                continue;
            }
            await this.sleep(this.probeFocusDelayMs());
            const after = this.editorSnapshot();
            if (!useProbe || (0, probe_ladder_1.verifyFocusAfterOpen)(before, after, ide)) {
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
                focusOpenCandidates: sanitizeFocusOpenCandidates(commands),
                cacheFocusOpen: sanitizeFocusOpenCommand(cache?.focusOpen),
                before,
                rejected,
            },
        };
    }
    async pasteText(text) {
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
    async tryDirectPasteCommands(text, ide, existing, cache, before, useProbe) {
        const directCommands = (0, probe_ladder_1.filterRegistered)((0, probe_ladder_1.orderWithCache)((0, probe_ladder_1.buildPasteDirectCommands)(ide), cache?.paste), existing);
        for (const cmd of directCommands) {
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
    async tryHostClipboardPaste(text, before, useProbe) {
        const inputFocused = await this.focusChatInput();
        if (!inputFocused.ok) {
            debugLog("HOST_PASTE_NO_INPUT_FOCUS");
        }
        await this.clearChatInput();
        const clip = await this.writeHostClipboard(text);
        if (!clip) {
            debugLog("HOST_PASTE_NO_CLIPBOARD_TOOL");
            return { handled: false, result: { ok: false, reason: "no host clipboard tool" } };
        }
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
            await vscode.env.clipboard.writeText(text);
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
    detectIde() {
        const app = (vscode.env.appName || "").toLowerCase();
        if (app.includes("antigravity"))
            return "antigravity";
        if (app.includes("windsurf"))
            return "windsurf";
        if (app.includes("cursor"))
            return "cursor";
        if (app.includes("codium") || app.includes("code - oss") || app.includes("code-oss"))
            return "vscodium";
        return "vscode";
    }
    send(env) {
        if (!this.socket)
            return;
        const line = JSON.stringify(env) + "\n";
        debugLog("OUT", env);
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
                void vscode.window.showWarningMessage(`koru autopilot: ${message}`);
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
        });
    }
    sendMessageSent(text) {
        console.log("koru autopilot: sending message.sent");
        this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
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
        const previous = await this.saveClipboard();
        const previousHost = await this.saveHostClipboard();
        try {
            await this._performInject(env, text, submit);
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            this.send({ type: "ack", id: env.id, ok: false, message });
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
        const existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        if (!existing.has("windsurf.sendTextToChat")) {
            // Do not execute Windsurf open/sidebar commands here. In current
            // Windsurf builds, workbench.view.windsurfAgentSidebarContainer is a
            // toggle and closes Cascade when it is already visible.
            return false;
        }
        try {
            await Promise.resolve(vscode.commands.executeCommand("windsurf.sendTextToChat", text));
            let submitCmd = "windsurf.sendTextToChat";
            if (submit) {
                await this.sleep(150);
                await this.focusChatInput();
                const submitResult = await this.submitChat();
                if (submitResult.ok) {
                    submitCmd = submitResult.command;
                }
                else {
                    // On Windsurf, typing a newline fallback when input is not focused is unsafe and closes the panel.
                    // Since windsurf.sendTextToChat might already send the text, we should not do any type:\n fallback!
                    submitCmd = "windsurf.sendTextToChat";
                }
            }
            this.sendSuccessAck(env, { ok: true, command: "none" }, { ok: true, command: "windsurf.sendTextToChat" }, submitCmd);
            if (submit) {
                this.sendMessageSent(text);
            }
            return true;
        }
        catch (err) {
            console.warn("koru autopilot: windsurf.sendTextToChat fast path failed, trying fallback", err);
            return false;
        }
    }
    async tryAntigravitySendPromptFastPath(env, text, submit) {
        if (this.detectIde() !== "antigravity" || !submit) {
            return false;
        }
        let existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
        let openCommand = (0, antigravity_fastpath_1.selectAntigravityOpenCommand)(existing);
        try {
            if (openCommand !== "none") {
                await Promise.resolve(vscode.commands.executeCommand(openCommand));
                await this.sleep(200);
                existing = new Set(await Promise.resolve(vscode.commands.getCommands(false)));
            }
            if (!(0, antigravity_fastpath_1.canUseAntigravitySendPrompt)(existing)) {
                return false;
            }
            await Promise.resolve(vscode.commands.executeCommand(antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND, text));
            this.sendSuccessAck(env, { ok: true, command: openCommand }, { ok: true, command: antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND }, antigravity_fastpath_1.ANTIGRAVITY_SEND_PROMPT_COMMAND);
            this.sendMessageSent(text);
            return true;
        }
        catch (err) {
            console.warn("koru autopilot: antigravity.sendPromptToAgentPanel fast path failed, trying fallback", err);
            return false;
        }
    }
    async submitAfterPaste(env, focus, pasted, submit) {
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
            this.sendSubmitFailureAck(env, focus, pasted, submitResult.command, submitResult);
            return null;
        }
        if (submitResult.ok) {
            return submitResult.command;
        }
        this.sendSubmitFailureAck(env, focus, pasted, submitResult.command, submitResult);
        return null;
    }
    async _performInject(env, text, submit) {
        if (await this.tryAntigravitySendPromptFastPath(env, text, submit)) {
            return;
        }
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
            this.sendPasteFailureAck(env, focus, pasted);
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
function activate(context) {
    debugLog("ACTIVATE", {
        appName: vscode.env.appName,
        extensionMode: context.extensionMode,
        extensionPath: context.extensionPath,
    });
    const bridge = new AutopilotBridge(context);
    activeBridge = bridge;
    context.subscriptions.push(vscode.commands.registerCommand("koruAutopilot.connect", () => bridge.connect()), vscode.commands.registerCommand("koruAutopilot.sendChat", async () => {
        const text = await vscode.window.showInputBox({ prompt: "Send to chat:" });
        if (text)
            await bridge.sendManualChat(text);
    }), vscode.commands.registerCommand("koruAutopilot.calibrateProbe", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrate", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.calibrateCompact", () => bridge.calibrateProbe()), vscode.commands.registerCommand("koruAutopilot.captureSubmitClick", () => bridge.captureSubmitClickPosition()), vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("koruAutopilot.socketPath") ||
            event.affectsConfiguration("koruAutopilot.autoConnect")) {
            const cfg = vscode.workspace.getConfiguration("koruAutopilot");
            if (cfg.get("autoConnect", true))
                bridge.connect();
        }
    }));
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    if (cfg.get("autoConnect", true))
        bridge.connect();
}
function deactivate() {
    if (activeBridge) {
        activeBridge.disconnect();
        activeBridge = null;
    }
}
//# sourceMappingURL=extension.js.map