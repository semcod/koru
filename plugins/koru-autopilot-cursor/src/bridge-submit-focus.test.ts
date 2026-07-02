import * as assert from "assert";
import Module = require("module");

type AnyBridge = Record<string, any>;

const registeredCommands = new Set<string>([
  "workbench.action.chat.focusInput",
  "workbench.action.chat.submit",
  "workbench.action.chat.typeText",
]);
const executedCommands: string[] = [];
const configValues = new Map<string, unknown>();

function getConfigValue<T>(key: string, fallback?: T): T {
  return (configValues.has(key) ? configValues.get(key) : fallback) as T;
}

const fakeVscode = {
  StatusBarAlignment: { Right: 2 },
  commands: {
    getCommands: async () => Array.from(registeredCommands),
    executeCommand: async (command: string, ..._args: unknown[]) => {
      executedCommands.push(command);
      return true;
    },
  },
  env: {
    appName: "Cursor",
    clipboard: {
      readText: async () => "",
      writeText: async (_text: string) => undefined,
    },
  },
  extensions: {
    getExtension: (_id: string) => ({
      packageJSON: {
        version: "test",
        koruAutopilotBuild: { sha: "test" },
      },
    }),
  },
  window: {
    activeTextEditor: undefined,
    createStatusBarItem: () => ({
      command: "",
      show: () => undefined,
      text: "",
      tooltip: "",
    }),
    showWarningMessage: async (_message: string) => undefined,
    tabGroups: {
      activeTabGroup: {
        activeTab: { label: "" },
      },
    },
  },
  workspace: {
    name: "test-workspace",
    workspaceFolders: [],
    getConfiguration: (_section: string) => ({
      get: getConfigValue,
    }),
  },
};

const moduleAny = Module as any;
const originalLoad = moduleAny._load;
moduleAny._load = function loadWithVscodeStub(
  this: unknown,
  request: string,
  ...args: unknown[]
): unknown {
  if (request === "vscode") {
    return fakeVscode;
  }
  return originalLoad.call(this, request, ...args);
};

const { SharedAutopilotBridge } = require("./_shared/autopilot-bridge") as {
  SharedAutopilotBridge: new (context: any, options: any) => AnyBridge;
};

function makeBridge(): { bridge: AnyBridge; sent: any[]; runCommands: string[] } {
  executedCommands.length = 0;
  configValues.clear();
  const sent: any[] = [];
  const runCommands: string[] = [];
  const context = {
    subscriptions: [],
    globalState: {
      get: <T>(_key: string, fallback?: T) => fallback,
      update: async (_key: string, _value: unknown) => undefined,
    },
  };
  const bridge = new SharedAutopilotBridge(context, {
    extensionPackageId: "semcod.koru-autopilot-cursor",
    enableCursorComposerFastPath: true,
  });
  bridge.captureCursorBubbleAnchor = async () => undefined;
  bridge.emitLiveDsl = (_step: unknown) => undefined;
  bridge.probeFocusDelayMs = () => 0;
  bridge.probeLadderEnabled = () => false;
  bridge.probePasteDelayMs = () => 0;
  bridge.runCommand = async (command: string) => {
    runCommands.push(command);
    return true;
  };
  bridge.send = (env: any) => {
    sent.push(env);
  };
  bridge.sleep = async (_ms: number) => undefined;
  return { bridge, sent, runCommands };
}

async function testSubmitAfterPasteFailsBeforeSubmitWhenCursorFocusUnconfirmed(): Promise<void> {
  const { bridge, sent } = makeBridge();
  let submitCalls = 0;
  bridge.focusChatInput = async () => ({
    ok: false,
    command: "workbench.action.chat.focusInput",
  });
  bridge.cursorRecoverGlassChatFocus = async () => ({
    ok: false,
    reason: "mock recovery exhausted",
  });
  bridge.probeChatInputContents = async () => null;
  bridge.submitChat = async () => {
    submitCalls += 1;
    return { ok: true, command: "workbench.action.chat.submit" };
  };

  const result = await bridge.submitAfterPaste(
    { type: "chat.send", id: "drive-1" },
    { ok: true, command: "composer.openComposer" },
    { ok: true, command: "workbench.action.chat.insertText" },
    true,
    "Ticket STARTER-999\nimplement the requested change",
  );

  assert.strictEqual(result, null);
  assert.strictEqual(submitCalls, 0, "submitChat must not run without confirmed Cursor input focus (non-composer direct paste)");
  assert.strictEqual(sent.length, 1);
  assert.strictEqual(sent[0].verification, "submit_unverified");
  assert.strictEqual(sent[0].attempted_submit, "cursor-submit-focus-unavailable");
}

