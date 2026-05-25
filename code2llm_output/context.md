# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/koru/plugins
- **Primary Language**: typescript
- **Languages**: typescript: 205, yaml: 15, md: 12, json: 11, kotlin: 5
- **Analysis Mode**: static
- **Total Functions**: 3385
- **Total Classes**: 142
- **Modules**: 250
- **Entry Points**: 2412

## Architecture by Module

### koru-autopilot-shared.src.autopilot-bridge
- **Functions**: 392
- **Classes**: 4
- **File**: `autopilot-bridge.ts`

### koru-autopilot-cursor.src._shared.autopilot-bridge
- **Functions**: 392
- **Classes**: 4
- **File**: `autopilot-bridge.ts`

### koru-autopilot-vscode.src._shared.autopilot-bridge
- **Functions**: 392
- **Classes**: 4
- **File**: `autopilot-bridge.ts`

### koru-autopilot-vscodium.src._shared.autopilot-bridge
- **Functions**: 391
- **Classes**: 3
- **File**: `autopilot-bridge.ts`

### koru-autopilot-vscodium.src.extension
- **Functions**: 389
- **Classes**: 1
- **File**: `extension.ts`

### koru-autopilot-antigravity.src.extension
- **Functions**: 373
- **Classes**: 2
- **File**: `extension.ts`

### koru-autopilot-windsurf.src.extension
- **Functions**: 373
- **Classes**: 2
- **File**: `extension.ts`

### koru-autopilot-vscodium.src.probe-ladder
- **Functions**: 53
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-antigravity.src.probe-ladder
- **Functions**: 49
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-cursor.src.probe-ladder
- **Functions**: 49
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-vscode.src.probe-ladder
- **Functions**: 49
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-windsurf.src.probe-ladder
- **Functions**: 49
- **Classes**: 3
- **File**: `probe-ladder.ts`

### koru-autopilot-cursor.src.probe-ladder.test
- **Functions**: 48
- **File**: `probe-ladder.test.ts`

### koru-autopilot-cursor.src.chat-history-watcher.test
- **Functions**: 43
- **File**: `chat-history-watcher.test.ts`

### koru-autopilot-antigravity.src.chat-history-watcher.test
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

### koru-autopilot-antigravity.src.ack-payload
- **Functions**: 35
- **File**: `ack-payload.ts`

### koru-autopilot-shared.src.ack-payload
- **Functions**: 35
- **File**: `ack-payload.ts`

## Key Entry Points

Main execution flows into the system:

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sock
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.on, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.getCommands, koru-autopilot-shared.src.autopilot-bridge.then, koru-autopilot-shared.src.autopilot-bridge.classifyCommands

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.connected
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.on, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.getCommands, koru-autopilot-shared.src.autopilot-bridge.then, koru-autopilot-shared.src.autopilot-bridge.classifyCommands

### koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.sock
- **Calls**: koru-autopilot-cursor.src._shared.autopilot-bridge.on, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-cursor.src._shared.autopilot-bridge.getCommands, koru-autopilot-cursor.src._shared.autopilot-bridge.then, koru-autopilot-cursor.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.connected
- **Calls**: koru-autopilot-cursor.src._shared.autopilot-bridge.on, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-cursor.src._shared.autopilot-bridge.getCommands, koru-autopilot-cursor.src._shared.autopilot-bridge.then, koru-autopilot-cursor.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.sock
- **Calls**: koru-autopilot-vscode.src._shared.autopilot-bridge.on, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-vscode.src._shared.autopilot-bridge.getCommands, koru-autopilot-vscode.src._shared.autopilot-bridge.then, koru-autopilot-vscode.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.connected
- **Calls**: koru-autopilot-vscode.src._shared.autopilot-bridge.on, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-vscode.src._shared.autopilot-bridge.getCommands, koru-autopilot-vscode.src._shared.autopilot-bridge.then, koru-autopilot-vscode.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-vscodium.src.extension.AutopilotBridge.sock
- **Calls**: koru-autopilot-vscodium.src.extension.on, koru-autopilot-vscodium.src.extension.AutopilotBridge.debugLog, koru-autopilot-vscodium.src.extension.AutopilotBridge.detectIde, koru-autopilot-vscodium.src.extension.AutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscodium.src.extension.AutopilotBridge.resolve, koru-autopilot-vscodium.src.extension.getCommands, koru-autopilot-vscodium.src.extension.then, koru-autopilot-vscodium.src.extension.classifyCommands

