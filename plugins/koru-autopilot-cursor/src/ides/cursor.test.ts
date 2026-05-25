/**
 * Contract tests for the Cursor IDE strategy.
 *
 * These tests must depend ONLY on the strategy module and the registry,
 * NOT on `extension.ts`, the activated VS Code API, or other IDE
 * strategies. That isolation is the whole point of the per-IDE split:
 * we want a regression in Cursor to be impossible to introduce while
 * editing VSCodium / Windsurf code, and vice versa.
 */

import { cursorStrategy } from "./cursor";
import { getStrategy, allStrategies } from "./registry";
import {
  buildFocusInputCommands,
  buildHostKeySubmitCandidates,
  buildPasteDirectCommands,
  buildSubmitCommands,
  ProbeCacheEntry,
  PROBE_CACHE_VERSION,
  sanitizeProbeCacheForIde,
} from "../probe-ladder";

function assert(condition: unknown, message: string): void {
  if (!condition) {
    throw new Error(`cursor-strategy test failed: ${message}`);
  }
}

function eq<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(
      `cursor-strategy test failed: ${message}\n  expected: ${String(expected)}\n  actual:   ${String(actual)}`,
    );
  }
}

function cursorCacheEntry(fields: Partial<ProbeCacheEntry>): ProbeCacheEntry {
  return {
    version: PROBE_CACHE_VERSION,
    ide: "cursor",
    appName: "Cursor",
    updatedAt: "",
    ...fields,
  };
}

function assertSanitizedCacheField(
  fields: Partial<ProbeCacheEntry>,
  key: keyof ProbeCacheEntry,
  expected: string | undefined,
  message: string,
): void {
  const sanitized = sanitizeProbeCacheForIde(cursorCacheEntry(fields), "cursor");
  eq(sanitized?.[key], expected, message);
}

function testRegistry(): void {
  const strat = getStrategy("cursor");
  assert(strat !== undefined, "cursor strategy must be registered");
  eq(strat, cursorStrategy, "getStrategy must return the same instance");
  assert(
    allStrategies().some((s) => s.id === "cursor"),
    "cursor must be in allStrategies()",
  );
  eq(getStrategy("CURSOR"), cursorStrategy, "id lookup must be case-insensitive");
}

function testIdentity(): void {
  eq(cursorStrategy.id, "cursor", "id is the canonical Koru string");
  eq(cursorStrategy.label, "Cursor", "label is the human-readable name");
}

function testDetectIde(): void {
  eq(cursorStrategy.detectIde("Cursor"), "cursor", "appName 'Cursor' detects as cursor");
  eq(cursorStrategy.detectIde("Cursor Insiders"), "cursor", "Cursor variants detected");
  eq(cursorStrategy.detectIde("Visual Studio Code"), undefined, "VS Code must not match");
  eq(cursorStrategy.detectIde("VSCodium"), undefined, "VSCodium must not match");
  eq(cursorStrategy.detectIde("Windsurf"), undefined, "Windsurf must not match");
  eq(cursorStrategy.detectIde(""), undefined, "empty appName must not match");
}

function testPasteCommands(): void {
  const cmds = cursorStrategy.pasteDirectCommandsPrefix();
  assert(cmds.length > 0, "Cursor must have its own paste prefix");
  assert(cmds.includes("cursor.action.chat.typeText"), "must include cursor.action.chat.typeText");
  assert(cmds.includes("composer.typeText"), "must include composer.typeText");
}

function testSubmitCommands(): void {
  const cmds = cursorStrategy.submitCommandsOverride();
  assert(cmds !== null, "Cursor must override the submit command list");
  if (cmds === null) return;
  eq(cmds[0], "composer.sendToAgent", "composer.sendToAgent MUST be first (real Cursor submit)");
  assert(cmds.includes("workbench.action.chat.submit"), "generic fallback retained");
}

function testHostKeyPreference(): void {
  // Cursor's chat textarea treats plain Return as a newline; only
  // Ctrl+Return submits. The strategy must report this preference.
  assert(cursorStrategy.preferCtrlSubmit(), "Cursor must prefer Ctrl+Return over plain Return");
}

function testSubmitFallbackPolicy(): void {
  assert(
    cursorStrategy.submitFallback.refuseTypeNewlineFallback,
    "Cursor must refuse the type-newline fallback (else newlines stack in chat input)",
  );
}

function testProbeLadderUsesCursorStrategy(): void {
  // buildPasteDirectCommands delegates to the strategy prefix
  const paste = buildPasteDirectCommands("cursor");
  eq(paste[0], "cursor.action.chat.typeText", "paste command 0 must come from strategy");
  // buildSubmitCommands returns the strategy override
  const submit = buildSubmitCommands("cursor");
  eq(submit[0], "composer.sendToAgent", "submit command 0 must come from strategy");
  // buildHostKeySubmitCandidates puts Ctrl+Return first for Cursor (auto mode)
  const hostKeys = buildHostKeySubmitCandidates("cursor", "auto", { XDG_SESSION_TYPE: "wayland" });
  const firstArgs = hostKeys[0]?.[1] || [];
  assert(
    firstArgs.some((arg) => /ctrl/i.test(arg)),
    "first host-key candidate for Cursor must include ctrl modifier",
  );
  // buildFocusInputCommands: Cursor has composer-specific focus commands first
  const focus = buildFocusInputCommands("cursor");
  eq(focus[0], "composer.focusComposer", "Cursor focus list starts with composer.focusComposer");
  assert(
    !focus.includes("workbench.action.focusAuxiliaryBar"),
    "Cursor must not try focusAuxiliaryBar (false-positive chat focus)",
  );
}

