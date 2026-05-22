/**
 * Chat-history watcher → emits ``message.received`` events per IDE.
 *
 * The VS Code Extension API does NOT expose any public "chat response
 * finished" event for the IDE-side LLM panels (Cursor Composer, Windsurf
 * Cascade, Antigravity, VS Code Built-in Chat). Without such a signal the
 * koru daemon can only see what *koru* pasted (``message.sent``), never
 * what the IDE-side LLM answered, leaving ``koru.llm_reflect`` (the
 * OpenRouter-backed reflection layer) without input.
 *
 * This module bridges the gap by polling each IDE's local conversation
 * store and emitting newly observed assistant messages as
 * ``message.received`` events on the autopilot socket.
 *
 * Adapter coverage (status as of plugin 0.1.52)
 * --------------------------------------------
 * - **cursor** — full support. Reads ``cursorDiskKV`` table from
 *   ``~/.config/Cursor/User/globalStorage/state.vscdb`` (and platform
 *   equivalents); each ``bubbleId:<conv>:<uuid>`` row is JSON with
 *   ``type`` (``2`` = assistant) and ``text``.
 * - **vscode**, **vscodium** — best-effort support via VS Code's
 *   Built-in Chat API store: ``chat.ChatSessionStore.index`` (JSON) plus
 *   per-session payloads. Returns no rows when the user's chat surface is
 *   served by a third-party extension that maintains its own opaque
 *   storage (Copilot Chat, Continue, …).
 * - **windsurf**, **antigravity** — STUB. Both encrypt their conversation
 *   protobuf files at rest (``~/.codeium/windsurf/cascade/*.pb`` and
 *   ``~/.gemini/antigravity/conversations/*.pb``), so the plugin cannot
 *   read message text without reverse-engineering each vendor's secret.
 *   The watcher logs a one-line ``CHAT_HISTORY_UNSUPPORTED`` notice once
 *   and stays silent. The other anti-clobber guards (input-busy precheck,
 *   escalation cooldown) still protect these IDEs.
 *
 * Implementation notes
 * --------------------
 * - Shells out to the ``sqlite3`` CLI to avoid adding a native dep
 *   (``better-sqlite3`` would require per-arch prebuilt binaries which
 *   complicate the .vsix package and break on minimal distros).
 * - Polls at a configurable interval (default 4 s); fail-closed on every
 *   error (missing CLI, schema drift, parse failure) — never crash the
 *   extension host.
 * - Adapter state (highest seen rowid for SQLite-backed adapters,
 *   per-file mtime+size cursor for filesystem adapters) is persisted via
 *   the caller-supplied ``initialCursor`` and ``onCursorAdvance`` hook.
 */

import * as cp from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { promisify } from "util";

const execFile = promisify(cp.execFile);

export type SupportedIde = "cursor" | "vscode" | "vscodium" | "windsurf" | "antigravity";

export interface ChatHistoryRow {
  /**
   * Monotonic position identifier. SQLite adapters use ``rowid``;
   * filesystem adapters use ``<mtimeMs>-<basename>``. Used by the watcher
   * to skip already-emitted rows after restart.
   */
  cursor: string;
  bubbleId: string;
  conversationId: string;
  type: number;
  text: string;
  createdAt: string;
}

export interface AdapterRunner {
  (binary: string, args: string[]): Promise<{ stdout: string; stderr: string }>;
}

export interface IdeAdapter {
  readonly ide: SupportedIde;
  /** Human description used in debug logs only. */
  readonly description: string;
  /**
   * Return rows newer than ``afterCursor`` (or all rows when ``""``),
   * oldest first. Must never throw — fail-closed and return ``[]``.
   */
  fetchNewer(afterCursor: string, runner: AdapterRunner | null): Promise<ChatHistoryRow[]>;
  /** True when the underlying store exists; controls whether we poll at all. */
  storeAvailable(): boolean;
}

// =====================================================================
// Path resolution
// =====================================================================

