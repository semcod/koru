# System Architecture Analysis
<!-- generated in 0.01s -->

## Overview

- **Project**: /home/tom/github/semcod/koru/plugins
- **Primary Language**: typescript
- **Languages**: typescript: 62, json: 7, md: 6, kotlin: 6, yaml: 1
- **Analysis Mode**: static
- **Total Functions**: 887
- **Total Classes**: 28
- **Modules**: 84
- **Entry Points**: 651

## Architecture by Module

### koru-autopilot-shared.src.autopilot-bridge
- **Functions**: 407
- **Classes**: 4
- **File**: `autopilot-bridge.ts`

### koru-autopilot-vscodium.src.probe-ladder
- **Functions**: 53
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-cursor.src.probe-ladder.test
- **Functions**: 48
- **File**: `probe-ladder.test.ts`

### koru-autopilot-antigravity.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-cursor.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-vscode.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-windsurf.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-vscodium.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-shared.src.ack-payload
- **Functions**: 35
- **File**: `ack-payload.ts`

### koru-autopilot-cursor.src.ides.cursor.test
- **Functions**: 28
- **File**: `cursor.test.ts`

### koru-autopilot-antigravity.src.cursor-bubble-adapter
- **Functions**: 22
- **Classes**: 1
- **File**: `cursor-bubble-adapter.ts`

### koru-autopilot-antigravity.src.vscode-chat-session-adapter
- **Functions**: 22
- **Classes**: 2
- **File**: `vscode-chat-session-adapter.ts`

### koru-autopilot-antigravity.src.dispatch-plan.test
- **Functions**: 22
- **File**: `dispatch-plan.test.ts`

### koru-autopilot-vscodium.src.probe-ladder.test
- **Functions**: 19
- **File**: `probe-ladder.test.ts`

### koru-autopilot-shared.src.socketPath
- **Functions**: 17
- **File**: `socketPath.ts`

### koru-autopilot-antigravity.src.socketPath
- **Functions**: 17
- **File**: `socketPath.ts`

### koru-autopilot-antigravity.src.step-decisions
- **Functions**: 14
- **Classes**: 1
- **File**: `step-decisions.ts`

### koru-autopilot-cursor.src.ides.cursor
- **Functions**: 14
- **File**: `cursor.ts`

### koru-autopilot-vscode.src.probe-ladder.test
- **Functions**: 14
- **File**: `probe-ladder.test.ts`

### koru-autopilot-antigravity.src.step-decisions.test
- **Functions**: 13
- **File**: `step-decisions.test.ts`

## Key Entry Points

Main execution flows into the system:

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sock
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.on, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.getCommands, koru-autopilot-shared.src.autopilot-bridge.then, koru-autopilot-shared.src.autopilot-bridge.classifyCommands

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.connected
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.on, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.getCommands, koru-autopilot-shared.src.autopilot-bridge.then, koru-autopilot-shared.src.autopilot-bridge.classifyCommands

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.random, koru-autopilot-shared.src.autopilot-bridge.toString, koru-autopilot-shared.src.autopilot-bridge.slice, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.focusChat, koru-autopilot-shared.src.autopilot-bridge.push, koru-autopilot-shared.src.autopilot-bridge.showWarningMessage, koru-autopilot-shared.src.autopilot-bridge.join

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directCommands
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previousClip
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.clipboardSeeded
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-antigravity.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-antigravity.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-antigravity.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-antigravity.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-cursor.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-cursor.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-cursor.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-cursor.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-vscode.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-vscode.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-vscode.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-vscode.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-windsurf.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-windsurf.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-windsurf.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-windsurf.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-vscodium.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-vscodium.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-vscodium.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-vscodium.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-vscodium.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-vscodium.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-cursor.src.ides.cursor.test.run
- **Calls**: koru-autopilot-cursor.src.ides.cursor.test.testRegistry, koru-autopilot-cursor.src.ides.cursor.test.testIdentity, koru-autopilot-cursor.src.ides.cursor.test.testDetectIde, koru-autopilot-cursor.src.ides.cursor.test.testPasteCommands, koru-autopilot-cursor.src.ides.cursor.test.testSubmitCommands, koru-autopilot-cursor.src.ides.cursor.test.testHostKeyPreference, koru-autopilot-cursor.src.ides.cursor.test.testSubmitFallbackPolicy, koru-autopilot-cursor.src.ides.cursor.test.testProbeLadderUsesCursorStrategy

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.verifySubmitStep
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge._probeChatInputContents, koru-autopilot-shared.src.autopilot-bridge.interpretPostSubmitProbe, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.op, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.trim

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previous
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge._performInject, koru-autopilot-shared.src.autopilot-bridge.String, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.send, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.currentOperationTrace, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.restoreHostClipboard

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previousHost
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge._performInject, koru-autopilot-shared.src.autopilot-bridge.String, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.send, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.currentOperationTrace, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.restoreHostClipboard

