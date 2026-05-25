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