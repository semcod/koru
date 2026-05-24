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
  assert(entry?.submit === undefined, "workbench.action.chat.submit cleared");
}

function testTrustFocusOpen() {
  const file = captureEditorSnapshot(undefined);
  assert(verifyFocusAfterOpen(file, file, "vscodium"), "vscodium trusts focus open");
}

function testSubmitCommandsGenericFallback() {
  const cmds = buildSubmitCommands("vscodium");
  assert(cmds.includes("workbench.action.chat.submit"), "generic submit fallback kept");
}

function run() {
  testRegistered();
  testPreferCtrlSubmit();
  testSubmitSanitize();
  testTrustFocusOpen();
  testSubmitCommandsGenericFallback();
  console.log("vscodium-strategy tests: ok");
}

run();
