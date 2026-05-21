import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildSubmitCommands,
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

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenCursorFirst();
testBuildFocusOpenVscodeDoesNotAutoOpenChatByDefault();
testBuildFocusInputUsesChatCommands();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
testVscodiumSubmitStillExposesWorkbenchFallback();
console.log("probe-ladder tests: ok");
