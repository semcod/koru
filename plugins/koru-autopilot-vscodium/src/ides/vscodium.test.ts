import { getStrategy } from "./registry";
import {
  buildHostKeySubmitCandidates,
  buildSubmitCommands,
  sanitizeProbeCacheForIde,
  PROBE_CACHE_VERSION,
  verifyFocusAfterOpen,
} from "../probe-ladder";
import { captureEditorSnapshot } from "../probe-ladder";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(`vscodium-strategy test failed: ${message}`);
}

function testRegistered() {
  assert(getStrategy("vscodium")?.id === "vscodium", "vscodium strategy registered");
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

function run() {
  testRegistered();
  testPreferCtrlSubmit();
  testSubmitSanitize();
  testTrustFocusOpen();
  testSubmitCommandsTryRegisteredSubmitFirst();
  console.log("vscodium-strategy tests: ok");
}

run();
