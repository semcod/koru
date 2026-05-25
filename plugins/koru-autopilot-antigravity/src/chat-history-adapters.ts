/**
 * Antigravity-only chat-history adapter factory.
 */

import { CursorBubbleAdapter } from "./cursor-bubble-adapter";
import type { IdeAdapter, SupportedIde } from "./chat-history-types";
import { UnsupportedAdapter } from "./unsupported-chat-adapter";
import { VSCodeChatSessionAdapter } from "./vscode-chat-session-adapter";

export { CursorBubbleAdapter, parseCursorBubbleRows } from "./cursor-bubble-adapter";
export { UnsupportedAdapter } from "./unsupported-chat-adapter";
export { VSCodeChatSessionAdapter, parseVSCodeChatIndex } from "./vscode-chat-session-adapter";

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {
  if (ide !== "antigravity") {
    throw new Error(
      `koru-autopilot-antigravity: unexpected IDE ${ide} — this VSIX only ships Antigravity support.`
    );
  }
  return new UnsupportedAdapter(
    "antigravity",
    "Antigravity conversations are stored encrypted; no readable text.",
  );
}
