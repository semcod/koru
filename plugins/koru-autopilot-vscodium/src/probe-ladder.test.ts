/**
 * vscodium-only probe-ladder regression tests.
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
  prioritizePlainHostKeySubmitCandidates,
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
  assert(verifyFocusAfterOpen(file, file, "vscodium"), "vscodium may trust unchanged snapshot");
}

function testHostKeyOrderVscodiumPrefersCtrlReturn(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  assert(firstKey(cands).includes("ctrl"), "VSCodium tries Ctrl+Return first");
}

function testPlainHostKeyPrioritizerPreservesRows(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  const prioritized = prioritizePlainHostKeySubmitCandidates(cands);
  assert(!firstKey(prioritized).includes("ctrl"), "plain Return can be promoted for focused webviews");
  assert(prioritized.length === cands.length, "prioritizer keeps all host-key candidates");
}

function testBuildFocusInputUsesChatCommands(): void {
  assert(buildFocusInputCommands("vscodium")[0] === "workbench.action.chat.focusInput", "focus input first");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testHostKeyOrderVscodiumPrefersCtrlReturn();
testPlainHostKeyPrioritizerPreservesRows();
testBuildFocusInputUsesChatCommands();