async function testRegisteredSubmitFailsClosedWhenCursorFocusUnconfirmed(): Promise<void> {
  const { bridge, runCommands } = makeBridge();
  bridge.focusChatInput = async () => ({
    ok: false,
    command: "workbench.action.chat.focusInput",
  });
  bridge.cursorRecoverGlassChatFocus = async () => ({
    ok: false,
    reason: "mock recovery exhausted",
  });
  bridge.probeChatInputContents = async () => null;

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.submit"],
    "Ticket STARTER-999\nsubmit this prompt",
    false,
  );

  assert.strictEqual(result?.unverified, true);
  assert.strictEqual(result?.command, "cursor-submit-focus-unavailable");
  assert.deepStrictEqual(runCommands, [], "registered submit command must not run when focus is unconfirmed");
}

async function testRegisteredSubmitTrustsGlassFocusWhenProbeEmptyOnShortPaste(): Promise<void> {
  const { bridge, runCommands } = makeBridge();
  bridge.probeLadderEnabled = () => true;
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "glass.focusInput",
  });
  bridge.probeChatInputContents = async () => "";
  bridge.submitChat = async () => ({
    ok: true,
    command: "workbench.action.chat.stopListeningAndSubmit",
  });

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.stopListeningAndSubmit"],
    "probe test",
    true,
  );

  assert.strictEqual(result?.ok, true);
  assert.strictEqual(result?.command, "workbench.action.chat.stopListeningAndSubmit");
  assert.deepStrictEqual(
    runCommands,
    ["workbench.action.chat.stopListeningAndSubmit"],
    "Glass focus + unreadable probe should still allow registered submit",
  );
}

async function testRegisteredSubmitBlocksWhenProbeShowsTinySnippetForLongPrompt(): Promise<void> {
  const prompt = `${"Ticket STARTER-470\n".repeat(4)}${"implement the requested change. ".repeat(40)}`;
  const { bridge, runCommands } = makeBridge();
  bridge.probeLadderEnabled = () => true;
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "workbench.action.chat.focusInput",
  });
  bridge.probeChatInputContents = async () => "unrelated editor selection";

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.stopListeningAndSubmit"],
    prompt,
    true,
  );

  assert.strictEqual(result?.unverified, true);
  assert.strictEqual(result?.command, "cursor-submit-focus-unavailable");
  assert.deepStrictEqual(runCommands, [], "must not submit when probe reads a short unrelated snippet");
}

async function testRegisteredSubmitTrustsFocusWhenProbeMismatch(): Promise<void> {
  const { bridge, runCommands } = makeBridge();
  bridge.probeLadderEnabled = () => true;
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "workbench.action.chat.focusInput",
  });
  bridge.probeChatInputContents = async () => "unrelated editor selection";

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.submit"],
    "Ticket STARTER-999\nsubmit this prompt",
    false,
  );

  assert.strictEqual(result?.ok, true);
  assert.strictEqual(result?.command, "workbench.action.chat.submit");
  assert.deepStrictEqual(
    runCommands,
    ["workbench.action.chat.submit"],
    "select-copy probes often read the file editor; trust focus command when refocus succeeded",
  );
}

