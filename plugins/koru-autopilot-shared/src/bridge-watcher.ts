import * as vscode from "vscode";
import { SharedAutopilotBridgeNetwork } from "./bridge-network";
import { debugLog } from "./bridge-config";
import { CursorBubbleAdapter } from "../cursor-bubble-adapter";
import { cursorBubbleTextMatchesPrompt } from "./submit-match";

export abstract class SharedAutopilotBridgeWatcher extends SharedAutopilotBridgeNetwork {
  protected cursorBubbleAnchorRowid: number | null = null;
  protected cursorBubbleVerifierAdapter: CursorBubbleAdapter | null = null;

  protected abstract sleep(ms: number): Promise<void>;

  protected async _verifySubmitViaCursorBubble(
    originalText: string
  ): Promise<{ matched: boolean; newUserBubbles: number } | null> {
    const anchor = this.cursorBubbleAnchorRowid;
    if (anchor === null) {
      debugLog("CURSOR_BUBBLE_VERIFY_NO_ANCHOR");
      return null;
    }
    const adapter = this.cursorBubbleVerifierAdapter ?? new CursorBubbleAdapter({ ide: "cursor" });
    this.cursorBubbleVerifierAdapter = adapter;
    if (!adapter.storeAvailable()) {
      debugLog("CURSOR_BUBBLE_VERIFY_DB_UNAVAILABLE");
      return null;
    }
    const cfg = vscode.workspace.getConfiguration("koruAutopilot");
    const timeoutMs = Math.max(500, Math.trunc(cfg.get<number>("submitVerifyTimeoutMs", 4000)));
    const deadline = Date.now() + timeoutMs;
    let attempts = 0;
    let lastRows: number = 0;
    while (Date.now() <= deadline) {
      attempts += 1;
      let rows;
      try {
        rows = await adapter.fetchLatestUserBubbles(anchor, null);
      } catch (err) {
        debugLog("CURSOR_BUBBLE_VERIFY_QUERY_ERROR", { err: String(err) });
        return null;
      }
      lastRows = rows.length;
      for (const row of rows) {
        if (row.type !== 1 || typeof row.text !== "string") {
          continue;
        }
        const match = cursorBubbleTextMatchesPrompt(row.text, originalText);
        if (match.matched) {
          debugLog("CURSOR_BUBBLE_VERIFY_MATCH", {
            attempts,
            rowid: row.cursor,
            bubbleId: row.bubbleId,
            textLength: row.text.length,
            mode: match.mode,
          });
          return { matched: true, newUserBubbles: rows.length };
        }
      }
      await this.sleep(150);
    }
    debugLog("CURSOR_BUBBLE_VERIFY_NO_MATCH", {
      attempts,
      anchor,
      promptLength: originalText.trim().length,
      newUserBubbles: lastRows,
    });
    return { matched: false, newUserBubbles: lastRows };
  }

  protected async captureCursorBubbleAnchor(): Promise<void> {
    if (this.detectIde() !== "cursor") {
      this.cursorBubbleAnchorRowid = null;
      return;
    }
    const adapter = this.cursorBubbleVerifierAdapter ?? new CursorBubbleAdapter({ ide: "cursor" });
    this.cursorBubbleVerifierAdapter = adapter;
    if (!adapter.storeAvailable()) {
      this.cursorBubbleAnchorRowid = null;
      debugLog("CURSOR_BUBBLE_ANCHOR_DB_UNAVAILABLE");
      return;
    }
    try {
      this.cursorBubbleAnchorRowid = await adapter.latestBubbleRowid(null);
      debugLog("CURSOR_BUBBLE_ANCHOR_CAPTURED", {
        rowid: this.cursorBubbleAnchorRowid,
      });
    } catch (err) {
      this.cursorBubbleAnchorRowid = null;
      debugLog("CURSOR_BUBBLE_ANCHOR_ERROR", { err: String(err) });
    }
  }
}
