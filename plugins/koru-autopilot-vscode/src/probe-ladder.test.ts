import {
  buildFocusOpenCommands,
  captureEditorSnapshot,
  chatFocusHeuristic,
  mergeUnique,
  orderWithCache,
  pasteLandedInEditor,
  verifyFocusAfterOpen,
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

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenCursorFirst();
console.log("probe-ladder tests: ok");
