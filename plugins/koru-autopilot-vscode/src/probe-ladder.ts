/**
 * Probe ladder: try IDE commands in order, verify side-effects, cache winners.
 */

export const PROBE_CACHE_VERSION = 2;

export interface EditorSnapshot {
  hasEditor: boolean;
  scheme: string;
  isFileLike: boolean;
  text: string;
}

export interface ProbeCacheEntry {
  version: typeof PROBE_CACHE_VERSION;
  ide: string;
  appName: string;
  focusOpen?: string;
  focusInput?: string;
  paste?: string;
  submit?: string;
  updatedAt: string;
}

export interface ProbeAttemptResult {
  ok: boolean;
  command: string;
  reason?: string;
}

export function captureEditorSnapshot(
  editor: { document: { uri: { scheme: string }; getText(): string } } | undefined
): EditorSnapshot {
  if (!editor) {
    return { hasEditor: false, scheme: "", isFileLike: false, text: "" };
  }
  const scheme = editor.document.uri.scheme;
  const isFileLike = scheme === "file" || scheme === "untitled";
  return {
    hasEditor: true,
    scheme,
    isFileLike,
    text: editor.document.getText(),
  };
}

/**
 * Decide, given the contents of the chat input observed AFTER running a
 * submit command, whether the submit actually cleared the input.
 *
 * This is the pure decision used by the runtime ``verifySubmitClearedInput``
 * helper in ``extension.ts``. Extracted here so it can be unit-tested
 * without mocking the ``vscode`` module (clipboard, command host, …).
 *
 * Inputs:
 * - ``observedAfter`` is the text the select-all + clipboardCopy probe
 *   read from the input. ``null`` means the probe could not run (no
 *   chat focus, clipboard unreadable, …) and we fall back to trusting
 *   the submit command's own success signal.
 * - ``originalText`` is the prompt we just pasted and asked the IDE to
 *   submit. Trimmed before comparison.
 *
 * Decision:
 * - ``null`` probe → ``cleared = true`` (ambiguous; do not punish a
 *   working submit because the probe failed).
 * - empty / whitespace probe → ``cleared = true``.
 * - probe contains the trailing ``tailLen`` characters of the original
 *   prompt (default 40) → ``cleared = false`` (the submit no-oped and
 *   our text is still in the textarea).
 * - otherwise → ``cleared = true`` (different content; probably an
 *   attachment chip or a fresh user message — leave it alone).
 */
export function decideSubmitCleared(
  observedAfter: string | null,
  originalText: string,
  tailLen = 40
): { cleared: boolean; tailMatched: boolean } {
  if (observedAfter === null) {
    return { cleared: true, tailMatched: false };
  }
  const trimmed = observedAfter.trim();
  if (trimmed.length === 0) {
    return { cleared: true, tailMatched: false };
  }
  const original = originalText.trim();
  if (original.length === 0) {
    return { cleared: true, tailMatched: false };
  }
  const tail = original.slice(-tailLen);
  if (tail.length >= 4 && trimmed.includes(tail)) {
    return { cleared: false, tailMatched: true };
  }
  return { cleared: true, tailMatched: false };
}

/** True when focus is unlikely to be a normal source file editor. */
export function chatFocusHeuristic(snapshot: EditorSnapshot): boolean {
  if (!snapshot.hasEditor) {
    return true;
  }
  if (snapshot.scheme === "output" || snapshot.scheme === "debug-console") {
    return true;
  }
  if (snapshot.isFileLike) {
    return false;
  }
  return true;
}

export function verifyFocusAfterOpen(before: EditorSnapshot, after: EditorSnapshot, ide?: string): boolean {
  if (ide === "windsurf") {
    return true;
  }
  if (ide === "vscodium") {
    // VSCodium chat opens as a workbench/webview surface that often leaves
    // activeTextEditor unchanged, so the editor snapshot is not a reliable
    // proof of focus. Paste verification still catches file-editor leakage.
    return true;
  }
  if (chatFocusHeuristic(after)) {
    return true;
  }
  // Opening chat often blurs the editor without focusing a readable document.
  if (before.hasEditor && before.isFileLike && !after.hasEditor) {
    return true;
  }
  return false;
}

/** Detect paste landing in a file editor instead of chat webview. */
export function pasteLandedInEditor(
  before: EditorSnapshot,
  after: EditorSnapshot,
  text: string
): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 4) {
    return false;
  }
  if (!after.hasEditor || !after.isFileLike) {
    return false;
  }
  const wasInBefore = before.text.includes(trimmed);
  const isInAfter = after.text.includes(trimmed);
  return isInAfter && !wasInBefore;
}

