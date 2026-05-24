import * as assert from "assert";
import {
  buildAdapterForIde,
  ChatHistoryRow,
  ChatHistoryWatcher,
  CursorBubbleAdapter,
  IdeAdapter,
  parseCursorBubbleRows,
  parseVSCodeChatIndex,
  UnsupportedAdapter,
  VSCodeChatSessionAdapter,
} from "./chat-history-watcher";

function buildSqliteOutput(rows: ChatHistoryRow[]): string {
  return rows
    .map((r) =>
      [r.cursor, `bubbleId:${r.conversationId}:${r.bubbleId}`, r.type, r.text, r.createdAt].join("\x1f"),
    )
    .join("\x1e");
}

async function testParseCursorBubbleRowsHandlesMultilineText(): Promise<void> {
  const stdout = buildSqliteOutput([
    {
      cursor: "100",
      conversationId: "0f8b8f5b",
      bubbleId: "abc-123",
      type: 2,
      text: "Hello\nworld\npipe|inside",
      createdAt: "2026-05-23T00:00:00.000Z",
    },
    {
      cursor: "101",
      conversationId: "0f8b8f5b",
      bubbleId: "def-456",
      type: 2,
      text: "Second response",
      createdAt: "2026-05-23T00:00:01.000Z",
    },
  ]);
  const rows = parseCursorBubbleRows(stdout);
  assert.strictEqual(rows.length, 2);
  assert.strictEqual(rows[0].text, "Hello\nworld\npipe|inside", "newlines and pipes inside text must be preserved");
  assert.strictEqual(rows[0].cursor, "100");
  assert.strictEqual(rows[0].conversationId, "0f8b8f5b");
  assert.strictEqual(rows[0].bubbleId, "abc-123");
  assert.strictEqual(rows[1].cursor, "101");
}

async function testWatcherEmitsNewBubblesAndAdvancesCursor(): Promise<void> {
  const seen: ChatHistoryRow[] = [];
  let call = 0;
  const fakeRunner = async () => {
    call += 1;
    if (call === 1) {
      return {
        stdout: buildSqliteOutput([
          {
            cursor: "10",
            conversationId: "conv1",
            bubbleId: "b1",
            type: 2,
            text: "first",
            createdAt: "t1",
          },
        ]),
        stderr: "",
      };
    }
    return {
      stdout: buildSqliteOutput([
        {
          cursor: "11",
          conversationId: "conv1",
          bubbleId: "b2",
          type: 2,
          text: "second",
          createdAt: "t2",
        },
      ]),
      stderr: "",
    };
  };
  const adapter: IdeAdapter = {
    ide: "cursor",
    description: "test cursor adapter",
    storeAvailable: () => true,
    fetchNewer: (_after, runner) => {
      const r = runner ?? fakeRunner;
      return r("sqlite3", []).then((res) => parseCursorBubbleRows(res.stdout));
    },
  };
  const advances: string[] = [];
  const watcher = new ChatHistoryWatcher({
    ide: "cursor",
    adapter,
    runner: fakeRunner,
    onMessage: (row) => {
      seen.push(row);
    },
    onCursorAdvance: (c) => {
      advances.push(c);
    },
  });
  await watcher.pollOnce();
  assert.deepStrictEqual(seen.map((r) => r.text), ["first"]);
  assert.strictEqual(watcher.currentCursor, "10", "cursor must advance after delivery");
  await watcher.pollOnce();
  assert.deepStrictEqual(seen.map((r) => r.text), ["first", "second"]);
  assert.strictEqual(watcher.currentCursor, "11");
  assert.deepStrictEqual(advances, ["10", "11"], "onCursorAdvance must fire each step");
}

async function testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse(): Promise<void> {
  const adapter: IdeAdapter = {
    ide: "cursor",
    description: "test",
    storeAvailable: () => true,
    fetchNewer: async () => [
      {
        cursor: "42",
        conversationId: "conv1",
        bubbleId: "b1",
        type: 2,
        text: "hello",
        createdAt: "t",
      },
    ],
  };
  const watcher = new ChatHistoryWatcher({
    ide: "cursor",
    adapter,
    onMessage: () => false,
  });
  await watcher.pollOnce();
  assert.strictEqual(
    watcher.currentCursor,
    "",
    "delivery callback returning false must keep cursor unchanged so the row re-delivers",
  );
}

async function testWatcherSwallowsAdapterErrors(): Promise<void> {
  const adapter: IdeAdapter = {
    ide: "cursor",
    description: "broken",
    storeAvailable: () => true,
    fetchNewer: async () => {
      throw new Error("sqlite3 not found");
    },
  };
  const watcher = new ChatHistoryWatcher({
    ide: "cursor",
    adapter,
    onMessage: () => {},
  });
  const rows = await watcher.pollOnce();
  assert.deepStrictEqual(rows, [], "errors must fail-closed: no crash, no rows");
}

async function testUnsupportedAdapterEmitsNothing(): Promise<void> {
  const adapter = new UnsupportedAdapter("windsurf", "encrypted");
  assert.strictEqual(adapter.storeAvailable(), false);
  const rows = await adapter.fetchNewer();
  assert.deepStrictEqual(rows, []);
}