### koru-autopilot-shared.src.extension-wrapper.createIdeBridgeExtension
- **Calls**: koru-autopilot-shared.src.extension-wrapper.activate, koru-autopilot-shared.src.extension-wrapper.debugLog, koru-autopilot-shared.src.extension-wrapper.isHost, koru-autopilot-shared.src.extension-wrapper.warn, koru-autopilot-shared.src.extension-wrapper.notHostWarning, koru-autopilot-shared.src.extension-wrapper.createBridgeController, koru-autopilot-shared.src.extension-wrapper.wireBridgeCommands, koru-autopilot-shared.src.extension-wrapper.deactivate

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows
- **Calls**: koru-autopilot-antigravity.src.cursor-bubble-adapter.includes, koru-autopilot-antigravity.src.cursor-bubble-adapter.split, koru-autopilot-antigravity.src.cursor-bubble-adapter.trim, koru-autopilot-antigravity.src.cursor-bubble-adapter.parseInt, koru-autopilot-antigravity.src.cursor-bubble-adapter.isFinite, koru-autopilot-antigravity.src.cursor-bubble-adapter.slice, koru-autopilot-antigravity.src.cursor-bubble-adapter.join, koru-autopilot-antigravity.src.cursor-bubble-adapter.push

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.discardToxicFocusOpenCache
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probeLadderEnabled, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.getProbeCache, koru-autopilot-shared.src.autopilot-bridge.toLowerCase, koru-autopilot-shared.src.autopilot-bridge.includes, koru-autopilot-shared.src.autopilot-bridge.startsWith, koru-autopilot-shared.src.autopilot-bridge.update, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.captureSubmitClickPosition
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.runHostCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.match, koru-autopilot-shared.src.autopilot-bridge.showWarningMessage, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.Number, koru-autopilot-shared.src.autopilot-bridge.getConfiguration, koru-autopilot-shared.src.autopilot-bridge.update, koru-autopilot-shared.src.autopilot-bridge.showInformationMessage

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep
- **Calls**: koru-autopilot-antigravity.src.cursor-bubble-adapter.split, koru-autopilot-antigravity.src.cursor-bubble-adapter.trim, koru-autopilot-antigravity.src.cursor-bubble-adapter.parseInt, koru-autopilot-antigravity.src.cursor-bubble-adapter.isFinite, koru-autopilot-antigravity.src.cursor-bubble-adapter.slice, koru-autopilot-antigravity.src.cursor-bubble-adapter.join, koru-autopilot-antigravity.src.cursor-bubble-adapter.push, koru-autopilot-antigravity.src.cursor-bubble-adapter.String

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep
- **Calls**: koru-autopilot-antigravity.src.cursor-bubble-adapter.split, koru-autopilot-antigravity.src.cursor-bubble-adapter.trim, koru-autopilot-antigravity.src.cursor-bubble-adapter.parseInt, koru-autopilot-antigravity.src.cursor-bubble-adapter.isFinite, koru-autopilot-antigravity.src.cursor-bubble-adapter.slice, koru-autopilot-antigravity.src.cursor-bubble-adapter.join, koru-autopilot-antigravity.src.cursor-bubble-adapter.push, koru-autopilot-antigravity.src.cursor-bubble-adapter.String

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge._tryHostClickSubmit
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.submitClickPoint, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.autoSubmitClickPoint, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.isWaylandSession, koru-autopilot-shared.src.autopilot-bridge._tryHostClickSubmitYdotool, koru-autopilot-shared.src.autopilot-bridge._tryHostClickSubmitXdotool

### koru-autopilot-vscodium.src.probe-ladder.buildFocusInputCommands
- **Calls**: koru-autopilot-vscodium.src.probe-ladder.getStrategy, koru-autopilot-vscodium.src.probe-ladder.focusInputCommandsPrefix, koru-autopilot-vscodium.src.probe-ladder.Set, koru-autopilot-vscodium.src.probe-ladder.map, koru-autopilot-vscodium.src.probe-ladder.toLowerCase, koru-autopilot-vscodium.src.probe-ladder.filter, koru-autopilot-vscodium.src.probe-ladder.has

