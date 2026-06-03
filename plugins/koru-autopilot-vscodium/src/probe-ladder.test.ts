/**
 * vscodium-only probe-ladder regression tests.
 */

import {
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildHostKeySubmitCandidates,
  buildSubmitCommands,
  chatFocusHeuristic,
  decideSubmitCleared,
  mergeUnique,
  orderWithCache,
  pasteLandedInEditor,
  prioritizePlainHostKeySubmitCandidates,
  sanitizeProbeCacheForIde,
  verifyFocusAfterOpen,
  PROBE_CACHE_VERSION,
} from "./probe-ladder";

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(`probe-ladder test failed: ${message}`);
}

function testOrderWithCache(): void {
  assert(orderWithCache(["a", "b", "c"], "b")[0] === "b", "cached first");
}

function testChatFocusHeuristic(): void {
  assert(chatFocusHeuristic({ hasEditor: false, scheme: "", isFileLike: false, text: "" }), "no editor");
  assert(!chatFocusHeuristic({ hasEditor: true, scheme: "file", isFileLike: true, text: "x" }), "file editor");
}

function testPasteLandedInEditor(): void {
  const before = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello" };
  const after = { hasEditor: true, scheme: "file", isFileLike: true, text: "hello __koru_probe__" };
  assert(pasteLandedInEditor(before, after, "__koru_probe__"), "paste in editor");
}

function testMergeUnique(): void {
  assert(mergeUnique(["a", "b"], ["b", "c"]).join() === "a,b,c", "dedupe");
}

function firstKey(cands: ReadonlyArray<[string, string[]]>): string {
  const [cmd, args] = cands[0];
  return `${cmd} ${args.join(" ")}`;
}

const WAYLAND_ENV = { XDG_SESSION_TYPE: "wayland", WAYLAND_DISPLAY: "wayland-0" };
const X11_ENV = { XDG_SESSION_TYPE: "x11" };

function testVerifyFocusAfterOpen(): void {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  assert(!verifyFocusAfterOpen(file, file, "vscodium"), "VSCodium rejects unchanged file snapshot");
}

function testHostKeyOrderVscodiumPrefersCtrlReturn(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  assert(firstKey(cands).includes("ctrl"), "VSCodium tries Ctrl+Return first");
}

function testPlainHostKeyPrioritizerPreservesRows(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  const prioritized = prioritizePlainHostKeySubmitCandidates(cands);
  assert(!firstKey(prioritized).includes("ctrl"), "plain Return can be promoted for focused webviews");
  assert(prioritized.length === cands.length, "prioritizer keeps all host-key candidates");
}

function testHostKeyOrderVscodiumWaylandPrefersYdotoolBeforeXdotool(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  const rendered = cands.map(([cmd, args]) => `${cmd} ${args.join(" ")}`);
  assert(
    rendered.indexOf("ydotool key ctrl+Return") < rendered.indexOf("xdotool key ctrl+Return"),
    "VSCodium tries ydotool before xdotool for Ctrl+Return on Wayland",
  );
  assert(
    rendered.indexOf("ydotool key Return") < rendered.indexOf("xdotool key Return"),
    "VSCodium tries ydotool before xdotool for Return on Wayland",
  );
}

function testHostKeyOrderVscodiumX11PrefersXdotoolBeforeYdotool(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", X11_ENV);
  const rendered = cands.map(([cmd, args]) => `${cmd} ${args.join(" ")}`);
  assert(
    rendered.indexOf("xdotool key ctrl+Return") < rendered.indexOf("ydotool key ctrl+Return"),
    "VSCodium tries xdotool before ydotool for Ctrl+Return on X11",
  );
  assert(
    rendered.indexOf("xdotool key Return") < rendered.indexOf("ydotool key Return"),
    "VSCodium tries xdotool before ydotool for Return on X11",
  );
}

function testBuildFocusInputUsesChatCommands(): void {
  const commands = buildFocusInputCommands("vscodium");
  assert(commands[0] === "chatgpt.sidebarView.focus", "ChatGPT sidebar focus first");
  assert(commands.includes("workbench.action.chat.focusInput"), "generic chat focus retained");
  assert(
    commands.indexOf("workbench.action.chat.focusInput")
      === commands.lastIndexOf("workbench.action.chat.focusInput"),
    "focus input commands are deduplicated",
  );
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testHostKeyOrderVscodiumPrefersCtrlReturn();
testPlainHostKeyPrioritizerPreservesRows();
testHostKeyOrderVscodiumWaylandPrefersYdotoolBeforeXdotool();
testHostKeyOrderVscodiumX11PrefersXdotoolBeforeYdotool();
testBuildFocusInputUsesChatCommands();
