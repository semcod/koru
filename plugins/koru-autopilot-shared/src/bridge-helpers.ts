// koru autopilot — shared bridge helpers
//
// IDE-agnostic helper functions for VS Code family plugins.

import { buildSubmitCommands } from "../probe-ladder";

const DISALLOWED_FOCUS_OPEN_COMMANDS = new Set([
  "workbench.action.chat.openagent",
  "workbench.action.chat.openask",
]);

const GLOBALLY_UNSAFE_FOCUS_OPEN_MARKERS = [
  "settings",
  "preferences",
];

const UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS = new Set([
  "workbench.action.openchat",
  "workbench.action.openquickchat",
  "workbench.action.chat.open",
  "workbench.action.chat.openchatemptystatesettings",
  "workbench.action.chat.focusinput",
  "workbench.action.chat.openinnewwindow",
  "workbench.action.chat.opensessioninnewwindow",
  "workbench.action.quickchat.openinchatview",
]);

const UNSAFE_ANTIGRAVITY_FOCUS_OPEN_COMMANDS = new Set([
  "antigravity.openagent",
]);

const UNSAFE_CURSOR_FOCUS_OPEN_COMMANDS = new Set([
  "workbench.panel.chat",
  "composer.openaspane",
  "aichat.newchataction",
  "workbench.action.toggleauxiliarybar",
  "workbench.view.chat.toggle",
  "workbench.panel.chat.view.copilot.focus",
  "workbench.panel.aichat.view.copilot.focus",
  "composer.focuscomposer",
]);

export function isAllowedFocusOpenCommand(command: unknown): command is string {
  return (
    typeof command === "string" &&
    command.trim().length > 0 &&
    !DISALLOWED_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()) &&
    !isGloballyUnsafeFocusOpenCommand(command)
  );
}

export function sanitizeFocusOpenCommand(command: unknown): string | undefined {
  if (!isAllowedFocusOpenCommand(command)) {
    return undefined;
  }
  return command.trim();
}

export function sanitizeFocusOpenCandidates(commands: readonly string[]): string[] {
  return commands.filter(isAllowedFocusOpenCommand);
}

export function filterUnsafeFocusOpenForIde(commands: readonly string[], ide: string): string[] {
  const globallySafe = commands.filter((command) => !isGloballyUnsafeFocusOpenCommand(command));
  const normalizedIde = ide.trim().toLowerCase();
  if (normalizedIde === "cursor") {
    return globallySafe.filter((command) => {
      const normalized = command.trim().toLowerCase();
      if (UNSAFE_CURSOR_FOCUS_OPEN_COMMANDS.has(normalized)) {
        return false;
      }
      return !normalized.includes("panel.chat.view") && !normalized.includes("panel.aichat.view");
    });
  }
  if (normalizedIde === "antigravity") {
    return globallySafe.filter(
      (command) => !UNSAFE_ANTIGRAVITY_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()),
    );
  }
  if (normalizedIde !== "vscode" && normalizedIde !== "vscodium") {
    return globallySafe;
  }
  return globallySafe.filter((command) => !UNSAFE_VSCODE_FOCUS_OPEN_COMMANDS.has(command.trim().toLowerCase()));
}

function isGloballyUnsafeFocusOpenCommand(command: string): boolean {
  const normalized = command.trim().toLowerCase();
  return GLOBALLY_UNSAFE_FOCUS_OPEN_MARKERS.some((marker) => normalized.includes(marker));
}

export function isSpecificChatInputFocusCommand(command: string | undefined): boolean {
  if (!command) {
    return false;
  }
  const normalized = command.toLowerCase();
  if (normalized.includes("openagent") || normalized.includes("openask") || normalized.includes("agentsidepanel.open")) {
    return false;
  }
  return normalized.includes("chat") || normalized.includes("composer") || normalized.includes("cascade") || normalized.includes("agent");
}

const TOGGLING_FOCUS_OPEN_COMMANDS: ReadonlySet<string> = new Set([
  "composer.openaspane",
  // Toggles the chat panel: when Composer is already visible this hides it
  // and the next paste/submit targets an invisible webview.
  "workbench.panel.chat",
  "workbench.action.toggleauxiliarybar",
  "workbench.action.togglepanel",
  "workbench.action.togglesidebar",
  "workbench.view.chat.toggle",
]);

export function isTogglingFocusOpenCommand(command: string | undefined): boolean {
  if (!command) {
    return false;
  }
  const normalized = command.trim().toLowerCase();
  if (TOGGLING_FOCUS_OPEN_COMMANDS.has(normalized)) {
    return true;
  }
  // Cursor panel view focus commands toggle visibility when the chat column is
  // already open — users see the Agent/Glass column briefly disappear.
  return normalized.includes("panel.chat.view") || normalized.includes("panel.aichat.view");
}

export function isVSCodiumSafeSubmitCommand(command: string): boolean {
  const normalized = command.trim().toLowerCase();
  if (buildSubmitCommands("vscodium").includes(command)) {
    return true;
  }
  return normalized.startsWith("workbench.action.chat.");
}

export function filterVSCodiumSubmitCandidates(commands: string[]): string[] {
  return commands.filter(isVSCodiumSafeSubmitCommand);
}

export function isHostClipboardPasteCommand(command: string | undefined): boolean {
  return Boolean(command && command.includes("host-clipboard"));
}
