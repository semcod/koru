import * as vscode from "vscode";
import { SharedAutopilotBridgeFocus } from "./bridge-focus";
import { debugLog } from "./bridge-config";
import {
  buildPasteDirectCommands,
  captureEditorSnapshot,
  decideSubmitCleared,
  filterRegistered,
  pasteLandedInEditor,
  type ProbeCacheEntry,
} from "../probe-ladder";
import {
  CommandOutcome,
  PasteAttempt,
} from "./types";
import { resolveCursorComposerPasteCandidates } from "./cursor-composer-paste";

export abstract class SharedAutopilotBridgePaste extends SharedAutopilotBridgeFocus {
  private isSubmitRequestedForCurrentDrive(): boolean {
    const trace = this.currentOperationTrace();
    for (let idx = trace.length - 1; idx >= 0; idx -= 1) {
      const step = trace[idx];
      if (step.op !== "drive") {
        continue;
      }
      const submit = step.detail?.submit;
      if (typeof submit === "boolean") {
        return submit;
      }
    }
    return true;
  }

  private directPasteMayImplicitlySubmit(ide: string, command: string): boolean {
    if (ide !== "cursor") {
      return false;
    }
    const lower = command.toLowerCase();
    return lower.includes("startcomposerprompt");
  }

  protected cursorComposerPromptPasteCommand(pasteCommand: string | undefined): boolean {
    return Boolean(pasteCommand && /startcomposerprompt/i.test(pasteCommand));
  }

  protected cursorPreSubmitProbeEmptyBlocksSubmit(
    observed: string,
    pastedText: string,
    refocusOk: boolean
  ): boolean {
    if (!refocusOk || !pastedText) {
      return false;
    }
    const trimmedObs = observed.trim();
    const trimmedPast = pastedText.trim();
    return trimmedPast.length >= 4 && trimmedObs.length === 0;
  }

  protected cursorPreSubmitProbeMismatchBlocksSubmit(
    observed: string,
    pastedText: string,
    refocusOk: boolean
  ): boolean {
    if (!refocusOk || !pastedText) {
      return false;
    }
    const trimmedObs = observed.trim();
    const trimmedPast = pastedText.trim();
    if (this.cursorPreSubmitProbeEmptyBlocksSubmit(observed, pastedText, refocusOk)) {
      return true;
    }
    if (trimmedPast.length < 32) {
      return false;
    }
    const decision = decideSubmitCleared(observed, pastedText);
    if (decision.tailMatched) {
      return false;
    }
    const threshold = Math.min(64, Math.floor(trimmedPast.length * 0.2));
    return trimmedObs.length < threshold;
  }

  protected cursorTypedPasteCommand(pasteCommand: string | undefined): boolean {
    const cmd = (pasteCommand || "").toLowerCase();
    return (
      cmd === "type" ||
      cmd.includes("typetext") ||
      cmd.includes("inserttext")
    );
  }