### koru-autopilot-vscodium.src.extension.AutopilotBridge.connected
- **Calls**: koru-autopilot-vscodium.src.extension.on, koru-autopilot-vscodium.src.extension.AutopilotBridge.debugLog, koru-autopilot-vscodium.src.extension.AutopilotBridge.detectIde, koru-autopilot-vscodium.src.extension.AutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscodium.src.extension.AutopilotBridge.resolve, koru-autopilot-vscodium.src.extension.getCommands, koru-autopilot-vscodium.src.extension.then, koru-autopilot-vscodium.src.extension.classifyCommands

### koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.sock
- **Calls**: koru-autopilot-vscodium.src._shared.autopilot-bridge.on, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.debugLog, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.detectIde, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.resolve, koru-autopilot-vscodium.src._shared.autopilot-bridge.getCommands, koru-autopilot-vscodium.src._shared.autopilot-bridge.then, koru-autopilot-vscodium.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.connected
- **Calls**: koru-autopilot-vscodium.src._shared.autopilot-bridge.on, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.debugLog, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.detectIde, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.maybeOpenChatOnConnect, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.resolve, koru-autopilot-vscodium.src._shared.autopilot-bridge.getCommands, koru-autopilot-vscodium.src._shared.autopilot-bridge.then, koru-autopilot-vscodium.src._shared.autopilot-bridge.classifyCommands

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.random, koru-autopilot-shared.src.autopilot-bridge.toString, koru-autopilot-shared.src.autopilot-bridge.slice, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.focusChat, koru-autopilot-shared.src.autopilot-bridge.push, koru-autopilot-shared.src.autopilot-bridge.showWarningMessage, koru-autopilot-shared.src.autopilot-bridge.join

### koru-autopilot-antigravity.src.extension.AutopilotBridge.sock
- **Calls**: koru-autopilot-antigravity.src.extension.on, koru-autopilot-antigravity.src.extension.AutopilotBridge.debugLog, koru-autopilot-antigravity.src.extension.AutopilotBridge.detectIde, koru-autopilot-antigravity.src.extension.AutopilotBridge.resolve, koru-autopilot-antigravity.src.extension.getCommands, koru-autopilot-antigravity.src.extension.then, koru-autopilot-antigravity.src.extension.classifyCommands, koru-autopilot-antigravity.src.extension.matchingCommandsFlat

### koru-autopilot-antigravity.src.extension.AutopilotBridge.connected
- **Calls**: koru-autopilot-antigravity.src.extension.on, koru-autopilot-antigravity.src.extension.AutopilotBridge.debugLog, koru-autopilot-antigravity.src.extension.AutopilotBridge.detectIde, koru-autopilot-antigravity.src.extension.AutopilotBridge.resolve, koru-autopilot-antigravity.src.extension.getCommands, koru-autopilot-antigravity.src.extension.then, koru-autopilot-antigravity.src.extension.classifyCommands, koru-autopilot-antigravity.src.extension.matchingCommandsFlat

### koru-autopilot-antigravity.src.extension.AutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-antigravity.src.extension.random, koru-autopilot-antigravity.src.extension.toString, koru-autopilot-antigravity.src.extension.slice, koru-autopilot-antigravity.src.extension.AutopilotBridge.detectIde, koru-autopilot-antigravity.src.extension.AutopilotBridge.focusChat, koru-autopilot-antigravity.src.extension.push, koru-autopilot-antigravity.src.extension.showWarningMessage, koru-autopilot-antigravity.src.extension.join

### koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-cursor.src._shared.autopilot-bridge.random, koru-autopilot-cursor.src._shared.autopilot-bridge.toString, koru-autopilot-cursor.src._shared.autopilot-bridge.slice, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.focusChat, koru-autopilot-cursor.src._shared.autopilot-bridge.push, koru-autopilot-cursor.src._shared.autopilot-bridge.showWarningMessage, koru-autopilot-cursor.src._shared.autopilot-bridge.join

### koru-autopilot-windsurf.src.extension.AutopilotBridge.sock
- **Calls**: koru-autopilot-windsurf.src.extension.on, koru-autopilot-windsurf.src.extension.AutopilotBridge.debugLog, koru-autopilot-windsurf.src.extension.AutopilotBridge.detectIde, koru-autopilot-windsurf.src.extension.AutopilotBridge.resolve, koru-autopilot-windsurf.src.extension.getCommands, koru-autopilot-windsurf.src.extension.then, koru-autopilot-windsurf.src.extension.classifyCommands, koru-autopilot-windsurf.src.extension.matchingCommandsFlat

### koru-autopilot-windsurf.src.extension.AutopilotBridge.connected
- **Calls**: koru-autopilot-windsurf.src.extension.on, koru-autopilot-windsurf.src.extension.AutopilotBridge.debugLog, koru-autopilot-windsurf.src.extension.AutopilotBridge.detectIde, koru-autopilot-windsurf.src.extension.AutopilotBridge.resolve, koru-autopilot-windsurf.src.extension.getCommands, koru-autopilot-windsurf.src.extension.then, koru-autopilot-windsurf.src.extension.classifyCommands, koru-autopilot-windsurf.src.extension.matchingCommandsFlat

### koru-autopilot-windsurf.src.extension.AutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-windsurf.src.extension.random, koru-autopilot-windsurf.src.extension.toString, koru-autopilot-windsurf.src.extension.slice, koru-autopilot-windsurf.src.extension.AutopilotBridge.detectIde, koru-autopilot-windsurf.src.extension.AutopilotBridge.focusChat, koru-autopilot-windsurf.src.extension.push, koru-autopilot-windsurf.src.extension.showWarningMessage, koru-autopilot-windsurf.src.extension.join

### koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-vscode.src._shared.autopilot-bridge.random, koru-autopilot-vscode.src._shared.autopilot-bridge.toString, koru-autopilot-vscode.src._shared.autopilot-bridge.slice, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.detectIde, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.focusChat, koru-autopilot-vscode.src._shared.autopilot-bridge.push, koru-autopilot-vscode.src._shared.autopilot-bridge.showWarningMessage, koru-autopilot-vscode.src._shared.autopilot-bridge.join

### koru-autopilot-vscodium.src.extension.AutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-vscodium.src.extension.random, koru-autopilot-vscodium.src.extension.toString, koru-autopilot-vscodium.src.extension.slice, koru-autopilot-vscodium.src.extension.AutopilotBridge.detectIde, koru-autopilot-vscodium.src.extension.AutopilotBridge.focusChat, koru-autopilot-vscodium.src.extension.push, koru-autopilot-vscodium.src.extension.showWarningMessage, koru-autopilot-vscodium.src.extension.join

### koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.calibrateProbe
- **Calls**: koru-autopilot-vscodium.src._shared.autopilot-bridge.random, koru-autopilot-vscodium.src._shared.autopilot-bridge.toString, koru-autopilot-vscodium.src._shared.autopilot-bridge.slice, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.detectIde, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.focusChat, koru-autopilot-vscodium.src._shared.autopilot-bridge.push, koru-autopilot-vscodium.src._shared.autopilot-bridge.showWarningMessage, koru-autopilot-vscodium.src._shared.autopilot-bridge.join

