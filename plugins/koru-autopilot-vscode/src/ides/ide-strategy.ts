/**
 * Per-IDE strategy contract.
 *
 * This is the **single place** that owns IDE-specific behavior on the
 * extension side. The legacy probe-ladder / extension.ts code paths used
 * scattered `if (ide === "cursor")` branches — that meant a fix for Cursor
 * could (and did) regress VSCodium / Windsurf because they all shared the
 * same functions. The IdeStrategy interface lets us extract one IDE at a
 * time into its own module so future changes for Cursor stay in
 * ``src/ides/cursor.ts`` and cannot reach the other IDEs.
 *
 * Adoption is **incremental**: when no strategy is registered for an IDE,
 * the probe-ladder and submit-fallback helpers fall through to their
 * existing behavior. Strategies override one decision at a time.
 */

import type { ProbeCacheEntry } from "../probe-ladder";

export interface SubmitFallbackPolicy {
  /**
   * When the host-key submit (xdotool/wtype/ydotool Return) produced no
   * effect, should the IDE refuse to keep typing more newlines / `\r`
   * characters into the chat textarea?
   *
   * `true` is the safe default for Cursor: the textarea is multi-line, so
   * extra newlines would just stack inside the prompt without sending. The
   * extension returns `"<ide>-submit-unavailable"` so the daemon can switch
   * strategies (OS injector, plugin reload, etc.).
   */
  readonly refuseTypeNewlineFallback: boolean;
}

export interface IdeStrategy {
  /** Canonical Koru id, e.g. "cursor". Must match the daemon-side string. */
  readonly id: string;
  /** Friendly label used in logs. */
  readonly label: string;

  /**
   * Returns the IDE id when `vscode.env.appName` (or another runtime
   * fingerprint) matches this IDE; otherwise `undefined`. Strategies
   * register themselves so `detectIde()` in `extension.ts` becomes a
   * thin iteration instead of a chain of `if`s.
   */
  detectIde(appName: string): string | undefined;

  /**
   * Commands to try **before** the generic chat-paste commands. Returning
   * `[]` means "use the generic list only".
   */
  pasteDirectCommandsPrefix(): string[];

  /**
   * Full ordered list of submit commands for this IDE. Returning `null`
   * means "use the generic list only" (no IDE-specific candidates).
   */
  submitCommandsOverride(): string[] | null;

  /**
   * Extra commands to try **before** the generic focus-input commands.
   * Returning `[]` means "use the generic list only".
   */
  focusInputCommandsPrefix(): string[];

  /**
   * Whether `buildHostKeySubmitCandidates` should prefer `Ctrl+Return`
   * over plain `Return` when `koruAutopilot.submitHostKey === "auto"`.
   *
   * Cursor's chat textarea treats `Return` as a newline; only `Ctrl+Return`
   * actually submits. VSCodium on Wayland can also report a successful plain
   * `Return` while the input remains unsent, so its own strategy prefers
   * `Ctrl+Return` without changing VS Code.
   */
  preferCtrlSubmit(): boolean;

  /**
   * Mutate the probe cache entry to discard poisoned wins specific to this
   * IDE (e.g. Wayland xdotool no-ops on Cursor). Default implementations
   * may be a no-op.
   */
  sanitizeProbeCache(entry: ProbeCacheEntry, opts: { isWayland: boolean }): void;

  /**
   * IDE-specific commands to open/focus chat before generic defaults
   * (e.g. Windsurf Cascade panel commands).
   */
  focusOpenCommandsDefaults(): string[];

  /**
   * When true, ``verifyFocusAfterOpen`` accepts open without editor-snapshot
   * proof (VSCodium chat webview).
   */
  trustFocusOpenWithoutEditorSnapshot(): boolean;

  /**
   * When ``executeCommand`` succeeds for a focus-open candidate, accept it
   * without editor-snapshot proof (Cursor Composer in auxiliary bar).
   */
  trustFocusOpenCommand?(command: string): boolean;

  /**
   * Generic focus-input commands to skip for this IDE (false positives).
   */
  focusInputCommandsBlocklist?(): string[];

  /** Submit fallback policy used by `_submitChat*Fallback` in extension.ts. */
  readonly submitFallback: SubmitFallbackPolicy;
}
