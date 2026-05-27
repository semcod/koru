import * as vscode from "vscode";
import { spawn } from "child_process";
import { SharedAutopilotBridgeWatcher } from "./bridge-watcher";
import { debugLog } from "./bridge-config";
import {
  captureEditorSnapshot,
  loadProbeCache,
  mergeProbeCache,
  orderWithCache,
  sanitizeProbeCacheForIde,
  type ProbeCacheEntry,
} from "../probe-ladder";
import {
  CommandCapability,
  CommandOutcome,
  HostCommandResult,
} from "./types";

export abstract class SharedAutopilotBridgeFocusCore extends SharedAutopilotBridgeWatcher {
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