### koru-autopilot-cursor.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-cursor.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-cursor.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-cursor.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-cursor.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-antigravity.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-antigravity.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-antigravity.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-antigravity.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-antigravity.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-vscode.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-vscode.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-vscode.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-vscode.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-vscode.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-vscode.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-windsurf.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-windsurf.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-windsurf.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-windsurf.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-windsurf.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-windsurf.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-vscodium.src.chat-history-watcher.test.main
- **Calls**: koru-autopilot-vscodium.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherEmitsNewBubblesAndAdvancesCursor, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse, koru-autopilot-vscodium.src.chat-history-watcher.test.testWatcherSwallowsAdapterErrors, koru-autopilot-vscodium.src.chat-history-watcher.test.testUnsupportedAdapterEmitsNothing, koru-autopilot-vscodium.src.chat-history-watcher.test.testBuildAdapterForIdeReturnsCorrectKind, koru-autopilot-vscodium.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses, koru-autopilot-vscodium.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directCommands
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.previousClip
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.clipboardSeeded
- **Calls**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.directPasteReadsClipboard, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.writeClipboardVerified, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.debugLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resolve, koru-autopilot-shared.src.autopilot-bridge.executeCommand, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sleep, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.probePasteDelayMs

### koru-autopilot-antigravity.src.extension.AutopilotBridge.directCommands
- **Calls**: koru-autopilot-antigravity.src.extension.AutopilotBridge.directPasteReadsClipboard, koru-autopilot-antigravity.src.extension.AutopilotBridge.writeClipboardVerified, koru-autopilot-antigravity.src.extension.AutopilotBridge.debugLog, koru-autopilot-antigravity.src.extension.AutopilotBridge.traceOperation, koru-autopilot-antigravity.src.extension.AutopilotBridge.resolve, koru-autopilot-antigravity.src.extension.executeCommand, koru-autopilot-antigravity.src.extension.AutopilotBridge.sleep, koru-autopilot-antigravity.src.extension.AutopilotBridge.probePasteDelayMs

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

## Key Classes

### koru-autopilot-vscodium.src.extension.AutopilotBridge
- **Methods**: 382
- **Key Methods**: koru-autopilot-vscodium.src.extension.AutopilotBridge.isConnected, koru-autopilot-vscodium.src.extension.AutopilotBridge.sendConsoleLog, koru-autopilot-vscodium.src.extension.AutopilotBridge.resetOperationTrace, koru-autopilot-vscodium.src.extension.AutopilotBridge.value, koru-autopilot-vscodium.src.extension.AutopilotBridge.commands, koru-autopilot-vscodium.src.extension.AutopilotBridge.server, koru-autopilot-vscodium.src.extension.AutopilotBridge.traceOperation, koru-autopilot-vscodium.src.extension.AutopilotBridge.safeLog, koru-autopilot-vscodium.src.extension.AutopilotBridge.emitLiveDsl, koru-autopilot-vscodium.src.extension.AutopilotBridge.seq

### koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge
- **Methods**: 376
- **Key Methods**: koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.isConnected, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sendConsoleLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.resetOperationTrace, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.value, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.commands, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.server, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.safeLog, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.emitLiveDsl, koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.seq

### koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge
- **Methods**: 376
- **Key Methods**: koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.isConnected, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.sendConsoleLog, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.resetOperationTrace, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.value, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.commands, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.server, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.safeLog, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.emitLiveDsl, koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.seq

### koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge
- **Methods**: 376
- **Key Methods**: koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.isConnected, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.sendConsoleLog, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.resetOperationTrace, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.value, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.commands, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.server, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.traceOperation, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.safeLog, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.emitLiveDsl, koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.seq

### koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge
- **Methods**: 375
- **Key Methods**: koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.isConnected, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.sendConsoleLog, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.resetOperationTrace, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.value, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.commands, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.server, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.traceOperation, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.safeLog, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.emitLiveDsl, koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.seq