  protected async confirmCursorChatInputBeforeSubmit(
    pastedText: string | undefined,
    route: string,
    pasteCommand?: string
  ): Promise<CommandOutcome> {
    if (pastedText && this.cursorComposerPromptPasteCommand(pasteCommand)) {
      this.traceOperation({
        op: "submit",
        route: `${route}:composer-prompt-bubble-verify`,
        ok: true,
        command: pasteCommand,
        reason:
          "startComposerPrompt paste targets Glass composer; proceeding with bubble-db submit verification",
        detail: { pasteCommand },
      });
      return {
        ok: true,
        command: pasteCommand || "cursor-composer-prompt-paste",
        reason: "composer prompt paste; bubble-db will verify submit",
      };
    }
    let refocus = await this.focusChatInput();
    if (!refocus.ok) {
      refocus = await this.cursorRecoverGlassChatFocus(route);
    }
    this.traceOperation({
      op: "submit",
      route,
      ok: refocus.ok,
      command: refocus.command,
      reason: refocus.ok
        ? undefined
        : "Cursor submit commands no-op unless the chat textarea is focused",
    });
    await this.sleep(this.probeFocusDelayMs());
    const shouldProbeInput = Boolean(pastedText) && (this.probeLadderEnabled() || !refocus.ok);
    if (pastedText && shouldProbeInput) {
      let observed = await this.probeChatInputContents();
      if (
        observed !== null &&
        this.cursorPreSubmitProbeEmptyBlocksSubmit(observed, pastedText, refocus.ok)
      ) {
        await this.sleep(Math.max(this.probeFocusDelayMs(), 120));
        const retry = await this.probeChatInputContents();
        if (retry !== null) {
          observed = retry;
        }
      }
      const decision = observed === null ? null : decideSubmitCleared(observed, pastedText);
      if (observed !== null && decision?.tailMatched) {
        this.traceOperation({
          op: "submit",
          route: `${route}:input-probe`,
          ok: true,
          reason: refocus.ok
            ? "chat input contains the pasted prompt; proceeding to submit"
            : "chat input still contains the pasted prompt; proceeding despite failed focus command",
          detail: {
            focusCommandOk: refocus.ok,
            observedLength: observed.trim().length,
            probeRequired: this.probeLadderEnabled(),
          },
        });
        return {
          ok: true,
          command: refocus.command || "cursor-input-probe",
          reason: "input probe matched pasted prompt",
        };
      }
      if (observed === null || observed.trim().length === 0) {
        if (pastedText && this.cursorTypedPasteCommand(pasteCommand)) {
          let focusForSubmit = refocus;
          if (!focusForSubmit.ok) {
            focusForSubmit = await this.cursorRecoverGlassChatFocus(route);
          }
          if (focusForSubmit.ok) {
            this.traceOperation({
              op: "submit",
              route: `${route}:typed-paste-bubble-verify`,
              ok: true,
              reason:
                "typed paste into chat; Glass focus recovered — proceeding with bubble-db submit verification",
              detail: { focusCommand: focusForSubmit.command, pasteCommand },
            });
            return {
              ok: true,
              command: focusForSubmit.command || "cursor-typed-paste-bubble-verify",
              reason: "typed paste with Glass focus; bubble-db will verify submit",
            };
          }
          this.traceOperation({
            op: "submit",
            route: `${route}:typed-paste-no-glass-focus`,
            ok: false,
            reason:
              "typed paste succeeded but Glass/chat input focus could not be recovered before submit",
            detail: { pasteCommand },
          });
        }
        if (refocus.ok) {
          this.traceOperation({
            op: "submit",
            route: `${route}:input-probe-unreadable`,
            ok: true,
            reason: "chat input probe unreadable; trusting focus command before submit",
            detail: { focusCommandOk: refocus.ok },
          });
          return {
            ok: true,
            command: refocus.command || "cursor-input-probe-unreadable",
            reason: "input probe unreadable; trusting focus command",
          };
        }
        this.traceOperation({
          op: "submit",
          route: `${route}:input-probe-unreadable`,
          ok: false,
          reason: "chat input probe unreadable and focus command failed",
          detail: { focusCommandOk: refocus.ok },
        });
      } else if (
        pastedText &&
        this.cursorPreSubmitProbeMismatchBlocksSubmit(observed, pastedText, refocus.ok)
      ) {
        this.traceOperation({
          op: "submit",
          route: `${route}:input-probe-mismatch`,
          ok: false,
          reason: this.cursorPreSubmitProbeEmptyBlocksSubmit(observed, pastedText, refocus.ok)
            ? "chat input probe read empty after paste; refusing submit until Glass/chat input is focused"
            : "chat input probe is far shorter than the pasted prompt; refusing submit until chat input is focused",
          detail: {
            focusCommandOk: refocus.ok,
            observedLength: observed.trim().length,
            pastedLength: pastedText.trim().length,
            probeRequired: this.probeLadderEnabled(),
          },
        });
        return {
          ok: false,
          command: refocus.command,
          reason: this.cursorPreSubmitProbeEmptyBlocksSubmit(observed, pastedText, refocus.ok)
            ? "Cursor chat input probe was empty (focus likely on editor/terminal, not chat)"
            : "Cursor chat input probe did not reflect the pasted prompt (likely wrong surface focused)",
        };
      } else {
        this.traceOperation({
          op: "submit",
          route: `${route}:input-probe-mismatch`,
          ok: refocus.ok,
          reason: refocus.ok
            ? "chat input probe did not match pasted prompt; trusting focus command before submit"
            : "Cursor chat input focus could not be confirmed before submit",
          detail: {
            focusCommandOk: refocus.ok,
            observedLength: observed.trim().length,
            probeRequired: this.probeLadderEnabled(),
          },
        });
      }
    }
    if (refocus.ok) {
      return refocus;
    }
    return {
      ok: false,
      command: refocus.command,
      reason: "Cursor chat input focus could not be confirmed before submit",
    };
  }