/** Return the per-IDE ``User`` base directory (parent of ``globalStorage``). */
export function ideUserDir(ide: SupportedIde): string {
  const home = os.homedir();
  const folderByIde: Record<SupportedIde, string> = {
    cursor: "Cursor",
    vscode: "Code",
    vscodium: "VSCodium",
    windsurf: "Windsurf",
    antigravity: "Antigravity",
  };
  const name = folderByIde[ide];
  if (process.platform === "darwin") {
    return path.join(home, "Library", "Application Support", name, "User");
  }
  if (process.platform === "win32") {
    const appdata = process.env.APPDATA || path.join(home, "AppData", "Roaming");
    return path.join(appdata, name, "User");
  }
  return path.join(home, ".config", name, "User");
}

export function defaultGlobalStateDbPath(ide: SupportedIde): string {
  return path.join(ideUserDir(ide), "globalStorage", "state.vscdb");
}

// =====================================================================
// Cursor (and Cursor-family) adapter — SQLite cursorDiskKV.bubbleId
// =====================================================================

const SQL_CURSOR_NEW_BUBBLES = `SELECT rowid, key, json_extract(value,'$.type'), json_extract(value,'$.text'), json_extract(value,'$.createdAt')
FROM cursorDiskKV
WHERE key LIKE 'bubbleId:%'
  AND rowid > ?
  AND json_extract(value,'$.type') = 2
  AND length(json_extract(value,'$.text')) > 0
ORDER BY rowid ASC
LIMIT 50;`;

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
    const args = [
      "-readonly",
      "-bail",
      "-noheader",
      "-cmd",
      ".separator \\x1f \\x1e",
      this.dbPath,
      SQL_CURSOR_NEW_BUBBLES.replace("?", String(lastRowid)),
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

// =====================================================================
// VS Code / VSCodium adapter — Built-in Chat API session store
// =====================================================================

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
 *
 * Returns no rows when the user's chat surface is served by a
 * third-party extension that maintains its own opaque storage (Copilot
 * Chat, Continue, …).
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

export function parseVSCodeChatIndex(jsonText: string, afterCursor: string): ChatHistoryRow[] {
  const trimmed = jsonText.trim();
  if (!trimmed) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return [];
  }
  if (!parsed || typeof parsed !== "object") return [];
  const entriesRaw = (parsed as { entries?: unknown }).entries;
  if (!entriesRaw || typeof entriesRaw !== "object") return [];
  const after = Number.parseFloat(afterCursor || "0") || 0;
  const rows: ChatHistoryRow[] = [];
  for (const [sessionId, entryRaw] of Object.entries(entriesRaw as Record<string, unknown>)) {
    if (!entryRaw || typeof entryRaw !== "object") continue;
    const entry = entryRaw as VSCodeChatSessionEntry;
    const responses = Array.isArray(entry.responses) ? entry.responses : [];
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

// =====================================================================
// Stub adapter for IDEs whose conversation store is encrypted/unknown
// =====================================================================

export class UnsupportedAdapter implements IdeAdapter {
  readonly ide: SupportedIde;
  readonly description: string;
  constructor(ide: SupportedIde, description: string) {
    this.ide = ide;
    this.description = description;
  }
  storeAvailable(): boolean {
    return false;
  }
  async fetchNewer(): Promise<ChatHistoryRow[]> {
    return [];
  }
}

// =====================================================================
// Adapter selector
// =====================================================================

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {
  switch (ide) {
    case "cursor":
      return new CursorBubbleAdapter({ ide });
    case "vscode":
    case "vscodium":
      return new VSCodeChatSessionAdapter({ ide });
    case "windsurf":
      return new UnsupportedAdapter(
        "windsurf",
        "Cascade conversations are stored encrypted at ~/.codeium/windsurf/cascade/*.pb; "
          + "no readable text. Input-busy precheck and escalation cooldown still apply.",
      );
    case "antigravity":
      return new UnsupportedAdapter(
        "antigravity",
        "Antigravity conversations are stored encrypted at ~/.gemini/antigravity/conversations/*.pb; "
          + "no readable text. Input-busy precheck and escalation cooldown still apply.",
      );
  }
}

// =====================================================================
// Watcher
// =====================================================================

export interface ChatHistoryWatcherOptions {
  ide: SupportedIde;
  /** Override the adapter (tests). */
  adapter?: IdeAdapter;
  pollIntervalMs?: number;
  /** Cursor to resume from across reloads (opaque per-adapter string). */
  initialCursor?: string;
  onMessage: (row: ChatHistoryRow) => boolean | void | Promise<boolean | void>;
  /**
   * Called whenever the watcher advances its persisted cursor; use to
   * persist across reloads (e.g. ``context.globalState.update``).
   */
  onCursorAdvance?: (cursor: string) => void | Promise<void>;
  log?: (msg: string, data?: unknown) => void;
  runner?: AdapterRunner;
}

export class ChatHistoryWatcher {
  private timer: NodeJS.Timeout | null = null;
  private polling = false;
  private cursor: string;
  private readonly adapter: IdeAdapter;
  private readonly opts: Required<Pick<ChatHistoryWatcherOptions, "pollIntervalMs" | "onMessage">> & {
    onCursorAdvance?: ChatHistoryWatcherOptions["onCursorAdvance"];
    log: NonNullable<ChatHistoryWatcherOptions["log"]>;
    runner: AdapterRunner | null;
  };
  private unsupportedLogged = false;

  constructor(options: ChatHistoryWatcherOptions) {
    this.adapter = options.adapter ?? buildAdapterForIde(options.ide);
    this.cursor = options.initialCursor ?? "";
    this.opts = {
      pollIntervalMs: Math.max(500, options.pollIntervalMs ?? 4000),
      onMessage: options.onMessage,
      onCursorAdvance: options.onCursorAdvance,
      log: options.log ?? (() => {}),
      runner: options.runner ?? null,
    };
  }

  get currentCursor(): string {
    return this.cursor;
  }

  get adapterDescription(): string {
    return this.adapter.description;
  }

  setCursor(cursor: string): void {
    if (typeof cursor === "string") this.cursor = cursor;
  }

  start(): void {
    if (this.timer) return;
    if (!this.adapter.storeAvailable()) {
      if (!this.unsupportedLogged) {
        this.opts.log("CHAT_HISTORY_UNSUPPORTED", {
          ide: this.adapter.ide,
          description: this.adapter.description,
        });
        this.unsupportedLogged = true;
      }
      return;
    }
    const tick = async (): Promise<void> => {
      if (this.polling) return;
      this.polling = true;
      try {
        await this.pollOnce();
      } finally {
        this.polling = false;
      }
    };
    this.timer = setInterval(() => void tick(), this.opts.pollIntervalMs);
    void tick();
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /** Run one poll iteration. Public for tests. */
  async pollOnce(): Promise<ChatHistoryRow[]> {
    if (!this.adapter.storeAvailable()) return [];
    let rows: ChatHistoryRow[] = [];
    try {
      rows = await this.adapter.fetchNewer(this.cursor, this.opts.runner);
    } catch (err) {
      this.opts.log("CHAT_HISTORY_POLL_ERROR", { err: String(err), ide: this.adapter.ide });
      return [];
    }
    if (!rows.length) return rows;
    for (const row of rows) {
      let verdict: boolean | void = undefined;
      try {
        verdict = await this.opts.onMessage(row);
      } catch (err) {
        this.opts.log("CHAT_HISTORY_DELIVERY_ERROR", {
          err: String(err),
          cursor: row.cursor,
          ide: this.adapter.ide,
        });
      }
      if (verdict === false) {
        return rows;
      }
      if (cursorAdvances(this.cursor, row.cursor)) {
        this.cursor = row.cursor;
        if (this.opts.onCursorAdvance) {
          try {
            await this.opts.onCursorAdvance(this.cursor);
          } catch {
            /* persistence is best-effort */
          }
        }
      }
    }
    return rows;
  }
}

function cursorAdvances(prev: string, next: string): boolean {
  const a = Number.parseFloat(prev || "0");
  const b = Number.parseFloat(next || "0");
  if (Number.isFinite(a) && Number.isFinite(b)) {
    return b > a;
  }
  return next > prev;
}
