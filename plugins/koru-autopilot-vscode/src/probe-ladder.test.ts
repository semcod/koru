import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildHostKeySubmitCandidates,
  buildSubmitCommands,
  captureEditorSnapshot,
  chatFocusHeuristic,
  mergeUnique,
  orderWithCache,
  pasteLandedInEditor,
  sanitizeProbeCacheForIde,
  verifyFocusAfterOpen,
  PROBE_CACHE_VERSION,
} from "./probe-ladder";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`probe-ladder test failed: ${message}`);
  }
}

function testOrderWithCache(): void {
  const ordered = orderWithCache(["a", "b", "c"], "b");
  assert(ordered[0] === "b" && ordered.length === 3, "cached command should be first");
  assert(orderWithCache(["a", "b"], undefined).join() === "a,b", "no cache preserves order");
  assert(orderWithCache(["a", "b"], "z").join() === "a,b", "stale cache must not add removed commands");
}

function testChatFocusHeuristic(): void {
  assert(
    chatFocusHeuristic({ hasEditor: false, scheme: "", isFileLike: false, text: "" }),
    "no editor should look like chat focus",
  );
  assert(
    !chatFocusHeuristic({ hasEditor: true, scheme: "file", isFileLike: true, text: "x" }),
    "file editor should not look like chat focus",
  );
}

function testVerifyFocusAfterOpen(): void {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  const none = { hasEditor: false, scheme: "", isFileLike: false, text: "" };
  assert(verifyFocusAfterOpen(file, none), "blur from file editor counts as open");
  assert(!verifyFocusAfterOpen(file, file, "vscode"), "vscode must not trust unchanged file-editor focus");
  assert(verifyFocusAfterOpen(file, file, "vscodium"), "vscodium chat open is trusted because snapshot can stay unchanged");
}

function testPasteLandedInEditor(): void {
  const before = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello" };
  const after = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello __koru_probe__" };
  assert(
    pasteLandedInEditor(before, after, "__koru_probe__"),
    "new probe text in file editor should fail verification",
  );
  assert(
    !pasteLandedInEditor(before, before, "__koru_probe__"),
    "unchanged editor should not count as paste in editor",
  );
}

function testMergeUnique(): void {
  assert(mergeUnique(["a", "b"], ["b", "c"]).join() === "a,b,c", "merge should dedupe");
}

function testBuildFocusOpenCursorFirst(): void {
  const cmds = buildFocusOpenCommands("cursor", []);
  assert(cmds.includes("composer.showComposer"), "cursor list should include composer");
}

function testBuildFocusOpenAntigravityFirst(): void {
  const cmds = buildFocusOpenCommands("antigravity", []);
  assert(cmds.length === 0, "antigravity must not auto-open/toggle agent panels from the generic ladder");
  assert(!cmds.includes("antigravity.toggleChatFocus"), "antigravity toggle command must never be used automatically");
  assert(!cmds.includes("antigravity.startNewConversation"), "antigravity must not create conversations as a focus side-effect");
}

function testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand(): void {
  const cmds = buildFocusOpenCommands("windsurf", []);
  assert(
    !cmds.includes("workbench.view.windsurfAgentSidebarContainer"),
    "windsurf sidebar command toggles the chat closed and must not be used automatically",
  );
  assert(cmds.includes("windsurf.cascadePanel.open"), "windsurf keeps non-toggle cascade open fallback");
}

function testBuildFocusOpenVscodeDoesNotAutoOpenChatByDefault(): void {
  assert(buildFocusOpenCommands("vscode", []).length === 0, "vscode must not auto-open chat by default");
  assert(
    buildFocusOpenCommands("vscode", ["workbench.action.chat.focusInput"]).join() === "workbench.action.chat.focusInput",
    "vscode should only use explicitly configured focus-open commands",
  );
}

function testBuildFocusInputUsesChatCommands(): void {
  const cmds = buildFocusInputCommands("vscodium");
  assert(cmds[0] === "workbench.action.chat.focusInput", "chat input focus should be the first generic input command");
  assert(cmds.includes("chat.action.focus"), "chat action focus should be available as a fallback");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  const cmds = buildSubmitCommands("vscode");
  assert(
    !cmds.includes("workbench.action.acceptSelectedQuickOpenItem"),
    "submit commands must not use Quick Open acceptance fallback",
  );
}