async function testRegisteredSubmitTrustsFocusWhenWebviewProbeUnreadable(): Promise<void> {
  const { bridge, runCommands } = makeBridge();
  bridge.probeLadderEnabled = () => true;
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "workbench.action.chat.focusInput",
  });
  bridge.probeChatInputContents = async () => null;

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.submit"],
    "Ticket STARTER-999\nsubmit this prompt",
    false,
  );

  assert.strictEqual(result?.ok, true);
  assert.strictEqual(result?.command, "workbench.action.chat.submit");
  assert.deepStrictEqual(
    runCommands,
    ["workbench.action.chat.submit"],
    "Cursor chat webviews often fail select-copy probes; trust focus command when probe is unreadable",
  );
}

async function testSubmitAfterPasteAllowsTypedPasteWhenProbeNullAfterGlassRecover(): Promise<void> {
  const { bridge, sent } = makeBridge();
  let submitCalls = 0;
  bridge.focusChatInput = async () => ({ ok: false });
  bridge.cursorRecoverGlassChatFocus = async () => ({
    ok: true,
    command: "glass.focusInput",
  });
  bridge.probeChatInputContents = async () => null;
  bridge.submitChat = async () => {
    submitCalls += 1;
    return { ok: true, command: "workbench.action.chat.stopListeningAndSubmit" };
  };

  const result = await bridge.submitAfterPaste(
    { type: "chat.send", id: "drive-typed-null" },
    { ok: true, command: "workbench.action.chat.open" },
    { ok: true, command: "type" },
    true,
    "probe test",
  );

  assert.strictEqual(result, "workbench.action.chat.stopListeningAndSubmit");
  assert.strictEqual(submitCalls, 1);
  assert.strictEqual(sent.length, 0);
}

async function testSubmitAfterPasteBlocksTypedPasteWhenGlassRecoverFails(): Promise<void> {
  const { bridge, sent } = makeBridge();
  bridge.focusChatInput = async () => ({ ok: false });
  bridge.cursorRecoverGlassChatFocus = async () => ({ ok: false, reason: "mock exhausted" });
  bridge.probeChatInputContents = async () => null;

  const result = await bridge.submitAfterPaste(
    { type: "chat.send", id: "drive-typed-blocked" },
    { ok: true, command: "workbench.action.chat.open" },
    { ok: true, command: "type" },
    true,
    "probe test",
  );

  assert.strictEqual(result, null);
  assert.strictEqual(sent.length, 1);
  assert.strictEqual(sent[0].verification, "submit_unverified");
}

async function testSubmitAfterPasteAllowsTypedPasteWhenProbeUnreadable(): Promise<void> {
  const { bridge, sent, runCommands } = makeBridge();
  let submitCalls = 0;
  bridge.focusChatInput = async () => ({ ok: false });
  bridge.cursorRecoverGlassChatFocus = async () => ({
    ok: true,
    command: "glass.focusInput",
  });
  bridge.probeChatInputContents = async () => "";
  bridge.submitChat = async () => {
    submitCalls += 1;
    return { ok: true, command: "workbench.action.chat.stopListeningAndSubmit" };
  };

  const result = await bridge.submitAfterPaste(
    { type: "chat.send", id: "drive-typed" },
    { ok: true, command: "workbench.action.chat.open" },
    { ok: true, command: "type" },
    true,
    "probe test",
  );

  assert.strictEqual(result, "workbench.action.chat.stopListeningAndSubmit");
  assert.strictEqual(submitCalls, 1);
  assert.strictEqual(sent.length, 0, "typed paste with empty probe should not emit submit_unverified");
}

async function testRegisteredSubmitAllowsProbeConfirmedCursorInput(): Promise<void> {
  const prompt = "Ticket STARTER-999\nsubmit this exact prompt";
  const { bridge, runCommands } = makeBridge();
  bridge.focusChatInput = async () => ({
    ok: false,
    command: "workbench.action.chat.focusInput",
  });
  bridge.probeChatInputContents = async () => prompt;

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.submit"],
    prompt,
    false,
  );

  assert.strictEqual(result?.ok, true);
  assert.strictEqual(result?.command, "workbench.action.chat.submit");
  assert.deepStrictEqual(runCommands, [
    "glass.focusInput",
    "workbench.action.chat.submit",
  ]);
}