export function orderWithCache(commands: string[], cached?: string): string[] {
  if (!cached || !commands.includes(cached)) {
    return [...commands];
  }
  const rest = commands.filter((c) => c !== cached);
  return [cached, ...rest];
}

export function mergeUnique(primary: string[], secondary: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const cmd of [...primary, ...secondary]) {
    if (!cmd || seen.has(cmd)) {
      continue;
    }
    seen.add(cmd);
    out.push(cmd);
  }
  return out;
}

export function buildFocusOpenCommands(ide: string, custom: string[]): string[] {
  const antigravityDefaults: string[] = [];
  const windsurfDefaults = [
    "windsurf.cascadePanel.open",
    "windsurf.cascadePanel.focus",
    "windsurf.action.openChat",
    "windsurf.chat.open",
    "windsurf.cascade.open",
    "windsurf.panel.chat",
    "cascade.focus",
    "windsurf.action.showCascade",
    "composer.showComposer",
    "aichat.newchataction",
  ];
  const genericDefaults = [
    "composer.showComposer",
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
    "aichat.newchataction",
    "cursor.composer.open",
    "workbench.panel.aichat.view.copilot.focus",
  ];
  if (ide === "vscode") {
    return mergeUnique(custom, []);
  }
  const defaults =
    ide === "antigravity" ? antigravityDefaults : ide === "windsurf" ? windsurfDefaults : genericDefaults;
  return mergeUnique(custom, defaults);
}

export function buildFocusInputCommands(ide: string): string[] {
  const windsurf = [
    "windsurf.cascadePanel.focus",
    "windsurf.action.focusChatInput",
    "windsurf.chat.focusInput",
    "windsurf.cascade.focusInput",
    "cascade.focusInput",
    "windsurf.action.focusCascadeInput",
  ];
  const generic = [
    "workbench.action.chat.focusInput",
    "chat.action.focus",
    "workbench.chat.action.focusLastFocused",
    "workbench.action.focusAuxiliaryBar",
    "workbench.action.focusPanel",
    "workbench.action.focusSideBar",
  ];
  return ide === "windsurf" ? [...windsurf, ...generic] : generic;
}

export function buildPasteDirectCommands(ide: string): string[] {
  if (ide === "windsurf") {
    return [
      "windsurf.sendTextToChat",
      "windsurf.action.chat.typeText",
      "windsurf.action.cascade.typeText",
      "windsurf.chat.typeText",
      "windsurf.cascade.typeText",
      "cascade.typeText",
    ];
  }
  if (ide === "cursor") {
    return [
      "cursor.action.chat.typeText",
      "composer.typeText",
      "aichat.typeText",
    ];
  }
  return [
    "workbench.action.chat.insertText",
    "workbench.action.chat.typeText",
    "aichat.typeText",
  ];
}

export function buildSubmitCommands(ide: string): string[] {
  const generic = [
    "workbench.action.chat.submit",
    "workbench.action.chat.acceptInput",
    "workbench.action.chat.send",
    "workbench.action.chat.sendMessage",
    "workbench.action.interactive.accept",
    "composer.submit",
    "aichat.submit",
  ];
  if (ide === "windsurf") {
    return [
      "windsurf.action.cascade.submit",
      "windsurf.action.submitCascade",
      "windsurf.action.submitChat",
      "windsurf.action.chat.submit",
      "windsurf.chat.submit",
      "windsurf.cascade.submit",
      "cascade.submit",
      ...generic,
    ];
  }
  if (ide === "cursor") {
    // Cursor's actual submit command is ``composer.sendToAgent`` — it sends
    // whatever is currently in the Composer/Agent chat input. The legacy
    // ``composer.submit`` / ``aichat.submit`` candidates are NOT registered
    // in recent Cursor builds, so we kept falling through to the host-key
    // ladder where ``xdotool key Return`` and ``xdotool key ctrl+Return``
    // both exit 0 but only insert a newline (the chat textarea is multi-line
    // and accepts both as in-input keys, not "submit"). Try the registered
    // command FIRST so we never need to forge keystrokes.
    return [
      "composer.sendToAgent",
      "composer.acceptComposerStep",
      "composer.startComposerPrompt",
      "composer.startComposerPrompt2",
      "composer.submit",
      "aichat.submit",
      ...generic,
    ];
  }
  return generic;
}

