import { classifyCommand, classifyCommands } from "./command-catalog";

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(
      `command-catalog test failed: ${message}; expected ${expected}, got ${actual}`,
    );
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, message: string): void {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(
      `command-catalog test failed: ${message}; expected ${expectedJson}, got ${actualJson}`,
    );
  }
}

function testClassifiesCursorSubmitAndPaste(): void {
  assertEqual(classifyCommand("composer.sendToAgent"), "submit", "Cursor submit");
  assertEqual(classifyCommand("composer.startComposerPrompt2"), "paste", "Cursor paste");
  assertEqual(classifyCommand("workbench.action.chat.submit"), "submit", "VS Code submit");
}

function testClassifiesFocusOpenVsInput(): void {
  assertEqual(classifyCommand("composer.openComposer"), "focus_open", "Composer open");
  assertEqual(classifyCommand("composer.focusComposer"), "focus_input", "Composer focus");
}

function testClassifiesUnknownChatHints(): void {
  assertEqual(classifyCommand("cursor.chat.experimentalFoo"), "unknown_chat", "chat hint");
  assertEqual(classifyCommand("workbench.files.save"), null, "non-chat command");
}

function testClassifyCommandsDeduplicatesAndSorts(): void {
  const catalog = classifyCommands([
    "composer.sendToAgent",
    "workbench.action.chat.submit",
    "composer.sendToAgent",
    "composer.openComposer",
  ]);
  assertDeepEqual(
    catalog.submit,
    ["composer.sendToAgent", "workbench.action.chat.submit"],
    "submit bucket",
  );
  assertDeepEqual(catalog.focus_open, ["composer.openComposer"], "focus_open bucket");
}

testClassifiesCursorSubmitAndPaste();
testClassifiesFocusOpenVsInput();
testClassifiesUnknownChatHints();
testClassifyCommandsDeduplicatesAndSorts();