function testProbeCacheSanitizationForCursor(): void {
  testCursorSubmitCacheSanitization();
  testCursorPasteAndFocusInputCacheSanitization();
  testCursorFocusOpenCacheSanitization();
}

function testCursorSubmitCacheSanitization(): void {
  assertSanitizedCacheField({ submit: "type:" }, "submit", undefined, "type: submit must be cleared");
  // Plain Return via any injector must be cleared for Cursor (chat textarea
  // treats Return as newline; only Ctrl+Return submits).
  assertSanitizedCacheField(
    { submit: "ydotool key Return" },
    "submit",
    undefined,
    "plain Return host-key win must be cleared for Cursor",
  );

  // Ctrl+Return via ydotool must be preserved (ydotool works on both X11
  // and Wayland — xdotool wins would also be cleared on Wayland by the
  // strategy's separate xdotool-on-Wayland rule, which is exactly the
  // regression behaviour we want).
  assertSanitizedCacheField(
    { submit: "ydotool key ctrl+Return" },
    "submit",
    "ydotool key ctrl+Return",
    "ydotool ctrl+Return win must be preserved for Cursor",
  );

  // Cursor strategy must not touch unrelated submit commands.
  assertSanitizedCacheField(
    { submit: "composer.sendToAgent" },
    "submit",
    "composer.sendToAgent",
    "registered composer.sendToAgent must be preserved",
  );
}

function testCursorPasteAndFocusInputCacheSanitization(): void {
  assertSanitizedCacheField(
    { paste: "editor.action.clipboardPasteAction" },
    "paste",
    undefined,
    "clipboardPasteAction paste cache must be cleared for Cursor",
  );

  assertSanitizedCacheField(
    { focusInput: "workbench.action.focusAuxiliaryBar" },
    "focusInput",
    undefined,
    "focusAuxiliaryBar focusInput cache must be cleared for Cursor",
  );
}

function testCursorFocusOpenCacheSanitization(): void {
  // aichat.newchataction opens a NEW chat tab in Cursor. If it ever
  // wins the focus_open probe, the cache must be invalidated so the
  // ladder re-probes against commands that target the existing chat
  // (composer.showComposer / workbench.panel.chat). Caching it leaves
  // every subsequent drive pasting+submitting into a fresh tab while
  // the user is staring at the original chat — i.e. the v0.1.64 bug.
  assertSanitizedCacheField(
    { focusOpen: "aichat.newchataction" },
    "focusOpen",
    undefined,
    "aichat.newchataction focus_open cache must be cleared for Cursor",
  );

  // composer.openAsPane is a TOGGLE in current Cursor builds: when the
  // Composer panel is already open, this command hides it. Cached as
  // the focus_open winner it produces the exact "schowal panel + wkleil
  // ale nie wysłał" symptom — the plugin pastes into a now-invisible
  // surface and submit commands no-op. The cache must be invalidated
  // so the ladder re-probes the non-toggling composer.openComposer.
  assertSanitizedCacheField(
    { focusOpen: "composer.openAsPane" },
    "focusOpen",
    undefined,
    "composer.openAsPane focus_open cache must be cleared for Cursor "
      + "(toggle hides an already-open chat panel)",
  );
}

function testFocusOpenDefaultsExcludeNewChatTab(): void {
  // Cursor's defaults list MUST NOT contain aichat.newchataction, which
  // opens a new chat tab and routes the next paste/submit there instead
  // of the existing chat the user is watching.
  const defaults = cursorStrategy.focusOpenCommandsDefaults();
  if (defaults.length === 0) {
    throw new Error(
      "Cursor focus_open defaults must be explicit so the generic " +
        "ladder doesn't fall through to aichat.newchataction",
    );
  }
  if (defaults.includes("aichat.newchataction")) {
    throw new Error(
      "Cursor focus_open defaults must NOT include aichat.newchataction " +
        "(opens a new chat tab; submits land in the wrong pane)",
    );
  }
  if (!defaults.includes("composer.openComposer")) {
    throw new Error(
      "Cursor focus_open defaults must include composer.openComposer " +
        "as the primary candidate for the existing chat surface",
    );
  }
}

function run(): void {
  testRegistry();
  testIdentity();
  testDetectIde();
  testPasteCommands();
  testSubmitCommands();
  testHostKeyPreference();
  testSubmitFallbackPolicy();
  testProbeLadderUsesCursorStrategy();
  testProbeCacheSanitizationForCursor();
  testFocusOpenDefaultsExcludeNewChatTab();
  console.log("cursor-strategy tests: ok");
}

run();
