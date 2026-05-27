import { SharedAutopilotBridgeFocusStrategy } from "./bridge-focus-strategy";
import {
  FocusOutcome,
} from "./types";

export abstract class SharedAutopilotBridgeFocus extends SharedAutopilotBridgeFocusStrategy {
  protected openChatPanelInFlight: Promise<FocusOutcome> | null = null;
  protected lastOpenChatPanelAt = 0;
  protected lastOpenChatPanelOutcome: FocusOutcome | null = null;

  async openChatFromCommand(): Promise<void> {
    await this.openChatPanel("command");
  }

  protected async openChatPanel(reason: string): Promise<FocusOutcome> {
    if (this.openChatPanelInFlight) {
      return this.openChatPanelInFlight;
    }
    const cached = this._cachedOpenChatPanelOutcome();
    if (cached) {
      return cached;
    }

    this.openChatPanelInFlight = this.performOpenChatPanel(reason);
    try {
      return await this._recordOpenChatPanelOutcome(this.openChatPanelInFlight);
    } finally {
      this.openChatPanelInFlight = null;
    }
  }

  private _cachedOpenChatPanelOutcome(): FocusOutcome | null {
    if (this.lastOpenChatPanelOutcome && this._lastOpenChatPanelOutcomeIsFresh()) {
      return this.lastOpenChatPanelOutcome;
    }
    return null;
  }

  private _lastOpenChatPanelOutcomeIsFresh(): boolean {
    return Date.now() - this.lastOpenChatPanelAt < 2000;
  }

  private async _recordOpenChatPanelOutcome(inFlight: Promise<FocusOutcome>): Promise<FocusOutcome> {
    const outcome = await inFlight;
    this.lastOpenChatPanelAt = Date.now();
    this.lastOpenChatPanelOutcome = outcome;
    return outcome;
  }

  private async performOpenChatPanel(reason: string): Promise<FocusOutcome> {
    this.resetOperationTrace();
    this.traceOperation({
      op: "focus_open",
      route: "plugin",
      ok: true,
      detail: { ide: this.detectIde(), reason },
    });
    const focus = await this.focusChat();
    this.traceOperation({
      op: focus.command ? `command:${focus.command}` : "command",
      route: focus.command ? `command:${focus.command}` : "command",
      ok: focus.ok,
      reason: focus.reason,
      attempts: focus.attempts,
      detail: focus.diagnostics,
    });
    this.send({
      type: "chat.opened",
      chat: "default",
      ok: focus.ok,
      reason,
      command: focus.command,
      message: focus.reason,
      operation_trace: this.currentOperationTrace(),
    });
    return focus;
  }

}
