/**
 * vscode-only probe-ladder regression tests.
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
  if (!condition) throw new Error(`probe-ladder test failed: ${message}`);
}

function testOrderWithCache(): void {
  assert(orderWithCache(["a", "b", "c"], "b")[0] === "b", "cached first");
}

function testChatFocusHeuristic(): void {
  assert(chatFocusHeuristic({ hasEditor: false, scheme: "", isFileLike: false, text: "" }), "no editor");
  assert(!chatFocusHeuristic({ hasEditor: true, scheme: "file", isFileLike: true, text: "x" }), "file editor");
}

function testPasteLandedInEditor(): void {
  const before = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello" };
  const after = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello __koru_probe__" };
  assert(pasteLandedInEditor(before, after, "__koru_probe__"), "paste in editor");
}

function testMergeUnique(): void {
  assert(mergeUnique(["a", "b"], ["b", "c"]).join() === "a,b,c", "dedupe");
}

function firstKey(cands: ReadonlyArray<[string, string[]]>): string {
  const [cmd, args] = cands[0];
  return `${cmd} ${args.join(" ")}`;
}

const WAYLAND_ENV = { XDG_SESSION_TYPE: "wayland", WAYLAND_DISPLAY: "wayland-0" };

function testVerifyFocusAfterOpen(): void {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  const none = { hasEditor: false, scheme: "", isFileLike: false, text: "" };
  assert(verifyFocusAfterOpen(file, none), "blur counts as open");
  assert(!verifyFocusAfterOpen(file, file, "vscode"), "vscode must not trust unchanged file-editor focus");
}

function testBuildFocusOpenVscode(): void {
  const cmds = buildFocusOpenCommands("vscode", []);
  assert(cmds.includes("workbench.action.chat.open"), "vscode includes safe chat-open fallback");
}

function testSanitizeVscodeDropsUnsafeFocusOpenCache(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "vscode",
    appName: "Visual Studio Code",
    updatedAt: "2026-05-24T20:00:00Z",
    focusOpen: "workbench.panel.chat",
    focusInput: "workbench.action.chat.focusInput",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "vscode");
  assert(sanitized?.focusOpen === undefined, "unsafe focus-open cache dropped");
  assert(sanitized?.focusInput === "workbench.action.chat.focusInput", "safe focus-input preserved");
}

function testSanitizeVscodeDropsNewChatFocusOpenCache(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "vscode",
    appName: "Visual Studio Code",
    updatedAt: "2026-05-24T20:00:00Z",
    focusOpen: "aichat.newchataction",
    focusInput: "workbench.action.chat.focusInput",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "vscode");
  assert(sanitized?.focusOpen === undefined, "new-chat focus-open cache dropped");
  assert(sanitized?.focusInput === "workbench.action.chat.focusInput", "safe focus-input preserved");
}

function testHostKeyOrderVscodeKeepsPlainReturnFirst(): void {
  const cands = buildHostKeySubmitCandidates("vscode", "auto", WAYLAND_ENV);
  assert(!firstKey(cands).includes("ctrl"), "VS Code keeps Return-first ordering");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("vscode").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenVscode();
testSanitizeVscodeDropsUnsafeFocusOpenCache();
testSanitizeVscodeDropsNewChatFocusOpenCache();
testHostKeyOrderVscodeKeepsPlainReturnFirst();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
