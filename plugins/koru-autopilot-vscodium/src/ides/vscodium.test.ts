import { getStrategy } from "./registry";
import { detectIdeViaStrategies } from "./registry";
import {
  buildHostKeySubmitCandidates,
  buildFocusOpenCommands,
  buildSubmitCommands,
  sanitizeProbeCacheForIde,
  PROBE_CACHE_VERSION,
  verifyFocusAfterOpen,
} from "../probe-ladder";
import { captureEditorSnapshot } from "../probe-ladder";
import { filterUnsafeFocusOpenForIde } from "../_shared/bridge-helpers";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(`vscodium-strategy test failed: ${message}`);
}

function testRegistered() {
  assert(getStrategy("vscodium")?.id === "vscodium", "vscodium strategy registered");
}

function testDetectIdeFromHostNameVariants() {
  assert(detectIdeViaStrategies("VSCodium") === "vscodium", "detects VSCodium host name");
  assert(detectIdeViaStrategies("Codium") === "vscodium", "detects Codium host name");
  assert(detectIdeViaStrategies("Code - OSS") === "vscodium", "detects Code - OSS host name");
  assert(detectIdeViaStrategies("") === "vscodium", "detects empty host name as VSCodium runtime");
}

function testPreferCtrlSubmit() {
  const host = buildHostKeySubmitCandidates("vscodium", "auto", { XDG_SESSION_TYPE: "wayland" });
  assert(
    host[0]?.[1]?.some((a) => /ctrl/i.test(a)),
    "vscodium host-key ladder prefers ctrl first",
  );
}

function testSubmitSanitize() {
  const entry = sanitizeProbeCacheForIde(
    {
      version: PROBE_CACHE_VERSION,
      ide: "vscodium",
      appName: "VSCodium",
      submit: "workbench.action.chat.submit",
      updatedAt: "",
    },
    "vscodium",
  );
  assert(entry?.submit === "workbench.action.chat.submit", "registered chat submit retained");
}

function testTrustFocusOpen() {
  const file = captureEditorSnapshot(undefined);
  assert(verifyFocusAfterOpen(file, file, "vscodium"), "vscodium trusts focus open");
}

function testSubmitCommandsTryRegisteredSubmitFirst() {
  const cmds = buildSubmitCommands("vscodium");
  assert(cmds[0] === "workbench.action.chat.submit", "vscodium tries native chat submit first");
}

function testFocusOpenAvoidsPanelOpenCommands() {
  const cmds = buildFocusOpenCommands("vscodium", []);
  assert(cmds[0] === "workbench.action.chat.focusInput", "vscodium focuses existing chat input first");
  assert(!cmds.includes("workbench.panel.chat"), "vscodium must not use workbench.panel.chat as default focus_open");
  assert(!cmds.includes("workbench.action.openChat"), "vscodium must not use openChat as default focus_open");
}

function testFocusOpenFiltersQuickChatCommands() {
  const cmds = filterUnsafeFocusOpenForIde(
    [
      "workbench.action.openQuickChat",
      "workbench.action.quickchat.openInChatView",
      "workbench.action.chat.openInNewWindow",
      "workbench.action.chat.focusInput",
    ],
    "vscodium",
  );
  assert(
    cmds.length === 1 && cmds[0] === "workbench.action.chat.focusInput",
    "vscodium must not run QuickChat/new-window focus_open commands",
  );
}

function run() {
  testRegistered();
  testDetectIdeFromHostNameVariants();
  testPreferCtrlSubmit();
  testSubmitSanitize();
  testTrustFocusOpen();
  testSubmitCommandsTryRegisteredSubmitFirst();
  testFocusOpenAvoidsPanelOpenCommands();
  testFocusOpenFiltersQuickChatCommands();
  console.log("vscodium-strategy tests: ok");
}

run();