### koru-autopilot-antigravity.src.extension.AutopilotBridge
- **Methods**: 358
- **Key Methods**: koru-autopilot-antigravity.src.extension.AutopilotBridge.isConnected, koru-autopilot-antigravity.src.extension.AutopilotBridge.sendConsoleLog, koru-autopilot-antigravity.src.extension.AutopilotBridge.resetOperationTrace, koru-autopilot-antigravity.src.extension.AutopilotBridge.value, koru-autopilot-antigravity.src.extension.AutopilotBridge.commands, koru-autopilot-antigravity.src.extension.AutopilotBridge.server, koru-autopilot-antigravity.src.extension.AutopilotBridge.traceOperation, koru-autopilot-antigravity.src.extension.AutopilotBridge.safeLog, koru-autopilot-antigravity.src.extension.AutopilotBridge.emitLiveDsl, koru-autopilot-antigravity.src.extension.AutopilotBridge.seq

### koru-autopilot-windsurf.src.extension.AutopilotBridge
- **Methods**: 358
- **Key Methods**: koru-autopilot-windsurf.src.extension.AutopilotBridge.isConnected, koru-autopilot-windsurf.src.extension.AutopilotBridge.sendConsoleLog, koru-autopilot-windsurf.src.extension.AutopilotBridge.resetOperationTrace, koru-autopilot-windsurf.src.extension.AutopilotBridge.value, koru-autopilot-windsurf.src.extension.AutopilotBridge.commands, koru-autopilot-windsurf.src.extension.AutopilotBridge.server, koru-autopilot-windsurf.src.extension.AutopilotBridge.traceOperation, koru-autopilot-windsurf.src.extension.AutopilotBridge.safeLog, koru-autopilot-windsurf.src.extension.AutopilotBridge.emitLiveDsl, koru-autopilot-windsurf.src.extension.AutopilotBridge.seq

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-vscode.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-windsurf.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter
- **Methods**: 17
- **Key Methods**: koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.storeAvailable, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.fetchNewer, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.r, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractResponsesFromSession, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.responses, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.resp, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.ts, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.text, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-vscodium.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.trimmed

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-windsurf.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter
- **Methods**: 16
- **Key Methods**: koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.storeAvailable, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.fetchNewer, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.lastRowid, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.latestBubbleRowid, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.n, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.r, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.recSep, koru-autopilot-vscodium.src.cursor-bubble-adapter.CursorBubbleAdapter.fldSep

### koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher
- **Methods**: 11
- **Key Methods**: koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.currentCursor, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.adapterDescription, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.setCursor, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.start, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.tick, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.stop, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.clearInterval, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.pollOnce, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.cursorAdvances, koru-autopilot-antigravity.src.chat-history-watcher.ChatHistoryWatcher.a

### koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher
- **Methods**: 11
- **Key Methods**: koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.currentCursor, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.adapterDescription, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.setCursor, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.start, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.tick, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.stop, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.clearInterval, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.pollOnce, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.cursorAdvances, koru-autopilot-cursor.src.chat-history-watcher.ChatHistoryWatcher.a

### koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher
- **Methods**: 11
- **Key Methods**: koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.currentCursor, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.adapterDescription, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.setCursor, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.start, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.tick, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.stop, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.clearInterval, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.pollOnce, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.cursorAdvances, koru-autopilot-vscode.src.chat-history-watcher.ChatHistoryWatcher.a

## Data Transformation Functions

Key functions that process and transform data:

### koru-autopilot-shared.src.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-shared.src.host-click-submit.split, koru-autopilot-shared.src.host-click-submit.match, koru-autopilot-shared.src.host-click-submit.parseInt, koru-autopilot-shared.src.host-click-submit.every, koru-autopilot-shared.src.host-click-submit.isFinite

### koru-autopilot-antigravity.src.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-antigravity.src.host-click-submit.split, koru-autopilot-antigravity.src.host-click-submit.match, koru-autopilot-antigravity.src.host-click-submit.parseInt, koru-autopilot-antigravity.src.host-click-submit.every, koru-autopilot-antigravity.src.host-click-submit.isFinite