  protected async pasteText(text: string, replaceCurrentInput = false): Promise<CommandOutcome> {
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

    const direct = await this.tryDirectPasteCommands(text, ide, existing, cache, before, useProbe);
    if (direct) {
      this.traceOperation({ op: "paste", route: "direct-command", ok: direct.ok, command: direct.command, reason: direct.reason });
      return direct;
    }

    if (ide === "windsurf") {
      return { ok: false };
    }

    if (ide !== "cursor") {
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
    } else {
      this.traceOperation({
        op: "paste",
        route: "vscode-clipboard",
        ok: false,
        reason: "clipboard paste skipped on Cursor; use typeText fast path or type command",
      });
    }

    if (ide === "vscodium" && this.allowVSCodiumHostInputFallback()) {
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

    if (ide === "cursor") {
      const { glassUi, promptPastes } = resolveCursorComposerPasteCandidates(existing);
      if (glassUi) {
        for (const pasteCmd of promptPastes) {
          this.traceOperation({
            op: "paste",
            route: `glass-composer-prompt:${pasteCmd}`,
            ok: true,
            command: pasteCmd,
            detail: { textLength: text.length },
          });
          try {
            const result = await Promise.resolve(vscode.commands.executeCommand(pasteCmd, text));
            if (result === false) {
              this.traceOperation({
                op: "paste",
                route: `glass-composer-prompt:${pasteCmd}`,
                ok: false,
                reason: "command returned false",
              });
              continue;
            }
          } catch (err) {
            this.traceOperation({
              op: "paste",
              route: `glass-composer-prompt:${pasteCmd}`,
              ok: false,
              reason: String(err),
            });
            continue;
          }
          await this.sleep(this.probePasteDelayMs());
          this.traceOperation({
            op: "paste",
            route: "glass-composer-prompt",
            ok: true,
            command: pasteCmd,
          });
          return { ok: true, command: pasteCmd };
        }
      }
    }

    const typed = await this.tryTypePaste(text, before, useProbe);
    this.traceOperation({ op: "paste", route: "type", ok: typed.ok, command: typed.command, reason: typed.reason });
    return typed;
  }

  /** Paste commands that read OS/selection clipboard instead of the drive text arg. */
  static isClipboardReadingPasteCommand(cmd: string): boolean {
    if (
      cmd === "editor.action.clipboardPasteAction"
      || cmd === "editor.action.selectionClipboardPaste"
      || cmd === "editor.action.pasteAs"
      || cmd === "execPaste"
      || cmd === "paste"
    ) {
      return true;
    }
    const lower = cmd.toLowerCase();
    return /clipboard.*paste|paste.*clipboard/.test(lower);
  }

  private static directPasteReadsClipboard(cmd: string): boolean {
    return SharedAutopilotBridgePaste.isClipboardReadingPasteCommand(cmd);
  }

  private async tryDirectPasteCommands(
    text: string,
    ide: string,
    existing: Set<string>,
    cache: ProbeCacheEntry | undefined,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<CommandOutcome | undefined> {
    const directCommands = filterRegistered(
      this.orderWithServerOverride("paste", buildPasteDirectCommands(ide), cache?.paste),
      existing
    );
    const submitRequested = this.isSubmitRequestedForCurrentDrive();
    const previousClip = await this.saveClipboard();
    let clipboardSeeded = false;
    try {
      for (const cmd of directCommands) {
        if (cmd.toLowerCase().includes("terminal.paste")) {
          this.traceOperation({
            op: "paste",
            route: `direct-command:${cmd}`,
            ok: false,
            reason: "terminal paste targets the integrated terminal, not chat",
          });
          continue;
        }
        if (
          ide === "cursor" &&
          cmd.toLowerCase().includes("startcomposerprompt")
        ) {
          this.traceOperation({
            op: "paste",
            route: `direct-command:${cmd}`,
            ok: false,
            reason: "startComposerPrompt* is reserved for the Cursor composer fast path",
          });
          continue;
        }
        if (ide === "cursor" && SharedAutopilotBridgePaste.directPasteReadsClipboard(cmd)) {
          this.traceOperation({
            op: "paste",
            route: `direct-command:${cmd}`,
            ok: false,
            reason: "clipboard-reading paste is unsafe on Cursor (targets active TextEditor, not chat webview)",
          });
          continue;
        }
        if (!submitRequested && this.directPasteMayImplicitlySubmit(ide, cmd)) {
          this.traceOperation({
            op: "paste",
            route: `direct-command:${cmd}`,
            ok: false,
            reason: "command may implicitly submit/toggle chat and was skipped because submit=false",
          });
          continue;
        }
        const readsClipboard = SharedAutopilotBridgePaste.directPasteReadsClipboard(cmd);
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
          if (useProbe && pasteLandedInEditor(before, after, text)) {
            debugLog("PROBE_PASTE_REJECT", { cmd, reason: "landed_in_editor" });
            continue;
          }
          if (useProbe) {
            await this.saveProbeCache({ paste: cmd });
          }
          return { ok: true, command: cmd };
        } catch {
          /* ignore */
        }
      }
      return undefined;
    } finally {
      if (clipboardSeeded) {
        await this.sleep(120);
        await this.restoreClipboard(previousClip);
      }
    }
  }

  private async tryHostClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("HOST_PASTE_NO_INPUT_FOCUS");
      this.traceOperation({ op: "paste", route: "host-clipboard:focus-input", ok: false, reason: "input focus unavailable" });
    }
    const guard = await this.guardVSCodiumTerminalRiskPaste("host-clipboard");
    if (guard) {
      return guard;
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
    if (useProbe && pasteLandedInEditor(before, after, text)) {
      this.traceOperation({ op: "paste", route: "host-clipboard:probe", ok: false, reason: "paste landed in editor" });
      return { handled: true, result: { ok: false, command: paste.command, reason: "paste landed in editor" } };
    }
    if (useProbe) {
      await this.saveProbeCache({ paste: `host-clipboard:${clip}+${paste.command}` });
    }
    return { handled: true, result: { ok: true, command: `host-clipboard:${clip}+${paste.command}` } };
  }

