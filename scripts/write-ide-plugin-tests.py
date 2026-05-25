#!/usr/bin/env python3
"""Write per-IDE probe-ladder.test.ts and patch chat-history-watcher.test.ts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

COMMON_HEADER = '''/**
 * {ide}-only probe-ladder regression tests.
 */

import {{
  buildFocusInputCommands,
  buildFocusOpenCommands,
  buildHostKeySubmitCandidates,
  buildSubmitCommands,
  chatFocusHeuristic,
  decideSubmitCleared,
  mergeUnique,
  orderWithCache,
  pasteLandedInEditor,
  sanitizeProbeCacheForIde,
  verifyFocusAfterOpen,
  PROBE_CACHE_VERSION,
}} from "./probe-ladder";

function assert(condition: unknown, message: string): void {{
  if (!condition) throw new Error(`probe-ladder test failed: ${{message}}`);
}}

function testOrderWithCache(): void {{
  assert(orderWithCache(["a", "b", "c"], "b")[0] === "b", "cached first");
}}

function testChatFocusHeuristic(): void {{
  assert(chatFocusHeuristic({{ hasEditor: false, scheme: "", isFileLike: false, text: "" }}), "no editor");
  assert(!chatFocusHeuristic({{ hasEditor: true, scheme: "file", isFileLike: true, text: "x" }}), "file editor");
}}

function testPasteLandedInEditor(): void {{
  const before = {{ hasEditor: true, scheme: "file", isFileLike: true, text: "hello" }};
  const after = {{ hasEditor: true, scheme: "file", isFileLike: true, text: "hello __koru_probe__" }};
  assert(pasteLandedInEditor(before, after, "__koru_probe__"), "paste in editor");
}}

function testMergeUnique(): void {{
  assert(mergeUnique(["a", "b"], ["b", "c"]).join() === "a,b,c", "dedupe");
}}

function firstKey(cands: ReadonlyArray<[string, string[]]>): string {{
  const [cmd, args] = cands[0];
  return `${{cmd}} ${{args.join(" ")}}`;
}}

const WAYLAND_ENV = {{ XDG_SESSION_TYPE: "wayland", WAYLAND_DISPLAY: "wayland-0" }};
'''

IDE_BLOCKS: dict[str, str] = {
    "vscode": '''
function testVerifyFocusAfterOpen(): void {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  const none = { hasEditor: false, scheme: "", isFileLike: false, text: "" };
  assert(verifyFocusAfterOpen(file, none), "blur counts as open");
  assert(!verifyFocusAfterOpen(file, file, "vscode"), "vscode must not trust unchanged file-editor focus");
}

function testBuildFocusOpenVscode(): void {
  const cmds = buildFocusOpenCommands("vscode", []);
  assert(cmds.includes("workbench.action.chat.open"), "vscode includes safe chat-open fallback");
}

function testSanitizeVscodeDropsUnsafeFocusOpenCache(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "vscode",
    appName: "Visual Studio Code",
    updatedAt: "2026-05-24T20:00:00Z",
    focusOpen: "workbench.panel.chat",
    focusInput: "workbench.action.chat.focusInput",
  };
  const sanitized = sanitizeProbeCacheForIde(poisoned, "vscode");
  assert(sanitized?.focusOpen === undefined, "unsafe focus-open cache dropped");
  assert(sanitized?.focusInput === "workbench.action.chat.focusInput", "safe focus-input preserved");
}

function testHostKeyOrderVscodeKeepsPlainReturnFirst(): void {
  const cands = buildHostKeySubmitCandidates("vscode", "auto", WAYLAND_ENV);
  assert(!firstKey(cands).includes("ctrl"), "VS Code keeps Return-first ordering");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("vscode").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenVscode();
testSanitizeVscodeDropsUnsafeFocusOpenCache();
testHostKeyOrderVscodeKeepsPlainReturnFirst();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
''',
    "vscodium": '''
function testVerifyFocusAfterOpen(): void {
  const file = { hasEditor: true, scheme: "file", isFileLike: true, text: "code" };
  assert(verifyFocusAfterOpen(file, file, "vscodium"), "vscodium may trust unchanged snapshot");
}

function testHostKeyOrderVscodiumPrefersCtrlReturn(): void {
  const cands = buildHostKeySubmitCandidates("vscodium", "auto", WAYLAND_ENV);
  assert(firstKey(cands).includes("ctrl"), "VSCodium tries Ctrl+Return first");
}

function testBuildFocusInputUsesChatCommands(): void {
  assert(buildFocusInputCommands("vscodium")[0] === "workbench.action.chat.focusInput", "focus input first");
}

testOrderWithCache();
testChatFocusHeuristic();
testVerifyFocusAfterOpen();
testPasteLandedInEditor();
testMergeUnique();
testHostKeyOrderVscodiumPrefersCtrlReturn();
testBuildFocusInputUsesChatCommands();
''',
    "windsurf": '''
function testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand(): void {
  const cmds = buildFocusOpenCommands("windsurf", []);
  assert(!cmds.includes("workbench.view.windsurfAgentSidebarContainer"), "no toggle sidebar");
  assert(cmds.includes("windsurf.cascadePanel.open"), "cascade open present");
}

function testSanitizeWindsurfDiscardsTypeSubmit(): void {
  const poisoned = {
    version: PROBE_CACHE_VERSION as typeof PROBE_CACHE_VERSION,
    ide: "windsurf",
    appName: "Windsurf",
    updatedAt: "2026-05-22T20:00:00Z",
    submit: "type:\\n",
  };
  assert(sanitizeProbeCacheForIde(poisoned, "windsurf")?.submit === undefined, "type submit discarded");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("windsurf").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenWindsurfDoesNotUseToggleSidebarCommand();
testSanitizeWindsurfDiscardsTypeSubmit();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
''',
    "antigravity": '''
function testBuildFocusOpenAntigravityEmpty(): void {
  assert(buildFocusOpenCommands("antigravity", []).length === 0, "no auto-open ladder");
}

function testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance(): void {
  assert(!buildSubmitCommands("antigravity").includes("workbench.action.acceptSelectedQuickOpenItem"), "no quick open");
}

testOrderWithCache();
testChatFocusHeuristic();
testPasteLandedInEditor();
testMergeUnique();
testBuildFocusOpenAntigravityEmpty();
testBuildSubmitCommandsDoesNotUseQuickOpenAcceptance();
''',
}

PLUGIN_DIR = {
    "vscode": "koru-autopilot-vscode",
    "vscodium": "koru-autopilot-vscodium",
    "windsurf": "koru-autopilot-windsurf",
    "antigravity": "koru-autopilot-antigravity",
}

ADAPTER_TEST: dict[str, str] = {
    "vscode": '''async function testBuildAdapterForIdeReturnsCorrectKind(): Promise<void> {
  assert.ok(buildAdapterForIde("vscode") instanceof VSCodeChatSessionAdapter);
  for (const foreign of ["cursor", "vscodium", "windsurf", "antigravity"] as const) {
    let threw = false;
    try { buildAdapterForIde(foreign); } catch { threw = true; }
    assert.ok(threw, `must refuse ${foreign}`);
  }
}''',
    "vscodium": '''async function testBuildAdapterForIdeReturnsCorrectKind(): Promise<void> {
  assert.ok(buildAdapterForIde("vscodium") instanceof VSCodeChatSessionAdapter);
  // VSCodium adapter accepts "vscode" alias (same SQLite session store).
  assert.ok(buildAdapterForIde("vscode") instanceof VSCodeChatSessionAdapter);
  for (const foreign of ["cursor", "windsurf", "antigravity"] as const) {
    let threw = false;
    try { buildAdapterForIde(foreign); } catch { threw = true; }
    assert.ok(threw, `must refuse ${foreign}`);
  }
}''',
    "windsurf": '''async function testBuildAdapterForIdeReturnsCorrectKind(): Promise<void> {
  assert.ok(buildAdapterForIde("windsurf") instanceof UnsupportedAdapter);
  for (const foreign of ["cursor", "vscode", "vscodium", "antigravity"] as const) {
    let threw = false;
    try { buildAdapterForIde(foreign); } catch { threw = true; }
    assert.ok(threw, `must refuse ${foreign}`);
  }
}''',
    "antigravity": '''async function testBuildAdapterForIdeReturnsCorrectKind(): Promise<void> {
  assert.ok(buildAdapterForIde("antigravity") instanceof UnsupportedAdapter);
  for (const foreign of ["cursor", "vscode", "vscodium", "windsurf"] as const) {
    let threw = false;
    try { buildAdapterForIde(foreign); } catch { threw = true; }
    assert.ok(threw, `must refuse ${foreign}`);
  }
}''',
}


def write_probe_tests(ide: str) -> None:
    plugin = REPO / "plugins" / PLUGIN_DIR[ide]
    content = COMMON_HEADER.format(ide=ide) + IDE_BLOCKS[ide]
    (plugin / "src" / "probe-ladder.test.ts").write_text(content, encoding="utf-8")


def patch_watcher_test(ide: str) -> None:
    path = REPO / "plugins" / PLUGIN_DIR[ide] / "src" / "chat-history-watcher.test.ts"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"async function testBuildAdapterForIdeReturnsCorrectKind\(\): Promise<void> \{.*?\n\}",
        ADAPTER_TEST[ide],
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace(
        "allRows.map((r) => r.text)",
        "allRows.map((r: { text: string }) => r.text)",
    )
    text = text.replace(
        "newer.map((r) => r.text)",
        "newer.map((r: { text: string }) => r.text)",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    for ide in sys.argv[1:] or IDE_BLOCKS:
        write_probe_tests(ide)
        patch_watcher_test(ide)
        print(f"updated tests for {ide}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