export function filterRegistered(commands: string[], existing: Set<string>): string[] {
  return commands.filter((cmd) => existing.has(cmd));
}

export type HostKeyCandidate = [string, string[]];

type Mod = "plain" | "ctrl";

function injectorRow(mod: Mod): ReadonlyArray<HostKeyCandidate> {
  if (mod === "ctrl") {
    return [
      ["wtype", ["-M", "ctrl", "-k", "Return", "-m", "ctrl"]],
      ["ydotool", ["key", "ctrl+Return"]],
      ["xdotool", ["key", "ctrl+Return"]],
    ];
  }
  return [
    ["wtype", ["-k", "Return"]],
    ["ydotool", ["key", "Return"]],
    ["xdotool", ["key", "Return"]],
  ];
}

function reorderForXSession(
  row: ReadonlyArray<HostKeyCandidate>,
  isWayland: boolean
): HostKeyCandidate[] {
  if (isWayland) {
    return [...row];
  }
  // X11 / no Wayland: xdotool is the only injector that reaches X clients,
  // wtype always fails, ydotool works only with daemon. Try xdotool first.
  const order = ["xdotool", "ydotool", "wtype"];
  return [...row].sort(
    (a, b) => order.indexOf(a[0]) - order.indexOf(b[0])
  );
}

/**
 * Order host-level submit candidates for an IDE and X session.
 *
 * Three forces fight for priority here:
 *
 * 1. **Modifier**: Cursor's chat textarea (Linux, recent builds) treats plain
 *    ``Enter`` as a newline and only submits on ``Ctrl+Enter``. Injectors all
 *    return exit code 0 even when the keystroke just inserts a newline, so
 *    the probe ladder happily latches onto a no-op ``Return`` if it is tried
 *    first. Force the ``Ctrl+Return`` variants ahead of ``Return`` for
 *    ``ide === "cursor"``.
 * 2. **Injector vs session**: on Wayland-native compositors (e.g. GNOME),
 *    ``xdotool`` cannot see Wayland surfaces — it succeeds with exit 0 but
 *    delivers the synthetic key to whatever XWayland window is active (often
 *    a terminal or an X11 sibling), never reaching Cursor. ``ydotool`` works
 *    via /dev/uinput which the compositor accepts as legitimate hardware
 *    input. ``wtype`` only works when the compositor advertises
 *    ``virtual-keyboard-v1`` (Sway / wlroots; not stock GNOME). On Wayland
 *    we therefore must try ``ydotool`` BEFORE ``xdotool`` — otherwise xdotool
 *    silently wins the probe and the message never reaches Cursor.
 * 3. **Override**: ``koruAutopilot.submitHostKey`` lets users pin a specific
 *    modifier (``"Return"`` / ``"ctrl+Return"`` / ``"auto"``).
 */
export function buildHostKeySubmitCandidates(
  ide: string | undefined,
  override: string = "auto",
  env: NodeJS.ProcessEnv = process.env
): HostKeyCandidate[] {
  const normalized = (override || "auto").toLowerCase();
  const isWayland =
    (env.XDG_SESSION_TYPE || "").toLowerCase() === "wayland" ||
    Boolean(env.WAYLAND_DISPLAY);
  const plain = reorderForXSession(injectorRow("plain"), isWayland);
  const ctrl = reorderForXSession(injectorRow("ctrl"), isWayland);
  if (normalized === "return" || normalized === "enter") {
    return [...plain, ...ctrl];
  }
  if (normalized === "ctrl+return" || normalized === "ctrl+enter") {
    return [...ctrl, ...plain];
  }
  if (ide === "cursor") {
    return [...ctrl, ...plain];
  }
  return [...plain, ...ctrl];
}

/**
 * Discard cache entries that are known to be poisonous for the given IDE.
 *
 * Historical note (plugin ≤0.1.46): on Cursor, the submit ladder would fall
 * through to ``vscode.commands.executeCommand("type", { text: "\n" })`` and
 * cache that as the "winning" submit command. In Cursor's multi-line chat
 * textarea this only inserts a newline (the LLM never receives the message),
 * but the plugin reported ``ok: true`` so the daemon logged
 * ``winning_submit=type:`` with ``verification=strict``. The next autonomous
 * cycle drove the same prompt again, accumulating pasted-but-not-sent
 * messages.
 *
 * Mutates a copy of the entry and returns it (callers may pass the value
 * straight from ``loadProbeCache``). Idempotent for already-clean caches.
 */