function testVscodiumSubmitStillExposesWorkbenchFallback(): void {
  const cmds = buildSubmitCommands("vscodium");
  assert(cmds.includes("workbench.action.chat.submit"), "vscodium keeps workbench submit as fallback");
}

function testSanitizeCursorDiscardsTypeSubmit(): void {
  // Regression for plugin ≤0.1.46: on Cursor the submit ladder cached
  // ``type:\n`` as the "winning" submit command because executing the
  // ``type`` builtin in a multi-line chat textarea succeeds without actually
  // submitting. That made every autonomous redrive paste-but-not-send.
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "cursor",
    appName: "Cursor",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "type:\n",
    paste: "editor.action.clipboardPasteAction",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "cursor");
  assert(sanitized !== undefined, "sanitize must keep the entry, only mutate submit");
  assert(sanitized?.submit === undefined, "Cursor: 'type:\\n' must be discarded");
  assert(
    sanitized?.paste === "editor.action.clipboardPasteAction",
    "Cursor: paste cache must be preserved (it really does land in chat input)",
  );
}

function testSanitizeCursorPreservesNonTypeSubmit(): void {
  const good = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "cursor",
    appName: "Cursor",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "wtype -M ctrl -k Return -m ctrl",
  };
  const sanitized = sanitizeProbeCacheForIde(good, "cursor");
  assert(
    sanitized?.submit === "wtype -M ctrl -k Return -m ctrl",
    "Cursor: Ctrl+Return host-key submit must survive sanitize",
  );
}

function testSanitizeCursorDiscardsHostPlainReturn(): void {
  // Regression for plugin 0.1.47: ``xdotool key Return`` got cached even
  // though plain Return does not submit Cursor's multi-line chat textarea.
  for (const submit of ["xdotool key Return", "wtype -k Return", "ydotool key Return"]) {
    const poisoned = {
      version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
      ide: "cursor",
      appName: "Cursor",
      updatedAt: "2026-05-22T20:00:00Z",
      submit,
      paste: "editor.action.clipboardPasteAction",
    };
    const sanitized = sanitizeProbeCacheForIde(poisoned, "cursor");
    assert(sanitized?.submit === undefined, `Cursor: '${submit}' must be discarded`);
    assert(
      sanitized?.paste === "editor.action.clipboardPasteAction",
      `Cursor: paste cache must survive while submit '${submit}' is discarded`,
    );
  }
}

function testSanitizeWindsurfStillDiscardsTypeSubmit(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "windsurf",
    appName: "Windsurf",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "type:\n",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "windsurf");
  assert(sanitized?.submit === undefined, "Windsurf must keep discarding 'type:\\n'");
}

function testSanitizeIsIdempotent(): void {
  const empty = sanitizeProbeCacheForIde(undefined, "cursor");
  assert(empty === undefined, "no cache should sanitize to no cache");
  const clean = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "vscode",
    appName: "Visual Studio Code",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "workbench.action.chat.submit",
  };
  const sanitized = sanitizeProbeCacheForIde(clean, "vscode");
  assert(sanitized?.submit === "workbench.action.chat.submit", "clean vscode cache must be untouched");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenCursorFirst();
testBuildFocusOpenAntigravityFirst();
testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand();
testBuildFocusOpenVscodeDoesNotAutoOpenChatByDefault();
testBuildFocusInputUsesChatCommands();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
testVscodiumSubmitStillExposesWorkbenchFallback();
testSanitizeCursorDiscardsTypeSubmit();
testSanitizeCursorPreservesNonTypeSubmit();
testSanitizeCursorDiscardsHostPlainReturn();
testSanitizeWindsurfStillDiscardsTypeSubmit();
testSanitizeIsIdempotent();

function firstKey(cands: ReadonlyArray<[string, string[]]>): string {
  const [cmd, args] = cands[0];
  return `${cmd} ${args.join(" ")}`;
}