### koru-autopilot-antigravity.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows
- **Output to**: koru-autopilot-antigravity.src.cursor-bubble-adapter.includes, koru-autopilot-antigravity.src.cursor-bubble-adapter.split, koru-autopilot-antigravity.src.cursor-bubble-adapter.trim, koru-autopilot-antigravity.src.cursor-bubble-adapter.parseInt, koru-autopilot-antigravity.src.cursor-bubble-adapter.isFinite

### koru-autopilot-antigravity.src.host-click-submit.test.testParseXdotoolGeometryShell
- **Output to**: koru-autopilot-antigravity.src.host-click-submit.test.parseXdotoolGeometryShell, koru-autopilot-antigravity.src.host-click-submit.test.Error, koru-autopilot-antigravity.src.host-click-submit.test.assert

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.trim, koru-autopilot-antigravity.src.vscode-chat-session-adapter.parse

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.parseFloat

### koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseVSCodeChatIndex
- **Output to**: koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractEntriesMap, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor, koru-autopilot-antigravity.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.entries, koru-autopilot-antigravity.src.vscode-chat-session-adapter.push

### koru-autopilot-antigravity.src._shared.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-antigravity.src._shared.host-click-submit.split, koru-autopilot-antigravity.src._shared.host-click-submit.match, koru-autopilot-antigravity.src._shared.host-click-submit.parseInt, koru-autopilot-antigravity.src._shared.host-click-submit.every, koru-autopilot-antigravity.src._shared.host-click-submit.isFinite

### koru-autopilot-cursor.src.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-cursor.src.host-click-submit.split, koru-autopilot-cursor.src.host-click-submit.match, koru-autopilot-cursor.src.host-click-submit.parseInt, koru-autopilot-cursor.src.host-click-submit.every, koru-autopilot-cursor.src.host-click-submit.isFinite

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-cursor.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.stringify, koru-autopilot-cursor.src.chat-history-watcher.test.answer, koru-autopilot-cursor.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual, koru-autopilot-cursor.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-cursor.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-cursor.src.chat-history-watcher.test.stringify, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-cursor.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-cursor.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-cursor.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.host-click-submit.test.testParseXdotoolGeometryShell
- **Output to**: koru-autopilot-cursor.src.host-click-submit.test.parseXdotoolGeometryShell, koru-autopilot-cursor.src.host-click-submit.test.Error, koru-autopilot-cursor.src.host-click-submit.test.assert

### koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson
- **Output to**: koru-autopilot-cursor.src.vscode-chat-session-adapter.trim, koru-autopilot-cursor.src.vscode-chat-session-adapter.parse

### koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor
- **Output to**: koru-autopilot-cursor.src.vscode-chat-session-adapter.parseFloat

### koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseVSCodeChatIndex
- **Output to**: koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.extractEntriesMap, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.safeParseJson, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.parseAfterCursor, koru-autopilot-cursor.src.vscode-chat-session-adapter.VSCodeChatSessionAdapter.entries, koru-autopilot-cursor.src.vscode-chat-session-adapter.push

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseCursorBubbleRowsHandlesMultilineText
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.buildSqliteOutput, koru-autopilot-antigravity.src.chat-history-watcher.test.parseCursorBubbleRows, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexExtractsAssistantResponses
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.stringify, koru-autopilot-antigravity.src.chat-history-watcher.test.answer, koru-autopilot-antigravity.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual, koru-autopilot-antigravity.src.chat-history-watcher.test.deepStrictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testParseVSCodeChatIndexReturnsEmptyOnGarbage
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.deepStrictEqual, koru-autopilot-antigravity.src.chat-history-watcher.test.parseVSCodeChatIndex, koru-autopilot-antigravity.src.chat-history-watcher.test.stringify, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-antigravity.src.chat-history-watcher.test.testCursorBubbleAdapterLatestBubbleRowidParsesMax
- **Output to**: koru-autopilot-antigravity.src.chat-history-watcher.test.CursorBubbleAdapter, koru-autopilot-antigravity.src.chat-history-watcher.test.latestBubbleRowid, koru-autopilot-antigravity.src.chat-history-watcher.test.strictEqual

