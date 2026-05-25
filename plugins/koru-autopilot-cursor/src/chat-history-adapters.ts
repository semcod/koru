import { CursorBubbleAdapter } from "./cursor-bubble-adapter";
import type { IdeAdapter, SupportedIde } from "./chat-history-types";
import { UnsupportedAdapter } from "./unsupported-chat-adapter";
import { VSCodeChatSessionAdapter } from "./vscode-chat-session-adapter";

export { CursorBubbleAdapter, parseCursorBubbleRows } from "./cursor-bubble-adapter";
export { UnsupportedAdapter } from "./unsupported-chat-adapter";
export { VSCodeChatSessionAdapter, parseVSCodeChatIndex } from "./vscode-chat-session-adapter";

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