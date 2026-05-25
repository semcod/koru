import * as cp from "child_process";
import * as fs from "fs";
import { promisify } from "util";

import { defaultGlobalStateDbPath } from "./chat-history-paths";
import type { AdapterRunner, ChatHistoryRow, IdeAdapter, SupportedIde } from "./chat-history-types";

const execFile = promisify(cp.execFile);

const SQL_CURSOR_NEW_BUBBLES = `SELECT rowid, key, json_extract(value,'$.type'), json_extract(value,'$.text'), json_extract(value,'$.createdAt')
FROM cursorDiskKV
WHERE key LIKE 'bubbleId:%'
  AND rowid > ?
  AND json_extract(value,'$.type') = 2
  AND length(json_extract(value,'$.text')) > 0
ORDER BY rowid ASC
LIMIT 50;`;

const SQL_CURSOR_LATEST_USER_BUBBLES = `SELECT rowid, key, json_extract(value,'$.type'), json_extract(value,'$.text'), json_extract(value,'$.createdAt')
FROM cursorDiskKV
WHERE key LIKE 'bubbleId:%'
  AND rowid > ?
  AND json_extract(value,'$.type') = 1
  AND length(json_extract(value,'$.text')) > 0
ORDER BY rowid DESC
LIMIT 5;`;

export class CursorBubbleAdapter implements IdeAdapter {
  readonly ide: SupportedIde;
  readonly description = "cursorDiskKV.bubbleId (Cursor SQLite)";
  private readonly dbPath: string;
  private readonly sqlite: string;

  constructor(opts: { ide?: SupportedIde; dbPath?: string; sqliteBinary?: string } = {}) {
    this.ide = opts.ide ?? "cursor";
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
    const lastRowid = Number.parseInt(afterCursor || "0", 10) || 0;
    return this._runQuery(SQL_CURSOR_NEW_BUBBLES, lastRowid, runner);
  }

  /**
   * Fetch the most recent ``type = 1`` (user) bubbles strictly after
   * ``afterRowid``. Used to verify that a programmatic submit actually
   * persisted to Cursor's conversation store — the only reliable signal
   * since ``editor.action.selectAll`` cannot reach Cursor's chat webview
   * and the post-submit clipboard probe always returns ``null``.
   */
  async fetchLatestUserBubbles(
    afterRowid: number,
    runner: AdapterRunner | null
  ): Promise<ChatHistoryRow[]> {
    return this._runQuery(SQL_CURSOR_LATEST_USER_BUBBLES, afterRowid, runner);
  }

  /**
   * Highest ``rowid`` currently in ``cursorDiskKV`` for any bubble. Used
   * as a "since" anchor: capture it BEFORE submit, then look for a fresh
   * user bubble with ``rowid > anchor`` after submit.
   */
  async latestBubbleRowid(runner: AdapterRunner | null): Promise<number> {
    const args = [
      "-readonly",
      "-bail",
      "-noheader",
      this.dbPath,
      "SELECT COALESCE(MAX(rowid), 0) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%';",
    ];
    const exec = runner ?? (async (bin, a) => {
      const r = await execFile(bin, a, { maxBuffer: 1024 * 1024 });
      return { stdout: r.stdout, stderr: r.stderr };
    });
    try {
      const r = await exec(this.sqlite, args);
      const n = Number.parseInt((r.stdout || "0").trim(), 10);
      return Number.isFinite(n) ? n : 0;
    } catch {
      return 0;
    }
  }

  private async _runQuery(
    sql: string,
    rowid: number,
    runner: AdapterRunner | null
  ): Promise<ChatHistoryRow[]> {
    const args = [
      "-readonly",
      "-bail",
      "-noheader",
      "-cmd",
      ".separator \\x1f \\x1e",
      this.dbPath,
      sql.replace("?", String(rowid)),
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
    return parseCursorBubbleRows(stdout);
  }
}

/**
 * Parse a 0x1f/0x1e-separated dump (or pipe/newline fallback used by
 * tests for readability) into structured rows.
 */
export function parseCursorBubbleRows(stdout: string): ChatHistoryRow[] {
  const rows: ChatHistoryRow[] = [];
  if (!stdout) return rows;
  const recSep = stdout.includes("\x1e") ? "\x1e" : "\n";
  const fldSep = stdout.includes("\x1f") ? "\x1f" : "|";
  for (const rec of stdout.split(recSep)) {
    if (!rec.trim()) continue;
    const fields = rec.split(fldSep);
    if (fields.length < 5) continue;
    const [rowidStr, key, typeStr, text, createdAt] = fields;
    const rowid = Number.parseInt(rowidStr, 10);
    const type = Number.parseInt(typeStr, 10);
    if (!Number.isFinite(rowid) || !Number.isFinite(type)) continue;
    const keyParts = key.split(":");
    const conversationId = keyParts.length >= 2 ? keyParts[1] : "";
    const bubbleId = keyParts.length >= 3 ? keyParts.slice(2).join(":") : "";
    rows.push({
      cursor: String(rowid),
      bubbleId,
      conversationId,
      type,
      text,
      createdAt,
    });
  }
  return rows;
}