import { classifyCommand, classifyCommands } from "./command-catalog";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`command-catalog test failed: ${message}`);
  }
}

function testClassifiesCursorSubmitAndPaste(): void {
  assert(classifyCommand("composer.sendToAgent") === "submit", "composer.sendToAgent → submit");
  assert(classifyCommand("composer.startComposerPrompt2") === "paste", "startComposerPrompt2 → paste");
  assert(classifyCommand("workbench.action.chat.submit") === "submit", "chat.submit → submit");
}

function testFocusOpenVsInput(): void {
  assert(classifyCommand("composer.openComposer") === "focus_open", "openComposer → focus_open");
  assert(classifyCommand("composer.focusComposer") === "focus_input", "focusComposer → focus_input");
  assert(
    classifyCommand("chatgpt.sidebarView.open") === "focus_open",
    "ChatGPT sidebar open → focus_open",
  );
  assert(
    classifyCommand("chatgpt.sidebarView.focus") === "focus_input",
    "ChatGPT sidebar focus → focus_input",
  );
}

function testSettingsCommandsAreNotFocusOpen(): void {
  assert(
    classifyCommand("workbench.action.chat.openChatEmptyStateSettings") === "window",
    "chat empty-state settings must not be focus_open",
  );
}

function testUnknownChatBucket(): void {
  assert(
    classifyCommand("cursor.chat.experimentalFoo") === "unknown_chat",
    "unknown chat hint → unknown_chat",
  );
  assert(classifyCommand("workbench.files.save") === null, "non-chat → null");
}

function testClassifyCommandsDeduplicates(): void {
  const catalog = classifyCommands([
    "composer.sendToAgent",
    "workbench.action.chat.submit",
    "composer.sendToAgent",
    "composer.openComposer",
  ]);
  assert(catalog.submit.length === 2, "submit dedup: expected 2, got " + catalog.submit.length);
  assert(
    catalog.submit.includes("composer.sendToAgent"),
    "submit must include composer.sendToAgent",
  );
  assert(
    catalog.submit.includes("workbench.action.chat.submit"),
    "submit must include workbench.action.chat.submit",
  );
  assert(catalog.focus_open.length === 1, "focus_open dedup: expected 1");
  assert(catalog.focus_open[0] === "composer.openComposer", "focus_open[0]");
}

testClassifiesCursorSubmitAndPaste();
testFocusOpenVsInput();
testSettingsCommandsAreNotFocusOpen();
testUnknownChatBucket();
testClassifyCommandsDeduplicates();

console.log("command-catalog: all tests passed");
