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

import { buildAdapterForIde } from "../chat-history-adapters";
import type { AdapterRunner, ChatHistoryRow, IdeAdapter, SupportedIde } from "./chat-history-types";

export { buildAdapterForIde } from "../chat-history-adapters";
export {
  CursorBubbleAdapter,
  parseCursorBubbleRows,
  UnsupportedAdapter,
  VSCodeChatSessionAdapter,
  parseVSCodeChatIndex,
} from "../chat-history-adapters";
export { defaultGlobalStateDbPath, ideUserDir } from "./chat-history-paths";
export type { AdapterRunner, ChatHistoryRow, IdeAdapter, SupportedIde } from "./chat-history-types";

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
