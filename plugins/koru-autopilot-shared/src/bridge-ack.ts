import * as vscode from "vscode";
import { SharedAutopilotBridgePaste } from "./bridge-paste";
import { debugLog } from "./bridge-config";
import {
  chatFocusOperatorHint,
  manualSendOperatorHint,
  pasteProbeOperatorHint,
} from "./operator-hints";
import {
  Envelope,
  FocusOutcome,
  SubmitOutcome,
} from "./types";

export abstract class SharedAutopilotBridgeAck extends SharedAutopilotBridgePaste {
  protected sendInputBusyAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    observedLength?: number
  ): void {
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
      message:
        "chat input already contains un-submitted text — skipping drive to "
        + "avoid clobbering the user's reply or concatenating prompts.",
    });
  }

  protected sendFocusFailureAck(env: Envelope, focus: FocusOutcome): void {
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
      message:
        "chat input is not focused/open; "
        + `ide=${details.ide || this.detectIde()} app=${details.appName || vscode.env.appName}; `
        + `focus_open_candidates=${candidates || "(none)"}; `
        + `${chatFocusOperatorHint(String(details.ide || this.detectIde()))}; `
        + "log=/tmp/koru-plugin-debug.log",
    });
  }

  protected sendPasteFailureAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string; reason?: string }
  ): void {
    const reason = pasted.reason || "unknown paste failure";
    const ide = this.detectIde();
    const operatorHint =
      reason.includes("probe inconclusive") || reason.includes("sentinel")
        ? pasteProbeOperatorHint(ide)
        : chatFocusOperatorHint(ide);
    this.send({
      type: "ack",
      id: env.id,
      ok: false,
      opened: true,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      attempted_paste: pasted.command,
      paste_failure_reason: reason,
      operator_hint: operatorHint,
      operation_trace: this.currentOperationTrace(),
      message: `chat opened but paste command failed (${reason}). ${operatorHint}`,
    });
  }

  protected sendSubmitFailureAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string },
    attemptedSubmit?: string,
    submitDetails?: SubmitOutcome
  ): void {
    if (this.options.enableDiscardToxicFocusOpenCache) {
      this.discardToxicFocusOpenCache(focus.command).catch((err) => {
        debugLog("FOCUS_OPEN_CACHE_DISCARD_FAILED", { err: String(err) });
      });
    }
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
      operator_hint: manualSendOperatorHint(this.detectIde()),
      operation_trace: this.currentOperationTrace(),
      message:
        "chat opened and text injected, but submit could not be verified; "
        + `${manualSendOperatorHint(this.detectIde())} `
        + "Input was cleared before paste to avoid prompt concatenation.",
    });
  }

  private _isInputOnlyFocusToken(focusToken: string): boolean {
    return (
      focusToken.includes("focuscomposer") ||
      focusToken.includes("focuscascade") ||
      (this.detectIde() === "cursor" &&
        (focusToken.includes("panel.chat.view") || focusToken.includes("panel.aichat.view"))) ||
      (this.detectIde() === "vscodium" && focusToken.includes("openquickchat")) ||
      (this.detectIde() === "vscodium" && focusToken.includes("quickchat.openinchatview")) ||
      focusToken.startsWith("input-only")
    );
  }

  private async discardToxicFocusOpenCache(focusCommand: string | undefined): Promise<void> {
    if (!this.probeLadderEnabled()) return;
    const cache = this.getProbeCache();
    const cached = cache?.focusOpen;
    if (!cached) return;
    const focusToken = (focusCommand || "").toLowerCase();
    if (!this._isInputOnlyFocusToken(focusToken)) return;
    const cleared: any = { ...cache, focusOpen: undefined };
    await this.context.globalState.update("probeCache.v3", cleared);
    debugLog("PROBE_CACHE_FOCUS_OPEN_DISCARDED", { previous: cached });
    this.traceOperation({
      op: "focus_open",
      route: "cache-discard",
      ok: false,
      command: cached,
      reason:
        "cached focus_open winner was an input-only/focus-only command "
        + "but submit could not be verified — discarding so the next "
        + "drive re-probes via the non-toggling open command",
    });
  }

  protected sendSuccessAck(
    env: Envelope,
    focus: { ok: boolean; command?: string },
    pasted: { ok: boolean; command?: string },
    submitCmd: string | undefined
  ): void {
    const submitted = Boolean(submitCmd);
    this.send({
      type: "ack",
      id: env.id,
      ok: true,
      delivered: true,
      opened: true,
      submitted,
      probe_ladder: this.probeLadderEnabled(),
      winning_focus_open: focus.command,
      winning_paste: pasted.command,
      winning_submit: submitCmd,
      operation_trace: this.currentOperationTrace(),
    });
  }

  protected sendMessageSent(text: string): void {
    console.log("koru autopilot: sending message.sent");
    this.traceOperation({
      op: "message_sent",
      route: "plugin-event",
      ok: true,
      detail: { length: text.length },
    });
    this.send({ type: "message.sent", chat: "default", text: text.substring(0, 200), length: text.length });
  }
}