function isLikelyWaylandSession(): boolean {
  const env = process.env;
  return (
    (env.XDG_SESSION_TYPE || "").toLowerCase() === "wayland" ||
    Boolean(env.WAYLAND_DISPLAY)
  );
}

function sanitizeWindsurfCache(sanitized: ProbeCacheEntry): void {
  const unsafePaste = ["editor.action.clipboardPasteAction", "type"];
  if (sanitized.paste && unsafePaste.includes(sanitized.paste)) {
    sanitized.paste = undefined;
  }
  if (sanitized.submit && (sanitized.submit.startsWith("type:") || sanitized.submit === "type")) {
    sanitized.submit = undefined;
  }
}

function sanitizeCursorSubmitCache(sanitized: ProbeCacheEntry): void {
  if (sanitized.submit && (sanitized.submit.startsWith("type:") || sanitized.submit === "type")) {
    sanitized.submit = undefined;
    return;
  }
  if (typeof sanitized.submit !== "string") return;
  const cmd = sanitized.submit;
  // On Wayland, xdotool cannot reach native Cursor windows at all — every
  // xdotool host-key probe is a false positive (exit 0, no effect). Discard
  // the cached winner so the ladder re-probes composer.sendToAgent / ydotool.
  if (isLikelyWaylandSession() && cmd.startsWith("xdotool ")) {
    sanitized.submit = undefined;
    return;
  }
  // Plugin 0.1.47 cached host-level plain ``Return`` for Cursor. On Linux
  // (Wayland with XWayland) ``xdotool key Return`` exits 0 even though
  // Cursor's chat textarea treats it as a newline rather than a submit.
  // Force a re-probe so 0.1.48's reordered ladder can pick ``Ctrl+Return``.
  // Match injector-specific renderings without ctrl modifier:
  //   "xdotool key Return", "ydotool key Return", "wtype -k Return"
  const hasCtrl = /\bctrl\b/i.test(cmd) || /-M\s+ctrl\b/.test(cmd);
  const isHostKey =
    /^(xdotool|ydotool)\s+key\s+Return$/.test(cmd) ||
    /^wtype(\s+-[Mm]\s+\S+)*\s+-k\s+Return$/.test(cmd);
  if (!hasCtrl && isHostKey) {
    sanitized.submit = undefined;
  }
}

export function sanitizeProbeCacheForIde(
  entry: ProbeCacheEntry | undefined,
  ide: string
): ProbeCacheEntry | undefined {
  if (!entry) {
    return entry;
  }
  const sanitized = { ...entry };
  if (ide === "windsurf") sanitizeWindsurfCache(sanitized);
  if (ide === "cursor") sanitizeCursorSubmitCache(sanitized);
  if (ide === "vscodium" && sanitized.submit === "workbench.action.chat.submit") {
    sanitized.submit = undefined;
  }
  return sanitized;
}

export function loadProbeCache(
  raw: unknown,
  ide: string,
  appName: string
): ProbeCacheEntry | undefined {
  if (!raw || typeof raw !== "object") {
    return undefined;
  }
  const entry = raw as ProbeCacheEntry;
  if (entry.version !== PROBE_CACHE_VERSION) {
    return undefined;
  }
  if (entry.ide !== ide || entry.appName !== appName) {
    return undefined;
  }
  return entry;
}

export function makeProbeCache(
  ide: string,
  appName: string,
  partial: Partial<Pick<ProbeCacheEntry, "focusOpen" | "focusInput" | "paste" | "submit">>
): ProbeCacheEntry {
  return {
    version: PROBE_CACHE_VERSION,
    ide,
    appName,
    updatedAt: new Date().toISOString(),
    ...partial,
  };
}

export function mergeProbeCache(
  prev: ProbeCacheEntry | undefined,
  ide: string,
  appName: string,
  wins: Partial<Pick<ProbeCacheEntry, "focusOpen" | "focusInput" | "paste" | "submit">>
): ProbeCacheEntry {
  return makeProbeCache(ide, appName, {
    focusOpen: wins.focusOpen ?? prev?.focusOpen,
    focusInput: wins.focusInput ?? prev?.focusInput,
    paste: wins.paste ?? prev?.paste,
    submit: wins.submit ?? prev?.submit,
  });
}
