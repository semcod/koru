/**
 * VS Code-only chat-history adapter factory.
 */

import { CursorBubbleAdapter } from "./cursor-bubble-adapter";
import type { IdeAdapter, SupportedIde } from "./chat-history-types";
import { UnsupportedAdapter } from "./unsupported-chat-adapter";
import { VSCodeChatSessionAdapter } from "./vscode-chat-session-adapter";

export { CursorBubbleAdapter, parseCursorBubbleRows } from "./cursor-bubble-adapter";
export { UnsupportedAdapter } from "./unsupported-chat-adapter";
export { VSCodeChatSessionAdapter, parseVSCodeChatIndex } from "./vscode-chat-session-adapter";

export function buildAdapterForIde(ide: SupportedIde): IdeAdapter {
  if (ide !== "vscode") {
    throw new Error(
      `koru-autopilot-vscode: unexpected IDE ${ide} — this VSIX only ships VS Code support.`
    );
  }
  return new VSCodeChatSessionAdapter({ ide });
}
