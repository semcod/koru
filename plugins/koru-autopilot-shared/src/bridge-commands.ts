import * as vscode from "vscode";
import { SharedAutopilotBridgeFastPath } from "./bridge-fastpath";
import { debugLog } from "./bridge-config";
import { Envelope } from "./types";

export abstract class SharedAutopilotBridgeCommands extends SharedAutopilotBridgeFastPath {
  protected abstract injectChat(env: Envelope): Promise<void>;

  async calibrateProbe(): Promise<void> {
    const token = `__koru_probe_${Math.random().toString(36).slice(2, 10)}__`;
    const lines: string[] = [`IDE: ${this.detectIde()} (${vscode.env.appName})`];
    const focus = await this.openChatPanel("probe");
    lines.push(focus.ok ? `focus open: ${focus.command}` : "focus open: FAILED");
    if (!focus.ok) {
      void vscode.window.showWarningMessage(`koru autopilot: could not open chat.\n${lines.join("\n")}`);
      return;
    }
    await this.sleep(this.probeFocusDelayMs());
    const pasted = await this.pasteText(token);
    lines.push(pasted.ok ? `paste: ${pasted.command}` : "paste: FAILED");
    if (!pasted.ok) {
      void vscode.window.showWarningMessage(`koru autopilot: paste failed.\n${lines.join("\n")}`);
      return;
    }
    const cache = this.getProbeCache();
    if (cache) {
      lines.push(`cache: ${JSON.stringify(cache)}`);
    }
    void vscode.window.showInformationMessage(`koru autopilot: probe OK\n${lines.join("\n")}`);
  }

  async captureSubmitClickPosition(): Promise<void> {
    const res = await this.runHostCommand("xdotool", ["getmouselocation"]);
    const match = res.stdout.match(/\bx:(\d+)\s+y:(\d+)\b/);
    if (!res.ok || !match) {
      void vscode.window.showWarningMessage(
        "koru autopilot: could not capture mouse position with xdotool.",
      );
      debugLog("SUBMIT_CLICK_CAPTURE_FAILED", { ok: res.ok, stdout: res.stdout });
      return;
    }
    const x = Number(match[1]);
    const y = Number(match[2]);
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    await cfg.update("submitClickX", x, vscode.ConfigurationTarget.Global);
    await cfg.update("submitClickY", y, vscode.ConfigurationTarget.Global);
    debugLog("SUBMIT_CLICK_CAPTURED", { x, y });
    void vscode.window.showInformationMessage(`koru autopilot: submit click captured: ${x}, ${y}`);
  }

  async sendManualChat(text: string): Promise<void> {
    await this.injectChat({ type: "chat.send", text, submit: true });
  }

  async openChatFromCommand(): Promise<void> {
    await this.openChatPanel("command");
  }
}
