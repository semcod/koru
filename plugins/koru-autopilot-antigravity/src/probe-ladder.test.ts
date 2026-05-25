/**
 * antigravity-only probe-ladder regression tests.
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

function testBuildFocusOpenAntigravityEmpty(): void {
  assert(buildFocusOpenCommands("antigravity", []).length === 0, "no auto-open ladder");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("antigravity").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenAntigravityEmpty();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
