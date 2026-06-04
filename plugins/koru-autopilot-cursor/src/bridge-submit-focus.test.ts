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
  bridge.probeChatInputContents = async () => null;
  bridge.submitChat = async () => {
    submitCalls += 1;
    return { ok: true, command: "workbench.action.chat.submit" };
  };

  const result = await bridge.submitAfterPaste(
    { type: "chat.send", id: "drive-1" },
    { ok: true, command: "composer.openComposer" },
    { ok: true, command: "workbench.action.chat.typeText" },
    true,
    "Ticket STARTER-999\nimplement the requested change",
  );

  assert.strictEqual(result, null);
  assert.strictEqual(submitCalls, 0, "submitChat must not run without confirmed Cursor input focus");
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

async function testRegisteredSubmitBlocksWhenProbeReadsEmptyAfterShortPaste(): Promise<void> {
  const { bridge, runCommands } = makeBridge();
  bridge.probeLadderEnabled = () => true;
  bridge.focusChatInput = async () => ({
    ok: true,
    command: "glass.focusInput",
  });
  bridge.probeChatInputContents = async () => "";

  const result = await bridge._tryRegisteredCommands(
    ["workbench.action.chat.stopListeningAndSubmit"],
    "probe test",
    true,
  );

  assert.strictEqual(result?.unverified, true);
  assert.strictEqual(result?.command, "cursor-submit-focus-unavailable");
  assert.deepStrictEqual(runCommands, [], "empty pre-submit probe must block submit on Cursor");
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
  assert.deepStrictEqual(runCommands, ["workbench.action.chat.submit"]);
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
  await testRegisteredSubmitBlocksWhenProbeReadsEmptyAfterShortPaste();
  await testRegisteredSubmitBlocksWhenProbeShowsTinySnippetForLongPrompt();
  await testRegisteredSubmitTrustsFocusWhenProbeMismatch();
  await testRegisteredSubmitTrustsFocusWhenWebviewProbeUnreadable();
  await testRegisteredSubmitAllowsProbeConfirmedCursorInput();
  await testCursorFastPathDoesNotTrustMissingBubbleDbWithInconclusiveProbe();
  await testCursorHostClickFallbackRequiresCalibratedPoint();
  console.log("bridge-submit-focus tests: ok");
}

void run().catch((err) => {
  console.error(err);
  process.exit(1);
});
