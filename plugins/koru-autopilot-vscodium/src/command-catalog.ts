/**
 * Runtime IDE command catalog — classifies vscode.commands.getCommands(false)
 * into capability buckets for the koruide daemon / LLM command picker.
 */

export type CommandCapability =
  | "focus_open"
  | "focus_input"
  | "paste"
  | "submit"
  | "history"
  | "visibility"
  | "window"
  | "unknown_chat";

export interface CommandCatalog {
  focus_open: string[];
  focus_input: string[];
  paste: string[];
  submit: string[];
  history: string[];
  visibility: string[];
  window: string[];
  unknown_chat: string[];
}

export const COMMAND_CATALOG_CAPABILITIES: readonly CommandCapability[] = [
  "focus_open",
  "focus_input",
  "paste",
  "submit",
  "history",
  "visibility",
  "window",
  "unknown_chat",
] as const;

const CHAT_HINT =
  /(?:chat|composer|cascade|codeium|windsurf|aichat|copilot|agent|assistant)/i;

type Rule = { capability: CommandCapability; pattern: RegExp };

/** First matching rule wins (ordered most-specific → generic). */
const RULES: Rule[] = [
  { capability: "window", pattern: /(?:settings|preferences|reloadWindow|reloadExtensions|restartExtensionHost|newWindow|openFolder)/i },
  { capability: "history", pattern: /(?:chat.*history|clear.*chat|delete.*chat|reset.*chat)/i },
  {
    capability: "visibility",
    pattern: /(?:toggle.*(?:chat|composer|cascade|panel)|show.*panel|hide.*panel|close.*panel)/i,
  },
  {
    capability: "submit",
    pattern:
      /(?:sendToAgent|acceptComposerStep|\.submit$|\.send$|acceptInput|sendMessage|interactive\.accept)/i,
  },
  {
    capability: "paste",
    pattern:
      /(?:insertText|typeText|startComposerPrompt|clipboardPaste|\.paste$|sendTextToChat)/i,
  },
  {
    capability: "focus_input",
    pattern:
      /(?:focusInput|focusComposer|focus.*(?:chat|composer|cascade)|chat\.action\.focus|focusLastFocused)/i,
  },
  {
    capability: "focus_open",
    pattern:
      /(?:openComposer|showComposer|open.*(?:chat|composer|cascade|agent)|newchataction|panel\.chat|composer\.open|cascadePanel\.open)/i,
  },
];

function emptyCatalog(): CommandCatalog {
  return {
    focus_open: [],
    focus_input: [],
    paste: [],
    submit: [],
    history: [],
    visibility: [],
    window: [],
    unknown_chat: [],
  };
}

function pushUnique(bucket: string[], command: string): void {
  if (!bucket.includes(command)) {
    bucket.push(command);
  }
}

export function classifyCommand(command: string): CommandCapability | null {
  for (const rule of RULES) {
    if (rule.pattern.test(command)) {
      return rule.capability;
    }
  }
  if (CHAT_HINT.test(command)) {
    return "unknown_chat";
  }
  return null;
}

export function classifyCommands(allCommands: string[]): CommandCatalog {
  const catalog = emptyCatalog();
  for (const command of allCommands) {
    const capability = classifyCommand(command);
    if (capability) {
      pushUnique(catalog[capability], command);
    }
  }
  for (const capability of COMMAND_CATALOG_CAPABILITIES) {
    catalog[capability].sort();
  }
  return catalog;
}

export function matchingCommandsFlat(catalog: CommandCatalog): string[] {
  const out: string[] = [];
  for (const capability of COMMAND_CATALOG_CAPABILITIES) {
    for (const command of catalog[capability]) {
      pushUnique(out, command);
    }
  }
  return out;
}
