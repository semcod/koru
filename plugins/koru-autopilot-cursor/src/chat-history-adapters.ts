/**
 * Cursor-only chat-history adapter factory.
 *
 * ``koru-autopilot-cursor`` is a Cursor-dedicated VSIX, so this file
 * only exposes the bubble-DB adapter. Sibling plugins
 * (``koru-autopilot-vscode``/``-vscodium``/``-windsurf``/``-antigravity``)
 * provide their own equivalents — keeping each IDE's adapter in its
 * own VSIX prevents a regression in one IDE's history reader from
 * cascading into another.
 */

import { CursorBubbleAdapter } from "./cursor-bubble-adapter";
import type { IdeAdapter, SupportedIde } from "./chat-history-types";
import { UnsupportedAdapter } from "./unsupported-chat-adapter";
import { VSCodeChatSessionAdapter, parseVSCodeChatIndex } from "./vscode-chat-session-adapter";

export { CursorBubbleAdapter, parseCursorBubbleRows } from "./cursor-bubble-adapter";
// Re-exported only to keep ``chat-history-watcher.ts`` (copied verbatim
// from the legacy plugin) typechecking. Cursor-only adapter is the
// sole adapter ever instantiated; see ``buildAdapterForIde`` below.
export { UnsupportedAdapter, VSCodeChatSessionAdapter, parseVSCodeChatIndex };

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {
  if (ide !== "cursor") {
    throw new Error(
      `koru-autopilot-cursor: unexpected IDE ${ide} requested in ` +
      "buildAdapterForIde — this VSIX only ships Cursor support."
    );
  }
  return new CursorBubbleAdapter({ ide });
}
