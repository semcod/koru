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
  if (!cached) {
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
  const windsurfDefaults = [
    "workbench.view.windsurfAgentSidebarContainer",
    "windsurf.cascadePanel.open",
    "windsurf.cascadePanel.focus",
    "windsurf.action.openCascade",
    "windsurf.action.openChat",
    "windsurf.chat.open",
    "windsurf.cascade.open",
    "windsurf.panel.chat",
    "cascade.focus",
    "windsurf.action.showCascade",
    "composer.showComposer",
    "aichat.newchataction",
    "windsurf.openCascade",
  ];
  const genericDefaults = [
    "composer.showComposer",
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
    "aichat.newchataction",
    "cursor.composer.open",
    "workbench.panel.aichat.view.copilot.focus",
  ];
  const defaults = ide === "windsurf" ? windsurfDefaults : genericDefaults;
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
    return ["composer.submit", "aichat.submit", ...generic];
  }
  return generic;
}

export function filterRegistered(commands: string[], existing: Set<string>): string[] {
  return commands.filter((cmd) => existing.has(cmd));
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