async function testBuildAdapterForIdeReturnsCorrectKind(): Promise<void> {
  assert.ok(buildAdapterForIde("cursor") instanceof CursorBubbleAdapter);
  assert.ok(buildAdapterForIde("vscode") instanceof VSCodeChatSessionAdapter);
  assert.ok(buildAdapterForIde("vscodium") instanceof VSCodeChatSessionAdapter);
  assert.ok(buildAdapterForIde("windsurf") instanceof UnsupportedAdapter);
  assert.ok(buildAdapterForIde("antigravity") instanceof UnsupportedAdapter);
}

async function testParseVSCodeChatIndexExtractsAssistantResponses(): Promise<void> {
  const payload = JSON.stringify({
    version: 1,
    entries: {
      "session-A": {
        sessionId: "session-A",
        title: "Refactor",
        lastMessageDate: 1700000000000,
        responses: [
          { message: { text: "First answer" }, createdAt: 1700000001000 },
          { message: "Second answer (string form)", createdAt: 1700000002000 },
          { message: null, createdAt: 1700000003000 },
        ],
      },
      "session-B": {
        sessionId: "session-B",
        responses: [
          { message: { text: "Older B" }, createdAt: 1690000000000 },
          { message: { text: "Newer B" }, createdAt: 1700000005000 },
        ],
      },
    },
  });

  const allRows = parseVSCodeChatIndex(payload, "0");
  assert.strictEqual(allRows.length, 4, "should ignore the null message but keep the rest");
  assert.deepStrictEqual(
    allRows.map((r) => r.text),
    ["Older B", "First answer", "Second answer (string form)", "Newer B"],
    "rows must be sorted oldest-first",
  );
  assert.strictEqual(allRows[0].conversationId, "session-B");
  assert.strictEqual(allRows[0].type, 2);

  const partialRows = parseVSCodeChatIndex(payload, "1700000001500");
  assert.deepStrictEqual(
    partialRows.map((r) => r.text),
    ["Second answer (string form)", "Newer B"],
    "afterCursor must filter older rows by their createdAt epoch",
  );
}

async function testParseVSCodeChatIndexReturnsEmptyOnGarbage(): Promise<void> {
  assert.deepStrictEqual(parseVSCodeChatIndex("", "0"), []);
  assert.deepStrictEqual(parseVSCodeChatIndex("not json", "0"), []);
  assert.deepStrictEqual(parseVSCodeChatIndex(JSON.stringify({ version: 1, entries: {} }), "0"), []);
  assert.deepStrictEqual(parseVSCodeChatIndex(JSON.stringify({ version: 1 }), "0"), []);
  // entries must be an object — string/number/array are rejected
  assert.deepStrictEqual(
    parseVSCodeChatIndex(JSON.stringify({ entries: "nope" }), "0"),
    [],
    "entries=string must yield no rows",
  );
  assert.deepStrictEqual(
    parseVSCodeChatIndex(JSON.stringify({ entries: 42 }), "0"),
    [],
    "entries=number must yield no rows",
  );
  // null sessions inside entries must be skipped without throwing
  const payload = JSON.stringify({
    entries: {
      "session-broken": null,
      "session-ok": {
        sessionId: "session-ok",
        responses: [
          { message: { text: "kept" }, createdAt: 1700000010000 },
        ],
      },
    },
  });
  const rows = parseVSCodeChatIndex(payload, "0");
  assert.strictEqual(rows.length, 1, "broken null session must be skipped, valid kept");
  assert.strictEqual(rows[0].text, "kept");
  // afterCursor parsing: malformed input falls back to 0 (does not throw)
  const allRows = parseVSCodeChatIndex(payload, "not-a-number");
  assert.strictEqual(allRows.length, 1, "malformed afterCursor must be treated as 0");
}

async function testWatcherSkipsPollingWhenStoreUnavailable(): Promise<void> {
  let polls = 0;
  const adapter: IdeAdapter = {
    ide: "windsurf",
    description: "encrypted (test)",
    storeAvailable: () => false,
    fetchNewer: async () => {
      polls += 1;
      return [];
    },
  };
  const logs: Array<{ msg: string; data?: unknown }> = [];
  const watcher = new ChatHistoryWatcher({
    ide: "windsurf",
    adapter,
    log: (msg, data) => logs.push({ msg, data }),
    onMessage: () => {},
  });
  watcher.start();
  watcher.stop();
  assert.strictEqual(polls, 0, "must not poll an unsupported store");
  assert.ok(
    logs.some((entry) => entry.msg === "CHAT_HISTORY_UNSUPPORTED"),
    "must log CHAT_HISTORY_UNSUPPORTED once for stub adapters",
  );
}

async function main(): Promise<void> {
  await testParseCursorBubbleRowsHandlesMultilineText();
  await testWatcherEmitsNewBubblesAndAdvancesCursor();
  await testWatcherDoesNotAdvanceWhenDeliveryReturnsFalse();
  await testWatcherSwallowsAdapterErrors();
  await testUnsupportedAdapterEmitsNothing();
  await testBuildAdapterForIdeReturnsCorrectKind();
  await testParseVSCodeChatIndexExtractsAssistantResponses();
  await testParseVSCodeChatIndexReturnsEmptyOnGarbage();
  await testWatcherSkipsPollingWhenStoreUnavailable();
  console.log("chat-history-watcher tests: ok");
}

void main().catch((err) => {
  console.error(err);
  process.exit(1);
});
