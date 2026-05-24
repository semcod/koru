import * as cp from "child_process";
import * as fs from "fs";
import { promisify } from "util";

import { defaultGlobalStateDbPath } from "./chat-history-paths";
import type { AdapterRunner, ChatHistoryRow, IdeAdapter, SupportedIde } from "./chat-history-types";

const execFile = promisify(cp.execFile);

interface VSCodeChatSessionEntry {
  sessionId: string;
  title?: string;
  lastMessageDate?: number;
  responses?: Array<{ message?: { text?: string } | string; createdAt?: number }>;
}

/**
 * Best-effort adapter for VS Code's Built-in Chat API.
 *
 * The store layout we target is the JSON value of
 * ``ItemTable.chat.ChatSessionStore.index`` in either ``globalStorage``
 * or per-workspace ``workspaceStorage`` ``state.vscdb``. The schema is
 * not part of VS Code's public API and may change; we therefore look for
 * any sub-object that smells like an assistant response and skip rows we
 * cannot understand.
 */
export class VSCodeChatSessionAdapter implements IdeAdapter {
  readonly ide: SupportedIde;
  readonly description = "ItemTable.chat.ChatSessionStore.index (VS Code Built-in Chat)";
  private readonly dbPath: string;
  private readonly sqlite: string;

  constructor(opts: { ide?: SupportedIde; dbPath?: string; sqliteBinary?: string } = {}) {
    this.ide = opts.ide ?? "vscode";
    this.dbPath = opts.dbPath ?? defaultGlobalStateDbPath(this.ide);
    this.sqlite = opts.sqliteBinary ?? "sqlite3";
  }

  storeAvailable(): boolean {
    try {
      return fs.existsSync(this.dbPath);
    } catch {
      return false;
    }
  }

  async fetchNewer(afterCursor: string, runner: AdapterRunner | null): Promise<ChatHistoryRow[]> {
    const args = [
      "-readonly",
      "-bail",
      "-noheader",
      this.dbPath,
      "SELECT value FROM ItemTable WHERE key='chat.ChatSessionStore.index';",
    ];
    const exec = runner ?? (async (bin, a) => {
      const r = await execFile(bin, a, { maxBuffer: 8 * 1024 * 1024 });
      return { stdout: r.stdout, stderr: r.stderr };
    });
    let stdout = "";
    try {
      const r = await exec(this.sqlite, args);
      stdout = r.stdout;
    } catch {
      return [];
    }
    return parseVSCodeChatIndex(stdout, afterCursor);
  }
}

function extractResponsesFromSession(
  sessionId: string,
  entry: VSCodeChatSessionEntry,
  after: number
): ChatHistoryRow[] {
  const responses = Array.isArray(entry.responses) ? entry.responses : [];
  const rows: ChatHistoryRow[] = [];
  for (let i = 0; i < responses.length; i++) {
    const resp = responses[i];
    if (!resp || typeof resp !== "object") continue;
    const ts = typeof resp.createdAt === "number" ? resp.createdAt : (entry.lastMessageDate ?? 0);
    if (ts <= after) continue;
    const text = extractMessageText(resp.message);
    if (!text) continue;
    rows.push({
      cursor: String(ts),
      bubbleId: `${sessionId}#${i}`,
      conversationId: sessionId,
      type: 2,
      text,
      createdAt: ts ? new Date(ts).toISOString() : "",
    });
  }
  return rows;
}

function safeParseJson(jsonText: string): unknown {
  const trimmed = jsonText.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function extractEntriesMap(parsed: unknown): Record<string, unknown> | null {
  if (!parsed || typeof parsed !== "object") return null;
  const entriesRaw = (parsed as { entries?: unknown }).entries;
  if (!entriesRaw || typeof entriesRaw !== "object") return null;
  return entriesRaw as Record<string, unknown>;
}

function parseAfterCursor(afterCursor: string): number {
  return Number.parseFloat(afterCursor || "0") || 0;
}

export function parseVSCodeChatIndex(jsonText: string, afterCursor: string): ChatHistoryRow[] {
  const entries = extractEntriesMap(safeParseJson(jsonText));
  if (!entries) return [];
  const after = parseAfterCursor(afterCursor);
  const rows: ChatHistoryRow[] = [];
  for (const [sessionId, entryRaw] of Object.entries(entries)) {
    if (!entryRaw || typeof entryRaw !== "object") continue;
    rows.push(...extractResponsesFromSession(sessionId, entryRaw as VSCodeChatSessionEntry, after));
  }
  rows.sort((a, b) => Number(a.cursor) - Number(b.cursor));
  return rows.slice(0, 50);
}

function extractMessageText(raw: unknown): string {
  if (typeof raw === "string") return raw;
  if (raw && typeof raw === "object" && typeof (raw as { text?: unknown }).text === "string") {
    return (raw as { text: string }).text;
  }
  return "";
}