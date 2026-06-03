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
import { cursorBubbleTextMatchesPrompt } from "./_shared/submit-match";

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
  // ``koru-autopilot-cursor`` is the Cursor-only VSIX; the factory must
  // ONLY know about CursorBubbleAdapter. Asking it for vscode/vscodium/
  // windsurf/antigravity adapters must throw so a stray code path that
  // accidentally registers a non-Cursor IDE blows up loudly in CI rather
  // than silently producing the wrong adapter.
  assert.ok(buildAdapterForIde("cursor") instanceof CursorBubbleAdapter);
  for (const foreign of ["vscode", "vscodium", "windsurf", "antigravity"] as const) {
    let threw = false;
    try {
      buildAdapterForIde(foreign);
    } catch (err) {
      threw = true;
      assert.match(String(err), /Cursor support/);
    }
    assert.ok(threw, `buildAdapterForIde must refuse to construct an adapter for ${foreign}`);
  }
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

async function testCursorBubbleAdapterFetchLatestUserBubblesPassesAnchor(): Promise<void> {
  const capturedArgs: string[][] = [];
  const adapter = new CursorBubbleAdapter({
    ide: "cursor",
    dbPath: "/tmp/nonexistent.vscdb",
  });
  const fakeRunner = async (_bin: string, args: string[]) => {
    capturedArgs.push(args);
    return {
      stdout: buildSqliteOutput([
        {
          cursor: "42",
          conversationId: "conv1",
          bubbleId: "user-bubble-1",
          type: 1,
          text: "Run a broad project discovery pass… STARTER-237",
          createdAt: "2026-05-25T10:00:00.000Z",
        },
      ]),
      stderr: "",
    };
  };
  const rows = await adapter.fetchLatestUserBubbles(99, fakeRunner);
  assert.strictEqual(capturedArgs.length, 1);
  const sqlArg = capturedArgs[0][capturedArgs[0].length - 1] || "";
  assert.ok(
    sqlArg.includes("AND json_extract(value,'$.type') = 1"),
    "must filter to type=1 (user bubbles)",
  );
  assert.ok(sqlArg.includes("rowid > 99"), "must use the anchor rowid as lower bound");
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].type, 1);
  assert.strictEqual(rows[0].bubbleId, "user-bubble-1");
}

async function testCursorBubbleAdapterLatestBubbleRowidParsesMax(): Promise<void> {
  const adapter = new CursorBubbleAdapter({
    ide: "cursor",
    dbPath: "/tmp/nonexistent.vscdb",
  });
  const fakeRunner = async () => ({ stdout: "  101\n", stderr: "" });
  const rowid = await adapter.latestBubbleRowid(fakeRunner);
  assert.strictEqual(rowid, 101);

  const adapterEmpty = new CursorBubbleAdapter({
    ide: "cursor",
    dbPath: "/tmp/nonexistent.vscdb",
  });
  const emptyRunner = async () => ({ stdout: "", stderr: "" });
  const rowidEmpty = await adapterEmpty.latestBubbleRowid(emptyRunner);
  assert.strictEqual(rowidEmpty, 0, "empty stdout must yield 0 instead of NaN");
}


async function testCursorBubbleMatchAcceptsNormalizedTail(): Promise<void> {
  const prompt = "Planfile status handoff:\n- run: planfile ticket done STARTER-437";
  const bubble = "Planfile status handoff:   - run: planfile ticket done STARTER-437";
  const result = cursorBubbleTextMatchesPrompt(bubble, prompt);

  assert.strictEqual(result.matched, true);
  assert.strictEqual(result.mode, "tail");
}


async function testCursorBubbleMatchAcceptsNormalizedHeadWhenTailMissing(): Promise<void> {
  const prompt = [
    "code2llm reports packages.coru.src.coru.cli._chat_loop with CC=36.",
    "Extract smaller functions and keep tests green.",
    "Planfile status handoff:",
    "- planfile ticket done STARTER-437",
  ].join("\n");
  const bubble = "code2llm reports packages.coru.src.coru.cli._chat_loop with CC=36. Extract smaller functions and keep tests green.";
  const result = cursorBubbleTextMatchesPrompt(bubble, prompt);

  assert.strictEqual(result.matched, true);
  assert.strictEqual(result.mode, "head");
}


async function testCursorBubbleMatchAcceptsMiddleSliceForLongPrompts(): Promise<void> {
  const prefix = "A".repeat(200);
  const middle = "Shotgun Surgery: allowed in src/koruide/protocol.py spans 5 functions";
  const suffix = "B".repeat(200);
  const prompt = `${prefix}${middle}${suffix}`;
  const bubble = `…${middle}…`;
  const result = cursorBubbleTextMatchesPrompt(bubble, prompt);

  assert.strictEqual(result.matched, true);
  assert.strictEqual(result.mode, "middle");
}


async function testCursorBubbleMatchRejectsUnrelatedText(): Promise<void> {
  const prompt = "planfile ticket done STARTER-437";
  const bubble = "unrelated user message in another chat";
  const result = cursorBubbleTextMatchesPrompt(bubble, prompt);

  assert.strictEqual(result.matched, false);
  assert.strictEqual(result.mode, "none");
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
  await testCursorBubbleAdapterFetchLatestUserBubblesPassesAnchor();
  await testCursorBubbleAdapterLatestBubbleRowidParsesMax();
  await testCursorBubbleMatchAcceptsNormalizedTail();
  await testCursorBubbleMatchAcceptsNormalizedHeadWhenTailMissing();
  await testCursorBubbleMatchAcceptsMiddleSliceForLongPrompts();
  await testCursorBubbleMatchRejectsUnrelatedText();
  console.log("chat-history-watcher tests: ok");
}

void main().catch((err) => {
  console.error(err);
  process.exit(1);
});