### koru-autopilot-vscodium.src.probe-ladder.buildHostKeySubmitCandidates
- **Calls**: koru-autopilot-vscodium.src.probe-ladder.toLowerCase, koru-autopilot-vscodium.src.probe-ladder.Boolean, koru-autopilot-vscodium.src.probe-ladder.reorderForVscodiumHostKeys, koru-autopilot-vscodium.src.probe-ladder.injectorRow, koru-autopilot-vscodium.src.probe-ladder.reorderForXSession, koru-autopilot-vscodium.src.probe-ladder.getStrategy, koru-autopilot-vscodium.src.probe-ladder.preferCtrlSubmit

### koru-autopilot-vscodium.src.ides.vscodium.test.run
- **Calls**: koru-autopilot-vscodium.src.ides.vscodium.test.testRegistered, koru-autopilot-vscodium.src.ides.vscodium.test.testPreferCtrlSubmit, koru-autopilot-vscodium.src.ides.vscodium.test.testSubmitSanitize, koru-autopilot-vscodium.src.ides.vscodium.test.testTrustFocusOpen, koru-autopilot-vscodium.src.ides.vscodium.test.testSubmitCommandsTryRegisteredSubmitFirst, koru-autopilot-vscodium.src.ides.vscodium.test.testFocusOpenAvoidsPanelOpenCommands, koru-autopilot-vscodium.src.ides.vscodium.test.log

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.initialCursor
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.ChatHistoryWatcher, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.send, koru-autopilot-shared.src.autopilot-bridge.substring, koru-autopilot-shared.src.autopilot-bridge.split, koru-autopilot-shared.src.autopilot-bridge.update

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.deadline
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.now, koru-autopilot-shared.src.autopilot-bridge.fetchLatestUserBubbles, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.String, koru-autopilot-shared.src.autopilot-bridge.includes, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tail
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.now, koru-autopilot-shared.src.autopilot-bridge.fetchLatestUserBubbles, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.String, koru-autopilot-shared.src.autopilot-bridge.includes, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.attempts
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.now, koru-autopilot-shared.src.autopilot-bridge.fetchLatestUserBubbles, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.String, koru-autopilot-shared.src.autopilot-bridge.includes, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep

### koru-autopilot-shared.src.socketPath.defaultSocketPathFromEnv
- **Calls**: koru-autopilot-shared.src.socketPath.trim, koru-autopilot-shared.src.socketPath.resolve, koru-autopilot-shared.src.socketPath.slugInstance, koru-autopilot-shared.src.socketPath.join, koru-autopilot-shared.src.socketPath.toString, koru-autopilot-shared.src.socketPath.replace

## Process Flows

Key execution flows identified:

### Flow 1: sock
```
sock [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> debugLog
  └─> detectIde
```

### Flow 2: connected
```
connected [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> debugLog
  └─> detectIde
```

### Flow 3: calibrateProbe
```
calibrateProbe [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> detectIde
  └─> focusChat
      └─> _buildFocusChatContext
          └─> detectIde
          └─> resolve
```

### Flow 4: directCommands
```
directCommands [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> directPasteReadsClipboard
  └─> writeClipboardVerified
      └─> debugLog
      └─> sleep
          └─> setTimeout
```

### Flow 5: previousClip
```
previousClip [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> directPasteReadsClipboard
  └─> writeClipboardVerified
      └─> debugLog
      └─> sleep
          └─> setTimeout
```

### Flow 6: clipboardSeeded
```
clipboardSeeded [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> directPasteReadsClipboard
  └─> writeClipboardVerified
      └─> debugLog
      └─> sleep
          └─> setTimeout
```

### Flow 7: main
```
main [koru-autopilot-antigravity.src.chat-history-watcher.test]
  └─> testParseCursorBubbleRowsHandlesMultilineText
      └─> buildSqliteOutput
  └─> testWatcherEmitsNewBubblesAndAdvancesCursor
      └─> buildSqliteOutput
      └─> r
```

### Flow 8: run
```
run [koru-autopilot-cursor.src.ides.cursor.test]
  └─> testRegistry
      └─> assert
  └─> testIdentity
      └─> eq
```

### Flow 9: verifySubmitStep
```
verifySubmitStep [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> sleep
      └─> setTimeout
          └─> openChatPanel
          └─> safeLog
  └─> _probeChatInputContents
      └─> now
      └─> saveClipboard
```

### Flow 10: previous
```
previous [koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge]
  └─> _performInject
      └─> detectIde
      └─> traceOperation
          └─> safeLog
  └─> traceOperation
      └─> safeLog
      └─> emitLiveDsl
```

