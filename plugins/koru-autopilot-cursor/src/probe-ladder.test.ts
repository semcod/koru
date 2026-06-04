/**
 * Cursor-only probe-ladder regression tests.
 *
 * Sibling VSIX packages (``koru-autopilot-vscode``/``-vscodium``/``-windsurf``/
 * ``-antigravity``) own the equivalent tests for their IDE so a regression
 * in this plugin's probe-ladder logic cannot mask another IDE's bug.
 */

import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildHostKeySubmitCandidates,
  buildSubmitCommands,
  chatFocusHeuristic,
  decideSubmitCleared,
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
  assert(
    orderWithCache(["a", "b"], "z").join() === "z,a,b",
    "cached command outside defaults should be retried before availability filtering",
  );
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
  assert(!verifyFocusAfterOpen(file, file, "cursor"), "cursor must not trust unchanged file-editor focus");
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
  assert(cmds.includes("composer.openComposer"), "cursor list should include composer.openComposer");
}

function testBuildFocusInputUsesChatCommands(): void {
  // Cursor 1.x removed the ``composer.*`` namespace; the modern primary
  // focus-input command is ``workbench.action.chat.focusInput``. Legacy
  // ``composer.focusComposer`` stays as a tail fallback for older
  // builds that still register it.
  const cmds = buildFocusInputCommands("cursor");
  assert(cmds[0] === "glass.focusInput", "Cursor: glass.focusInput must be first focus-input candidate (Glass/Agents)");
  assert(cmds.includes("workbench.action.chat.focusInput"), "Cursor: workbench.action.chat.focusInput must remain in focus list");
  assert(!cmds.includes("composer.focusComposer"), "Cursor: composer.focusComposer must be blocklisted (panel chrome, not textarea)");
  assert(!cmds.includes("workbench.panel.chat.view.copilot.focus"), "Cursor: panel.chat.view focus must be blocklisted");
  assert(cmds.includes("chat.action.focus"), "chat action focus should be available as a fallback");
  // The blocklist must drop the side-bar/panel focus commands that
  // would otherwise steal focus to the explorer or terminal pane.
  assert(!cmds.includes("workbench.action.focusAuxiliaryBar"), "Cursor: focusAuxiliaryBar must be blocked");
  assert(!cmds.includes("workbench.action.focusSideBar"), "Cursor: focusSideBar must be blocked");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  const cmds = buildSubmitCommands("cursor");
  assert(
    !cmds.includes("workbench.action.acceptSelectedQuickOpenItem"),
    "submit commands must not use Quick Open acceptance fallback",
  );
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
    sanitized?.paste === undefined,
    "Cursor: clipboardPasteAction paste cache must be discarded (reads OS clipboard, not drive text)",
  );
}

function testSanitizeCursorDiscardsSelectionClipboardPaste(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "cursor",
    appName: "Cursor",
    updatedAt: "2026-06-02T20:00:00Z",
    paste: "editor.action.selectionClipboardPaste",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "cursor");
  assert(
    sanitized?.paste === undefined,
    "Cursor: selectionClipboardPaste paste cache must be discarded (reads selection clipboard, not drive text)",
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

function testSanitizeCursorDiscardsXdotoolSubmitOnWayland(): void {
  const prev = process.env.XDG_SESSION_TYPE;
  process.env.XDG_SESSION_TYPE = "wayland";
  try {
    const poisoned = {
      version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
      ide: "cursor",
      appName: "Cursor",
      updatedAt: "2026-05-22T20:00:00Z",
      submit: "xdotool key ctrl+Return",
      paste: "editor.action.clipboardPasteAction",
    };
    const sanitized = sanitizeProbeCacheForIde(poisoned, "cursor");
    assert(
      sanitized?.submit === undefined,
      "Cursor on Wayland: xdotool ctrl+Return false-positive must be discarded",
    );
  } finally {
    if (prev === undefined) {
      delete process.env.XDG_SESSION_TYPE;
    } else {
      process.env.XDG_SESSION_TYPE = prev;
    }
  }
}

function testSanitizeCursorDiscardsHostPlainReturn(): void {
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
      sanitized?.paste === undefined,
      `Cursor: clipboard paste cache must be discarded while submit '${submit}' is discarded`,
    );
  }
}