### koru-autopilot-cursor.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows
- **Output to**: koru-autopilot-cursor.src.cursor-bubble-adapter.includes, koru-autopilot-cursor.src.cursor-bubble-adapter.split, koru-autopilot-cursor.src.cursor-bubble-adapter.trim, koru-autopilot-cursor.src.cursor-bubble-adapter.parseInt, koru-autopilot-cursor.src.cursor-bubble-adapter.isFinite

### koru-autopilot-cursor.src._shared.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-cursor.src._shared.host-click-submit.split, koru-autopilot-cursor.src._shared.host-click-submit.match, koru-autopilot-cursor.src._shared.host-click-submit.parseInt, koru-autopilot-cursor.src._shared.host-click-submit.every, koru-autopilot-cursor.src._shared.host-click-submit.isFinite

### koru-autopilot-vscode.src.host-click-submit.parseXdotoolGeometryShell
- **Output to**: koru-autopilot-vscode.src.host-click-submit.split, koru-autopilot-vscode.src.host-click-submit.match, koru-autopilot-vscode.src.host-click-submit.parseInt, koru-autopilot-vscode.src.host-click-submit.every, koru-autopilot-vscode.src.host-click-submit.isFinite

### koru-autopilot-vscode.src.cursor-bubble-adapter.CursorBubbleAdapter.parseCursorBubbleRows
- **Output to**: koru-autopilot-vscode.src.cursor-bubble-adapter.includes, koru-autopilot-vscode.src.cursor-bubble-adapter.split, koru-autopilot-vscode.src.cursor-bubble-adapter.trim, koru-autopilot-vscode.src.cursor-bubble-adapter.parseInt, koru-autopilot-vscode.src.cursor-bubble-adapter.isFinite

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryCursorComposerPromptFastPath` - 24 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.tryCursorComposerPromptFastPath` - 22 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.tryCursorComposerPromptFastPath` - 22 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.tryCursorComposerPromptFastPath` - 22 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-vscodium.src.extension.AutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.tryConnectNext` - 20 calls
- `koru-autopilot-antigravity.src.extension.AutopilotBridge.tryConnectNext` - 19 calls
- `koru-autopilot-windsurf.src.extension.AutopilotBridge.tryConnectNext` - 19 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.sock` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.connected` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-antigravity.src.extension.AutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-antigravity.src.extension.AutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.sock` - 15 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.connected` - 15 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-cursor.src._shared.autopilot-bridge.SharedAutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-windsurf.src.extension.AutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-windsurf.src.extension.AutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.sock` - 15 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.connected` - 15 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-vscode.src._shared.autopilot-bridge.SharedAutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-vscodium.src.extension.AutopilotBridge.sock` - 15 calls
- `koru-autopilot-vscodium.src.extension.AutopilotBridge.connected` - 15 calls
- `koru-autopilot-vscodium.src.extension.AutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-vscodium.src.extension.AutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.sock` - 15 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.connected` - 15 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.submitChat` - 15 calls
- `koru-autopilot-vscodium.src._shared.autopilot-bridge.AutopilotBridge.pasteText` - 15 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.focusChatInput` - 14 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.injectChat` - 14 calls
- `koru-autopilot-shared.src.autopilot-bridge.SharedAutopilotBridge.calibrateProbe` - 14 calls
- `koru-autopilot-antigravity.src.extension.AutopilotBridge.sock` - 14 calls
- `koru-autopilot-antigravity.src.extension.AutopilotBridge.connected` - 14 calls

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
    sock --> getCommands
    connected --> getCommands
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.