function renderKey(cand: [string, string[]]): string {
  const [cmd, args] = cand;
  return `${cmd} ${args.join(" ")}`;
}

const WAYLAND_ENV = { XDG_SESSION_TYPE: "wayland", WAYLAND_DISPLAY: "wayland-0" };
const X11_ENV = { XDG_SESSION_TYPE: "x11" };

function testHostKeyOrderCursorPrefersCtrlReturn(): void {
  // Regression for plugin ≤0.1.47: on Cursor the chat textarea treats plain
  // ``Enter`` as a newline. Injectors all exit 0 even though the message
  // never gets submitted, so the host-key ladder latched onto a no-op Return.
  // Ctrl+Return is the canonical submit shortcut and must be tried first for
  // Cursor.
  const cands = buildHostKeySubmitCandidates("cursor", "auto", WAYLAND_ENV);
  assert(
    firstKey(cands).includes("ctrl"),
    "Cursor host-key ladder must try Ctrl+Return first",
  );
  const flat = cands.map(renderKey).join("|");
  assert(flat.includes("Return"), "plain Return must remain in the ladder");
}

function testHostKeyOrderVscodeKeepsPlainReturnFirst(): void {
  const cands = buildHostKeySubmitCandidates("vscode", "auto", WAYLAND_ENV);
  assert(
    !firstKey(cands).includes("ctrl"),
    "VS Code keeps Return-first ordering (Ctrl+Return is its newline shortcut)",
  );
}

function testHostKeyOverrideCtrlReturnForcesCtrlForAllIdes(): void {
  const cands = buildHostKeySubmitCandidates("vscode", "ctrl+Return", WAYLAND_ENV);
  assert(
    firstKey(cands).includes("ctrl"),
    "submitHostKey=ctrl+Return overrides VS Code default and tries Ctrl first",
  );
}

function testHostKeyOverrideReturnForcesPlainEvenOnCursor(): void {
  const cands = buildHostKeySubmitCandidates("cursor", "Return", WAYLAND_ENV);
  assert(
    !firstKey(cands).includes("ctrl"),
    "submitHostKey=Return overrides Cursor auto and tries plain Return first",
  );
}

function testHostKeyWaylandPrefersYdotoolOverXdotool(): void {
  // Regression for plugin 0.1.48: on Wayland-native compositors (GNOME),
  // ``xdotool key Return`` exits 0 but only delivers the synthetic key to
  // whatever XWayland window is active — never reaching Wayland-native apps
  // like recent Cursor builds. ``ydotool`` (uinput) is the only injector
  // that reliably crosses from process to compositor, so it must come BEFORE
  // ``xdotool`` whenever the session is Wayland.
  const cands = buildHostKeySubmitCandidates("vscode", "auto", WAYLAND_ENV);
  const flat = cands.map(renderKey).join("|");
  const ydotoolPos = flat.indexOf("ydotool key");
  const xdotoolPos = flat.indexOf("xdotool key");
  assert(ydotoolPos !== -1, "ydotool must appear in the ladder");
  assert(xdotoolPos !== -1, "xdotool must remain as fallback");
  assert(
    ydotoolPos < xdotoolPos,
    "Wayland session must try ydotool before xdotool (xdotool cannot reach Wayland-native windows)",
  );
}

function testHostKeyX11KeepsXdotoolFirst(): void {
  const cands = buildHostKeySubmitCandidates("vscode", "auto", X11_ENV);
  const plainOnly = cands.filter((c) => !renderKey(c).includes("ctrl"));
  const order = plainOnly.map(([cmd]) => cmd);
  assert(order[0] === "xdotool", "X11 session must keep xdotool first within plain-Return row");
}

testHostKeyOrderCursorPrefersCtrlReturn();
testHostKeyOrderVscodeKeepsPlainReturnFirst();
testHostKeyOverrideCtrlReturnForcesCtrlForAllIdes();
testHostKeyOverrideReturnForcesPlainEvenOnCursor();
testHostKeyWaylandPrefersYdotoolOverXdotool();
testHostKeyX11KeepsXdotoolFirst();
console.log("probe-ladder tests: ok");