async function testCursorFastPathDoesNotTrustMissingBubbleDbWithInconclusiveProbe(): Promise<void> {
  const prompt = "Ticket STARTER-999\nsubmit this exact prompt";
  const { bridge, sent, runCommands } = makeBridge();
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "workbench.action.chat.focusInput",
  });
  bridge.probeChatInputContents = async () => null;
  bridge._verifySubmitViaCursorBubble = async () => null;

  const result = await bridge._runCursorComposerFastPathPaste(
    { type: "chat.send", id: "drive-fast" },
    prompt,
    true,
    "workbench.action.chat.typeText",
    ["workbench.action.chat.submit"],
  );

  assert.strictEqual(result, false);
  assert.deepStrictEqual(executedCommands, ["workbench.action.chat.typeText"]);
  assert.deepStrictEqual(runCommands, ["workbench.action.chat.submit"]);
  assert.strictEqual(sent.length, 0, "fast path must not ack success without submit proof");
}

async function testGlassUiFastPathUsesStartComposerPromptWhenTypeTextMissing(): Promise<void> {
  registeredCommands.clear();
  for (const cmd of [
    "glass.focusInput",
    "composer.startComposerPrompt2",
    "composer.startComposerPrompt",
    "workbench.action.chat.stopListeningAndSubmit",
  ]) {
    registeredCommands.add(cmd);
  }
  executedCommands.length = 0;

  const prompt = "probe test";
  const { bridge, sent, runCommands } = makeBridge();
  bridge._verifySubmitViaCursorBubble = async () => ({
    matched: true,
    newUserBubbles: 1,
  });

  const handled = await bridge.tryCursorComposerPromptFastPath(
    { type: "chat.send", id: "drive-glass" },
    prompt,
    true,
  );

  assert.strictEqual(
    handled,
    false,
    "Glass UI with submit must defer to probe ladder for verified submit",
  );
  assert.strictEqual(executedCommands.length, 0);
  assert.strictEqual(sent.length, 0);
}

async function testGlassUiFastPathPrefersComposerPromptEvenWhenTypeTextRegistered(): Promise<void> {
  registeredCommands.clear();
  for (const cmd of [
    "glass.focusInput",
    "workbench.action.chat.typeText",
    "workbench.action.chat.stopListeningAndSubmit",
    "composer.startComposerPrompt2",
  ]) {
    registeredCommands.add(cmd);
  }
  executedCommands.length = 0;

  const { bridge, sent } = makeBridge();
  bridge._verifySubmitViaCursorBubble = async () => ({
    matched: true,
    newUserBubbles: 1,
  });
  const handled = await bridge.tryCursorComposerPromptFastPath(
    { type: "chat.send", id: "drive-modern" },
    "probe test",
    true,
  );

  assert.strictEqual(
    handled,
    false,
    "Glass with submit must defer to probe ladder even when typeText is registered",
  );
  assert.strictEqual(executedCommands.length, 0);
}

async function testGlassUiFastPathUsesOptimisticComposerPromptWhenHiddenFromGetCommands(): Promise<void> {
  registeredCommands.clear();
  for (const cmd of [
    "glass.focusInput",
    "workbench.action.chat.stopListeningAndSubmit",
    "workbench.action.chat.typeText",
  ]) {
    registeredCommands.add(cmd);
  }
  executedCommands.length = 0;

  const { bridge, sent } = makeBridge();
  bridge._verifySubmitViaCursorBubble = async () => ({
    matched: true,
    newUserBubbles: 1,
  });
  const handled = await bridge.tryCursorComposerPromptFastPath(
    { type: "chat.send", id: "drive-glass-hidden" },
    "probe test",
    true,
  );

  assert.strictEqual(
    handled,
    false,
    "Glass UI with submit must defer to probe ladder even when composer prompt is hidden",
  );
  assert.strictEqual(executedCommands.length, 0);
}