  private async tryClipboardPaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<PasteAttempt> {
    const inputFocused = await this.focusChatInput();
    if (!inputFocused.ok) {
      debugLog("PROBE_PASTE_NO_INPUT_FOCUS");
      if (useProbe && before.hasEditor && before.isFileLike) {
        return { handled: true, result: { ok: false, reason: "chat input focus unavailable; refusing editor clipboard paste fallback" } };
      }
    }
    try {
      const guard = await this.guardVSCodiumTerminalRiskPaste("vscode-clipboard");
      if (guard) {
        return guard;
      }
      await this.clearChatInput();
      const ok = await this.writeClipboardVerified(text);
      if (!ok) {
        debugLog("CLIPBOARD_PASTE_ABORT_UNVERIFIED");
        return {
          handled: true,
          result: {
            ok: false,
            reason:
              "clipboard writeText did not propagate (readback mismatch); "
              + "refusing paste to avoid clobbering chat input with stale clipboard content",
          },
        };
      }
      await vscode.commands.executeCommand("editor.action.clipboardPasteAction");
      await this.sleep(this.probePasteDelayMs());
      const after = this.editorSnapshot();
      if (useProbe && pasteLandedInEditor(before, after, text)) {
        return { handled: true, result: { ok: false } };
      }
      if (useProbe) {
        await this.saveProbeCache({ paste: "editor.action.clipboardPasteAction" });
      }
      return { handled: true, result: { ok: true, command: "editor.action.clipboardPasteAction" } };
    } catch {
      /* ignore */
    }
    return { handled: false, result: { ok: false } };
  }