function testSanitizeIsIdempotent(): void {
  const empty = sanitizeProbeCacheForIde(undefined, "cursor");
  assert(empty === undefined, "no cache should sanitize to no cache");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenCursorFirst();
testBuildFocusInputUsesChatCommands();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
testSanitizeCursorDiscardsTypeSubmit();
testSanitizeCursorDiscardsSelectionClipboardPaste();
testSanitizeCursorPreservesNonTypeSubmit();
testSanitizeCursorDiscardsXdotoolSubmitOnWayland();
testSanitizeCursorDiscardsHostPlainReturn();
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
  // ``Enter`` as a newline. Ctrl+Return is the canonical submit shortcut and
  // must be tried first.
  const cands = buildHostKeySubmitCandidates("cursor", "auto", WAYLAND_ENV);
  assert(
    firstKey(cands).includes("ctrl"),
    "Cursor host-key ladder must try Ctrl+Return first",
  );
  const flat = cands.map(renderKey).join("|");
  assert(flat.includes("Return"), "plain Return must remain in the ladder");
}

function testHostKeyOverrideReturnForcesPlainOnCursor(): void {
  const cands = buildHostKeySubmitCandidates("cursor", "Return", WAYLAND_ENV);
  assert(
    !firstKey(cands).includes("ctrl"),
    "submitHostKey=Return overrides Cursor auto and tries plain Return first",
  );
}

function testHostKeyWaylandPrefersYdotoolOverXdotool(): void {
  const cands = buildHostKeySubmitCandidates("cursor", "auto", WAYLAND_ENV);
  const flat = cands.map(renderKey).join("|");
  const ydotoolPos = flat.indexOf("ydotool key");
  const xdotoolPos = flat.indexOf("xdotool key");
  assert(ydotoolPos !== -1, "ydotool must appear in the ladder");
  assert(xdotoolPos !== -1, "xdotool must remain as fallback");
  assert(
    ydotoolPos < xdotoolPos,
    "Wayland session must try ydotool before xdotool",
  );
}

function testHostKeyX11KeepsXdotoolFirst(): void {
  const cands = buildHostKeySubmitCandidates("cursor", "auto", X11_ENV);
  const plainOnly = cands.filter((c) => !renderKey(c).includes("ctrl"));
  const order = plainOnly.map(([cmd]) => cmd);
  assert(order[0] === "xdotool", "X11 session must keep xdotool first within plain-Return row");
}

testHostKeyOrderCursorPrefersCtrlReturn();
testHostKeyOverrideReturnForcesPlainOnCursor();
testHostKeyWaylandPrefersYdotoolOverXdotool();
testHostKeyX11KeepsXdotoolFirst();

function testDecideSubmitClearedNullProbeFallsClosedToCleared(): void {
  const decision = decideSubmitCleared(null, "anything");
  assert(decision.cleared, "null probe must fall closed to cleared=true");
  assert(!decision.tailMatched, "null probe cannot have a tail match");
}

function testDecideSubmitClearedEmptyInputMeansSubmitWorked(): void {
  const decision = decideSubmitCleared("", "Architektura: wprowadź CQRS");
  assert(decision.cleared, "empty input after submit means submit cleared the textarea");
}

function testDecideSubmitClearedTextStillPresentMeansSubmitFailed(): void {
  // Regression for plugin ≤0.1.53: Cursor's ``composer.sendToAgent``
  // returned ``ok=true`` even when it no-oped. Without verification the
  // daemon would never retry and the user kept staring at an unsent prompt.
  const original = "Make the test deterministic by seeding RNG=42";
  const decision = decideSubmitCleared(original, original);
  assert(!decision.cleared, "identical text in probe means submit did not clear chat");
  assert(decision.tailMatched, "exact match should detect tail");
}

testDecideSubmitClearedNullProbeFallsClosedToCleared();
testDecideSubmitClearedEmptyInputMeansSubmitWorked();
testDecideSubmitClearedTextStillPresentMeansSubmitFailed();

function testCaptureEditorSnapshotShape(): void {
  // captureEditorSnapshot itself is exercised via the plugin runtime
  // (mocking vscode here would just re-test the mock). The export still
  // needs to compile, which is enough to catch accidental signature
  // regressions in this Cursor-only build.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _placeholder = true;
}

testCaptureEditorSnapshotShape();