async function testGlassUiFastPathPasteOnlyDefersToProbeLadder(): Promise<void> {
  registeredCommands.clear();
  for (const cmd of [
    "glass.focusInput",
    "workbench.action.chat.stopListeningAndSubmit",
    "composer.startComposerPrompt2",
  ]) {
    registeredCommands.add(cmd);
  }
  executedCommands.length = 0;

  const { bridge, sent } = makeBridge();
  const handled = await bridge.tryCursorComposerPromptFastPath(
    { type: "chat.send", id: "drive-glass-paste" },
    "probe test",
    false,
  );

  assert.strictEqual(
    handled,
    false,
    "Glass UI paste-only must defer to probe ladder to avoid opening new Composer windows",
  );
  assert.strictEqual(executedCommands.length, 0);
  assert.strictEqual(sent.length, 0);
}

async function testComposerPromptPasteBypassesGlassFocusBeforeSubmit(): Promise<void> {
  const { bridge } = makeBridge();
  let focusCalls = 0;
  bridge.focusChatInput = async () => {
    focusCalls += 1;
    return { ok: false, command: "glass.focusInput" };
  };

  const result = await bridge.confirmCursorChatInputBeforeSubmit(
    "probe test",
    "cursor-composer-fastpath:submit:test:focus",
    "composer.startComposerPrompt2",
  );

  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.command, "composer.startComposerPrompt2");
  assert.strictEqual(focusCalls, 0, "composer prompt paste should not require glass.focusInput recovery");
}

async function testCursorHostClickFallbackRequiresCalibratedPoint(): Promise<void> {
  const { bridge } = makeBridge();
  const optionsSeen: unknown[] = [];
  bridge._tryHostClickSubmit = async (options: unknown = {}) => {
    optionsSeen.push(options);
    return { ok: false, reason: "missing calibrated submit click coordinates" };
  };
  bridge._tryVerifiedHostKeySubmit = async () => ({
    ok: false,
    reason: "host-key unavailable",
  });
  bridge.koruStepConfig = () => ({
    probeLadder: false,
    verifySubmit: false,
    skipWhenInputBusy: true,
  });

  const result = await bridge._submitChatCursorVSCodeFallback("cursor", "Ticket STARTER-999", false);

  assert.deepStrictEqual(optionsSeen, [{}]);
  assert.strictEqual(result?.command, "cursor-submit-unavailable");
}

async function run(): Promise<void> {
  await testSubmitAfterPasteFailsBeforeSubmitWhenCursorFocusUnconfirmed();
  await testRegisteredSubmitFailsClosedWhenCursorFocusUnconfirmed();
  await testRegisteredSubmitTrustsGlassFocusWhenProbeEmptyOnShortPaste();
  await testRegisteredSubmitBlocksWhenProbeShowsTinySnippetForLongPrompt();
  await testRegisteredSubmitTrustsFocusWhenProbeMismatch();
  await testRegisteredSubmitTrustsFocusWhenWebviewProbeUnreadable();
  await testSubmitAfterPasteAllowsTypedPasteWhenProbeNullAfterGlassRecover();
  await testSubmitAfterPasteBlocksTypedPasteWhenGlassRecoverFails();
  await testSubmitAfterPasteAllowsTypedPasteWhenProbeUnreadable();
  await testRegisteredSubmitAllowsProbeConfirmedCursorInput();
  await testCursorFastPathDoesNotTrustMissingBubbleDbWithInconclusiveProbe();
  await testGlassUiFastPathUsesStartComposerPromptWhenTypeTextMissing();
  await testGlassUiFastPathPrefersComposerPromptEvenWhenTypeTextRegistered();
  await testGlassUiFastPathUsesOptimisticComposerPromptWhenHiddenFromGetCommands();
  await testGlassUiFastPathPasteOnlyDefersToProbeLadder();
  await testComposerPromptPasteBypassesGlassFocusBeforeSubmit();
  await testCursorHostClickFallbackRequiresCalibratedPoint();
  console.log("bridge-submit-focus tests: ok");
}

void run().catch((err) => {
  console.error(err);
  process.exit(1);
});
