/**
 * windsurf-only probe-ladder regression tests.
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

function testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand(): void {
  const cmds = buildFocusOpenCommands("windsurf", []);
  assert(!cmds.includes("workbench.view.windsurfAgentSidebarContainer"), "no toggle sidebar");
  assert(cmds.includes("windsurf.cascadePanel.open"), "cascade open present");
}

function testSanitizeWindsurfDiscardsTypeSubmit(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "windsurf",
    appName: "Windsurf",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "type:\n",
  };
  assert(sanitizeProbeCacheForIde(poisoned, "windsurf")?.submit === undefined, "type submit discarded");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("windsurf").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand();
testSanitizeWindsurfDiscardsTypeSubmit();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