## Key Classes

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge
- **Methods**: 389
- **Key Methods**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.isConnected, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sendConsoleLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resetOperationTrace, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.value, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.commands, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.server, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.safeLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.emitLiveDsl, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.seq

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher
- **Methods**: 11
- **Key Methods**: koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.currentCursor, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.adapterDescription, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.setCursor, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.start, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.tick, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.stop, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.clearInterval, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.pollOnce, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.cursorAdvances, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.a

### koru-autopilot-antigravity.src.unsupported-chat-adapter.UnsupportedAdapter
- **Methods**: 2
- **Key Methods**: koru-autopilot-antigravity.src.unsupported-chat-adapter.UnsupportedAdapter.storeAvailable, koru-autopilot-antigravity.src.unsupported-chat-adapter.UnsupportedAdapter.fetchNewer

### koru-autopilot-shared.src.autopilot-bridge.Envelope
- **Methods**: 0

### koru-autopilot-shared.src.autopilot-bridge.BridgeOptions
- **Methods**: 0

### koru-autopilot-shared.src.autopilot-bridge.BridgeHandle
- **Methods**: 0

### koru-autopilot-shared.src.types.Envelope
- **Methods**: 0

### koru-autopilot-shared.src.bridge-base.WireBridgeCommandsOptions
- **Methods**: 0

### koru-autopilot-shared.src.dispatch-plan.EnvelopeLike
- **Methods**: 0

### koru-autopilot-shared.src.chat-history-types.ChatHistoryRow
- **Methods**: 0

### koru-autopilot-shared.src.chat-history-types.AdapterRunner
- **Methods**: 0

### koru-autopilot-shared.src.chat-history-types.IdeAdapter
- **Methods**: 0

### koru-autopilot-shared.src.extension-wrapper.IdeBridgeExtensionConfig
- **Methods**: 0

### koru-autopilot-shared.src.extension-wrapper.IdeBridgeExtensionRuntime
- **Methods**: 0

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionEntry
- **Methods**: 0

### koru-autopilot-antigravity.src.ide-control-strategy.IdeControlStrategy
- **Methods**: 0

### koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcherOptions
- **Methods**: 0

### koru-autopilot-antigravity.src.command-catalog.CommandCatalog
- **Methods**: 0

## Data Transformation Functions

Key functions that process and transform data:

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.parsed
- **Output to**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation

### koru-autopilot-shared.src.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-shared.src.host-click-submit.split, koru-autopilot-shared.src.host-click-submit.match, koru-autopilot-shared.src.host-click-submit.parseInt, koru-autopilot-shared.src.host-click-submit.every, koru-autopilot-shared.src.host-click-submit.isFinite

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-antigravity.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.stringify, koru-autopilot-antigravity.src.chat-history-watcher.test.answer, koru-autopilot-antigravity.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual, koru-autopilot-antigravity.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-antigravity.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-antigravity.src.chat-history-watcher.test.stringify, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-antigravity.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows
- **Output to**: koru-autopilot-antigravity.src.cursor-bubble-adapter.includes, koru-autopilot-antigravity.src.cursor-bubble-adapter.split, koru-autopilot-antigravity.src.cursor-bubble-adapter.trim, koru-autopilot-antigravity.src.cursor-bubble-adapter.parseInt, koru-autopilot-antigravity.src.cursor-bubble-adapter.isFinite

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.trim, koru-autopilot-antigravity.src.vscode-chat-session-adapter.parse

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.parseFloat

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseVSCodeChatIndex
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractEntriesMap, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.entries, koru-autopilot-antigravity.src.vscode-chat-session-adapter.push

### koru-autopilot-antigravity.src.host-click-submit.test.testParseXdotoolGeometryShell
- **Output to**: koru-autopilot-antigravity.src.host-click-submit.test.parseXdotoolGeometryShell, koru-autopilot-antigravity.src.host-click-submit.test.Error, koru-autopilot-antigravity.src.host-click-submit.test.assert

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-cursor.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.stringify, koru-autopilot-cursor.src.chat-history-watcher.test.answer, koru-autopilot-cursor.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual, koru-autopilot-cursor.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-cursor.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-cursor.src.chat-history-watcher.test.stringify, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-cursor.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-vscode.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-vscode.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-vscode.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-vscode.src.chat-history-watcher.test.strictEqual

### koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-vscode.src.chat-history-watcher.test.stringify, koru-autopilot-vscode.src.chat-history-watcher.test.answer, koru-autopilot-vscode.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-vscode.src.chat-history-watcher.test.strictEqual, koru-autopilot-vscode.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-vscode.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-vscode.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-vscode.src.chat-history-watcher.test.stringify, koru-autopilot-vscode.src.chat-history-watcher.test.strictEqual

