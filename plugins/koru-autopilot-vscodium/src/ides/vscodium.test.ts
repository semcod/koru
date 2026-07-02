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

function testFocusOpenSanitizeRejectsSettings() {
  const entry = sanitizeProbeCacheForIde(
    {
      version: PROBE_CACHE_VERSION,
      ide: "vscodium",
      appName: "VSCodium",
      focusOpen: "workbench.action.chat.openChatEmptyStateSettings",
      updatedAt: "",
    },
    "vscodium",
  );
  assert(entry?.focusOpen === undefined, "settings focus_open cache must be cleared");
}

function testFocusOpenSanitizeRejectsNewChat() {
  const entry = sanitizeProbeCacheForIde(
    {
      version: PROBE_CACHE_VERSION,
      ide: "vscodium",
      appName: "VSCodium",
      focusOpen: "aichat.newchataction",
      updatedAt: "",
    },
    "vscodium",
  );
  assert(entry?.focusOpen === undefined, "new-chat focus_open cache must be cleared");
}

function testTrustFocusOpen() {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  assert(!verifyFocusAfterOpen(file, file, "vscodium"), "vscodium does not trust unchanged focus snapshot");
}

function testSubmitCommandsTryRegisteredSubmitFirst() {
  const cmds = buildSubmitCommands("vscodium");
  assert(cmds[0] === "workbench.action.chat.submit", "vscodium tries native chat submit first");
}

function testFocusOpenAvoidsPanelOpenCommands() {
  const cmds = buildFocusOpenCommands("vscodium", []);
  assert(cmds[0] === "chatgpt.sidebarView.open", "vscodium opens ChatGPT sidebar first");
  assert(!cmds.includes("workbench.action.chat.focusInput"), "vscodium must not use focusInput as focus_open");
  assert(cmds.includes("workbench.panel.chat"), "vscodium may open the chat panel after ChatGPT sidebar candidates");
  assert(!cmds.includes("workbench.action.openChat"), "vscodium must not use openChat as default focus_open");
}

function testFocusOpenFiltersQuickChatCommands() {
  const cmds = filterUnsafeFocusOpenForIde(
    [
      "workbench.action.openQuickChat",
      "workbench.action.quickchat.openInChatView",
      "workbench.action.chat.openNewChatToTheSide",
      "workbench.action.chat.openInNewWindow",
      "workbench.action.chat.openChatEmptyStateSettings",
      "workbench.action.chat.focusInput",
      "chatgpt.sidebarView.open",
      "workbench.panel.chat",
    ],
    "vscodium",
  );
  assert(
    cmds.join(",") === "chatgpt.sidebarView.open,workbench.panel.chat",
    "vscodium must only keep reusable chat open/focus commands",
  );
}

function run() {
  testRegistered();
  testDetectIdeFromHostNameVariants();
  testPreferCtrlSubmit();
  testSubmitSanitize();
  testFocusOpenSanitizeRejectsSettings();
  testFocusOpenSanitizeRejectsNewChat();
  testTrustFocusOpen();
  testSubmitCommandsTryRegisteredSubmitFirst();
  testFocusOpenAvoidsPanelOpenCommands();
  testFocusOpenFiltersQuickChatCommands();
  console.log("vscodium-strategy tests: ok");
}

run();