  private async guardVSCodiumTerminalRiskPaste(route: string): Promise<PasteAttempt | null> {
    if (this.detectIde() !== "vscodium" || !this.probeLadderEnabled()) {
      return null;
    }
    const observed = await this.probeChatInputContents();
    if (observed !== null) {
      return null;
    }
    const reason =
      "chat input probe inconclusive; refusing terminal-risk paste fallback";
    this.traceOperation({
      op: "paste",
      route: `${route}:terminal-risk-guard`,
      ok: false,
      reason,
    });
    return { handled: true, result: { ok: false, reason } };
  }

  private async tryTypePaste(
    text: string,
    before: ReturnType<typeof captureEditorSnapshot>,
    useProbe: boolean
  ): Promise<CommandOutcome> {
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
      if (useProbe && pasteLandedInEditor(before, after, text)) {
        return { ok: false };
      }
      if (useProbe) {
        await this.saveProbeCache({ paste: "type" });
      }
      return { ok: true, command: "type" };
    } catch {
      return { ok: false };
    }
  }

  protected async probeChatInputContents(): Promise<string | null> {
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
    } catch (err) {
      debugLog("CHAT_INPUT_PROBE_ERROR", { err: String(err) });
      return null;
    } finally {
      await this.restoreClipboard(previous);
      await this.collapseProbeSelection();
    }
  }

  private async collapseProbeSelection(): Promise<void> {
    try {
      await Promise.resolve(vscode.commands.executeCommand("cursorMove", {
        to: "wrappedLineEnd",
        select: false,
      }));
      this.traceOperation({ op: "input_probe", route: "collapse-selection", ok: true });
    } catch (err) {
      const fallbackOk = await this.runCommand("cursorLineEnd");
      this.traceOperation({
        op: "input_probe",
        route: "collapse-selection",
        ok: fallbackOk,
        reason: fallbackOk ? undefined : String(err),
      });
    }
  }

  protected async saveClipboard(): Promise<string | null> {
    try {
      return await vscode.env.clipboard.readText();
    } catch {
      return null;
    }
  }

  protected async restoreClipboard(previous: string | null): Promise<void> {
    if (previous !== null) {
      try {
        await vscode.env.clipboard.writeText(previous);
      } catch {
        /* ignore */
      }
    }
  }

  protected async writeClipboardVerified(text: string): Promise<boolean> {
    const maxTries = 6;
    for (let i = 0; i < maxTries; i++) {
      try {
        await vscode.env.clipboard.writeText(text);
      } catch (err) {
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
      } catch (err) {
        debugLog("CLIPBOARD_READBACK_ERROR", { err: String(err) });
      }
    }
    debugLog("CLIPBOARD_WRITE_UNVERIFIED", { length: text.length });
    return false;
  }

  protected allowVSCodiumHostInputFallback(): boolean {
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    return cfg.get<boolean>("allowVSCodiumHostInputFallback", true)
      || process.env.KORU_VSCODIUM_ALLOW_HOST_INPUT_FALLBACK === "1";
  }

  protected async saveHostClipboard(): Promise<string | null> {
    if (this.detectIde() !== "vscodium") {
      return null;
    }
    for (const [cmd, args] of [
      ["wl-paste", ["--no-newline"]],
      ["xclip", ["-selection", "clipboard", "-out"]],
      ["xsel", ["--clipboard", "--output"]],
    ] as Array<[string, string[]]>) {
      const res = await this.runHostCommand(cmd, args);
      if (res.ok) {
        debugLog("HOST_CLIPBOARD_READ", { cmd });
        return res.stdout;
      }
    }
    return null;
  }

  private async writeHostClipboard(text: string): Promise<string | null> {
    for (const [cmd, args] of [
      ["wl-copy", []],
      ["xclip", ["-selection", "clipboard"]],
      ["xsel", ["--clipboard", "--input"]],
    ] as Array<[string, string[]]>) {
      const res = await this.runHostCommand(cmd, args, text);
      if (res.ok) {
        debugLog("HOST_CLIPBOARD_WRITE", { cmd, length: text.length });
        return cmd;
      }
    }
    return null;
  }

  protected async restoreHostClipboard(previous: string | null): Promise<void> {
    if (previous === null || this.detectIde() !== "vscodium") {
      return;
    }
    await this.writeHostClipboard(previous);
    debugLog("HOST_CLIPBOARD_RESTORE", { length: previous.length });
  }
}