### koru-autopilot-vscode.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-vscode.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-vscode.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-vscode.src.chat-history-watcher.test.strictEqual

### koru-autopilot-windsurf.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-windsurf.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-windsurf.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-windsurf.src.chat-history-watcher.test.strictEqual

### koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-windsurf.src.chat-history-watcher.test.stringify, koru-autopilot-windsurf.src.chat-history-watcher.test.answer, koru-autopilot-windsurf.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-windsurf.src.chat-history-watcher.test.strictEqual, koru-autopilot-windsurf.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-windsurf.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-windsurf.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-windsurf.src.chat-history-watcher.test.stringify, koru-autopilot-windsurf.src.chat-history-watcher.test.strictEqual

### koru-autopilot-windsurf.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-windsurf.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-windsurf.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-windsurf.src.chat-history-watcher.test.strictEqual

### koru-autopilot-vscodium.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-vscodium.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-vscodium.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-vscodium.src.chat-history-watcher.test.strictEqual

### koru-autopilot-vscodium.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-vscodium.src.chat-history-watcher.test.stringify, koru-autopilot-vscodium.src.chat-history-watcher.test.answer, koru-autopilot-vscodium.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-vscodium.src.chat-history-watcher.test.strictEqual, koru-autopilot-vscodium.src.chat-history-watcher.test.deepStrictEqual

## Behavioral Patterns

### state_machine_SharedAutopilotBridge
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.isConnected, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sendConsoleLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resetOperationTrace, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.value, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.commands

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryCursorComposerPromptFastPath` - 24 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sock` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.connected` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.focusChatInput` - 14 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.injectChat` - 14 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.calibrateProbe` - 14 calls
- `koru-autopilot-cursor.src.ides.cursor.test.testProbeLadderUsesCursorStrategy` - 13 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directCommands` - 12 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previousClip` - 12 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.clipboardSeeded` - 12 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.ensureWindsurfChatPanelVisible` - 12 calls
- `koru-autopilot-antigravity.src.chat-history-watcher.test.main` - 12 calls
- `koru-autopilot-cursor.src.chat-history-watcher.test.main` - 12 calls
- `koru-autopilot-vscode.src.chat-history-watcher.test.main` - 12 calls
- `koru-autopilot-windsurf.src.chat-history-watcher.test.main` - 12 calls
- `koru-autopilot-vscodium.src.chat-history-watcher.test.main` - 12 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.startChatHistoryWatcherIfEligible` - 11 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryWindsurfSendTextFastPath` - 11 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryAntigravitySendPromptFastPath` - 11 calls
- `koru-autopilot-cursor.src.ides.cursor.test.run` - 11 calls
- `koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor` - 10 calls
- `koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor` - 10 calls
- `koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor` - 10 calls
- `koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor` - 10 calls
- `koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor` - 10 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.verifySubmitStep` - 9 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.focusChat` - 9 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previous` - 9 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previousHost` - 9 calls
- `koru-autopilot-shared.src.extension-wrapper.createIdeBridgeExtension` - 9 calls
- `koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows` - 9 calls
- `koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseVSCodeChatIndex` - 9 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.emitLiveDsl` - 8 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.onData` - 8 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.discardToxicFocusOpenCache` - 8 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.captureSubmitClickPosition` - 8 calls
- `koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherSkipsPollingWhenStoreUnavailable` - 8 calls

## System Interactions

How components interact:

```mermaid
graph TD
    sock --> on
    sock --> debugLog
    sock --> detectIde
    sock --> maybeOpenChatOnConne
    sock --> resolve
    connected --> on
    connected --> debugLog
    connected --> detectIde
    connected --> maybeOpenChatOnConne
    connected --> resolve
    calibrateProbe --> random
    calibrateProbe --> toString
    calibrateProbe --> slice
    calibrateProbe --> detectIde
    calibrateProbe --> focusChat
    directCommands --> directPasteReadsClip
    directCommands --> writeClipboardVerifi
    directCommands --> debugLog
    directCommands --> traceOperation
    directCommands --> resolve
    previousClip --> directPasteReadsClip
    previousClip --> writeClipboardVerifi
    previousClip --> debugLog
    previousClip --> traceOperation
    previousClip --> resolve
    clipboardSeeded --> directPasteReadsClip
    clipboardSeeded --> writeClipboardVerifi
    clipboardSeeded --> debugLog
    clipboardSeeded --> traceOperation
    clipboardSeeded --> resolve
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.